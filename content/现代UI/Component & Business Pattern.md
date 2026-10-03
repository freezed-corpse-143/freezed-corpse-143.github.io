# 什么是 Component & Business Pattern

**Component**：基础 UI 组件，比如按钮、输入框、弹窗。  
**Business Pattern**：由组件组合而成的、解决某类业务场景的固定交互模式，比如登录表单、筛选栏、分页列表、向导流程。

这一层之所以重要，是因为它决定了你能否：

- 快速把需求翻译成界面结构
- 选对交互模式，而不是硬造
- 和产品、设计、后端沟通时用同一套语言
- 避免“功能能做，但体验很怪”

所谓 **UI Pattern Vocabulary（UI 模式词汇表）**，就是你脑子里有一套现成的“模式库”。别人说“要一个能快速跳转的命令面板”，你立刻想到 Command Palette；说“要一个不打断操作的轻提示”，你想到 Toast，而不是 Alert。

# Navigation：导航类模式

导航解决的是：**用户在哪、能去哪、怎么去**。

- **Navbar**：顶部全局导航，通常放品牌、主入口、用户菜单。
- **Sidebar**：侧边导航，适合后台、多层级、模块多的系统。
- **Tabs**：同一上下文下的平级视图切换，比如“详情 / 评论 / 历史”。
- **Breadcrumb**：面包屑，显示层级路径，帮助返回上级。
- **Stepper**：步骤器，适合多步流程，比如下单、注册、审批。
- **Pagination**：分页，适合大列表，强调页码和总量。
- **Command Palette**：命令面板，键盘驱动，快速搜索和执行操作，如 VS Code 的 `Cmd+K`。
- **Bottom Navigation**：底部导航，移动端主入口切换，通常 3–5 个。

**使用边界**：  
Tabs 是同级切换，Breadcrumb 是层级回溯，Stepper 是流程推进，Pagination 是数据分页。它们不是互替关系，而是不同导航问题。

# Input：输入类模式

输入解决的是：**用户如何录入、选择、上传、搜索数据**。

- **Input**：单行文本。
- **Textarea**：多行文本。
- **Select**：从固定选项里选一个。
- **Combobox**：可输入 + 可下拉选择，适合选项多或需要搜索。
- **Checkbox**：多选。
- **Radio**：单选，选项少且需要平铺。
- **Switch**：开关，立即生效的二元状态。
- **Slider**：范围或数值调节。
- **Date Picker**：日期选择。
- **File Upload**：文件上传。
- **Search**：搜索输入，通常带建议、历史、快捷键。
- **Tag Input**：标签输入，适合多值、自由输入，如邮箱收件人、关键词。

**关键边界**：

- Select vs Combobox：选项少用 Select，选项多或要搜索用 Combobox。
- Checkbox vs Radio：多选用 Checkbox，单选用 Radio。
- Switch vs Checkbox：Switch 是“立即生效”，Checkbox 通常要提交。

# Feedback：反馈类模式

反馈解决的是：**系统状态如何告诉用户**。

- **Toast**：轻量、短暂、不打断，比如“已保存”。
- **Alert**：重要提示，通常需要用户注意，可能阻断。
- **Progress**：进度条，显示完成比例。
- **Spinner**：加载中，短时等待。
- **Skeleton**：骨架屏，内容加载前的占位，减少跳动。
- **Empty State**：空状态，告诉用户“这里为什么没内容、下一步做什么”。
- **Error State**：错误状态，说明出错原因和恢复方式。
- **Confirmation**：确认操作，防止误删、误提交。
- **Undo**：撤销，适合可逆操作，比确认更轻。

**关键边界**：

- Toast vs Alert：Toast 不打断，Alert 打断。
- Spinner vs Skeleton：Spinner 适合未知等待，Skeleton 适合已知结构的内容加载。
- Confirmation vs Undo：高风险且不可逆用 Confirmation，可逆操作可用 Undo。

# Overlay：浮层类模式

浮层解决的是：**在不离开当前页面的前提下，展示额外信息或操作**。

- **Tooltip**：悬停/聚焦时显示简短说明，纯信息，不可交互。
- **Popover**：点击/悬停触发的浮层，可放少量交互内容。
- **Dropdown**：下拉菜单，通常是一组操作或选项。
- **Context Menu**：右键菜单，和当前上下文强相关。
- **Dialog**：模态对话框，阻断当前操作，要求用户处理。
- **Drawer**：抽屉，从侧边滑出，适合表单、详情、设置。
- **Sheet**：底部或侧边面板，移动端常见，轻量模态。
- **Command Palette**：命令面板，键盘驱动的全局操作入口。

**必须搞明白的使用边界**：

- **Tooltip ≠ Popover**  
  Tooltip 只展示文本提示，不承载复杂交互；Popover 可以放按钮、表单、链接。

- **Popover ≠ Dialog**  
  Popover 不阻断页面，适合轻量操作；Dialog 是模态，阻断当前流程，要求用户先处理。

- **Dialog ≠ Drawer**  
  Dialog 聚焦、打断、适合确认或小表单；Drawer 不一定要完全阻断，适合较长内容或侧边任务。

- **Dropdown ≠ Context Menu**  
  Dropdown 通常由按钮触发，是显式操作入口；Context Menu 由右键触发，和鼠标位置、上下文对象强相关。

- **Command Palette ≠ Dropdown**  
  Command Palette 是全局、键盘优先、可搜索的命令入口；Dropdown 是局部、有限选项的操作菜单。