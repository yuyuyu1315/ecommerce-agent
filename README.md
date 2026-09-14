# 电商运营 Agent（E-commerce Operations Agent）

面向中小电商的 **AI 多智能体运营系统**：选品 / 定价 / 营销 三大 Agent + RAG 知识库 + 数据看板。
方案来源：飞书知识库《Agent项目-电商运营Agent》，按新版依赖与本地环境落地实现。

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | 项目骨架：目录 / venv / 依赖 / SQL 建库 / 后端可启动 | ✅ 完成（v0.1.0） |
| 1 | 数据层：SQLAlchemy 模型 + 种子数据 + 基础 API | ✅ 完成（v0.2.0） |
| 2 | Agent：选品 Agent（接 DeepSeek）+ API | ✅ 完成（v0.3.0） |
| 3 | RAG：ChromaDB 知识库 + 问答 | ✅ 完成（v0.4.0） |
| 4 | 前端：Vue3 + Element Plus 看板 + 聊天页 | ⏳ 待做 |
| 5 | 补齐定价/营销 Agent + 全部页面 + 联调 | ⏳ 待做 |
| 6 | Docker 部署（可选） | ⏳ 待做 |

## 目录结构

```
ecommerce-agent/
├── backend/            # 后端（FastAPI + LangChain + SQLAlchemy）
│   ├── .venv/          # 虚拟环境（Python 3.10，D 盘）
│   ├── main.py         # 入口（v0.2.0：数据层已接入）
│   ├── config.py       # 配置（.env 读取）
│   ├── database.py     # 异步 SQLAlchemy
│   ├── models/         # SQLAlchemy 模型（user/product/knowledge，14 表）
│   ├── agents/         # Agent（base 基类 + selection 选品 Agent）
│   ├── rag/            # RAG 引擎（ChromaDB 检索 + DeepSeek 生成）
│   ├── api/            # 路由（products / dashboard / agents / rag）
│   ├── seed.py         # 种子数据脚本
│   └── (agents/ rag/ ... 后续阶段补齐)
├── frontend/           # 前端（Vue 3，待建）
├── sql/                # 数据库脚本
│   ├── init_database.sql  # PostgreSQL 15 原版（Docker 部署用）
│   ├── init_sqlite.sql    # SQLite 建库参考脚本
│   └── seed_data.sql      # 示例数据（PostgreSQL 版）
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
