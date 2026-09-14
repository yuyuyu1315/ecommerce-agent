"""知识库数据模型"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # 存 JSON 数组字符串
    source = Column(String(255), nullable=True)
    author = Column(String(100), nullable=True)
    embedding_id = Column(String(100), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def word_count(self) -> int:
        return len(self.content)

    @property
    def read_time_minutes(self) -> int:
        return max(1, self.word_count // 500)

    def increment_view(self):
        self.view_count = (self.view_count or 0) + 1

    def __repr__(self):
        return f"<KnowledgeBase({self.title}, {self.category})>"
