## 定位

生产导向的 FastAPI RAG 系统 starter——不止"传文本、问问题"，而是完整支持**认证、文档归属、文档级检索隔离、语义缓存、评估管线、内置 UI**。

## 核心特性（来自 README + 代码验证）

- Agent 循环 + 工具调用（`retrieve_context` 检索工具）
- Chroma 向量库（本地持久化）
- OpenAI / HuggingFace 双 Embedding Provider（可插拔）
- 可选 Cohere Reranker（重排）
- 检索前 Query Refinement（查询改写）
- Postgres + pgvector 语义缓存
- 文本 + PDF 摄取（pdfplumber，页级元数据，表格识别）
- JWT access + refresh 认证（fastapi-users）
- 文档归属、列表、软删除
- 评估管线：检索指标（ Hit@k / Recall@k /MRR）+ LLM judge 答案指标（Accuracy/Completeness/Relevance/Groundedness），支持运行历史、失败用例重跑、数据集复用
- Jinja UI（登录、提问、评估、对比）

## 规模与技术栈

**规模**：87 个 Python 文件，~6900 行。

| 层 | 技术 |
|---|---|
| API | FastAPI |
| ORM / DB | SQLAlchemy, Alembic, PostgreSQL, pgvector |
| 向量库 | Chroma |
| LLM | OpenAI-compatible chat 后端 |
| Embeddings | OpenAI 或 Hugging Face |
| Reranking | Cohere |
| 认证 | FastAPI Users + 自定义 JWT login/refresh 流程 |
| PDF 提取 | pdfplumber, pandas, rapidfuzz |
| UI | Jinja 模板 + 共享浏览器端 auth client |
| 开发/运行 | Docker, Docker Compose, uv |

## Demo 页面

- `/login-ui` — JWT 浏览器登录
- `/ask-ui` — 单轮提问 UI（引用、缓存状态、改写查询）
- `/evaluation-ui` — 创建评估运行
- `/evaluation-history-ui` — 历史运行对比
- `/evaluations/{run_id}/ui` — 用例检查与失败重跑

## 为什么存在（设计动机）

大多数 RAG demo 止步于"上传文本、问问题"。本项目进一步支持：

- 认证用户与归属文档
- 文档级检索隔离，防止跨文档泄漏
- 文本与 PDF 摄取
- 可插拔 embeddings 与 reranking
- 语义答案缓存
- 带运行历史、用例检查、重跑支持的评估管线
- 开箱即用的提问与评估 UI

## 前置要求

- Python `3.12+`
- `uv`
- Docker 与 Docker Compose
- 所需 provider 的 API 凭据（OpenAI / HuggingFace / Cohere）

## 环境配置

```bash
cp .env.example .env
```

至少检查：

- 数据库设置
- JWT secrets
- 模型与 provider 设置
- reranker 设置（如启用）
- 评估 judge model

## 方式 A：Docker 运行（全栈最快）

```bash
docker compose up --build
```

服务地址：

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- pgAdmin: `http://localhost:5050`

应用容器启动时自动运行 Alembic 迁移，本地开发以 reload 模式运行 FastAPI。

## 方式 B：本地运行

```bash
uv sync --dev            # 安装依赖
uv run alembic upgrade head   # 跑迁移
uv run uvicorn main:app --reload   # 启动
```

## 典型工作流

### 1. 注册并登录

- 通过 Swagger 或认证流注册
- 从 `/login-ui` 登录，或 `POST /auth/jwt/login`

### 2. 摄取文档

文本：

```bash
curl -X POST http://localhost:8000/rag/ingest/text \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text":"...","source":"inline-text"}'
```

PDF：`POST /rag/ingest/pdf`，multipart 上传，携带同一 bearer token。

### 3. 向 agent 提问

```bash
curl -X POST "http://localhost:8000/agent/ask?use_cache=true" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"doc_id":"<doc_id>","question":"What does the policy define as an Account?"}'
```

