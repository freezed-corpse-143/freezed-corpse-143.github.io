# Agent Harness（Pi / DeepSeek Harness）

对象：`C:/Projects/pi`（earendil-works/pi）与 `C:/Projects/deepseek-harness`（DeepSeek Harness，下称 dsh）。

共同问题一句话：**怎么把一个模型放进一个循环里，让它用工具在一个代码库里真的干活，并且这个循环能被中断、恢复、复现、扩展。**

结论先行：

```text
两者都不是"模型前向 + API"，而是"工具循环 + 会话记录 + 扩展面"的三件套。
它们的根本区别不是支持哪些模型或工具，
而是把哪一层当作自己的核心抽象：
  Pi  → 一个进程内的 agent loop + 一棵会话树（loop 是库）
  dsh → 一棵 Cordis 插件树（loop 是配置里的一行）
```

所有断言都带 `path:line` 锚点，两个仓库各自为根。本机两个 checkout 在同一天，版本：pi `packages/coding-agent@1.1.0`（HEAD `6fb2e7815`），dsh `@deepseek-ai/dsh@0.2.1-alpha.1`。

---

# 统一框架

把「推理框架」的骨架搬过来，按"智能体脚手架"这个领域重新划边：

```text
智能体脚手架（agent harness）
├─ 接入面：交互 TUI / 一次性打印 / JSON 事件流 / RPC / SDK / Web / 编辑器 / 远程 / webhook
├─ 提示与输入面：用户输入展开、系统提示组装、技能与模板、斜杠命令、环境上下文注入
├─ 控制面：agent loop（turn / step）、工具调用调度、取消与中断、守卫
├─ 状态面：会话事件日志、持久化格式与迁移、恢复 / 分叉、投影
├─ 计算面：模型适配与流式词汇、工具注册表与执行管线
├─ 资源面：上下文窗口预算、压缩、溢出恢复、工具结果外化
├─ 平台面：模型 provider、终端渲染、编辑器协议、沙箱与权限、远程执行
└─ 产物面：可执行体 / npm 包 / wheel / SDK、发布的扩展契约
     ＋ 贯穿全部层的切面：扩展模型本身、配置、凭据、遥测
```

和推理框架那一版的对照（骨架槽位是同一串，内容领域特化）：

| 骨架槽位 | 推理框架 | 智能体脚手架 |
| :--- | :--- | :--- |
| 接入 | HTTP / CLI / C API | 交互 TUI / print / RPC / SDK / Web / ACP |
| 表示 | 模型工件与加载层 | 会话事件日志与消息表示 |
| 控制 | 调度与批处理 | agent loop（turn / step）与工具调度 |
| 状态 | KV Cache、请求状态 | 会话树 / 事件日志、压缩摘要 |
| 计算 | forward、算子 | 模型流式调用、工具执行 |
| 资源 | 显存、权重驻留 | **上下文窗口预算**（这是领域特化最重的一格） |
| 平台 | CUDA / ROCm / CPU | provider / 终端 / 编辑器 / 沙箱 / SSH |
| 产物 | cubin、生成的源码 | 可执行体、SDK、插件契约 |
| 切面 | 前缀缓存、并行策略 | **扩展模型**（下面会看到，它才是最大的分歧源） |

两个项目都填满了全部九格——没有"其他 / 不适用"格。这本身是个信号：这一层抽象是完备的。

---

# 根本区别：把哪一层当作核心抽象

| | Pi | dsh |
| :--- | :--- | :--- |
| 核心抽象 | 一个进程内的 **agent loop + 会话树** | 一棵 **Cordis 插件树** |
| loop 的位置 | 库 `@earendil-works/pi-agent-core`，被 CLI 直接 import | 配置里的一行插件 `id: agent-loop` |
| 产品的形态 | 一个 CLI + 一个 SDK + 一批可被 import 的库 | 一个启动器 + 五个 profile（web/headless/acp/sdk/sdk-minimal） |
| 扩展的形态 | 进程内 TypeScript 模块，注册钩子 | 配置行 + service 注册 + 可逆 effect |

loop 的可替换性是这句话最硬的证据，两家都给得很明确：

```text
Pi   packages/coding-agent/src/core/sdk.ts:2
     import { Agent, type AgentMessage, ... } from "@earendil-works/pi-agent-core"
     → loop 是依赖，行为只能通过 AgentLoopConfig 的钩子改（packages/agent/src/types.ts:193）

dsh  packages/bundle/base/cordis.patch.yml:511-515
     - id: agent-loop
       name: '@deepseek-ai/dsh-agent-loop'
     → loop 是一行配置；且 .agents/notes/archived/architecture/2026-06-11-microkernel-event-taxonomy.md:21
       明确写下：dsh-agent-loop 是唯一的具体循环插件，自身可替换，外部不得依赖它
```

一个反直觉但很能说明问题的观察：**dsh 复用了 Pi 的一个包，但复用的不是 loop，是模型适配层。**

```text
packages/llm/llm-pi-ai/package.json:44   "@earendil-works/pi-ai": "^0.87.1"
```

dsh 把 Pi 的 `@earendil-works/pi-ai`（多 provider 单次请求抽象）当成一个第三方 provider 库，挂在自己的 `ctx.llm` seam 后面；Pi 的 loop、TUI、server、coding-agent 一行都没碰。这正是"把哪一层当核心抽象"的直接后果：**能被复用的是无状态的那一层（单次请求），不能被复用的是有主张的那一层（循环与状态）。**

---

# 面 × 项目

## 1. 接入面

