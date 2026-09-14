"""选品 Agent：分析品类/产品 → 产出结构化选品建议并落库"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select

from backend.agents.base import BaseAgent
from backend.database import AsyncSessionLocal
from backend.models import (
    AgentTask,
    Category,
    CompetitorPrice,
    KnowledgeBase,
    Product,
    ProductSelection,
)

SELECTION_SYSTEM_PROMPT = """你是一位资深的电商选品专家，拥有丰富的市场分析与产品判断经验。
你的任务是基于提供的产品/市场数据，输出一份专业、可执行的选品分析建议。
必须严格按 JSON 格式输出，不要输出 JSON 以外的任何文字。"""


class ProductSelectionAgent(BaseAgent):
    """选品分析 Agent（对应文档 agents/selection.py）"""

    name = "ProductSelectionAgent"

    async def analyze(
        self,
        category: str = "",
        product_name: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行一次选品分析并落库

        Args:
            category: 品类关键词，如「连衣裙」
            product_name: 具体产品名称关键词（与 category 二选一或组合）
            params: 附加参数（user_id、预算、目标客群等）
        """
        params = params or {}
        session = AsyncSessionLocal()

        # 1. 建任务记录
        task = AgentTask(
            task_type="selection",
            agent_name=self.name,
            input_data={"category": category, "product_name": product_name, "params": params},
            status="running",
            progress=10,
            user_id=params.get("user_id"),
            started_at=datetime.now(timezone.utc),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        start = time.perf_counter()

        try:
            # 2. 组装上下文（产品数据 + 竞品 + 知识库）
            context = await self._build_context(session, category, product_name)
            if not context["products"]:
                raise ValueError(
                    f"未找到与「{category or product_name}」相关的产品数据，请换一个品类关键词"
                )

            # 3. 调用 LLM
            user_prompt = self._build_prompt(category, product_name, params, context)
            result, usage = await self.ainvoke_json(SELECTION_SYSTEM_PROMPT, user_prompt)
            result.pop("_meta", None)
            normalized = self._normalize_result(result)

            # 4. 落库（同名 pending 记录则更新）
            record = await self._save_selection(session, normalized, params.get("user_id"))

            # 5. 更新任务状态
            task.status = "completed"
            task.progress = 100
            task.output_data = normalized
            task.tokens_used = (usage or {}).get("total_tokens")
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {"success": True, "analysis": normalized, "record_id": record.id}

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

    async def _build_context(self, session, category: str, product_name: str) -> Dict[str, Any]:
        """构建送入 LLM 的上下文：产品/竞品/评价/知识库摘要"""
        # 产品 + 分类
        stmt = select(Product, Category.name).join(Category, Product.category_id == Category.id)
        if category:
            stmt = stmt.where(
                or_(
                    Category.name.like(f"%{category}%"),
                    Product.name.like(f"%{category}%"),
                )
            )
        elif product_name:
            stmt = stmt.where(Product.name.like(f"%{product_name}%"))
        else:
            stmt = stmt.order_by(Product.sales_month.desc()).limit(10)

        rows = (await session.execute(stmt)).all()

        products = []
        for p, cat_name in rows[:10]:
            comps = (
                (
                    await session.execute(
                        select(CompetitorPrice)
                        .where(CompetitorPrice.product_id == p.id)
                        .order_by(CompetitorPrice.fetched_at.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            products.append(
                {
                    "name": p.name,
                    "sku": p.sku,
                    "category": cat_name,
                    "cost_price": p.cost_price,
                    "current_price": p.current_price,
                    "stock": p.stock_quantity,
                    "sales_month": p.sales_month,
                    "rating": p.rating,
                    "review_count": p.review_count,
                    "positive_rate": p.positive_rate,
                    "competitors": [
                        {"name": c.competitor_name, "platform": c.platform, "price": c.price}
                        for c in comps
                    ],
                }
            )

        # 知识库（选品相关）
        docs = (
            (
                await session.execute(
                    select(KnowledgeBase)
                    .where(KnowledgeBase.category.like("%选品%"))
                    .where(KnowledgeBase.is_active.is_(True))
                    .limit(3)
                )
            )
            .scalars()
            .all()
        )
        knowledge = [
            {"title": d.title, "category": d.category, "summary": d.summary, "content": d.content[:400]}
            for d in docs
        ]

        return {"products": products, "knowledge": knowledge}

    def _build_prompt(self, category, product_name, params, context) -> str:
        products_json = self._safe_json(context["products"])
        knowledge_json = self._safe_json(context["knowledge"])
        extra = self._safe_json(params) if params else "{}"
        return f"""【任务】电商选品分析

【用户输入】
- 品类：{category or "（未指定）"}
- 产品：{product_name or "（未指定）"}
- 附加要求：{extra}

【现有产品与市场数据】
{products_json}

【选品知识库参考】
{knowledge_json}

【输出要求】
输出 JSON，字段如下（务必全部给出）：
{{
  "product_name": "推荐选品名称（从现有产品中选择最值得上架的，或基于数据提出新品名）",
  "category": "所属品类",
  "selection_reason": "选品理由（结合数据，150字内）",
  "confidence_score": 0.0,  // 置信度 0~1
  "estimated_margin_percent": 0.0,  // 预估毛利率 %
  "estimated_sales": 0,  // 预估月销量
  "estimated_revenue": 0.0,  // 预估月销售额
  "risk_level": "low",  // low / medium / high
  "risk_factors": ["风险1", "风险2"],
  "opportunity_factors": ["机会1", "机会2"],
  "priority": 5  // 优先级 1~10
}}"""

    def _normalize_result(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """规整 LLM 输出为可落库字段"""
        try:
            confidence = round(float(raw.get("confidence_score", 0)), 2)
        except (TypeError, ValueError):
            confidence = 0.0
        try:
            margin = round(float(raw.get("estimated_margin_percent", 0)), 2)
        except (TypeError, ValueError):
            margin = 0.0

        risk = str(raw.get("risk_level", "medium")).strip().lower()
        if risk not in ("low", "medium", "high"):
            risk = "medium"

        return {
            "product_name": str(raw.get("product_name", "")).strip() or "未命名选品",
            "category": str(raw.get("category", "")).strip(),
            "selection_reason": str(raw.get("selection_reason", "")).strip(),
            "confidence_score": min(max(confidence, 0.0), 1.0),
            "estimated_margin": margin,
            "estimated_sales": int(raw.get("estimated_sales") or 0),
            "estimated_revenue": float(raw.get("estimated_revenue") or 0),
            "risk_level": risk,
            "risk_factors": raw.get("risk_factors") or [],
            "opportunity_factors": raw.get("opportunity_factors") or [],
            "status": "pending",
            "priority": min(max(int(raw.get("priority") or 5), 1), 10),
        }

    async def _save_selection(
        self, session, data: Dict[str, Any], user_id: Optional[int]
    ) -> ProductSelection:
        """写入 product_selections（同名 pending 记录则更新，避免重复）"""
        stmt = select(ProductSelection).where(
            ProductSelection.product_name == data["product_name"],
            ProductSelection.status == "pending",
        )
        record = (await session.execute(stmt)).scalars().first()
        if record:
            for k, v in data.items():
                setattr(record, k, v)
            record.created_by = user_id or record.created_by
        else:
            record = ProductSelection(**data, created_by=user_id)
            session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    def _safe_json(obj) -> str:
        try:
            import json

            return json.dumps(obj, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return "[]"
