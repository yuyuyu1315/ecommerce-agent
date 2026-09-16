# 电商运营 Agent（E-commerce Operations Agent）

面向中小电商的 **AI 多智能体运营系统**：选品 / 定价 / 营销 三大 Agent + RAG 知识库 + 数据看板。

> **个人独立项目**（产品定义 · 架构设计 · 开发实现 · 测试验收 全流程负责人）
> 2026.06 – 2026.09 完成 v0.1 → v0.6 六轮迭代，借助 AI Coding 工具辅助编程实现，可本地一键启动演示。

## 项目简介

电商运营长期依赖人工经验，选品、定价、营销决策缺乏数据支撑、效率低、难以沉淀方法。本项目用 **多智能体（Multi-Agent）+ RAG 检索增强** 构建一个可对话的 AI 运营助手，把运营决策从"拍脑袋"变为"数据 + 模型"驱动：

| 功能模块 | 说明 |
|---|---|
| 选品 Agent | 基于商品与竞品数据生成选品建议，支持审批生效、写入决策记录 |
| 定价 Agent | 输出定价建议，审批后自动更新售价并写入价格历史，可追溯 |
| 营销 Agent | 生成营销策划方案与推广文案 |
| 知识问答（RAG） | 基于业务知识库与商品数据检索增强回答，带来源标注 |
| 数据看板 | 指标卡 + ECharts 图表可视化运营数据（前端 Vue3） |

## 技术架构

```mermaid
flowchart LR
    U[用户] --> F[Vue3 前端<br/>数据看板 · Agent 对话页]
    F -->|REST API| B[FastAPI 后端]
    B --> S[业务路由<br/>products / dashboard / agents / rag]
    S --> A1[选品 Agent]
    S --> A2[定价 Agent]
    S --> A3[营销 Agent]
    S --> R[RAG 引擎<br/>ChromaDB 向量检索]
    A1 & A2 & A3 & R --> L[DeepSeek 大模型 API]
    A1 & A2 & A3 & R --> DB[(SQLite / PostgreSQL<br/>14 张业务表)]
    R --> V[(ChromaDB<br/>知识向量库)]
```

## 技术栈

**FastAPI · LangChain · DeepSeek · ChromaDB（RAG）· SQLAlchemy · Vue3 · Element Plus · ECharts · Docker**

## 快速开始

```powershell
# 后端（端口 8001）
$env:USERPROFILE = 'D:\ecommerce-agent\.home'
cd /d D:\ecommerce-agent
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir D:\ecommerce-agent --port 8001

# 前端（端口 5173，需后端已启动）
cd /d D:\ecommerce-agent\frontend
D:\nodejs\npm.cmd run dev
```

- 前端地址：http://localhost:5173
- 后端 API 文档：http://127.0.0.1:8001/docs
- 演示数据：8 商品 / 12 分类 / 9 竞品价 / 8 评价 / 3 活动 / 4 知识库文档

---

## 目录结构

```
ecommerce-agent/
├── backend/            # 后端（FastAPI + LangChain + SQLAlchemy）
│   ├── main.py         # 入口
│   ├── config.py       # 配置（.env 读取）
│   ├── database.py     # 异步 SQLAlchemy
│   ├── models/         # SQLAlchemy 模型（14 张表）
│   ├── agents/         # Agent（base 基类 + selection 选品 / pricing 定价 / marketing 营销）
│   ├── rag/            # RAG 引擎（ChromaDB 检索 + DeepSeek 生成）
│   ├── api/            # 路由（products / dashboard / agents / rag）
│   └── seed.py         # 种子数据脚本
├── frontend/           # 前端（Vue3 + Element Plus + ECharts）
├── sql/                # 数据库脚本（PostgreSQL / SQLite / 种子数据）
├── data/               # 本地数据（SQLite / ChromaDB）
├── tests/
└── requirements.txt
```

## 运行方法（后端）

```powershell
# 启动（端口 8001；USERPROFILE 指向 D 盘，让向量模型缓存落在 D 盘项目内）
$env:USERPROFILE = 'D:\ecommerce-agent\.home'
cd /d D:\ecommerce-agent
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir D:\ecommerce-agent --port 8001
```