| | Pi | dsh |
| :--- | :--- | :--- |
| 交互 | `InteractiveMode` TUI（`packages/coding-agent/src/modes/interactive/interactive-mode.ts`） | Web UI（profile `web`，`packages/bundle/web-app/src/index.ts:251` 挂 dist 静态前端） |
| 一次性 | print 文本 / print JSON（`src/modes/print-mode.ts:170`、`:120`） | `headless` profile（`pnpm dsh --profile headless "task"`） |
| 程序化 | RPC over stdin/stdout JSONL（`src/modes/rpc/rpc-mode.ts:47`，命令联合 `rpc-types.ts:18-71`，32 条命令） | SDK JSON-RPC（`packages/sdk/server/src/index.ts:20`，ND-JSON-RPC 2.0，`packages/sdk/protocol/src/transport.ts:62`） |
| SDK | TS：`src/index.ts` 直接导出 `AgentSession` 等（进程内） | TS：`packages/sdk/client/src/launch.ts:128` **spawn 同版本 dsh**；Python：`python/sdk/src/deepseek_harness/client.py:79` Popen 打包好的运行时 |
| 编辑器 | 无对应物 | ACP over stdio JSON-RPC（`packages/acp/acp/src/index.ts:374`）；另有 Codex / Claude Code hook 桥（`packages/hooks/*`） |
| 远程 | 实验性 Unix socket server/client（`src/experimental/server.ts`，自有 CBOR 协议 `PROTOCOL_VERSION = 8`，`packages/protocol/src/protocol.ts:5`） | `packages/ssh` 一组 provider（subprocess / fs / sandbox 同时换后端） |
| 事件驱动 | 无 | webhook（`packages/webhook/webhook-github/src/index.ts:50`，精确路由 + 202 立即返回） |

模式派发：Pi 在 `src/main.ts:112-125` 解析出 `interactive | print | json | rpc` 四种，`:949-990` 派发。

dsh 只有一个进程入口：`apps/cli/src/bin.ts:26`，四种模式 `profile | plugin | dump-config | dump-config-schema`；其余"应用"都是 profile。这条规则被 CI 强制（`scripts/verify-application-entrypoints.ts`：任何 `bin` 绕过 dsh 启动器就报错）。

空面（明确缺失，不是没查到）：**Pi 没有 Web UI / 桌面 / webhook；dsh 没有 TUI**（`packages/boot/app-boot/src/profile.ts:179` 的五个 profile 模板里没有 tui，仓库里也没有 `dsh-tui` 包）。

## 2. 提示与输入面

| | Pi | dsh |
| :--- | :--- | :--- |
| 输入 → 消息 | `AgentSession.prompt`（`core/agent-session.ts:1968`）串起一整条流水线 | `Agent.followup/send` 先入 inbox，再由 `agent/pre-step` waterfall 决定接受 / 改写 / 拒绝（`packages/core/agent/src/runtime-types.ts:320`，`core/agent-loop/src/agent.ts:267`） |
| 顺序 | 扩展命令 → input 钩子 → `/skill:` 展开 → 提示模板 → 排队 → 校验 → 压缩检查 → before-agent-start → 收集｜`:1968-2110` | claim 一批 → 组装系统提示 → 投影运行时上下文 → `agent/pre-step` → 记 `user/message` |
| 系统提示 | 一次性组装成具名 XML 分节（`core/system-prompt.ts:120-230`），**持久化为 system 消息 + 后续只记分节 patch**（`diffSystemPromptSections` `:255`） | 注册表：`section / context / tools(provider) / variable` + 中央 order 表（`packages/core/system-prompt/src/index.ts:122`），**每步重装**，只有变化才写 surface 节点（`core/agent-loop/src/runtime-context.ts:95`） |
| 环境上下文 | `AGENTS.md` / `CLAUDE.md` → 系统提示的一个分节（`core/resource-loader.ts:184-186`、`:232-270`） | `packages/context/agent-instructions` 把它注入成**持久 user 角色消息**（默认 64 KiB 上限） |
| 技能 | 目录扫描 + frontmatter，`/skill:name` 展开成消息（`core/skills.ts:414`，`agent-session.ts:2147`） | `ctx.skills` seam + 面向模型的 `skill` 工具（`packages/skill/*`） |
| 人类命令 | 24 个内建斜杠命令，交互层一条 `if` 链（`core/slash-commands.ts:19-44`，`interactive-mode.ts:3199`） | `ctx.commands`，命令**不变成模型消息**（`packages/interaction/commands`） |

这里有个容易看漏的分歧点：**"环境上下文放哪"两家给了相反答案。**

Pi 放系统提示 → 提示前缀稳定，但内容不参与会话记录的重放；dsh 放会话消息 → 内容照常 replay / compact，代价是每轮都占用上下文。这是同一个问题（"注入的静态上下文该不该被当成历史"）的两种正解。

## 3. 控制面

| | Pi | dsh |
| :--- | :--- | :--- |
| loop 位置 | `packages/agent/src/agent-loop.ts`（949 行） | `packages/core/agent-loop/src/agent.ts` |
| 结构 | 双层 `while`：外层 run（`:179`），内层 step（`:183 while (hasMoreToolCalls \|\| pendingMessages.length > 0)`） | 显式 `Phase` 状态机 `idle \| maintenance \| running`（`agent.ts:42`）；`kick()` 里 `while (await this.turn())`（`agent.ts:254`），`turn()` `:296` / `step()` `:398` |
| 谁决定下一步 | 上层 `AgentSession._runAgentPrompt`：`while (!abortRequested)` 里看有没有队列消息 / 是否要续跑（`core/agent-session.ts:1822-1850`） | loop 自己：一个 step 的自然停止 + 待处理输入 + `agent/turn-stopping` 序列检查点（`agent.ts:359-362`） |
| 迭代上限 | **没有**（全包 grep `maxTurns` / `maxIterations` 无匹配）；只有重试上限与压缩阈值 | 也没有 loop 内上限；上限在策略插件里（goal 的 round cap、Ralph 的 `maxTotalAgents`） |
| 扩展点 | `AgentLoopConfig` 一组函数钩子：`convertToLlm` / `transformContext` / `finishTurn` / `prepareRequest` / `prepareNextTurn` / `getSteeringMessages` / `getFollowUpMessages` / `beforeToolCall` / `afterToolCall`（`packages/agent/src/types.ts:193`） | Cordis waterfall 事件：`agent/pre-step` / `agent/request` / `llm/stream` / `agent/request-error` / `tools/*`，返回值是**类型化的决策**（`PreStepDecision` `runtime-types.ts:104`） |
| 中断 | `Agent.abort()`（`agent.ts:341`）；未发出的队列消息退回编辑器（`interactive-mode.ts:3070-3090`） | `cancel(cause)`，cause 是 `user \| parent \| hook{reason} \| disposed`（`packages/core/session/src/types.ts:189`），并**逐字段拷贝**成 `turn/end` 的原因（`agent-loop/src/agent.ts:80`） |
| 工具调度 | 默认并行（`agent-loop.ts:519-522`），结果按 assistant 源序发消息 | 屏障 vs 有界滚动池（`tool-calls.ts:132`，`maxParallelToolCalls` 默认 10 见 `agent-loop/src/constants.ts:6`，配置在 `agent-loop/src/index.ts:334`），结果**按模型序连续提交**（`commitReady` `tool-calls.ts:132` 区段） |
| 取消的账 | —— | 启动了的工具照常收；没启动的补合成 `tool/result`（`appendSkippedToolCall` `tool-calls.ts:250`），保证日志可重放 |

