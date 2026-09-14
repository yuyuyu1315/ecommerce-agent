"""产品/定价/选品/营销活动/Agent 任务数据模型
（基于文档 6.4 节落地，修正 JS 笔误：toFixed / this.，删除 SQL 中不存在的 duration_days）
"""
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Category(Base):
    """产品分类表"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    path = Column(String(500), nullable=True)  # 层级路径，如 /1/11
    level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    icon_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Product(Base):
    """产品表"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    # 价格信息
    cost_price = Column(Float, nullable=False, default=0)  # 成本价
    current_price = Column(Float, nullable=False)  # 当前售价
    original_price = Column(Float, nullable=True)  # 原价
    target_price = Column(Float, nullable=True)  # 目标价格
    min_price = Column(Float, nullable=True)  # 最低价格
    max_price = Column(Float, nullable=True)  # 最高价格

    # 库存信息
    stock_quantity = Column(Integer, default=0)
    safety_stock = Column(Integer, default=10)  # 安全库存
    stock_status = Column(String(20), default="normal")  # normal, low, out

    # 销售统计
    sales_month = Column(Integer, default=0)  # 月销量
    sales_quarter = Column(Integer, default=0)  # 季度销量
    sales_year = Column(Integer, default=0)  # 年销量

    # 评价信息
    rating = Column(Float, default=0)
    review_count = Column(Integer, default=0)
    positive_rate = Column(Float, default=0)  # 好评率

    # 产品属性
    status = Column(String(20), default="active")  # active, inactive, out_of_stock
    image_url = Column(String(500), nullable=True)
    detail_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)  # 自定义属性

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    competitor_prices = relationship("CompetitorPrice", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def margin_percent(self):
        """计算利润率"""
        if self.current_price and self.cost_price and self.current_price > 0:
            return round((self.current_price - self.cost_price) / self.current_price * 100, 2)
        return 0

    @property
    def profit(self):
        """计算利润"""
        if self.current_price and self.cost_price:
            return round(self.current_price - self.cost_price, 2)
        return 0

    @property
    def stock_turnover_days(self):
        """估算库存周转天数"""
        if self.sales_month > 0:
            daily_sales = self.sales_month / 30
            if daily_sales > 0:
                return round(self.stock_quantity / daily_sales, 1)
        return None

    def is_low_stock(self) -> bool:
        """是否低于安全库存"""
        return self.stock_quantity <= self.safety_stock

    def is_out_of_stock(self) -> bool:
        """是否缺货"""
        return self.stock_quantity <= 0

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.current_price})>"


class PriceHistory(Base):
    """价格历史表"""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    old_price = Column(Float, nullable=True)
    new_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=True)
    change_type = Column(String(20), nullable=False)
    change_reason = Column(Text, nullable=True)
    margin_percent = Column(Float, nullable=True)
    changed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(id={self.id}, {self.old_price}->{self.new_price})>"


