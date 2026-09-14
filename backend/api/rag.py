"""RAG API 路由：知识库问答 / 文档列表 / 重建索引"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import KnowledgeBase
from backend.rag import rag_engine

router = APIRouter()


class QueryRequest(BaseModel):
    """RAG 问答请求体"""

    question: str = Field(..., description="问题，如：如何做好电商选品？")
    top_k: int = Field(4, ge=1, le=10, description="检索文档数量")


@router.post("/query")
async def rag_query(req: QueryRequest):
    """RAG 问答：向量检索知识库 → DeepSeek 结合资料回答"""
    if not req.question.strip():
        return {"success": False, "error": "问题不能为空"}
    return await rag_engine.answer(req.question, req.top_k)


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """知识库文档列表"""
    rows = (
        (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.id)))
        .scalars()
        .all()
    )
    return {
        "success": True,
        "count": len(rows),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "summary": d.summary,
                "source": d.source,
                "word_count": d.word_count,
            }
            for d in rows
        ],
    }


@router.post("/rebuild")
async def rebuild_index():
    """从数据库重建向量索引（知识库文档 + 产品数据）"""
    return await rag_engine.rebuild()