两家的守卫位置也不同：Pi 的守卫是 CLI 层的**工具白名单分级**（`--tools/--no-builtin-tools`，`agent-session.ts:1537-1571`）；dsh 的守卫是 `core/tools` 里的**单调 guard 链**（`ToolGuard`，只能拒绝不能复活，`packages/core/tools/src/index.ts:731/1136`）+ 独立的 `packages/guard` 插件（重复调用提醒、`tools/execute` 超时）。

## 4. 状态面

| | Pi | dsh |
| :--- | :--- | :--- |
| 形态 | 单个 append-only JSONL **树**，每行有 `id` / `parentId`（`core/session-manager.ts`，`CURRENT_SESSION_VERSION = 3` `:41`） | append-only **事件日志 + surface 投影**（`SessionEventMap` `packages/core/session/src/types.ts:281-428`） |
| 位置 | `~/.pi/agent/sessions/--<path>--/<ts>_<id>.jsonl` | `SessionPersistence` seam：`create/open/flush/stat/list`（`packages/session/session-persistence/src/index.ts`），后端可换（JSONL / SQLite） |
| 分支 | 文件内分支是主要语义：在任意 entry 继续 → 新分支；fork / clone 复制历史到新文件（`:1632`、`:1815`） | `buildForkSeed` 复制闭区间前缀 + 记 `session/end-seed {inherited:true}` + 补 `openTurnClosers`（`packages/core/session/src/fork.ts:26`） |
| 迁移 | v1 线性 → v2 树 → v3 `hookMessage`→`custom`（`migrateSessionEntries` `session-manager.ts:350`） | `SESSION_FORMAT_VERSION = 4`（`packages/core/session/src/types.ts:89`），**版本不符直接拒绝，没有升级路径**（`assertVersion`） |
| 崩溃尾修复 | —— | `interruptedTurnClosers` 修中断的尾巴（`agent-loop/src/repair.ts`），resume 时重开写句柄 |
| 投影 | `buildSessionProjection` / `buildSessionContext`（`session-manager.ts:543/:576`） | `SessionProjectionRegistry` + `stateOf()`（`packages/session/session-projection/src/index.ts:199/319`）；loop 自己注册 `turnBoundary` 与 `inbox` 两个投影 |
| 一段历史怎么变成请求 | 活跃分支 → 消息投影（`:439-576`） | `Session.deriveMessages()`（`packages/core/session/src/index.ts:856`）按 `contentGeneration` 缓存，是**唯一**的消息来源 |

## 5. 计算面

**模型侧：**

| | Pi | dsh |
| :--- | :--- | :--- |
| seam | `StreamFn` 函数类型 + `setDefaultStreamFn` 注入（`packages/agent/src/stream-fn.ts:11`，文件 19 行） | `ctx.llm` 服务 + `LlmAdapter` 抽象类（`packages/llm/llm/src/index.ts:48-78`，`registerAdapter` `:389`） |
| provider 契约 | `Provider` 接口（`packages/ai/src/models.ts:150`）、`Models`（`:250`）、`createProvider`（`:1041`） | `prepareCall()` + `stream()`（`llm/src/index.ts:278/290`） |
| 流式词汇 | `AssistantMessageEventStream` + `AssistantMessageEvent`（`packages/ai/src/utils/event-stream.ts:120`，`types.ts:801`：`text_start/delta/end`、`toolcall_start/delta/end`、`done/error`） | `StreamChunk`（`packages/llm/llm/src/types.ts:452`：`block-start \| text-delta \| reasoning-delta \| tool-call-delta \| block-end \| usage \| finish`） |
| 具体适配器 | 40+ 家内置 provider 清单（`packages/ai/src/providers/all.ts`），目录由生成器编译进 TS（`scripts/generate-models.ts` → `models.generated.ts`） | `llm-deepseek`（自建 wire）、`llm-deepseek-api-key`、`llm-deepseek-account`、**`llm-pi-ai`**、`llm-retry`、`token-meter` |
| 重试 | provider 请求层（`packages/ai/src/utils/provider-retry.ts:107`），会话层另有 `_prepareRetry`（`agent-session.ts:3762`） | 独立插件 `llm-retry` 在 loop 的请求恢复点排期，**先持久化再重试** |

**工具侧：**

| | Pi | dsh |
| :--- | :--- | :--- |
| 注册表 | 静态定义 + 合并（`core/tools/index.ts:95`，`_refreshToolRegistry` `agent-session.ts:3495`） | `ToolRuntime extends Service` 即 `ctx.tools`（`packages/core/tools/src/index.ts:807`），按 scope 分层（`ScopedLayers`） |
| 声明 | `AgentTool`（pi-ai 的 typebox schema） | `defineTool` + 自研 schema DSL，编译成裸 JSON Schema（`core/tools/src/schema.ts:554`） |
| 模型能看到什么 | 全部注册工具（可用 exposure 分级：direct/model-only/deferred/codemode/hidden，`agent-session.ts:1549`） | 白名单投影：`schemaOf` 只发 `name/description/parameters/deferLoading`，`timeoutMs` / 回调 / output 永远不进模型（`tools/src/index.ts:1282`） |
| 执行管线 | prepare（查表 → 参数校验 → `beforeToolCall`）→ execute → finalize（`afterToolCall`）→ 结果消息（`agent-loop.ts:708/821/859/930`） | `tools/pre-execute` waterfall → 单调 guard → `tools/execute` waterfall → body → `projectContent` → `tools/post-execute` → 冻结结果 → `tools/result`（`tools/src/index.ts:1369/1493/1601/1641/1669`） |
| 谁写日志 | CLI 层 `_handleAgentEvent` 写（`agent-session.ts:1103-1170`） | **只有 loop 写**：`appendToolCall` / `appendToolResult`（`tool-calls.ts:263/269`），注册表只返回冻结值 |
| 内建工具 | 8 个：`read bash powershell edit write grep find ls`（`core/tools/index.ts:95`）；**没有 web / fetch / search** | 30+ 个工具包（清单见 `docs/tool-catalog.md`，由生成器**真实 boot 每个插件并读 `ctx.tools.schemas()`** 得到） |

