"""应用全局配置管理（pydantic-settings v2）"""
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 = backend 的上一级；.env 用绝对路径加载（不依赖启动目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """应用配置，从 .env 读取"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============ 应用基础配置 ============
    APP_NAME: str = Field(default="电商运营Agent", description="应用名称")
    APP_VERSION: str = Field(default="0.3.0", description="版本号")
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
    LLM_TEMPERATURE: float = Field(default=0.3, description="LLM 采样温度")

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
