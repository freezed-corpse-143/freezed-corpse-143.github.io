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