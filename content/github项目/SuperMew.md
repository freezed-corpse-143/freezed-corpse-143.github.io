# 项目简介

## 定位

一个"可爱猫娘（Cute Cat Bot）"形象的 Agent 项目记录，本质是生产导向的 **LangChain Agent + LangGraph RAG 知识库问答系统**——不止"传文档、问问题"，而是完整支持**用户体系与 RBAC、文档三级分块入库、Milvus 混合检索、证据评分路由、查询重写、人工介入（HITL）、SSE 流式问答与全链路可观测**，并配有现代工程化前端（Vite + Vue 3 + TypeScript）。

## 核心特性（来自 README + 代码验证）

- LangChain Agent + 自定义工具（`get_current_weather` 天气、`search_knowledge_base` 知识库检索）
- **混合检索落地**：稠密向量（本地 bge-m 3）+ BM 25 稀疏向量，Milvus Hybrid Search + RRF 排序，兼顾语义与词匹配
- **三级分块 + Auto-merging**：L 1/L 2/L 3 三层滑窗切分；检索优先召回 L 3 叶子，满足阈值自动合并到父块（L 3→L 2→L 1）
- **Leaf-only 向量化**：仅叶子分块写入 Milvus，父块写入 PostgreSQL（DocStore），减少向量冗余
- **Milvus 2.5+ 服务端原生 BM 25**：schema 绑定 `FunctionType.BM25` 计算函数，服务端提取稀疏特征，与稠密检索统计完美对齐
- **复杂度规划 + 并行 Sub-Agent**：单事实问题本地规则直接走标准流程；其余由 FAST_MODEL 一次完成 simple/complex 判断并给出 2-4 个子问题；复杂问题经 LangGraph `Send` 并行检索，Synthesis 节点去重合成
- **纠错型 RAG（Corrective RAG）**：GRADE_MODEL 结构化判断证据相关性/可回答性/歧义，路由到回答/重写/澄清/范围选择/无知识
- **Step-back / HyDE 单选查询重写**：证据不足时 FAST_MODEL 一次结构化调用单选一种方式，只执行一次二次检索（重写预算 = 1）
- **人工介入（HITL）**：证据不足需澄清或需用户选择检索范围时暂停流程，向用户提问，恢复时跳过主图做定向检索
- **Jina Rerank 接入**：Hybrid/Dense 召回后 API 级精排，返回 `rerank_score` 并前端可视化；失败自动降级 RRF 排序
- **双向降级**：稀疏生成或 Hybrid 调用失败自动降级纯稠密检索
- **流式输出**：`agent.astream(stream_mode="messages")` 逐 token 推送，前端 SSE + ReadableStream 打字机效果，支持 AbortController 中断
- **实时 RAG 过程可视化**：检索/评分/重写步骤在模型"思考中"阶段实时推送（`asyncio.Queue` + `run_in_executor` 事件循环穿透）
- **会话摘要记忆**：自动摘要旧消息为 `persistent_note` 注入系统提示，控制 token
- 用户注册/登录、JWT 鉴权、PBKDF 2-SHA 256 密码（兼容历史 bcrypt）、RBAC（admin/user）、管理员邀请码

## 规模与技术栈

**规模**：后端 41 个 Python 文件 ~5300 行；前端 30 个 TS/Vue 文件 ~3800 行；测试 6 个文件 ~1350 行。

| 层          | 技术                                                                             |
| ---------- | ------------------------------------------------------------------------------ |
| API        | FastAPI（同步 SQLAlchemy 2.0）                                                     |
| 编排         | LangChain Agent（`create_agent`）+ LangGraph（StateGraph + Send API）              |
| LLM        | OpenAI-compatible 三模型分工：`MODEL`（生成）/ `FAST_MODEL`（复杂度+重写）/ `GRADE_MODEL`（证据评分） |
| Embeddings | langchain-huggingface，本地 BAAI/bge-m 3（dense, 1024 维）                           |
| 向量库        | Milvus 2.5+（服务端 BM 25 FunctionType + Hybrid Search + RRF）                      |
| Rerank     | Jina 兼容 `/v1/rerank` API（可选，不配自动降级）                                            |
| DB / 缓存    | PostgreSQL 15（业务+父块 DocStore）、Redis 7（热点会话+父块缓存）                               |
| 文档解析       | pypdf, docx 2 txt, unstructured/Excel, beautifulsoup 4(HTML), msoffcrypto-tool |
| 认证         | python-jose JWT (HS 256) + passlib PBKDF 2-SHA 256                             |
| 前端         | Vite + Vue 3 + TypeScript + Pinia + Axios + Sass                               |
| 开发/运行      | uv, Docker Compose（postgres/redis/etcd/minio/milvus/attu）                      |