dsh 的工具箱铺得很开：`read/write/edit/str_replace_editor/glob/grep`、`bash/pwsh`（含 PTY 持久版）、`terminal_*`、`lsp`、`web_fetch/web_search`、`skill`、`subagent`（+ `send_message/interrupt_agent/list_agents`）、`job_*`、`todo_write`、`create_goal/update_goal`、`schedule_*`、`ask_user_question`、`present`、`session_search/session_trace`、`workflow`、`ralph`、`spawn_teammate`、`plugin_manager`、`cordis_inspect_*`、MCP 动态工具。

Pi 的选择相反：8 个工具 + 让扩展/MCP 补（`tool_search`、`codemode`、`mcp__<server>__<tool>`）。

## 6. 资源面

| | Pi | dsh |
| :--- | :--- | :--- |
| 计量 | 会话统计 + provider usage | `ctx.tokenMeter`：**replay-aware 的每会话 fold**（`packages/llm/token-meter/src/index.ts:101`），provider usage 与启发式估算并列 |
| 触发压缩 | `shouldCompact(contextTokens > contextWindow - reserveTokens)`（`core/compaction/compaction.ts:267`），默认 `reserveTokens 16384`、`keepRecentTokens 20000` | `thresholdRatio 0.8`、`retainRatio 0.16`、`headroomTokens 65_536`（`packages/compaction/compaction-basic/src/config.ts:75/120-140`） |
| 压缩时机 | 四种：每轮后（`:2947`）、新提示前（`:2054`）、逐步之间（`:776`）、溢出恢复（`:3038`）、手动 `/compact` | 两种触发器：`agent/pre-step`（`'pressure'`）与 `agent/request-error`（`'context-overflow'`，且要求 `surface.replaceGeneration` 真的前进才允许 retry） |
| 压缩的形态 | 插入一个 summary entry，**原 entry 留在树里**，只是不再进模型请求 | 用一个 summary 节点**替换**被选中的 surface 区间；不能压系统提示 / 工具 / session prefix |
| 结果外化 | 输出截断（`core/tools/truncate.ts`） | `spill` seam：`ctx.spillStore.saveText()` → session 私有目录 + locator，超 `maxInlineTokens`（base bundle 里 12500）时把工具结果换成预览 + 定位符（`packages/spill/spill-policy/src/index.ts:93-110`）；压前先 `ctx.toolResultPruner` 裁超大工具输出 |
| 提示缓存 | 系统提示分节 diff，只记 patch（`diffSystemPromptSections` `system-prompt.ts:255`） | session prefix **按实例冻结**（组合先于首次 `pre-step`，漂移落在 `'resume'` header 上）；`request/header` 只在真的不同才记（`agent-loop/src/agent.ts:620-640`） |

两家都把"保持可缓存前缀不变"当设计目标，但一个在**渲染层**做 diff，一个在**日志层**做 epoch。

## 7. 平台面

| | Pi | dsh |
| :--- | :--- | :--- |
| provider | `ModelRuntime implements Models`（`core/model-runtime.ts:172`）+ 虚拟模型路由（`core/virtual-models.ts`） | `ctx.llm` + 四个适配器族；`llm-pi-ai` 把 dsh 消息与 pi-ai 的 `Context/Message/Tool` 互转（`packages/llm/llm-pi-ai/src/context.ts:17`） |
| 终端 | 自研 TUI 库 `packages/tui`：差分渲染在 renderer 子类里内联（`tui-main-screen.ts:363-381` 比较上一帧行算 first/lastChanged，`BoundedTerminalWriter` `:18` 写 terminal），16 ms 节流（`tui.ts:518`） | 无 |
| 编辑器 | 无 | ACP server + Claude Code / Codex hook 桥 |
| 沙箱 | **无内建**：进程即权限边界（`docs/extensions.md:5-7`），要隔离就容器化（`docs/containerization.md`：Gondolin 微虚机 / Docker / OpenShell） | `ctx.sandbox` seam，后端链 `linux:[bwrap, landlock]`、`darwin:[seatbelt]`、`win32:[windows-acl]`（`packages/sandbox/sandbox-local/src/index.ts:160`），不可用即 **fail closed**；Windows 后端用 WRITE_RESTRICTED token + Low integrity，自称 `partial` |
| 权限 / 审批 | **无内建逐工具审批**；由扩展的 `tool_call` 钩子拦（`agent-session.ts:658`），文档里明确把权限交给"权限扩展" | `ctx.approval` seam（`ask` 决策在无审批服务时降级为拒绝）+ `ctx.permissionPresets` + sandbox policy |
| 凭据 | `~/.pi/agent/auth.json` + `RuntimeCredentials`（`core/model-runtime.ts:614`） | `ctx.credentials`：配置里只放**引用**，值在 `$DSH_HOME/.credentials.yaml`，跨进程写锁 + 原子写 |
| 远程执行 | 实验 Unix socket + CBOR | `packages/ssh`：一组 provider 同时换掉 subprocess / fs / sandbox |

一个值得抄的做法：dsh 的 fs / shell / subprocess / sandbox 共享同一个"执行世界"，所以**把 provider 指向远端沙箱，Bash、PTY、LSP 会一起搬过去，不需要给每个工具 fork 一份**。这就是它坚持"能力 seam 三角色（Service Definition / Service Provider / Consumer）"的实际回报。

## 8. 产物面

| | Pi | dsh |
| :--- | :--- | :--- |
| 主产物 | `@earendil-works/pi-coding-agent`，`bin.pi → dist/bundle/cli.js`；另出单文件 Bun 二进制 `dist/pi` | `@deepseek-ai/dsh`，唯一 bin；五个 profile |
| 库产物 | 7 个包：`chord` / `telemetry` / `pi-ai` / `durable` / `pi-agent-core` / `coding-agent` / `tui` | `@deepseek-ai/dsh-*` 上百个包，按能力族分组（`packages/README.md`） |
| 扩展分发 | Pi packages：npm / git 打包扩展 + 技能 + 模板 + 主题 | bundle 包：`package.json` 里 `dsh.bundle.patch` 指向自己的 patch 层 |
| 生成物也是产物 | `models.generated.ts`（模型目录）、Nix pin `nix/model-catalog.json` | typert 生成的 host/client 两份产物（`typert.host.js/.d.ts`、`typert.remote-client.js/.d.ts.map`），客户端调用可跳回 Host 实现 |
| 其它语言 | 无 | Python 两个 wheel（SDK + runtime-bin，runtime wheel 里是 SEA 单文件 dsh） |
| 原生 | 无 | `@deepseek-ai/node-addon-system`：`landlock-run`（静态 musl C）+ `system.node`（异步 `flock`），按 os/cpu 作为 optionalDependencies 发布 |
| 桌面 | 无 | Electron，`private: true`——发行物是安装器不是 npm 包 |