- API 文档：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health
- 产品列表：http://127.0.0.1:8001/api/products
- 看板汇总：http://127.0.0.1:8001/api/dashboard/summary
- 选品记录：http://127.0.0.1:8001/api/agents/selection
- Agent 任务：http://127.0.0.1:8001/api/agents/tasks
- 知识库问答：POST /api/rag/query（body: {"question": "..."}）

## Agent 接口

```bash
# 选品分析（真实调用 DeepSeek，结果写入 product_selections）
POST /api/agents/selection/analyze
# body: {"category": "连衣裙", "params": {"user_id": 2}}

# 审批选品建议
POST /api/agents/selection/{id}/approve
```

## Agent 接口（定价 / 营销）

```bash
# 定价分析（真实调用 DeepSeek，结果写入 price_suggestions）
POST /api/agents/pricing/analyze
# body: {"product_id": 1, "params": {"user_id": 2}}

# 定价建议列表（可按 status 过滤）
GET /api/agents/pricing?status=pending

# 审批定价（更新产品售价 + 写入 price_history）
POST /api/agents/pricing/{id}/approve

# 驳回定价建议
POST /api/agents/pricing/{id}/reject

# 营销策划（生成方案 + 文案，更新活动信息）
POST /api/agents/marketing/analyze
# body: {"campaign_id": 1, "params": {"user_id": 2}}

# 活动列表 / 详情（含 AI 文案）
GET /api/agents/marketing/campaigns
GET /api/agents/marketing/campaigns/{id}
```

## RAG 接口

```bash
# 知识库问答（向量检索 + DeepSeek 结合资料回答，带来源标注）
POST /api/rag/query
# body: {"question": "如何做好电商选品？", "top_k": 4}

# 重建向量索引（知识库文档 + 产品数据，启动时自动执行）
POST /api/rag/rebuild

# 知识库文档列表
GET /api/rag/documents
```

> 向量模型：Chroma 内置 ONNX MiniLM（384 维，模型缓存位于 `D:\ecommerce-agent\.home\.cache\chroma`）。
> 中文语义检索如需更强召回，可后续换装 BGE 中文向量模型。

## Docker 部署（生产环境）

项目提供完整 Docker 部署包（PostgreSQL 15 + 后端 + 前端 Nginx），在有 Docker 的机器上一键启动：

```bash
# 在项目根目录（D:\ecommerce-agent）执行；OPENAI_API_KEY 自动从根 .env 读取
docker compose up -d --build
```

- 前端：http://localhost:8080 （Nginx 托管，/api 自动反代到后端）
- 后端 API 文档：http://localhost:8000/docs
- 数据库：PostgreSQL 15（数据卷 pgdata 持久化）
- 初始化：后端启动时自动建表（SQLAlchemy create_all）+ 幂等导入种子数据（SEED_ON_START）
- 向量库：./data/chromadb 挂载持久化

> ⚠️ 说明：本机因"软件只装 D 盘"约束未安装 Docker Desktop，compose 已通过 YAML 结构校验与容器环境变量覆盖模拟（DATABASE_URL/API Key 均验证），未在本机端到端执行；在任何装有 Docker 的机器上运行即可。

## 种子数据

数据库已内置演示数据（8 产品 / 12 分类 / 9 竞品价 / 8 评价 / 3 活动 / 4 知识库文档 / 3 Agent 任务记录）。

重灌种子数据（会重置数据库）：

```bash
python -m backend.seed   # 在 D:\ecommerce-agent 下执行
```

## 关键配置（.env）

- `OPENAI_API_KEY`：DeepSeek Key（OpenAI 兼容，模型 `deepseek-flash`）
- `DATABASE_URL`：本地 SQLite；部署时改 PostgreSQL
- `CORS_ORIGINS`：允许 Vite 前端（localhost:5173）

## 说明

- SQLite 本地版已建 **14 张表**（用户/产品/竞品价格/评价/选品/活动/知识库/Agent 任务等）。
- 文档原代码存在版本过时、JS 笔误等坑，落地时已按新版 API（langchain 1.4 / langchain-openai 1.6）修正。