## Demo 页面

前端为单页应用（`frontend/dist` 由 FastAPI 静态托管，`/` 访问）：

- 登录/注册面板（`AuthPanel.vue`，支持 admin 邀请码）
- 聊天主界面（`ChatArea.vue` / `ChatInput.vue`，SSE 流式 + 中止按钮）
- RAG 思考链路可视化（`ThinkingTrace.vue` + `RetrievalTraceDetails.vue`：Searching → Grading → Rewriting 步骤实时展示，含子问题并行、合并与召回详情）
- 知识来源引用（`References.vue`：折叠卡片，含 RRF Rank / Rerank 得分 / 合并叶子块数 / 层级 / 页码）
- 文档管理（`UploadSection.vue` 多阶段上传进度轮询 + `DocumentSettings.vue` + `DocumentItem.vue`）
- 会话历史侧栏（`HistorySidebar.vue` 列表/切换/删除）

## 为什么存在（设计动机）

README 声明为"Agent 的项目记录，方便后续持续更新与展示"。技术动机上，大多数 RAG demo 止步于"上传文本、问问题"；本项目进一步落地：

- 语义 + 词面双路混合检索（Milvus 服务端 BM 25 + RRF），并在候选池上做精排
- 三级分块 + Auto-merging，平衡检索精度与上下文完整性
- 证据评分驱动的纠错路由（Corrective RAG）与单选查询重写，控制模型调用数与最坏延迟
- 复杂问题并行子问题检索，简单问题零模型开销快速路径
- 人工介入与恢复机制（HITL），处理模糊/多义问题
- 全链路过程可观测与流式体验，把 RAG 从"黑盒"变成"看得见每一步"

# 快速开始

# SuperMew — 快速开始

## 前置要求

- Python `3.12+`
- 包管理建议 `uv`（也支持 `pip`）
- Docker 与 Docker Compose（启动 PostgreSQL / Redis / Milvus 全家桶）
- Node.js + npm（编译前端）
- 所需 provider 的 API 凭据（ARK 兼容 OpenAI endpoint：`ARK_API_KEY`、`MODEL`、`FAST_MODEL`、`GRADE_MODEL`）

## 环境配置

```bash
cp .env.example .env
```

至少检查：

- 模型设置：`MODEL`（主模型）、`FAST_MODEL`（复杂度/重写）、`GRADE_MODEL`（证据评分）、`BASE_URL`
- 本地向量：`EMBEDDING_MODEL`（默认 BAAI/bge-m 3）、`HF_ENDPOINT`（国内镜像，默认 hf-mirror.com）
- 检索参数：`RETRIEVAL_TOP_K` / `RETRIEVAL_CANDIDATE_K` / `AUTO_MERGE_*` / `RERANK_*`（不配 rerank 自动降级）
- 数据库：`DATABASE_URL`（PostgreSQL）、`REDIS_URL`、`MILVUS_HOST/PORT`
- 认证：`JWT_SECRET_KEY`（务必替换）、`ADMIN_INVITE_CODE`

## 方式 A：Docker 启动依赖（最快）

```bash
docker compose up -d
```

一次拉起全部依赖（业务 + 向量）：

- PostgreSQL：`5432`
- Redis：`6379`
- Milvus standalone：`19530`（健康检查 `9091`）
- etcd / MinIO（Milvus 内部依赖，`9000` / `9001`）
- Attu（Milvus Web 管理台）：`8080`

## 方式 B：本地运行

