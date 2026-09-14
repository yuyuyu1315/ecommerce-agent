"""营销 Agent API：活动列表 / 活动详情 / 策划分析 / 营销内容"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import MarketingAgent
from backend.database import get_db
from backend.models import Campaign, CampaignProduct, MarketingContent, Product

router = APIRouter()

_agent: Optional[MarketingAgent] = None


def get_agent() -> MarketingAgent:
    """懒加载营销 Agent"""
    global _agent
    if _agent is None:
        _agent = MarketingAgent()
    return _agent


class MarketingRequest(BaseModel):
    """营销策划请求体"""

    campaign_id: int = Field(..., description="活动 ID")
    params: dict = Field(default_factory=dict, description="附加参数，如 user_id / 预算上限")


def _campaign_dict(c: Campaign, contents_count: int = 0) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "campaign_type": c.campaign_type,
        "description": c.description,
        "goal": c.goal,
        "target_audience": c.target_audience,
        "strategy_summary": c.strategy_summary,
        "discount_type": c.discount_type,
        "discount_value": c.discount_value,
        "budget": c.budget,
        "expected_revenue": c.expected_revenue,
        "expected_roi": c.expected_roi,
        "start_date": str(c.start_date) if c.start_date else None,
        "end_date": str(c.end_date) if c.end_date else None,
        "status": c.status,
        "contents_count": contents_count,
        "duration_display": c.duration_display,
        "discount_display": c.discount_display,
    }


@router.get("/marketing/campaigns")
async def list_campaigns(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """营销活动列表（含 AI 生成内容数量）"""
    stmt = select(Campaign).order_by(Campaign.id.desc())
    if status:
        stmt = stmt.where(Campaign.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    counts = {}
    if rows:
        cids = [c.id for c in rows]
        cnt_rows = (
            await db.execute(
                select(MarketingContent.campaign_id, MarketingContent.id)
                .where(MarketingContent.campaign_id.in_(cids))
            )
        ).all()
        for cid, _ in cnt_rows:
            counts[cid] = counts.get(cid, 0) + 1
    return {
        "success": True,
        "count": len(rows),
        "campaigns": [_campaign_dict(c, counts.get(c.id, 0)) for c in rows],
    }


@router.get("/marketing/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """活动详情（含营销内容与参与产品）"""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="活动不存在")

    # 显式查询关联数据，避免异步关系懒加载
    contents = (
        (
            await db.execute(
                select(MarketingContent)
                .where(MarketingContent.campaign_id == campaign_id)
                .order_by(MarketingContent.id.desc())
            )
        )
        .scalars()
        .all()
    )
    cp_rows = (
        (
            await db.execute(
                select(CampaignProduct, Product)
                .join(Product, CampaignProduct.product_id == Product.id)
                .where(CampaignProduct.campaign_id == campaign_id)
            )
        )
        .all()
    )
    products = []
    for cp, p in cp_rows:
        products.append(
            {
                "product_id": p.id,
                "name": p.name,
                "price": p.current_price,
                "discount_percent": cp.discount_percent,
                "final_price": cp.final_price,
                "is_featured": cp.is_featured,
            }
        )

    return {
        "success": True,
        "campaign": _campaign_dict(campaign, len(contents)),
        "products": products,
        "contents": [
            {
                "id": c.id,
                "content_type": c.content_type,
                "platform": c.platform,
                "tone": c.tone,
                "title": c.title,
                "content": c.content,
                "hashtags": c.hashtags,
                "created_by": c.created_by,
            }
            for c in contents
        ],
    }


@router.post("/marketing/analyze")
async def analyze_marketing(req: MarketingRequest):
    """对指定活动执行一次 AI 营销策划（生成方案 + 文案并落库）"""
    try:
        agent = get_agent()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return await agent.analyze(req.campaign_id, req.params)