dsh 有**依赖治理**特征：框架层（Cordis）是**源码 vendor** 进来并 rescope 到 `@deepseek-ai`（`vendor/README.md`：可审计、可打补丁、钉版本）。
Pi 有**供应链治理**特征：直依赖精确钉版、`.npmrc` 设 `min-release-age=2`、install-lock 钉传递依赖、生命周期脚本白名单。

同一件事（"我不想被依赖漂移坑"）的两种正解：一个**收进仓库**，一个**钉死在锁文件**。

## 9. 切面

| | Pi | dsh |
| :--- | :--- | :--- |
| 扩展模型 | jiti 加载的进程内 TS 模块（`core/extensions/loader.ts:828-880`）；~50 个事件（`core/extensions/types.ts`） | Cordis 插件：`ctx.plugin()` 返回 Fiber，`ctx.effect()` 收集 disposer 并在卸载时**逆序**执行（`vendor/cordis/src/fiber.ts:415`） |
| 事件语义 | 钩子函数返回结果，宿主据此决定 | 五种分发模式（`emit / parallel / serial / bail / waterfall`，`vendor/cordis/src/events.ts:34`）；waterfall 不调 `next()` 即否决 |
| 注册的可逆性 | 卸载靠显式清理 | 注册即 effect，随 fiber 卸载自动回滚；同名服务二次注册报错 |
| 配置 | 全局 + 项目 `settings.json` 深合并，**项目配置未经 trust 不生效**（`core/settings-manager.ts:364`） | profile patch 层叠加 + `!!js` 惰性求值；`ctx.settings` 把 Config schema 投影成表单元数据 |
| 遥测 | 只有安装 ping（`core/telemetry.ts:8`） | OTel 接入（`packages/telemetry/otel`）+ 匿名身份（每 `$DSH_HOME` 一个随机 UUID，绝不从 hostname/网络/derive） |
| 安全姿态 | 扩展在进程内、用进程的操作系统权限跑；安全边界 = 信任决策（`resolveProjectTrusted` `core/project-trust.ts:53-104`） | 沙箱 fail closed + 审批 seam + 凭据只放引用 |

---

# 共性：领域不变量

逐列向下读，两家都填满、且填法结构一致的格子：

### 1. 语义正确性 —— "模型可见的，必须可从持久记录重建"

```text
领域不变量：模型请求不是"构造出来的"，而是"从会话记录投影出来的"。
证据：
  Pi  ：会话树 + 系统提示以分节持久化，工具集从 transcript 恢复（agent-session.ts:1809）
  dsh ：Session.deriveMessages() 是唯一消息来源（session/src/index.ts:856）；
        且 Session.append 在**编译期**要求 surface 事件必须带 SurfaceIntent，非 surface 事件禁止带（index.ts:718）
```

dsh 把这条不变量做得更硬：它有一个 `dsh-agent-loop/invariant` 伴随导出，用**重算**的方式验证"每个 loop 构造的请求都能从日志重建"。这是我在两个仓库里见到的最强的"不变量可执行化"。

### 2. 资源调度 —— 上下文窗口预算是硬约束

```text
领域不变量：上下文窗口是唯一无法回避的稀缺资源；
          凡是长会话，都必须有"阈值触发压缩 + 溢出恢复 + 保留近窗口"三件套。
证据：
  Pi  ：shouldCompact(contextTokens > contextWindow - reserveTokens)（compaction.ts:267），5 个触发点
  dsh ：thresholdRatio 0.8 / retainRatio 0.16 + 'context-overflow' 触发器 + spill 外化
```

两家都还多做了一件事：**保持可缓存前缀不变**。Pi 用系统提示分节 diff，dsh 用 session prefix 按实例冻结 + `request/header` 只在变化时记。这说明"省 token"在这个领域里是两条腿：少发内容，和让前缀命中缓存。

### 3. 时间优化 —— 减少无效往返与无效搬运

```text
领域不变量：要么减少模型往返，要么减少工具往返里的空转。
证据：
  Pi  ：工具默认并行、结果按源序发；取消后队列消息退回编辑器；重试只重试请求不重跑 pre-step
  dsh ：有界滚动池 + 屏障；取消时补合成 tool/result；重试"先持久化再重试"，且不重复 pre-step 与用户准入
```

### 再往上抽一层

```text
1. 语义正确性（可重建）
2. 资源调度（上下文窗口预算 + 缓存前缀）
3. 时间优化（减少无效往返与无效搬运）
```

和推理框架、kernel 编译器两次的收敛结果**位置完全一致**，内容是领域特化：

| | 推理框架 | kernel 编译器 | 智能体脚手架 |
| :--- | :--- | :--- | :--- |
| 1 | 语义正确性 | 语义正确性 | 语义正确性（可重建） |
| 2 | 资源调度（显存） | 硬件映射 | 资源调度（上下文窗口） |
| 3 | 时间优化 | 时间优化 | 时间优化 |

三次不同领域，第 1、3 条逐字相同，第 2 条是同一位置的领域特化。这已经不是巧合，是骨架的稳定性证据。

---

# 差异：设计空间

每一条都翻译成"设计选项 + 代价 + 决定因素"，而不是"甲这样、乙那样"。

### Q1：扩展以什么为界？

```text
选项甲（Pi）：进程内 TypeScript 模块 + 钩子函数（jiti 加载，~50 个事件）
              擅长：三行 npm 安装即可用；扩展能直接拿到进程内对象（TUI 渲染器、编辑器上下文）
              代价：产品各部分不可替换（loop、会话存储、工具注册表都是实现细节）
选项乙（dsh）：配置行 + service + 可逆 effect
              擅长：产品每一部分都可被第三方替换，且可 HMR、可 dump 出完整启动树
              代价：启动配置 94 行起（base patch），依赖解析语义、加载顺序都成为要理解的东西
决定因素：你要的是"一个可被改的 CLI"，还是"一个可被重组的平台"。
```

