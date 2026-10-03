# 什么是“Business UI Pattern”

UI Pattern 可以理解为：**在特定业务场景中反复出现、已经被验证过的界面结构与交互组合**。

比如：

- “登录/注册/引导”是一套 SaaS 获客流程模式。
- “表格 + 筛选 + 排序 + 分页 + 批量操作”是一套后台数据管理模式。
- “树形结构 + 标签页 + 分栏 + 属性面板”是一套编辑器模式。
- “聊天 + 流式输出 + 停止/重新生成/分支”是一套 AI 对话应用模式。

这一层的目标不是掌握某个具体组件，而是：**看到业务需求，能迅速反应出它应该由哪些成熟模式拼装而成。**

# SaaS 业务 UI Pattern

SaaS 是 Software as a Service，典型特征是：多租户、订阅制、团队协作、权限、配额、账单。

## Login / Signup / Onboarding

- **Login**：登录页。通常包含邮箱密码、第三方登录、忘记密码、验证码等。
- **Signup**：注册页。可能包含邀请码、企业邮箱验证、试用开通。
- **Onboarding**：新用户引导。比如创建第一个项目、邀请成员、选择模板、填写资料。

这一组解决的是：**用户如何进入产品并完成初始激活。**

## Workspace / Team / Invite

- **Workspace**：工作区。SaaS 中常见的隔离单位，一个账号可能有多个工作区。
- **Team**：团队成员管理。
- **Invite**：邀请成员加入，通常涉及邮件邀请、链接邀请、角色分配。

这一组解决的是：**多用户如何组织、隔离和协作。**

## Billing / Subscription / Usage / Quota

- **Billing**：账单页，发票、支付方式、历史账单。
- **Subscription**：订阅计划，如 Free / Pro / Team / Enterprise。
- **Usage**：用量展示，如 API 调用次数、存储空间、 seats 数量。
- **Quota**：配额限制，如超出后提示升级、限制功能。

这一组解决的是：**SaaS 如何商业化、限制资源、引导付费。**

## Settings / API Keys / Permissions

- **Settings**：设置页，通常分组很多，如个人设置、组织设置、安全设置。
- **API Keys**：API 密钥管理，创建、复制、撤销、权限范围。
- **Permissions**：权限设置，谁能做什么。

这一组解决的是：**配置、安全与访问控制。**

# Admin / Dashboard Business UI Pattern

这类是后台管理系统、数据看板、运营平台的核心模式。

## Dashboard

仪表盘。通常展示：

- 关键指标卡片
- 图表
- 最近活动
- 待办事项
- 快捷入口

目标是：**让管理者快速了解全局状态。**

## Data Table / Filter / Sort / Search / Pagination

这是后台最核心的一组模式：

- **Data Table**：数据表格，展示结构化数据。
- **Filter**：筛选，如按状态、时间、负责人过滤。
- **Sort**：排序。
- **Search**：搜索。
- **Pagination**：分页，或无限滚动。

这一组解决的是：**大量数据如何被高效浏览和查找。**

## Bulk Action / CRUD

- **Bulk Action**：批量操作，如批量删除、批量导出、批量改状态。
- **CRUD**：增删改查，Create / Read / Update / Delete。

这是管理系统的基本操作闭环。

## Audit Log / RBAC

- **Audit Log**：审计日志，记录谁在什么时候做了什么。
- **RBAC**：Role-Based Access Control，基于角色的权限控制。

这一组解决的是：**企业级系统的安全、合规与权限管理。**

# Editor Business UI Pattern

编辑器类产品，如 IDE、设计工具、低代码平台、文档编辑器。

## Tree View / Tabs / Split Pane / Inspector

- **Tree View**：树形结构，如文件树、目录树、组件树。
- **Tabs**：标签页，同时打开多个文件或视图。
- **Split Pane**：分栏布局，如左右分栏、上下分栏。
- **Inspector**：属性面板，展示和编辑当前选中对象的属性。

这一组解决的是：**复杂对象如何组织、切换和查看细节。**

## Toolbar / Command Palette / Context Menu

- **Toolbar**：工具栏，常用操作按钮。
- **Command Palette**：命令面板，如 VS Code 的 Ctrl+Shift+P。
- **Context Menu**：右键菜单，针对当前上下文操作。

这一组解决的是：**操作入口如何高效触达。**

## Drag & Drop / Keyboard Shortcut / Autosave

- **Drag & Drop**：拖拽，如拖动文件、调整顺序、拖入画布。
- **Keyboard Shortcut**：快捷键。
- **Autosave**：自动保存。

这一组解决的是：**高频编辑操作如何更顺畅、更安全。**

# AI Application Business UI Pattern

## Chat / Streaming Response / Stop / Regenerate / Branch

- **Chat**：对话界面。
- **Streaming Response**：流式输出，逐字显示。
- **Stop**：停止生成。
- **Regenerate**：重新生成。
- **Branch**：分支，从某条消息另开一条对话线。

这一组解决的是：**人与模型多轮对话的基本交互。**

## Tool Call / Citation / Artifact

- **Tool Call**：工具调用展示，如搜索、代码执行、数据库查询。
- **Citation**：引用来源展示。
- **Artifact**：产物展示，如生成的代码、文档、网页、图表。

这一组解决的是：**AI 不只输出文本，还调用工具、引用来源、生成可操作产物。**

## Model Selector / Prompt Composer / Attachment / Thinking / Progress State

- **Model Selector**：模型选择器，如 GPT、Claude、本地模型。
- **Prompt Composer**：提示词输入区，可能支持变量、模板、系统提示。
- **Attachment**：附件上传，如图片、PDF、代码文件。
- **Thinking / Progress State**：思考中、进度状态、步骤展示。

这一组解决的是：**AI 应用的输入、控制与过程透明性。**