class CompetitorPrice(Base):
    """竞品价格表"""

    __tablename__ = "competitor_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    competitor_name = Column(String(100), nullable=False)
    competitor_sku = Column(String(100), nullable=True)
    product_name = Column(String(255), nullable=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    product_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    stock_status = Column(String(20), nullable=True)
    platform = Column(String(50), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="competitor_prices")

    @property
    def discount(self):
        if self.original_price and self.original_price > 0:
            return round((1 - self.price / self.original_price) * 100, 2)
        return 0

    def is_cheaper(self, our_price: float) -> bool:
        return self.price < our_price

    def __repr__(self):
        return f"<CompetitorPrice({self.competitor_name}, {self.price})>"


class Review(Base):
    """用户评价表"""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)
    external_id = Column(String(100), nullable=True)
    user_name = Column(String(100), nullable=True)
    user_level = Column(String(50), nullable=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    keywords = Column(JSON, nullable=True)
    is_verified = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    reply_content = Column(Text, nullable=True)
    review_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")

    @property
    def is_positive(self) -> bool:
        return self.rating >= 4

    @property
    def is_negative(self) -> bool:
        return self.rating <= 2

    @property
    def star_display(self) -> str:
        return "⭐" * self.rating + "☆" * (5 - self.rating)

    def __repr__(self):
        return f"<Review(id={self.id}, rating={self.rating})>"


class ProductSelection(Base):
    """选品记录表"""

    __tablename__ = "product_selections"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    selection_reason = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0)
    estimated_margin = Column(Float, nullable=True)
    estimated_sales = Column(Integer, nullable=True)
    estimated_revenue = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    risk_factors = Column(JSON, nullable=True)
    opportunity_factors = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=5)
    tags = Column(JSON, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    actual_sales = Column(Integer, nullable=True)
    actual_revenue = Column(Float, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", back_populates="created_selections", foreign_keys=[created_by])

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence_score >= 0.8

    @property
    def is_low_risk(self) -> bool:
        return self.risk_level == "low"

    @property
    def roi_estimate(self) -> float:
        if self.estimated_revenue and self.estimated_revenue > 0:
            estimated_cost = self.estimated_revenue * 0.6
            if estimated_cost > 0:
                return round((self.estimated_revenue - estimated_cost) / estimated_cost * 100, 2)
        return 0

    def __repr__(self):
        return f"<ProductSelection({self.product_name}, {self.confidence_score})>"


class Campaign(Base):
    """营销活动表"""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    campaign_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(String(50), nullable=True)
    target_audience = Column(Text, nullable=True)
    strategy_summary = Column(Text, nullable=True)
    discount_type = Column(String(20), nullable=True)
    discount_value = Column(Float, nullable=True)
    min_order_amount = Column(Float, nullable=True)
    max_discount = Column(Float, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    budget = Column(Float, nullable=True)
    actual_spend = Column(Float, nullable=True)
    expected_roi = Column(Float, nullable=True)
    actual_roi = Column(Float, nullable=True)
    expected_revenue = Column(Float, nullable=True)
    actual_revenue = Column(Float, nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", back_populates="created_campaigns", foreign_keys=[created_by])
    campaign_products = relationship("CampaignProduct", back_populates="campaign", cascade="all, delete-orphan")
    marketing_contents = relationship("MarketingContent", back_populates="campaign", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        today = date.today()
        return self.status == "active" and self.start_date <= today <= (self.end_date or today)

    @property
    def duration_display(self) -> str:
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days + 1
            return f"{delta}天"
        return "未知"

    @property
    def discount_display(self) -> str:
        if self.discount_type == "percent":
            return f"满减{int(self.discount_value)}%"
        elif self.discount_type == "amount":
            return f"满减{int(self.discount_value)}元"
        return str(self.discount_value)

    def __repr__(self):
        return f"<Campaign({self.name}, {self.status})>"


class CampaignProduct(Base):
    """活动产品关联表"""

    __tablename__ = "campaign_products"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    custom_discount = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    priority = Column(Integer, default=1)
    is_featured = Column(Boolean, default=False)
    expected_sales = Column(Integer, nullable=True)
    actual_sales = Column(Integer, nullable=True)

    campaign = relationship("Campaign", back_populates="campaign_products")
    product = relationship("Product")

    @property
    def final_price(self) -> float:
        if self.product and self.product.current_price:
            if self.discount_percent:
                return round(self.product.current_price * (1 - self.discount_percent / 100), 2)
            elif self.custom_discount:
                return round(self.product.current_price - self.custom_discount, 2)
            return self.product.current_price
        return 0

    def __repr__(self):
        return f"<CampaignProduct({self.campaign_id}, {self.product_id})>"


class MarketingContent(Base):
    """营销内容表"""

    __tablename__ = "marketing_contents"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    content_type = Column(String(50), nullable=False)
    platform = Column(String(50), nullable=True)
    tone = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    variant = Column(String(10), nullable=True)
    keywords = Column(JSON, nullable=True)
    hashtags = Column(JSON, nullable=True)
    media_urls = Column(JSON, nullable=True)
    ab_test_id = Column(Integer, nullable=True)
    ab_variant = Column(String(10), nullable=True)
    metrics = Column(JSON, nullable=True)
    created_by = Column(String(100), default="AI")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", back_populates="marketing_contents")

    @property
    def view_count(self) -> int:
        return self.metrics.get("views", 0) if self.metrics else 0

    @property
    def click_count(self) -> int:
        return self.metrics.get("clicks", 0) if self.metrics else 0

    @property
    def conversion_count(self) -> int:
        return self.metrics.get("conversions", 0) if self.metrics else 0

    @property
    def ctr(self) -> float:
        if self.view_count > 0:
            return round(self.click_count / self.view_count * 100, 2)
        return 0

    @property
    def conversion_rate(self) -> float:
        if self.click_count > 0:
            return round(self.conversion_count / self.click_count * 100, 2)
        return 0

    def __repr__(self):
        return f"<MarketingContent({self.content_type}, {self.platform})>"


class AgentTask(Base):
    """Agent 任务记录表"""

    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False)
    agent_name = Column(String(50), nullable=False)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    cost_amount = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    @property
    def is_success(self) -> bool:
        return self.status == "completed" and not self.error_message

    @property
    def duration_display(self) -> str:
        if self.duration_ms:
            if self.duration_ms < 1000:
                return f"{self.duration_ms}ms"
            return f"{self.duration_ms / 1000:.1f}s"
        return "N/A"

    @property
    def cost_display(self) -> str:
        return f"${(self.cost_amount or 0):.4f}"

    def __repr__(self):
        return f"<AgentTask({self.task_type}, {self.agent_name}, {self.status})>"