### Q2：谁拥有 agent loop？

```text
选项甲（Pi）：loop 是库，行为只能通过 AgentLoopConfig 的钩子改
              擅长：API 面窄、可预测；loop 代码 949 行可整段读完
              代价：想换掉整个循环策略，得 fork
选项乙（dsh）：loop 是一个插件，可以从配置里换掉，外部不许依赖具体实现
              擅长：策略与机制分离（goal 的 round、Ralph 的 fresh-agent 都靠组合实现，不改 loop）
              代价：loop 只能通过事件与日志与外界对话，间接层明显更厚
决定因素：是否需要"多种循环策略共存于同一产品"。
```

### Q3：会话状态是"一个文件"还是"一个可换后端"？

```text
选项甲（Pi）：单个 JSONL 树文件（id/parentId，v3）
              擅长：可读、可 grep、可导出、可分享；分支是文件内路径，"在任意点继续"变成写一行
              代价：格式即产品契约，迁移要写 v1→v2→v3 三段
选项乙（dsh）：事件日志 + surface 投影 + SessionPersistence 接口（create/open/flush/stat/list）
              擅长：能换 JSONL / SQLite / 云；投影可以从日志重算出任意派生状态
              代价：v4 不兼容时**直接拒绝**（没有升级路径），版本纪律极严
决定因素：会话是"用户的文件"，还是"产品的数据"。
```

### Q4：工具结果谁写日志？

```text
选项甲（Pi）：CLI 层边收事件边写（agent-session.ts:1103）
              擅长：写在哪、怎么写一目了然
              代价：写日志与执行耦合在同一个类里
选项乙（dsh）：注册表从不写日志，只返回冻结值；只有 loop 写 tool/call + tool/result
              擅长：工具无法伪造历史；"模型可见 ⟺ 已记录"是结构性的而非靠纪律
              代价：需要一条 scheduler seam（prepare/dispatch/finalize/finish 四个阶段）来让 loop 既能重叠执行又保持策略有序
决定因素：日志是"副产品"还是"唯一事实来源"。选了后者，就必须把写权限收成一处。
```

### Q5：提示词怎么拼？

```text
选项甲（Pi）：一次性组装成具名分节，之后只记分节 patch
              擅长：前缀稳定，缓存命中率高；diff 小
              代价：动态新增一段要设计成"分节"
选项乙（dsh）：注册表（section/context/tools provider/variable）+ 中央 order 表 + assemble waterfall，每步重装
              擅长：任意插件都能贡献提示内容，顺序可被集中仲裁（冲突即报错）
              代价：每步都要重装；要靠 surface 节点的 append/replace 判断来决定记不记日志
决定因素：提示词是"宿主拼好的常量"，还是"多插件共同贡献的视图"。
```

### Q6：环境上下文（AGENTS.md）放哪？

```text
选项甲（Pi）：放系统提示的一个分节
              擅长：不占对话历史、不参与压缩
              代价：不参与会话重放（要靠系统提示的重放语义单独保证）
选项乙（dsh）：注入成持久 user 角色消息
              擅长：照常 replay / compact，模型请求可完全从日志重建
              代价：每轮占上下文，且会被压缩策略当成普通历史
决定因素：这条"环境事实"算不算会话的一部分。
```

### Q7：权限与沙箱放哪？

```text
选项甲（Pi）：不内建，交给扩展或容器
              擅长：核心保持小；不替用户决定安全模型（README 明说不含权限系统）
              代价：默认姿态就是"用进程的全部权限跑"
选项乙（dsh）：内建 seam（approval + permission presets + sandbox 后端链，不可用即 fail closed）
              擅长：能同时服务本地 CLI 与托管 Web / Desktop / SDK
              代价：要维护三个平台的后端（bwrap/landlock、seatbelt、windows-acl），且要承认"partial"
决定因素：产品是单人本机工具，还是要跑在别人的机器 / 浏览器里。
```

### Q8：工具怎么并发？

```text
选项甲（Pi）：默认并行，按 assistant 源序发结果
              擅长：简单、对模型友好（顺序一致）
              代价：无法表达"这两个必须互斥"
选项乙（dsh）：先按 executionMode 分组（独占屏障 vs 有界滚动池），且**开跑前重新分类**，
              结果按模型序**连续**提交
              擅长：互斥工具（改文件 vs 读文件）能安全并发；提交顺序严格模型序，重放一致
              代价：调度器明显复杂（reclassify before start / commitReady / 合成中止结果）
决定因素：工具集里有没有"会互相踩"的写工具。
```

### Q9：加一个新入口（Web / 编辑器 / 远程）要改什么？

```text
选项甲（Pi）：CLI 加一个 mode，或起一个实验性 server；SDK 走 import 或 RPC
              擅长：接入面变化不牵动核心
              代价：每个入口各自处理会话生命周期
选项乙（dsh）：加一个 bundle + profile，共享同一个 loop 与同一套 session 事件
              擅长：web / headless / acp / sdk / desktop 全部免费拿到同一套语义
              代价：入口必须走同一个启动器（CI 强制），灵活性换一致性
决定因素：入口数量与一致性哪个更重要。
```

### Q10：模型目录谁维护？

```text
选项甲（Pi）：脚本拉上游目录编译进 TS（40+ 家，generate-models.ts 3599 行），离线可用
              擅长：开箱即用，类型安全，Nix 场景能锁目录
              代价：目录是生成物，需要门禁（check:model-data）与重生成流程
选项乙（dsh）：provider 插件自己声明 route，pi-ai 的目录只作默认值
              擅长：自定义/自托管 route 不需要改代码，YAML 写完即可
              代价：默认覆盖度取决于挂了哪个适配器
决定因素：用户是"选一个已支持的模型"，还是"接一个自己的端点"。
```

---

# 核心技术

S5 是横向（同一面比两家），这一节是纵向（一家凭什么跟别人不一样）。**凡是两家都有的，属于上文共性，不列在这里。**

## Pi

