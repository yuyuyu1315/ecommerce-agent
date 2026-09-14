"""定价 Agent API：定价分析 / 建议列表 / 审批生效 / 驳回"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import PricingAgent
from backend.database import get_db
from backend.models import PriceSuggestion

router = APIRouter()

_agent: Optional[PricingAgent] = None


def get_agent() -> PricingAgent:
    """懒加载定价 Agent"""
    global _agent
    if _agent is None:
        _agent = PricingAgent()
    return _agent


class PricingRequest(BaseModel):
    """定价分析请求体"""

    product_id: int = Field(..., description="产品 ID")
    params: dict = Field(default_factory=dict, description="附加参数，如 user_id / target_margin")


@router.post("/pricing/analyze")
async def analyze_pricing(req: PricingRequest):
    """对指定产品执行一次 AI 定价分析（结果写入 price_suggestions）"""
    try:
        agent = get_agent()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return await agent.analyze(req.product_id, req.params)


@router.get("/pricing")
async def list_suggestions(
    status: Optional[str] = None, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """定价建议列表（可按状态过滤：pending / approved / rejected）"""
    stmt = select(PriceSuggestion).order_by(PriceSuggestion.id.desc()).limit(min(max(limit, 1), 200))
    if status:
        stmt = stmt.where(PriceSuggestion.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "success": True,
        "count": len(rows),
        "suggestions": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "product_name": r.product_name,
                "current_price": r.current_price,
                "recommended_price": r.recommended_price,
                "price_change_percent": r.price_change_percent,
                "strategy": r.strategy,
                "margin_percent_after": r.margin_percent_after,
                "confidence_score": r.confidence_score,
                "reason": r.reason,
                "risk_level": r.risk_level,
                "status": r.status,
                "created_at": str(r.created_at),
            }
            for r in rows
        ],
    }


@router.post("/pricing/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: int, db: AsyncSession = Depends(get_db)):
    """审批通过定价建议（更新产品售价 + 写入价格历史）"""
    agent = get_agent()
    result = await agent.approve(suggestion_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pricing/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: int):
    """驳回定价建议"""
    agent = get_agent()
    result = await agent.reject(suggestion_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
