"""电商运营 Agent - FastAPI 主入口（骨架版 v0.1.0）"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import close_database, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    # 启动时
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)

    await init_database()

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
