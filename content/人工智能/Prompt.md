# 快速理解复杂项目

- Round 1
  ```prompt
  系统全景说明（System Overview）
  按以下格式说明系统：
  - 项目目标 / 核心功能
  - 用户路径（User Flow）
  - 输入 / 输出定义
  - 边界（系统做什么、不做什么）
  ```

- Round 2
  ```prompt
  功能模块拆解（Functional Decomposition） 
  把系统拆成最小“职责单元”。 通过文字和画图，比如mermaid的flowchart+subgraph+配色。通过子图和连线，绘制模块之间的关系。图外文字说明图中模块的作用，输入与输出。
  ```

- Round 3
  ```prompt
  业务流程 / 控制流
  按业务流程进行拆分，对每个流程画出 mermaid 的时序图，并给每个时序图配上文字说明
  ```

- Round 4
  ```prompt
  数据流 & 状态模型
  先拆分数据流和状态模型，再绘制
  
  - 数据从哪里来 → 去哪里
  - 状态如何变化
  - 数据或状态的生命周期。
  
  你可以自行决定选择使用mermaid 最合适的 flowchart、subgraph、stateDiagram-v2、journey、note来绘制数据流模型
  ```

- Round 5
  ```prompt
  依赖分析（Dependency Mapping）
  
  外部依赖：对外部服务、组件的依赖
  
  内部依赖： 模块之间调用关系
  你可以选择使用mermaid的各种图像显示。记得将在每个图下面将每个模块映射到的具体文件路径显示出来。
  ```

- Round 6
  `````prompt
  分层架构图（D2）
  
  目标：
  生成一张“横向分层 + 纵向模块排列”的系统架构图，使用 D2 的 grid diagram 布局。
  
  核心目标：
  每一层必须是一整行，并且每一行的最左侧必须是该层标题。
  
  【整体布局】
  
  1. 必须使用：
     direction: right
     grid-rows: N
     grid-columns: M
  
  2. N = 层数。
  3. M = 所有层中“标题 + 模块”数量的最大值。
  4. 每一层必须刚好占满 M 个 grid 单元。
  5. 如果某一层模块数量不足 M，需要在该层末尾补空白占位节点。
  6. 空白占位节点必须放在该层最后，不能插入标题和模块之间。
  
  【每行结构】
  
  每一行必须严格是：
  
  LayerTitle + Module1 + Module2 + Module3 + ... + Blank...
  
  也就是说：
  
  - 第 1 个节点：层标题
  - 第 2 到第 K 个节点：该层功能模块
  - 第 K+1 到第 M 个节点：空白占位节点
  
  【层标题强约束】
  
  1. 层标题节点必须是该行声明顺序中的第一个节点。
  2. 层标题节点必须位于最左侧。
  3. 层标题节点不能嵌套在任何容器中。
  4. 层标题节点必须和该层模块处于同一层级。
  5. 不允许把层标题放到该行最后或右侧。
  
  【模块强约束】
  
  6. 模块节点必须紧跟在层标题节点之后。
  7. 模块节点不能嵌套。
  8. 模块粒度必须是“功能模块”，不要使用文件名或路径。
  
  【禁止事项】
  
  9. ❌ 不允许使用容器、subgraph、group、嵌套对象。
  10. ❌ 不允许使用 L1: { ... } 这种包裹结构。
  11. ❌ 不允许出现任何连线。
  12. ❌ 不允许使用 ->、--、<->。
  13. ❌ 不允许把层标题和模块放在不同层。
  14. ❌ 不允许省略 grid-columns。
  15. ❌ 不允许某一行节点数量少于 grid-columns。
  16. ❌ 不允许空白节点出现在行首或行中。
  
  【空白占位节点规则】
  
  当某一层节点数量不足 grid-columns 时，必须补空白节点：
  
  ExampleBlank1: ""
  
  并设置：
  
  ExampleBlank1.style.opacity: 0
  ExampleBlank1.style.stroke: "transparent"
  ExampleBlank1.style.fill: "transparent"
  
  【视觉风格】
  
  17. 每一层使用统一配色：
     - 层标题：深色
     - 模块：浅色，同色系
  
  18. 不同层颜色必须不同。
  19. 所有节点使用矩形默认样式。
  20. 层标题字体颜色使用白色。
  21. 模块字体颜色使用黑色。
  
  【正确示例】
  
  ```D2
  direction: right
  grid-rows: 3
  grid-columns: 5
  
  L1Title: "入口层"
  CLI: "CLI Interface"
  Config: "Configuration Input"
  Intent: "Intent Collector"
  L1Blank1: ""
  
  L2Title: "编排层"
  Runner: "Pipeline Runner"
  Initializer: "Project Initializer"
  Orchestrator: "Agent Orchestrator"
  Controller: "Workflow Controller"
  
  L3Title: "状态层"
  State: "State Manager"
  Knowledge: "Knowledge Base"
  Metadata: "Project Metadata"
  L3Blank1: ""
  
  L1Title.style.fill: "#1565C0"
  L1Title.style.font-color: "#FFFFFF"
  CLI.style.fill: "#E3F2FD"
  Config.style.fill: "#E3F2FD"
  Intent.style.fill: "#E3F2FD"
  L1Blank1.style.opacity: 0
  L1Blank1.style.stroke: "transparent"
  L1Blank1.style.fill: "transparent"
  ````
  
  【输出要求】
  
  22. 只输出 D2 代码。
  23. 不要解释。
  24. 不要添加额外说明。
  25. 不要使用 Markdown 标题。
  26. 不要在 D2 代码外输出任何文字。
  `````

- Round 7
  ```prompt
  技术选型（Technology Stack）
  
  请按以下要求输出系统的技术选型方案。并且，联网搜索，尽量复用已经存在的模块，减少重复造轮子。
  
  【输出结构】
  
  # 1. 总体技术栈
  
  # 2. 分层选型
  
  # 3. 关键决策说明（每条不超过 3 行）
  
  ```

- Round 8
  ```prompt
  实现顺序（Implementation Sequence）
  
  请输出从零实现该系统的 **最小增量式交付顺序**。
  
  【规则】
  1. 按“垂直切片”划分，而不是按层划分
  2. 每个阶段 = 一个可运行的最小功能子集
  3. 阶段之间靠“依赖”串联，不超前实现
  
  【输出格式】
  
  ### 阶段 0 – 骨架构建
  
  ### 阶段 1 – 核心闭环
  
  ### 阶段 2 – 状态与异常
  
  ### 阶段 3 – 扩展功能
  
  【输出要求】
  - 每个阶段必须有一个“可运行验证方式”
  - 不要写测试框架相关（放到 Round 10）
  - 不要写部署相关
  ```

- Round 9
  ```prompt
  开发指导（Development Guide）
  
  输出面向 **实际编码人员** 的开发指南，不包含架构理论。
  
  【章节要求】
  
  编码规范
  模块开发步骤模板
  如何新增一个模块
  调试方法
  
  ```

- Round 10

  ```prompt
  测试资产的准备（Test Assets）
  
  请输出一套**可落地执行**的测试资产清单与内容示例。可供本地搭建测试环境。
  ```