响应包含：

- 最终答案
- `cache_status`
- `refined_query`
- `tools_used`
- `steps`
- 带 `doc_id`、`chunk_id`、可选 `page_number` 的引用

### 4. 运行评估

- 打开 `/evaluation-ui`
- 上传 JSONL 数据集
- 选择 `doc_id`
- 启动运行并监控进度
- 在运行详情页直接重跑失败用例
- 在 `/evaluation-history-ui` 对比历史运行

## API 概览（核心端点）

| 方法     | 路径                                   | 说明              |
| ------ | ------------------------------------ | --------------- |
| POST   | `/auth/jwt/login`                    | 登录              |
| POST   | `/auth/jwt/refresh`                  | 刷新 access token |
| POST   | `/auth/jwt/logout`                   | 登出              |
| GET    | `/users/me`                          | 当前用户            |
| POST   | `/rag/ingest/text`                   | 文本摄取            |
| POST   | `/rag/ingest/pdf`                    | PDF 摄取          |
| POST   | `/agent/ask`                         | agent 提问        |
| GET    | `/documents`                         | 文档列表            |
| GET    | `/documents/{doc_id}`                | 文档详情            |
| DELETE | `/documents/{doc_id}`                | 删除文档（软删除）       |
| POST   | `/evaluations/rag`                   | 创建评估运行          |
| GET    | `/evaluations`                       | 运行列表            |
| GET    | `/evaluations/{run_id}`              | 运行详情            |
| GET    | `/evaluations/{run_id}/cases`        | 用例列表            |
| POST   | `/evaluations/{run_id}/rerun-failed` | 重跑失败用例          |
| GET    | `/llm/health`                        | LLM 健康检查        |
| GET    | `/tools/health`                      | 工具健康检查          |

## 评估体系

检索指标：

- Hit@k
- Recall@k
- MRR

答案指标：

- Accuracy
- Completeness
- Relevance
- Groundedness

每次运行存储：聚合指标、逐用例结果、生成答案、引用、检索排名、配置快照（可复现）。

## 目录结构（物理结构）

```
agentic-rag/
├── main.py                  # FastAPI 入口: lifespan + 8 个 router 注册 + /static
├── pyproject.toml / uv.lock / pytest.ini
├── alembic/                 # 9 个迁移 (users, documents, cache, eval 表, 配置快照)
├── docker-compose.yml / Dockerfile
├── templates/               # Jinja UI: login/ask/documents/evaluation×5
├── static/                  # 浏览器端 JS/CSS
├── tests/                   # unit/ + integration/
├── output/                  # 样例评估输出 (jsonl + pdf)
└── src/
    ├── api/v1/              # 表现层: routes/(8 个) + schemas/ + dependencies.py(DI 装配)
    ├── agents/              # ask_pipeline(编排) / service(agent 循环) / query_refinement / cache_policy
    ├── rag/
    │   ├── pipeline/        # services.py: RAGIngestionService + RAGRetrievalService
    │   ├── ingestion/       # chunker + chunking/{fixed_window,recursive_semantic} + pdf_extractor
    │   ├── embeddings/      # EmbeddingProvider 接口
    │   ├── reranker/        # Reranker 接口
    │   ├── vectorstore/     # VectorStore 接口
    │   └── models.py        # RetrievedChunk / RAGChunk
    ├── modules/             # 业务领域模块 (users/documents/semantic_cache/evaluation)
    ├── infrastructure/      # 适配器: database/ llm/{openai,hf} reranker/cohere vector_db/chroma
    ├── tools/               # retriever_tool + registry + ping_tool
    ├── settings/            # pydantic-settings: app/auth/ai/rag/database/evaluation/agent
    └── shared/              # tracing(全链路 trace) + interfaces/{llm,tool}
```

## 分层规则

`api → agents/rag → modules/infrastructure → 外部服务`

