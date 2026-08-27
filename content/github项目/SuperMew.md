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

