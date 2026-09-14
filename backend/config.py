"""应用全局配置管理（pydantic-settings v2）"""
from functools import lru_cache
from typing import List, Optional
import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从 .env 读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============ 应用基础配置 ============
    APP_NAME: str = Field(default="电商运营Agent", description="应用名称")
    APP_VERSION: str = Field(default="0.1.0", description="版本号")
    DEBUG: bool = Field(default=False, description="调试模式")
    SECRET_KEY: str = Field(default="change-me-in-production", description="密钥")

    # ============ 数据库配置 ============
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/ecommerce.db",
        description="数据库连接字符串",
    )

    # ============ Redis 配置 ============
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis连接")
    CACHE_ENABLED: bool = Field(default=False, description="是否启用缓存")
    CACHE_TTL: int = Field(default=3600, description="缓存过期时间(秒)")

    # ============ LLM 配置（DeepSeek，OpenAI 兼容） ============
    LLM_PROVIDER: str = Field(default="deepseek", description="LLM提供商")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="API密钥")
    OPENAI_MODEL: str = Field(default="deepseek-flash", description="模型名称")
    OPENAI_BASE_URL: str = Field(default="https://api.deepseek.com", description="API地址")

    # 智谱 GLM（备选）
    ZHIPU_API_KEY: Optional[str] = Field(default=None)
    ZHIPU_MODEL: str = Field(default="glm-4")

    # 通义千问（备选）
    QWEN_API_KEY: Optional[str] = Field(default=None)
    QWEN_MODEL: str = Field(default="qwen-turbo")

    # ============ RAG 配置 ============
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="嵌入模型",
    )
    VECTOR_DB_PATH: str = Field(default="./data/chromadb", description="向量库路径")
    RAG_TOP_K: int = Field(default=5, description="检索数量")

    # ============ API 配置 ============
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="CORS白名单",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """解析 CORS 配置（支持 JSON 字符串）"""
        if isinstance(v, str):
            return json.loads(v)
        return v


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()