```bash
uv sync                          # 安装后端依赖
cd frontend && npm install && npm run build && cd ..   # 编译前端（生成 frontend/dist）
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

服务地址：

- 前端 SPA：`http://127.0.0.1:8000/`（后端静态托管 `frontend/dist`）
- Swagger UI：`http://127.0.0.1:8000/docs`

前端开发模式（可选）：`cd frontend && npm run dev`，运行于 `http://localhost:3000`，内置反向代理至 8000。

## 典型工作流

### 1. 注册并登录（admin 可上传文档）

```bash
# 注册（管理员需带 admin_code）
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret","role":"admin","admin_code":"supermew-admin-2026"}'

# 登录获取 token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret"}'
```

### 2. 上传文档（admin，同步或异步）

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@policy.pdf"
```

异步版本返回 `job_id`，前端/调用方轮询 `GET /documents/upload/jobs/{job_id}` 查看五阶段进度（upload → cleanup → parse → parent_store → vector_store）。

支持格式：`.pdf` / `.docx` / `.doc` / `.xlsx` / `.xls` / `.html` / `.htm`。

### 3. 流式提问

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"What does the policy define as an Account?","session_id":"s1"}'
```

SSE 事件流：

- `rag_step` — 实时 RAG 过程步骤（Searching → Grading → Rewriting → …）
- `content` — 逐 token 答案
- `trace` — 完整 `rag_trace`（检索/评分/重写/合并/精排详情）
- `hitl_request` — 人工介入：需澄清/需选择范围时暂停提问
- `session_title` — 首条消息自动生成会话标题
- `error` / `[DONE]`

### 4. 会话管理

```bash
GET    /sessions                       # 会话列表
GET    /sessions/{session_id}          # 会话消息（含 rag_trace）
DELETE /sessions/{session_id}          # 删除会话（user 仅可删自己的）
```

## API 概览（核心端点）

| 方法     | 路径                                           | 说明                        | 权限     |
| ------ | -------------------------------------------- | ------------------------- | ------ |
| POST   | `/auth/register`                             | 注册（可带 admin_code 升 admin） | 公开     |
| POST   | `/auth/login`                                | 登录 → JWT                  | 公开     |
| GET    | `/auth/me`                                   | 当前用户信息                    | 登录     |
| POST   | `/chat`                                      | 同步聊天                      | 登录     |
| POST   | `/chat/stream`                               | 流式聊天（SSE）                 | 登录     |
| GET    | `/sessions`                                  | 会话列表                      | 登录（本人） |
| GET    | `/sessions/{session_id}`                     | 会话消息                      | 登录（本人） |
| DELETE | `/sessions/{session_id}`                     | 删除会话                      | 登录（本人） |
| GET    | `/documents`                                 | 文档列表                      | admin  |
| POST   | `/documents/upload`                          | 同步上传                      | admin  |
| POST   | `/documents/upload/async`                    | 异步上传                      | admin  |
| GET    | `/documents/upload/jobs` / `…/jobs/{job_id}` | 上传任务轮询                    | admin  |
| DELETE | `/documents/{filename}`                      | 同步删除                      | admin  |
| DELETE | `/documents/delete/async/{filename}`         | 异步删除                      | admin  |
| GET    | `/documents/delete/jobs/{job_id}`            | 删除任务轮询                    | admin  |
| GET    | `/`                                          | 前端 SPA                    | 公开     |
| GET    | `/docs`                                      | Swagger UI                | 公开     |

## 三模型分工

| 模型            | 用途                                                  | 特点                  |
| ------------- | --------------------------------------------------- | ------------------- |
| `MODEL`       | Agent 主对话生成（含最终答案）                                  | temperature 0.3     |
| `FAST_MODEL`  | 复杂度规划（simple/complex + 2-4 子问题）、Step-back/HyDE 单选重写 | 低延迟、temperature 0.2 |
| `GRADE_MODEL` | 证据评分（相关性/可回答性/歧义/置信度）与路由                            | 独立高能力模型，结构化输出       |

复杂度规划对明显的单事实问题走本地规则快速路径，不调用模型。

# 功能结构
