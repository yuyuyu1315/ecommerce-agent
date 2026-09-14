"""Agent API 路由：选品分析 / 选品记录 / Agent 任务"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import ProductSelectionAgent
from backend.database import get_db
from backend.models import AgentTask, ProductSelection

router = APIRouter()

_agent: Optional[ProductSelectionAgent] = None


def get_agent() -> ProductSelectionAgent:
    """懒加载选品 Agent（构造时校验 API Key）"""
    global _agent
    if _agent is None:
        _agent = ProductSelectionAgent()
    return _agent


class AnalyzeRequest(BaseModel):
    """选品分析请求体"""

    category: str = Field("", description="品类关键词，如：连衣裙")
    product_name: str = Field("", description="产品名称关键词（可选）")
    params: dict = Field(default_factory=dict, description="附加参数，如 user_id / 预算")


@router.post("/selection/analyze")
async def analyze_selection(req: AnalyzeRequest):
    """运行一次选品分析（调用 DeepSeek，结果写入 product_selections）"""
    if not req.category and not req.product_name:
        raise HTTPException(status_code=422, detail="请提供 category 或 product_name 至少一个")
    try:
        agent = get_agent()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return await agent.analyze(req.category, req.product_name, req.params)


@router.get("/selection")
async def list_selections(
    status: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """选品记录列表（可按状态过滤：pending / approved / rejected）"""
    stmt = select(ProductSelection).order_by(ProductSelection.id.desc())
    if status:
        stmt = stmt.where(ProductSelection.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "success": True,
        "count": len(rows),
        "selections": [
            {
                "id": r.id,
                "product_name": r.product_name,
                "category": r.category,
                "selection_reason": r.selection_reason,
                "confidence_score": r.confidence_score,
                "estimated_margin": r.estimated_margin,
                "estimated_sales": r.estimated_sales,
                "estimated_revenue": r.estimated_revenue,
                "risk_level": r.risk_level,
                "status": r.status,
                "priority": r.priority,
                "created_at": str(r.created_at),
            }
            for r in rows
        ],
    }


@router.post("/selection/{selection_id}/approve")
async def approve_selection(selection_id: int, db: AsyncSession = Depends(get_db)):
    """审批通过一条选品建议"""
    record = await db.get(ProductSelection, selection_id)
    if not record:
        raise HTTPException(status_code=404, detail="选品记录不存在")
    record.status = "approved"
    record.priority = max(1, min((record.priority or 5) - 1, 10))
    await db.commit()
    return {"success": True, "message": f"已通过选品「{record.product_name}」", "id": record.id}


@router.get("/tasks")
async def list_agent_tasks(
    task_type: Optional[str] = None, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """Agent 任务记录列表（含耗时/token 用量）"""
    stmt = select(AgentTask).order_by(AgentTask.id.desc()).limit(min(max(limit, 1), 100))
    if task_type:
        stmt = select(AgentTask).where(AgentTask.task_type == task_type).order_by(AgentTask.id.desc()).limit(min(max(limit, 1), 100))
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "success": True,
        "count": len(rows),
        "tasks": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "agent_name": t.agent_name,
                "status": t.status,
                "progress": t.progress,
                "tokens_used": t.tokens_used,
                "duration_ms": t.duration_ms,
                "error_message": t.error_message,
                "input_data": t.input_data,
                "output_data": t.output_data,
                "created_at": str(t.created_at),
            }
            for t in rows
        ],
    }