1. **会话树 + 分支语义**。每个 entry 有 `id` / `parentId`，在任意 entry 继续就产生新分支；`fork` / `clone` / `branchWithSummary` 让"从某点重来"成为一等操作（`core/session-manager.ts:1579/1600/1632/1815`）。会话历史不是线性日志，是树——这是 Pi 最独特的抽象。
2. **系统提示分节 + 增量 patch**。提示词按具名分节组装并可完整替换（`--system-prompt`），后续变化只记 `diffSystemPromptSections`（`core/system-prompt.ts:255`）。这既是缓存策略，也是审计策略。
3. **模型目录生成器**。`scripts/generate-models.ts` 把上游 catalog 编译成 TS 表，`check:model-data` 做门禁，Nix 构建用 pin 保证离线一致性（`nix/model-catalog.json`）。
4. **19 行的 StreamFn 注入接缝**。`setDefaultStreamFn` / `getDefaultStreamFn`（`packages/agent/src/stream-fn.ts:11`）——宿主替换整个模型运行时的唯一入口，`packages/agent` 内不出现任何 provider 概念。
5. **codemode：QuickJS-WASM 沙箱**。每次执行起一个 worker 线程 + 一个 QuickJS VM，能力集就是注入的工具 map，跨边界只走 JSON 字符串，没有 fs / fetch / require（`packages/codemode/src/runtime/host.ts:340`、`worker.ts:63-101`）。
6. **chord：产品内的组合基质**。facet / service / replicated state / delta / bundler（`packages/chord/src/api.ts:22/69/73/91`），被 `durable` / `server` / `client` / `protocol` / `coding-agent` 运行时共用——一个与 agent 概念无关的通用插件运行时，长在自己的仓库里。
7. **durable：把 agent loop 变成可恢复的持久任务**。`Storage` / `Tx` / `Session` + `GenerationTask` / `ToolTask` / `CompactionTask`（`packages/durable/src/types.ts:1015/766/921`，`src/harness/*`），三种后端（memory / jsonl / sqlite）。
8. **自有的远端协议**。长度前缀 CBOR、`PROTOCOL_VERSION = 8`、`RpcTarget` 支持 `{serverId, sessionId, attachmentId}` 三级寻址（`packages/protocol/src/protocol.ts:24-38`、`framing.ts:28`）。
9. **TUI 差分渲染**。diff 状态内联在 renderer 子类里（主屏按行 first/lastChanged，`tui-main-screen.ts:363-381`；备用屏按行字符串比较 `tui-alt-screen.ts:1706`），16 ms 节流调度（`packages/tui/src/tui.ts:518`）。
10. **供应链硬化**。直依赖精确钉版 + `min-release-age=2` + install-lock 钉传递依赖 + 生命周期脚本 allowlist + 预提交拦 lockfile（`README.md`、`AGENTS.md`）。

## dsh

1. **全插件化 + 可逆注册**。`ctx.effect()` 收集 disposer，卸载时逆序执行（`vendor/cordis/src/fiber.ts:415`）；`ctx.on()` 的监听器也随 fiber 死（`events.ts:242-255`）。"注册即 effect"让热卸载和插件替换成为结构性能力。
2. **profile / bundle / patch 三层组合**。profile 列 bundle，bundle 声明自己的 patch 文件，patch 按 id 整行替换；`!!js` 惰性求值到条目自己的 fiber（`packages/boot/app-boot/src/index.ts:539/973`，`vendor/loader/src/config/utils.ts:5-22`）；`dsh --dump-config` 能看到自己机器上真实启动的树。
3. **能力 seam 三角色**。Service Definition / Service Provider / Consumer，角色在独立演化时分包（`packages/README.md`、`docs/glossary.md`）。最有说服力的回报：fs 与 subprocess 指向同一执行世界，所以换一个远端 provider，Bash / PTY / LSP 一起搬。
4. **三个事件域 + waterfall 语义**。session 事件（持久）、`agent/*`（实时）、能力事件（策略与适配器），waterfall 监听器不调 `next()` 即否决（`docs/architecture.md`、`vendor/cordis/src/events.ts:234-250`）。
5. **"模型可见 ⟺ 已记录"的编译期强制**。`Session.append` 对 surface 事件**必填** `SurfaceIntent`、对非 surface 事件**禁止**该字段（`packages/core/session/src/index.ts:718-721`）；`deriveMessages()` 是唯一消息来源；派生消息深度冻结并打 `markAgentLoopRequest` 标记。
6. **请求不变量可执行化**。`@deepseek-ai/dsh-agent-loop/invariant` 从日志**重算**每个 loop 请求，把"可重建"从口号变成 CI 门禁（`.agents/notes/implemented/architecture/2026-07-19-package-owned-invariant-service.md:65-66`）。
7. **typert 类型图 + Remote 装饰器 → 两遍产物**。`@Remote` 标过的方法才进 Client 面，生成 `typert.host.*` 与 `typert.remote-client.*`（带 `.d.ts.map` 跳回实现）；unary 走 `POST /api/<ns>/<method>`，流走 `/api/remote.mux`（`docs/api-gateway.md:7-9/58`）。
8. **agent scope**。注册以不透明 scope key 分层（在 loop 里 key 就是 Agent 对象本身），同名就近遮蔽，`tools.restrict` 做交集过滤；被过滤掉的全局工具在提示里不存在、执行时也拒绝，与"从未存在"不可区分（`docs/glossary.md#agent-scope`，`packages/core/tools/src/index.ts:1097/1178`）。
9. **PTC（程序化工具调用）**。模型可以只调 `run_code`，由沙箱里的脚本去调工具；配合工具呈现模式 `native | ptc | both`（`packages/core/tools/src/index.ts:1247`、`packages/ptc-runtime`）。
10. **spill**。超限工具结果外化成 session 私有文件 + locator，失败一律 best-effort 保留原文（`packages/spill/spill-policy/src/index.ts:93-110`）。
11. **沙箱 fail closed 三平台后端**。后端链按平台选择，能力探测分 full / partial / unusable，不可用即拒绝；Windows 用 WRITE_RESTRICTED token + Low integrity 且自称 partial（`packages/sandbox/sandbox-local/src/index.ts:160/503`、`sandbox-windows-acl`）。
12. **框架层 vendor 化 + 复用对手的模型层**。Cordis 源码 vendor 进仓库并 rescope（`vendor/README.md`）；同时把 Pi 的 `pi-ai` 当第三方 provider 用，还打补丁去掉它"每个 delta 重解析 tool JSON"的行为（`patches/@earendil-works__pi-ai@0.87.1.patch`）——因为增量装配由 dsh 自己的 `BlockAssembler` 负责。

---

# 横切验证：一个最小单元走完全程