- `rag/` 内是**接口层**（embeddings/reranker/vectorstore 目录只有协议），实现全部在 `infrastructure/` ——刻意设计的依赖倒置。
- `api/v1/dependencies.py` 是唯一的 DI 装配点，用 `@lru_cache` 单例装配 provider 与 service。
- `alembic/versions/` 9 个迁移：users → documents → semantic_cache → evaluation 表 → config snapshot → keyword 字段 → 移除旧评估表 → chunking 配置。

## 完整源文件清单（87 个 Python 文件）

```
src/__init__.py
src/agents/__init__.py
src/agents/ask_pipeline.py
src/agents/cache_policy.py
src/agents/query_refinement.py
src/agents/service.py
src/api/v1/dependencies.py
src/api/v1/routes/__init__.py
src/api/v1/routes/agent.py
src/api/v1/routes/auth.py
src/api/v1/routes/documents.py
src/api/v1/routes/evaluations.py
src/api/v1/routes/health.py
src/api/v1/routes/rag.py
src/api/v1/routes/ui.py
src/api/v1/routes/users.py
src/api/v1/schemas/__init__.py
src/api/v1/schemas/agent.py
src/api/v1/schemas/documents.py
src/api/v1/schemas/evaluation.py
src/api/v1/schemas/health.py
src/api/v1/schemas/rag.py
src/infrastructure/database/__init__.py
src/infrastructure/database/database.py
src/infrastructure/llm/__init__.py
src/infrastructure/llm/huggingface_embeddings.py
src/infrastructure/llm/openai_embeddings.py
src/infrastructure/llm/openai_llm.py
src/infrastructure/reranker/__init__.py
src/infrastructure/reranker/cohere_reranker.py
src/infrastructure/vector_db/__init__.py
src/infrastructure/vector_db/chroma_vectorstore.py
src/modules/__init__.py
src/modules/documents/__init__.py
src/modules/documents/dependencies.py
src/modules/documents/models.py
src/modules/documents/repository.py
src/modules/evaluation/__init__.py
src/modules/evaluation/dataset.py
src/modules/evaluation/judge.py
src/modules/evaluation/matching.py
src/modules/evaluation/metrics.py
src/modules/evaluation/models.py
src/modules/evaluation/repository.py
src/modules/evaluation/retriever.py
src/modules/evaluation/service.py
src/modules/semantic_cache/__init__.py
src/modules/semantic_cache/models.py
src/modules/semantic_cache/repository.py
src/modules/semantic_cache/service.py
src/modules/users/__init__.py
src/modules/users/dependencies.py
src/modules/users/jwt.py
src/modules/users/models.py
src/modules/users/schemas.py
src/modules/users/security/__init__.py
src/modules/users/security/jwt.py
src/rag/embeddings/__init__.py
src/rag/embeddings/interface.py
src/rag/ingestion/__init__.py
src/rag/ingestion/chunker.py
src/rag/ingestion/chunking/__init__.py
src/rag/ingestion/chunking/base.py
src/rag/ingestion/chunking/fixed_window.py
src/rag/ingestion/chunking/recursive_semantic.py
src/rag/ingestion/chunking/registry.py
src/rag/ingestion/pdf_extractor.py
src/rag/models.py
src/rag/pipeline/__init__.py
src/rag/pipeline/services.py
src/rag/reranker/__init__.py
src/rag/reranker/interface.py
src/rag/vectorstore/__init__.py
src/rag/vectorstore/interface.py
src/settings/__init__.py
src/settings/agent.py
src/settings/ai.py
src/settings/app.py
src/settings/auth.py
src/settings/config.py
src/settings/database.py
src/settings/evaluation.py
src/settings/rag.py
src/shared/interfaces/llm.py
src/shared/interfaces/tool.py
src/shared/tracing.py
src/tools/__init__.py
src/tools/ping_tool.py
src/tools/registry.py
src/tools/retriever_tool.py
```

## 功能结构（逻辑结构）