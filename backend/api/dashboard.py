"""数据看板 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    AgentTask,
    Campaign,
    CampaignProduct,
    Category,
    KnowledgeBase,
    MarketingContent,
    Product,
    ProductSelection,
    Review,
)

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    """看板汇总：核心数量指标 + 关键聚合"""
    product_count = (await db.scalar(select(func.count()).select_from(Product))) or 0
    category_count = (await db.scalar(select(func.count()).select_from(Category))) or 0
    campaign_count = (await db.scalar(select(func.count()).select_from(Campaign))) or 0
    active_campaigns = (
        await db.scalar(select(func.count()).select_from(Campaign).where(Campaign.status == "active"))
    ) or 0
    knowledge_count = (await db.scalar(select(func.count()).select_from(KnowledgeBase))) or 0
    review_count = (await db.scalar(select(func.count()).select_from(Review))) or 0
    selection_count = (await db.scalar(select(func.count()).select_from(ProductSelection))) or 0
    agent_task_count = (await db.scalar(select(func.count()).select_from(AgentTask))) or 0
    campaign_product_count = (await db.scalar(select(func.count()).select_from(CampaignProduct))) or 0
    marketing_content_count = (await db.scalar(select(func.count()).select_from(MarketingContent))) or 0

    avg_rating = (await db.scalar(select(func.avg(Product.rating)))) or 0
    low_stock_count = (
        await db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.stock_quantity <= Product.safety_stock)
        )
    ) or 0
    approved_selections = (
        await db.scalar(
            select(func.count()).select_from(ProductSelection).where(ProductSelection.status == "approved")
        )
    ) or 0

    return {
        "success": True,
        "summary": {
            "product_count": product_count,
            "category_count": category_count,
            "campaign_count": campaign_count,
            "active_campaigns": active_campaigns,
            "campaign_product_count": campaign_product_count,
            "marketing_content_count": marketing_content_count,
            "knowledge_count": knowledge_count,
            "review_count": review_count,
            "selection_count": selection_count,
            "approved_selections": approved_selections,
            "agent_task_count": agent_task_count,
            "avg_rating": round(float(avg_rating), 2),
            "low_stock_count": low_stock_count,
        },
    }