最小完整单元：**一条用户消息 → 到它第一次落进模型请求**。六问必须完全一致地问两家。

| 问 | Pi | dsh |
| :--- | :--- | :--- |
| 1. 外部输入在哪进入？ | `AgentSession.prompt(text)`（`core/agent-session.ts:1968`）← CLI 拼的 `buildInitialMessage`（`cli/initial-message.ts:20`） | `Agent.followup/send` 入 inbox（`packages/core/agent/src/runtime-types.ts`）← Web RPC / SDK JSON-RPC / ACP |
| 2. 第一次转换在哪？ | prompt 内部按序展开（扩展命令 → input 钩子 → `/skill:` → 模板）→ 生成 `AgentMessage` | `inbox.claim()` → `agent/pre-step` waterfall 决定 enter / reject → 记 `user/message` |
| 3. 内部表示是什么？ | `AgentMessage[]` + `AgentContext`（`packages/agent/src/types.ts:502`） | 持久事件日志 + `deriveMessages()` 投影出的消息数组 |
| 4. 谁决定下一次计算？ | `AgentSession._runAgentPrompt` 的 `while (!abortRequested)` 调 `agent.continue()`（`:1822-1850`） | `ReactLoopAgent`：`kick()` 的 `while (await this.turn())`，一个 step = 一次请求 + 它引发的工具（`agent.ts:254/296/398`） |
| 5. 谁调最底层？ | `streamAssistantResponse` 里的 `streamFunction(...)`（`agent-loop.ts:403`），最终落到 pi-ai 的 `Models.streamSimple` | loop 经 `llm.prepareCall()` 绑定调用能力后 dispatch `llm/stream`（`packages/llm/llm/src/index.ts:929/1137`） |
| 6. 结果在哪变回外部形式？ | `AgentEvent` 流 → TUI 渲染 / print JSON / RPC 响应 | `session/event`（持久）与 `agent/*`（实时）→ 投影给 Web / SDK；`agent/assistant-stream` 是瞬态帧 |

六问都答得出来 → S1 划的面没有漏。副产品是上手路径：

```text
读 Pi：  core/agent-session.ts（入口）→ packages/agent/src/agent-loop.ts（循环）→ packages/ai/src/models.ts（请求）
读 dsh： docs/architecture.md 的 turn flow → packages/core/agent-loop/src/agent.ts → packages/core/tools/src/index.ts
```

---

# 可迁移的提问清单

下次遇到任何一个智能体脚手架，先问这一组（不依赖具体项目）：

**定位**
- 它把哪一层当作核心抽象：循环、会话、工具、还是组合？
- 用一句话说清"它不是别的什么"（不是模型前向 + API）。
- 它的 loop 可以被替换吗？换掉之后，产品还剩多少？

**结构**
- 接入面有几种？它们共享同一套会话语义，还是各写一套？
- 模型可见的输入，能不能只从持久记录重建出来？
- 工具结果的写权限收在一处，还是分散在调用方？
- 上下文预算由谁计量、谁触发压缩、压缩后原记录还在不在？
- 提示词是"组装一次 + 打补丁"还是"每步重装 + 判变化"？
- 环境上下文（AGENTS.md 类）放系统提示还是放会话消息？
- 权限、沙箱、凭据分别是内建 seam 还是交给外部？
- 工具并发怎么表达互斥？结果按谁的顺序提交？

**判据**
- 哪些能力是切面（同时影响加载、调度、执行、缓存、输出）？
- 每处差异的决定因素是什么（本机 CLI 还是托管服务；单策略还是多策略）？
- 它把什么不稳定性隔离在了哪一层？
- 这个选择的代价是什么？

**收口**
- 这个领域躲不掉的三件事是什么？（正确性 / 资源 / 时间）
- 换一个新脚手架，这套面还成立吗？

---

# 附：一次意外的交叉验证

并行学习法说"设计空间要靠并排读才能看出来"。这次多了一条更硬的证据：**两家产品自己做了这个对照实验。**

```text
dsh 的 packages/llm/llm-pi-ai 自称 "design-verification twin of dsh-llm-deepseek"
（packages/llm/llm-pi-ai/package.json:3）

也就是说：dsh 手写了一个 DeepSeek 适配器，又用 Pi 的 pi-ai 实现了第二个，
两个都挂在同一个 LlmAdapter seam 的后面，互为对照。
```

它还顺手证明了一件事：**能被跨产品复用的，是没有主张的那一层。**

```text
被复用：pi-ai —— 单次请求的 provider 抽象（无状态、无循环、无策略）→ 可以换成插件
未被复用：Pi 的 agent loop / 会话树 / TUI —— 有主张、有状态、有取舍 → 复用了就要接受它的世界观
```

如果你要设计一个"可被复用的那一层"，这就是它的定义：**只描述一次请求的输入输出，不描述谁在什么时候发出它。**

---

# 最终的认知

```text
Pi
  → 看"一个 agent loop + 一棵会话树，怎么被接到 4 种模式、40+ 家 provider、8 个工具上"
  → 看它的边界纪律：packages/agent 里不出现 provider，packages/ai 里不出现 loop

dsh
  → 看"一棵插件树怎么长成一个完整产品"
  → 看它的强制手段：编译期 surface 标记、请求可重建的不变量测试、启动器唯一性 CI 门禁
```

最值得带走的两条判据：

> **这一步是谁决定的——用户显式声明，还是系统推导？**
> 用在扩展面上就是：这个能力是"宿主提供的功能"，还是"配置里的一行"？Pi 与 dsh 的全部分歧几乎都从这里长出来。

> **哪些东西可以被替换，替换后语义是否一致？**
> Pi 的答案是"库可以换，CLI 的语义不变"；dsh 的答案是"任何一行都可以换，包括 loop，但所有入口的会话语义取自同一份日志"。

以及一个可复用的元判断：

```text
智能体脚手架的复杂度几乎全部来自一件事——
把"一次会中断、会恢复、要省钱、要被扩展"的对话，
做成一个能被重放的状态机。
剩下的都是它的推论。
```

---

参考：`C:/Projects/pi`、`C:/Projects/deepseek-harness`、`C:/Projects/jojo-blog/content/元学习/并行学习法.md`、`C:/Projects/jojo-blog/content/人工智能/推理框架.md`、`C:/Projects/jojo-blog/content/人工智能/TileLang与Triton.md`
