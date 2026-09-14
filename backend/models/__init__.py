"""模型注册：导入所有模型，确保 Base.metadata 包含全部表"""
from backend.database import Base
from backend.models.user import OperationLog, User
from backend.models.product import (
    AgentTask,
    Campaign,
    CampaignProduct,
    Category,
    CompetitorPrice,
    MarketingContent,
    PriceHistory,
    Product,
    ProductSelection,
    Review,
)
from backend.models.knowledge import KnowledgeBase

__all__ = [
    "Base",
    "User",
    "OperationLog",
    "Category",
    "Product",
    "PriceHistory",
    "CompetitorPrice",
    "Review",
    "ProductSelection",
    "Campaign",
    "CampaignProduct",
    "MarketingContent",
    "KnowledgeBase",
    "AgentTask",
]
