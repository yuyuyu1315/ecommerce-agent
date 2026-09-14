# ============================================================
# 后端镜像（FastAPI + LangChain + ChromaDB + SQLAlchemy）
# 构建上下文：项目根目录（docker build -f backend/Dockerfile .）
# ============================================================
FROM python:3.10-slim

WORKDIR /app

# 系统依赖（chromadb/onnxruntime 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY backend ./backend
COPY .env.example ./.env.example

EXPOSE 8000

# SEED_ON_START=true 时先导入种子数据（幂等，已有数据自动跳过）
CMD sh -c 'if [ "$SEED_ON_START" = "true" ]; then python -m backend.seed; fi; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000'
