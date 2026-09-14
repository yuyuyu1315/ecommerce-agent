"""电商运营 Agent - FastAPI 主入口（v0.2.0：接入数据层与基础 API）"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import backend.models  # noqa: F401  确保所有模型注册到 Base.metadata
from backend.api import agents, dashboard, products, rag
from backend.config import get_settings
from backend.database import close_database, init_database
from backend.rag import rag_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    # 启动时
    os.makedirs(PROJECT_ROOT / "data", exist_ok=True)
    os.makedirs(PROJECT_ROOT / "logs", exist_ok=True)

    await init_database()

    # 启动时构建 RAG 向量索引（失败不阻塞启动，可随时通过接口重建）
    try:
        result = await rag_engine.rebuild()
        print(f"✅ RAG 索引构建完成：共 {result['indexed']} 条文档")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ RAG 索引构建失败（可稍后调用 POST /api/rag/rebuild）：{e}")

    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} 启动完成")

    yield

    # 关闭时
    await close_database()
    print("👋 应用已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="电商运营 Agent - 选品、定价与营销自动化",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(products.router, prefix="/api/products", tags=["产品"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agent"])
    app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "app": settings.APP_NAME}

    # 根路径
    @app.get("/")
    async def root():
        return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION} 运行中", "status": "ok"}

    return app


app = create_app()
