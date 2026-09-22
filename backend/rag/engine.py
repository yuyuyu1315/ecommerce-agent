"""RAG 检索问答引擎：ChromaDB 向量检索 + DeepSeek 生成（RAG 全流程）"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.config import get_settings
from backend.database import AsyncSessionLocal
from backend.models import AgentTask, Category, KnowledgeBase, Product

RAG_SYSTEM_PROMPT = """你是一个专业的电商运营知识助手。请基于【参考资料】回答问题，严格遵守：
1. 引用资料时标注来源，格式【来源：文档标题】；
2. 参考资料不足以回答时，直接说明"资料中未找到相关内容"，不要编造；
3. 回答简洁专业，可使用分点；必要时给出可直接执行的操作建议。"""

# V3 优化（评测驱动）：来源加权。
# V2 分类型混合检索后，300 条商品文档与查询的余弦相似度常高于知识库业务文档，
# 导致方法论文档仍被挤出 top-k（命中率 66.7% 未提升）。
# 业务方法论属权威来源，按类型加权后融合排序（knowledge ×1.25 / product ×1.0）。
SOURCE_WEIGHT = {"knowledge": 1.25, "product": 1.0}


class RagEngine:
    """RAG 引擎：建索引 → 向量检索 → 增强提示 → DeepSeek 生成"""

    def __init__(self):
        self.settings = get_settings()
        self.client = chromadb.PersistentClient(path=self.settings.VECTOR_DB_PATH)
        self.embedder = DefaultEmbeddingFunction()  # ONNX MiniLM（384 维）
        self.collection = self.client.get_or_create_collection(
            name="knowledge",
            embedding_function=self.embedder,
            metadata={"hnsw:space": "cosine"},
        )
        self._agent = BaseAgent()
        self._agent.name = "RagAgent"

    # ---------- 索引 ----------

    async def rebuild(self) -> Dict[str, Any]:
        """从 SQLite 全量重建向量索引（知识库文档 + 产品数据）"""
        session = AsyncSessionLocal()
        try:
            docs = (
                (
                    await session.execute(
                        select(KnowledgeBase).where(KnowledgeBase.is_active.is_(True))
                    )
                )
                .scalars()
                .all()
            )
            prod_rows = (
                (
                    await session.execute(
                        select(Product, Category.name)
                        .outerjoin(Category, Product.category_id == Category.id)
                        .where(Product.status == "active")
                    )
                )
                .all()
            )

            ids: List[str] = []
            documents: List[str] = []
            metadatas: List[Dict[str, str]] = []

            for d in docs:
                ids.append(f"kb-{d.id}")
                documents.append(f"{d.title}\n{d.summary or ''}\n{d.content}")
                metadatas.append(
                    {
                        "type": "knowledge",
                        "title": d.title,
                        "category": d.category,
                        "source": d.source or "",
                    }
                )

            for p, cat_name in prod_rows:
                ids.append(f"prod-{p.id}")
                documents.append(
                    f"{p.name} 分类：{cat_name or ''}；售价 {p.current_price} 元，成本 {p.cost_price} 元，"
                    f"月销 {p.sales_month} 件，评分 {p.rating}，好评率 {p.positive_rate}%；"
                    f"库存 {p.stock_quantity}（安全库存 {p.safety_stock}）。"
                )
                metadatas.append(
                    {"type": "product", "title": p.name, "category": cat_name or "", "source": "产品数据库"}
                )

            # 重建集合
            self.client.delete_collection("knowledge")
            self.collection = self.client.create_collection(
                name="knowledge",
                embedding_function=self.embedder,
                metadata={"hnsw:space": "cosine"},
            )
            if ids:
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

            return {
                "success": True,
                "indexed": len(ids),
                "knowledge_docs": len(docs),
                "product_docs": len(prod_rows),
            }
        finally:
            await session.close()

    # ---------- 检索 ----------

    def retrieve(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """向量检索 top-k 文档

        V2→V3 优化（评测驱动）：
        初版 top-4 检索，商品文档（描述相似度高）挤占名额，知识库无法召回（命中率 66.7%）；
        V2 分类型混合检索后，商品文档余弦相似度仍普遍高于知识库文档，top-k 依然被商品挤占；
        V3 引入来源加权：知识库（业务方法论，权威来源）×1.25，商品（数据条目，参考来源）×1.0，
        加权后融合排序取 top-k。
        """
        if self.collection.count() == 0:
            return []
        merged: List[Dict[str, Any]] = []
        for type_filter in ("knowledge", "product"):
            try:
                res = self.collection.query(
                    query_texts=[query], n_results=k, where={"type": type_filter}
                )
                for i, doc_id in enumerate(res["ids"][0]):
                    meta = res["metadatas"][0][i]
                    merged.append(
                        {
                            "id": doc_id,
                            "title": meta.get("title", doc_id),
                            "category": meta.get("category", ""),
                            "type": meta.get("type", ""),
                            "content": res["documents"][0][i][:800],
                            "score": round(
                                (1 - res["distances"][0][i]) * SOURCE_WEIGHT.get(type_filter, 1.0), 4
                            ),
                        }
                    )
            except Exception:  # noqa: BLE001
                continue
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:k]

    # ---------- 问答 ----------

    async def answer(self, question: str, top_k: int = 4) -> Dict[str, Any]:
        """RAG 问答：检索 → 增强 → 生成，并记录 AgentTask"""
        session = AsyncSessionLocal()
        task = AgentTask(
            task_type="rag",
            agent_name="RagAgent",
            input_data={"question": question, "top_k": top_k},
            status="running",
            progress=10,
            started_at=datetime.now(timezone.utc),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        start = time.perf_counter()

        try:
            sources = self.retrieve(question, top_k)
            if not sources:
                raise ValueError("知识库尚未建立索引，请先调用 POST /api/rag/rebuild")

            context = "\n\n".join(
                f"[{i + 1}] 标题：{s['title']}（分类：{s['category'] or '未分类'}）\n{s['content']}"
                for i, s in enumerate(sources)
            )
            answer_text, usage = await self._agent.ainvoke_text(
                RAG_SYSTEM_PROMPT,
                f"【参考资料】\n{context}\n\n【问题】\n{question}",
            )

            task.status = "completed"
            task.progress = 100
            task.output_data = {
                "answer": answer_text[:500],
                "sources": [s["title"] for s in sources],
            }
            task.tokens_used = (usage or {}).get("total_tokens")
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {"success": True, "answer": answer_text, "sources": sources}

        except Exception as e:  # noqa: BLE001
            task.status = "failed"
            task.error_message = str(e)[:500]
            task.progress = 0
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return {"success": False, "error": str(e)}

        finally:
            await session.close()


# 全局单例（启动时由 lifespan 调用 rebuild）
rag_engine = RagEngine()
