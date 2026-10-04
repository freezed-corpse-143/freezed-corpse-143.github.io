# 统一框架

```text
终端 UI 框架
├─ 接入面：怎么描述界面（JSX 组件树 / Widget 构造 + Rect / Element 管道装饰）
├─ 表示面：内部 UI 表示对象是什么（DOMElement⊕Yoga / Buffer⟨Cell⟩ / Node 树 + Screen）
├─ 布局面：谁算位置和尺寸（Yoga WASM flexbox / Cassowary 约束求解 / 两遍协议 + 整数 flex）
├─ 渲染面：表示对象怎么写进字符网格（树遍历写操作队列 / Widget::render 写 Cell / Node::Render 写 Screen）
├─ 控制面：谁拥有事件循环、谁决定下一帧（React commit 驱动 / 调用者 / App 自带）
├─ 状态面：库自己存什么、活多久（Ink 实例 + 上一帧字符串 / Terminal 双 Buffer / App + Component 树）
├─ 输入面：字节怎么变成"某组件的一次按键"（stdin→解析器→EventEmitter→useInput / 完全外置 / 解析器→Event→惰性 OR）
├─ 平台面：终端抽象（Node 流，无后端抽象 / Backend trait + 4 实现 / #ifdef + 运行时能力探测）
├─ 产物面：交给终端什么（ANSI 字符串 / 变化 cell 迭代器 / 全量网格 + 光标归位）
└─ 切面层：样式、Unicode 宽度、可访问性、测试后端、异步/动画、滚动
```

三个项目的根本区别，不是"支持哪些终端"，而是**把哪一层当作自己的核心抽象**：

- **ink**：以 **React reconciler 的终端宿主**为核心抽象。UI 是 React 树，reconciler 把它提交成一棵"每个节点挂一个 Yoga 节点的 DOMElement 树"，再投射到一块虚拟字符网格上拼成 ANSI 字符串。
- **ratatui**：以 **一块 `Vec<Cell>` 的字符网格 + 帧间差分**为核心抽象。没有 UI 树、没有事件循环、没有输入类型——`Widget::render` 直接往 Buffer 里写字，库负责 diff 与写后端。
- **FTXUI**：以 **一棵自包含的三层栈（screen / dom / component）**为核心抽象。dom 的 `Node` 树（`Element = shared_ptr<Node>`）负责布局与绘制，component 树负责状态与事件，`App` 同时是 Screen 和事件循环。

一句话记法：

```text
ink      → React 的终端宿主实现（框架迁就 React 的提交模型）
ratatui  → 立即模式的 Cell 缓冲 + diff 引擎（一个纯库，什么都不拥有）
FTXUI    → 自带循环的三层 DOM 栈（一个自洽的小操作系统的终端版）
```

## 先看三条根本问题（领域不变量收敛到 3 条）

| # | 根本问题 | 三个项目都必须回答的问题 |
| :--- | :--- | :--- |
| 1 | **语义正确性** | 声明式描述 → 字符网格：布局怎么算、宽字符怎么占位、裁剪怎么裁、样式怎么叠加 |
| 2 | **屏幕状态归属** | "上一帧屏幕上是什么"由谁记？谁拥有循环？谁能重入？ |
| 3 | **字节与计算最小化** | 每帧怎么少算（缓存/脏标记）与少写（diff 粒度/节流） |

第 3 条在三个项目里的实现差异最大，也最能看出设计取向——见「设计空间」。

---

# 接入面

三家都把"声明"和"启动"分开，但声明语汇完全不同。

|       | ink 8.0.0                                                                      | ratatui 0.30.2                                                                                        | FTXUI 7.1.0                                                                               |                  |        |                                             |
| :---- | :----------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- | ---------------- | ------ | ------------------------------------------- |
| 声明方式  | React/JSX 组件树（`Box` / `Text` / `Static`）                                       | 构造 widget + 自己给 `Rect`                                                                                | `Element` 管道装饰 + `Component` 工厂                                                           |                  |        |                                             |
| 启动入口  | `render(node, options)`（`src/render.ts:201`）                                   | `ratatui::run(f)` / `Terminal::new`（`ratatui/src/init.rs:323`、`ratatui-core/src/terminal/init.rs:56`） | `App::FitComponent()` + `screen.Loop(component)`（`examples/component/button.cpp:61-62`）   |                  |        |                                             |
| 无终端入口 | `renderToString`（`src/render-to-string.ts:48`）                                 | `TestBackend` 渲染到内存（`ratatui-core/src/backend/test.rs:36`）                                            | `Screen` + `Render(screen, element)`（本身就是 headless，见 `src/ftxui/dom/text_test.cpp:17-25`） |                  |        |                                             |
| 宿主元素  | 小写标签 `ink-root` / `ink-box` / `ink-text`（`src/dom.ts:15-16`）                   | 无（widget 是 trait 实现，`ratatui-core/src/widgets/widget.rs:70-76`）                                       | 无标签概念，`Element` 是 `shared_ptr<Node>`（`include/ftxui/dom/node.hpp:21`）                     |                  |        |                                             |
| 语法糖   | JSX 本身                                                                         | 宏：`span!` `line!` `constraints!` `vertical!`（`ratatui-macros/src/lib.rs`）                             | `operator                                                                                 | ` 装饰器：`text("x") | border | color(...)`（`src/ftxui/dom/util.cpp:45-90`） |
| 多实例约束 | 同一 stdout 只允许一个活实例（WeakMap，`src/instances.ts:9`；复用会警告 `src/render.ts:262-280`） | 无约束（库无全局状态）                                                                                           | 无约束（`App` 是普通对象）                                                                          |                  |        |                                             |

**要点**：入口不是引擎。

- ink 的入口把"React 运行时"带进来了——`render()` 是 `react-reconciler` 的 `createContainer` 封装，所以入口决定了整个后续数据流。
- ratatui 的入口是可以被剥掉的薄壳：`run()`/`init()` 只是"进备用屏 + raw mode + panic hook"的便利函数（`ratatui/src/init.rs:218,323,433`），核心路径只需要 `Terminal::new`。
- FTXUI 的入口是可选的：只做一次性渲染（CLI 里画个表格）时，`dom` + `screen` 完全不需要 `App`（`src/ftxui/dom/node.cpp:96` 的 `Render` 是自由函数）。

---

# 表示面

**这一面是全篇最关键的对照点**：三家都最终落在一块 Cell 网格上，但"库承认的、跨帧存活的那个对象"完全不同。

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 元素层 | `DOMElement` 树，每节点自带 `yogaNode`（`src/dom.ts:24,97`） | **没有**元素树（widget 用完即弃） | `Node` 树，`Element = shared_ptr<Node>`（`include/ftxui/dom/node.hpp:38,89-92`） |
| 网格层 | `Output`：`StyledChar[][]`，**每帧新建**，`get()` 时才展开（`src/output.ts:132,355`） | `Buffer { area, content: Vec<Cell> }`，**跨帧存活**（`ratatui-core/src/buffer/buffer.rs:67-72`） | `Surface/Screen`：`std::vector<Cell>` + `stencil`（`include/ftxui/screen/surface.hpp:68,70`） |
| 状态层对象 | React Fiber 树（库外） | 无（`StatefulWidget::State` 由调用者持有） | `ComponentBase` 对象树（`include/ftxui/component/component_base.hpp:31`） |
| 单元内容 | `StyledChar`（字符 + SGR 属性） | `Cell`（grapheme + fg/bg/underline + `CellDiffOption`，`ratatui-core/src/buffer/cell.rs:38-80`） | `Cell`（grapheme + 9 个位域样式 + hyperlink id，`include/ftxui/screen/cell.hpp:19-60`） |
| 文本输入侧的类型 | 无（文本是字符串，样式在组件层就转成 SGR） | `Span` / `Line` / `Text` 三层（`ratatui-core/src/text.rs:3-8`） | 无（`text()` 直接产出 `Text` Node） |

三种典型取向：

```text
ink      :  元素树 = 持久（React 拥有），网格 = 每帧临时（库拥有）
ratatui  :  元素树 = 不存在，      网格 = 持久（Terminal 拥有，双份）
FTXUI    :  元素树 = 每帧重建（Component 每帧 Render 出新树），网格 = 持久（App 拥有，跨帧复用内存）
```

FTXUI 这一格是最反直觉的——**元素树每帧重建、但网格跨帧复用**（`src/ftxui/component/component.cpp:124-131` 重建树，`src/ftxui/component/app.cpp:1059-1067,1128` 复用 grid）。原因见「控制面」：它把"重建树"当成便宜的纯函数，把"分配网格"当成贵的（O(w·h)）那一项。

---

# 布局面

三种布局引擎，三套完全不同的数学。

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 引擎 | Yoga（facebook 的 flexbox，WASM）（`src/dom.ts:1,97`） | Cassowary 约束求解器（`kasuari` crate）（`ratatui-core/src/layout/layout.rs:11`） | 自研两遍协议 + 整数 flex 分配（`src/ftxui/dom/node.cpp:19-44,105-127`） |
| 用户模型 | CSS 风格 flexbox（`src/styles.ts:770` 是唯一的样式→Yoga 映射表） | `Layout::vertical/horizontal` + `Constraint::{Length,Percentage,Min,Max,Ratio,Fill}`（`ratatui-core/src/layout/layout.rs:580,820-899`） | `hbox` / `vbox` / `flexbox` / `gridbox` 节点 + `Requirement`（`include/ftxui/dom/requirement.hpp:16-27`） |
| 文本参与布局的方式 | Yoga `setMeasureFunc` → `measureTextNode` 回调里 wrap/truncate（`src/dom.ts:100-102,266-295`） | 不参与：调用者先给 `Rect`，widget 在 `Rect` 内部换行（`ratatui-widgets/src/reflow.rs:26`） | 节点自己声明 `min_x/min_y` + flex 因子，父节点分配（`src/ftxui/dom/border.cpp:49-62`） |
| 数值基础 | Yoga 内部浮点 | f64 求解 → `FLOAT_PRECISION_MULTIPLIER = 100.0` 缩放后转 u16（`ratatui-core/src/layout/layout.rs:43`） | 纯整数，`SafeRatio` 避免溢出（`src/ftxui/dom/box_helper.cpp:13-16`） |
| 复用/缓存 | 布局树常驻（React 树内），只有脏节点重算 | `thread_local LruCache<⟨Rect, Layout⟩>`，容量 500；`no_std` 降级为 `critical_section::Mutex`（`ratatui-core/src/layout/layout.rs:49-57,220`） | 无缓存，**每帧全量重算** |
| 迭代 | 不需要（Yoga 一轮） | 单轮求解（约束冲突按 strength 让步） | **迭代式**：`Status{iteration, need_iteration}`，上限 20 轮（`include/ftxui/dom/node.hpp:70-79`、`src/ftxui/dom/node.cpp:105-118`） |

三个设计选项：

```text
Q：布局引擎是"用现成的"还是"自己算"？
  - ink  ：复用 Yoga——擅长表达力（gap/align/wrap 全都有），代价是 WASM 依赖 + 手动 freeRecursive
           （节点删除时必须把 yogaNode 引用置空以防 use-after-free，src/dom.ts:208-212）
  - ratatui：复用 Cassowary 求解器——擅长"多个约束同时成立"，代价是浮点精度舍入与 LRU 复杂度
  - FTXUI：自己写——擅长零依赖 + 纯整数确定性，代价是表达力靠自己堆（flexbox_helper.cpp:369 是换行+对齐的全部实现）

Q：文本测量放在布局期还是渲染期？
  - ink     ：布局期（Yoga measure 回调），因为 flex 需要知道文本高度
  - ratatui ：渲染期（调用者已给出 Rect），因为库不做"内容决定尺寸"
  - FTXUI   ：布局期（节点自己算 Requirement）
  决定因素：布局引擎是否允许"尺寸依赖内容"。ratatui 的答案是"不允许，由调用者决定"——
            这就是它为什么能用最少的代码支持最多的布局需求（手算 Rect 也是合法用法）

Q：布局结果缓存还是不缓存？
  - ratatui：缓存（LRU），因为每帧全量重建 widget 的模型下重复求解是主要 CPU 开销
  - FTXUI ：不缓存，但每帧只重建树、布局全量走一遍 20 轮以内的迭代
  - ink    ：Yoga 树常驻，只重算脏节点
```

---

# 渲染面

三家都是"遍历表示树 → 往网格写字"，但写入的**目标对象**和**结算时机**不同。

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 遍历起点 | `renderer()`（`src/renderer.ts:27`）→ `renderNodeToOutput`（`src/render-node-to-output.ts:103`） | `Frame::render_widget`（`ratatui-core/src/terminal/frame.rs:106`）→ `Widget::render` | 自由函数 `Render(Screen&, Node*)`（`src/ftxui/dom/node.cpp:96-148`） |
| 写入对象 | `Output.write/clip/unclip` **只入队**（`src/output.ts:288,305,311`） | `Buffer::set_stringn/set_line/set_style` **立即写 cell**（`ratatui-core/src/buffer/buffer.rs:336-372,373-386,405`） | `Node::Render(Screen&)` **立即写 cell**（`src/ftxui/dom/text.cpp:98`、`border.cpp:81`、`color.cpp:21-45`） |
| 裁剪 | 嵌套 clip 取交集，`get()` 时结算（`src/output.ts:74-88,373-382`） | 由 widget 自己 respect `Rect`（`Buffer` 越界即忽略） | `Surface::stencil`（`include/ftxui/screen/surface.hpp:68`、`src/ftxui/screen/surface.cpp:44-53`） |
| 结算时机 | `Output.get()` 一次性把操作应用到格子（`src/output.ts:355-398`） | 无结算步骤——写进去就是最终值 | `Screen::ToString()` 扫描网格生成转义序列（`src/ftxui/screen/screen.cpp:474-519`） |
| 宽字符处理 | 占两格；被裁剪/覆盖时用保留样式的空格占位（`src/output.ts:225-260,323-350`） | `set_stringn` 按 grapheme 写并 reset 尾随 cell（`ratatui-core/src/buffer/buffer.rs:336-372`） | 全宽字符占两格，渲染后跳过下一格（`src/ftxui/screen/screen.cpp:489-508`） |
| 边框 | `render-border.ts:22` 自己拼边框字符 | `Block::render` → `render_borders/render_sides/render_corners`（`ratatui-widgets/src/block.rs:799-822`） | `Border::Render`（`src/ftxui/dom/border.cpp:81`） |

**ink 的"操作队列 + 延迟绘制"是三家唯一的**：因为 JSX 的绘制顺序不等于最终叠加顺序（父节点背景、边框、子节点文本、`Transform` 变换都要按确定顺序结算），所以它不能在遍历时流式拼 ANSI，必须先把操作入队，最后在二维网格上一次性结算。这是"声明式模型"给渲染层带来的直接后果。

反过来说，ratatui 的"立即写 cell"之所以可行，是因为它的绘制顺序**就是**用户调用 `render_widget` 的顺序——用户自己保证先后。FTXUI 介于两者之间：遍历顺序由 `Node` 树结构决定（`node.cpp:70-74` 默认递归 children），所以顺序是确定的。

---

# 控制面

**这是三家分歧最大、也最能判断"这个库适不适合我的场景"的一面。**

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 谁拥有事件循环 | **谁都不拥有**：React commit 触发渲染，Node/进程提供事件循环（`src/reconciler.ts:245`） | **调用者**：库明确声明"不包含任何输入处理"（`ratatui/src/lib.rs:272`） | **库自带**：`App`（`src/ftxui/component/app.cpp:1543-1546`）+ `Loop` 薄包装（`src/ftxui/component/loop.cpp:37-51`） |
| 触发下一次绘制 | React 提交：`resetAfterCommit` → `onComputeLayout` → `onRender`/`onImmediateRender`（`src/reconciler.ts:245-283`） | 调用者调 `Terminal::draw`（`ratatui-core/src/terminal/render.rs:81`） | 事件/任务/动画入队 → `RunOnce` → `Draw`（`src/ftxui/component/app.cpp:820-847,1012-1133`） |
| 无变化时 | 比较上一帧字符串，相同则跳过写入（`src/ink.tsx:229-249,725-731`） | 无此概念（用户不调 `draw` 就没帧） | `frame_valid_` 脏标记，`Draw` 首行直接返回（`src/ftxui/component/app.cpp:120,929,1013-1015`） |
| 节流 | `maxFps` 默认 30，`es-toolkit` throttle（`src/ink.tsx:424-444`） | 无（调用者决定） | `RunOnceBlocking` 有 60fps 上限（`src/ftxui/component/app.cpp:849-868`） |
| 可嵌入自有循环 | 是（React 状态更新即渲染） | 是（这是唯一模式） | 是：`while(!loop.HasQuitted()) loop.RunOnce();`（`include/ftxui/component/loop.hpp:33-44`） |
| 唯一内部定时器 | 动画共享定时器 `scheduleAnimationTick`（`src/components/App.tsx:145-180`） | 无 | 任务队列里的 `AnimationTask` 统一走 60fps 节流（`include/ftxui/component/task.hpp:14`） |

```text
Q：事件循环归库还是归调用者？
  - 归调用者（ratatui）：擅长任意异步/输入栈自由组合、库零运行时、可重入，
                        代价是每个应用都要自己写 poll/read + tick（ratatui/src/init.rs:84 就是样板）
  - 归库（FTXUI）：擅长开箱即用、动画/任务/线程 Post 统一调度，
                   代价是 App 继承 Screen 造成语义混叠（include/ftxui/component/app.hpp:37），
                   且非交互场景要显式绕过 App
  - 归框架但不归库（ink）：擅长"状态一变就重绘"的 React 心智，
                           代价是没有稳定帧率保证，动画得自己加调度层
  决定因素：这个库是"给应用开发者用"还是"给库/工具作者当积木用"
```

一个反直觉的推论：**ratatui 的"什么都不拥有"反而让它在生态上最灵活**——因为它不只是不给循环，连终端后端也是 trait（见「平台面」），所以它同时被 `crossterm`/`termion`/`termwiz`/`termina` 四种输入栈和任意异步运行时组合使用。FTXUI 因为全包了，反而在同一个仓库里出现了 `App` 与 `Screen` 的继承耦合。

---

# 状态面

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 库拥有的跨帧状态 | `Ink` 实例字段：`lastOutput`/`lastOutputHeight`/终端尺寸/kitty 协商状态等（`src/ink.tsx:213-256`） | `Terminal`：`backend`/`buffers[2]`/`current`/`viewport`/`last_known_*`/`frame_count`（`ratatui-core/src/terminal.rs:398-458`） | `App::Internal`：任务队列/`frame_valid_`/installation 状态（`src/ftxui/component/app.cpp:120`）；`ComponentBase::Impl`（`src/ftxui/component/component.cpp:31-36`） |
| 上一帧存在哪 | 整帧**字符串**（`LogUpdate.previousOutput`，`src/log-update.ts:36-46`） | 上一块 **Buffer**（`buffers[1-current]`） | 上一帧的 **Cell 网格本身**（复用同一块 `cells_`） |
| 网格是否跨帧复用 | 否：`Output` 每帧新建（`src/renderer.ts:62`） | 否（内容清空但内存复用：`swap_buffers` → `reset()`，`ratatui-core/src/terminal/buffers.rs:121-124`） | **是**：只在尺寸变化时重建 `cells_`（`src/ftxui/component/app.cpp:1059-1067`），帧末 `Clear()` 填默认 Cell 但不释放（`src/ftxui/component/app.cpp:1128`、`src/ftxui/screen/surface.cpp:72-74`） |
| 应用状态放哪 | React state（Fiber 树内） | `StatefulWidget::State`，由**调用者**持有（`ratatui-core/src/widgets/stateful_widget.rs:124`；`ListState{offset,selected}` `ratatui-widgets/src/list/state.rs:41-45`） | 组件对象内部，或用 `Ref<T>` 绑到调用者变量（`include/ftxui/util/ref.hpp:10-99`） |
| 其他缓存 | 文本尺寸 QuickLRU(4096)（`src/measure-text.ts:6`）；Output 内宽度 Map 缓存（`src/output.ts:85-130`） | 布局 LRU(500)（`ratatui-core/src/layout/layout.rs:49-57`） | 无（`string_width` 有 ASCII 快路径，但无结果缓存） |

三种"上一帧"粒度直接决定了产物面的 diff 粒度：

```text
上一帧 = 字符串（ink）      → 只能做"整帧/按行"差
上一帧 = Buffer（ratatui）  → 能做"逐 cell"差
上一帧 = 网格本身（FTXUI）  → 甚至不需要"上一帧"这个概念：网格就是要显示的东西，输出时才逐 cell 比较样式
```

---

# 输入面

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 输入从哪进 | `stdin` 的 `'readable'` 事件（`src/components/App.tsx:373`），同步抽干 `stdin.read()`（`src/components/App.tsx:322`） | **库内没有**：直接调后端库（如 `crossterm::event`）（`ratatui/src/lib.rs:272-276`） | `App::FetchTerminalEvents`：Windows `ReadConsoleInput`（`src/ftxui/component/app.cpp:1344`）/ POSIX `read`（`:1400`） |
| 字节→事件 | 两层：`input-parser`（切完整序列，跨 chunk 留 pending，20ms 后 flush 悬空 ESC，`src/components/App.tsx:124-125,311-318`）→ `parse-keypress`（`src/input-parser.ts:268`、`src/parse-keypress.ts:435`） | 无 | `TerminalInputParser` 状态机：UTF8/ESC/CSI/OSC/DCS/mouse（`src/ftxui/component/terminal_input_parser.hpp:17,84-90`） |
| 事件类型 | `ParsedKey` / `Key`（`src/hooks/use-input.ts` 里映射） | 无（后端库的类型） | `Event`（字符/鼠标/光标上报/终端元信息），带 `screen_` 反向指针（`include/ftxui/component/event.hpp:35`） |
| 分发 | 单个 `EventEmitter`：`emit('input')` 给所有 `useInput` 监听者（`src/components/App.tsx:304`） | 无 | 惰性 OR：`ComponentBase::OnEvent` 依次问 children，返回 true 即停（`src/ftxui/component/component.cpp:174-183`） |
| 焦点 | `FocusContext` + App 内的 activeId 注册表，Tab/Shift+Tab 由 App 处理（`src/components/FocusContext.ts:17`、`src/components/App.tsx:536-583`） | 无 | 从 root 沿 `ActiveChild()` 链判定，`Focused()` 走祖先链 O(depth)（`src/ftxui/component/component.cpp:194-203,216-231,243-250`） |
| 库抢答的键 | Ctrl+C 退出、Esc 清焦点（`src/components/App.tsx:269-296`） | 无 | Ctrl-C/Ctrl-Z 默认被抢答，可用 `ForceHandleCtrlC/Z` 关掉（`src/ftxui/component/app.cpp:922-928`） |
| 粘贴 | 独立 paste 通道 + 括号粘贴模式（引用计数）（`src/hooks/use-paste.ts:39`、`src/components/App.tsx:453-485`） | 无 | **无 bracketed paste**：粘贴就是逐字符 `Event::Character`（全仓库 grep `paste`/`bracket` 零命中），长粘贴会被事件化成一串字符 |
| raw mode | 引用计数，最后一个释放者延迟到 microtask（`src/components/App.tsx:383-451`） | 由 `init()` 或调用者负责（`ratatui/src/init.rs:433`） | `App` 安装/反安装时处理（`src/ftxui/component/app.cpp:Install/Uninstall`） |

**"输入面不存在"是 ratatui 的重大发现，不是遗漏**：它的 `Backend` trait 一共 17 个方法（`draw`/`clear`/`clear_region`/`cursor` 系列/`size`/`window_size`/`flush`/`append_lines`/`scroll_region_*`），没有一个和事件有关（`ratatui-core/src/backend.rs:160-422`）。它清楚地把"字符输出"和"事件输入"切成两个正交的库，用"后端 crate re-export"（`ratatui-crossterm/src/lib.rs:36-45`）保证版本一致。

代价是每个应用都要写这段样板；收益是这个库可以被任何事件模型驱动（async、线程、poll、甚至非终端）。

---

# 平台/后端面

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 抽象形态 | **无后端抽象**：直接接收 `stdout`/`stdin`/`stderr` 三个 Node 流（`src/render.ts:209-213`、`src/stream.ts:1-27`） | `trait Backend`（`ratatui-core/src/backend.rs:160`，`draw` 在 :169） | **无后端抽象**：`Terminal` 命名空间 + 编译期 `#if defined(_WIN32)`（`include/ftxui/screen/terminal.hpp:28-40`） |
| 实现 | 1 个（Node 流）；测试用假流 + node-pty + 极简终端重放器（`test/helpers/create-stdout.ts:10`、`term.ts:13`、`reconstruct-terminal.ts:21`） | 5 个：`CrosstermBackend` / `TermionBackend` / `TerminaBackend` / `TermwizBackend` / `TestBackend`（`ratatui-core/src/backend/test.rs:36`） | 1 个（进程自带终端） |
| 切换方式 | 传不同的流 | **编译期 feature flag**（`ratatui/Cargo.toml` features）；`crossterm` 自身还有 `crossterm_0_28`/`crossterm_0_29` 版本 feature，最新者胜（`ratatui-crossterm/src/lib.rs:66-78`） | 编译期 `#ifdef` + **运行时能力探测** |
| 能力检测 | 运行时布尔：`stdout.isTTY` + `is-in-ci`（`src/ink.tsx:655-657`）；同步输出要求 `isTTY`（`src/write-synchronized.ts:6-13`） | 后端能力差异靠 feature + 默认实现兜底（如 `save_cursor_position` 默认返回 false，`ratatui-core/src/backend.rs:248-262`） | `TERM`/`COLORTERM`/`TERM_PROGRAM` + DA1/DA2/XTVERSION 上报的多级启发式（`src/ftxui/screen/terminal.cpp:327-381`）；`Quirks` 可全局强制覆盖（`include/ftxui/screen/terminal.hpp:53`） |
| 尺寸获取 | `stdout.columns/rows` → `terminal-size` → 80×24（`src/utils.ts:21-40`） | `Backend::size()`；`autoresize` 在每 pass 开头（`ratatui-core/src/terminal/render.rs:184`、`resize.rs:80`） | `ioctl(TIOCGWINSZ)` / `GetConsoleScreenBufferInfo`（`src/ftxui/screen/terminal.cpp:262-278`），失败用 `SetFallbackSize` |
| Windows | 一处特判：`isWindowsConsole`（`src/ink.tsx:44`），Windows 控制台整屏帧强制走全清分支避免右下角写入引发滚动（`src/ink.tsx:63-119`） | crossterm 为默认跨平台后端；termion 在 Windows 被 `cfg(not(windows))` 排除；crossterm 后端有 `execute_winapi` stub 返回 Unsupported（`ratatui-crossterm/src/lib.rs:751,799`） | 启动时对 stdout 开 `ENABLE_VIRTUAL_TERMINAL_PROCESSING`（WindowsEmulateVT100，`src/ftxui/screen/screen.cpp:48-81`）+ `SetConsoleCP(CP_UTF8)`（`:454-460`）；默认 quirks：`BlockCharacters=false, CursorHiding=false, ComponentAscii=true`（`src/ftxui/screen/terminal.cpp:57-63`） |
| 协议协商 | kitty 键盘协议：向 stdout 写 `CSI ? u`，等 200ms 由普通输入管线收回复（`src/ink.tsx:826-891`） | 无（留给后端） | 终端能力上报事件（DA1/DA2/XTVERSION）走自己的事件队列（`src/ftxui/component/app.cpp:887-908`） |

```text
Q：终端抽象放哪？
  - trait + feature flag（ratatui）：擅长一套核心配 N 种输入栈、no_std 可行（`ratatui-core` 第 1 行就是 `#![no_std]`，
    ratatui-core/src/lib.rs:1），代价是能力差异要靠默认实现/feature 组合兜底
  - 进程流抽象（ink）：擅长零配置、天然支持非 TTY 输出（管道、CI），代价是没有 terminfo 级精确能力表
  - 无抽象 + #ifdef（FTXUI）：擅长零虚函数开销、代码量最小、零依赖，代价是新增平台要散改多处 #ifdef，
    且库内无法插入自定义后端（这是一个 "absent" 格，include/ftxui/screen/terminal.hpp 只有函数，没有接口）
  决定因素：这个库要不要"被别人当积木嵌进别的运行时"
```

FTXUI 的 `Terminal` 面是**唯一一个真正的"缺失层"**：它有尺寸/颜色/quirks 的探测函数，但没有 `TerminalBackend` 接口，也没有运行时注册/切换。这不是疏忽——FTXUI 的定位是"独立应用框架"，不需要被嵌入别人的事件循环。

---

# 产物面

三家都在"少写字节"上做了功夫，但优化的**单位**不同。

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 交给终端的东西 | ANSI **字符串**（SGR + CSI 光标/擦除） | `Iterator<Item=(u16,u16,&Cell)>`——**变化 cell 的迭代器**（`ratatui-core/src/backend.rs:169-171`） | 整块网格序列化出的 ANSI 字符串 + 光标归位序列（`src/ftxui/screen/screen.cpp:474-519,544-563`） |
| diff 单位 | 整帧字符串 / 行（`standard` vs `incremental`，`src/log-update.ts:36,180`） | **逐 Cell**（`BufferDiff`，零分配迭代器；处理宽字符/VS16 与 `CellDiffOption`，`ratatui-core/src/buffer/diff.rs:5-30,89-120`） | **样式层**：`UpdateCellStyle` 只对变化的属性发 SGR（含 256 色去重），内容**全量重写**（`src/ftxui/screen/screen.cpp:89-160`） |
| 擦除策略 | `eraseLines(上一帧行数)` + 重写（`src/log-update.ts:76-110`），必要时全清 `homeAndEraseDown`（`src/ink.tsx:63-119`） | 无擦除：只把变化的 cell 用 `MoveTo` + 写字符覆盖（`ratatui-crossterm/src/lib.rs:232-310`） | 无擦除：`ResetPosition` 发 `\r` + 每行 `\x1B[1A` 回到上一帧左上角，重叠覆盖（`src/ftxui/screen/screen.cpp:544-563`） |
| 抗撕裂 | BSU/ESU（`CSI ?2026h/l`）包裹每帧（`src/write-synchronized.ts:3-4`） | 无（交给终端/后端） | 无 |
| 帧末尾 | — | `Backend::flush` + 光标定位（`ratatui-core/src/terminal/render.rs:288-320`） | 追加 `'\0'` 后 flush（`src/ftxui/screen/screen.cpp:521-523`、`src/ftxui/component/app.cpp:1146-1153`） |
| 默认保守/激进 | 增量模式**默认关闭**（`incrementalRendering`，`src/log-update.ts:397`） | 永远只发 diff（因为 buffer 双份是库强制的） | 永远全量重绘（除样式差分） |

```text
Q：增量做到哪一层？
  - 到 cell（ratatui）：字节最省，代价是必须维护"终端当前状态 == previous buffer"这个不变量，
                          任何外部写入（子进程、打印日志）都会破坏它
  - 到样式（FTXUI）：字节中等，但永不依赖"终端状态"——因为每帧都重写内容、靠光标归位，
                      所以对终端的假设最少（这也是它能放行 printAbove 之类特性的原因）
  - 到行/帧（ink）：字节最多（默认整帧重写），但能正确处理"行数变化"这种 cell 模型不表达的事
                    （文字变长变短会移动整个后续内容）
  决定因素：这个库允不允许"终端里还有别的东西在写"（日志、子进程、Static 输出）
```

这一条是三家最本质的差异之一：**ratatui 的 diff 只在自己的缓冲区有效，FTXUI 的重绘假设整个屏幕归自己**，ink 因为要跟 `console.log`、`<Static>`、子进程共存，选择了最保守的整帧重写。

---

# 切面层

| 切面 | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 样式/颜色 | 组件层就把文本包成 SGR（`chalk`/`colorize`，`src/colorize.ts:16`、`src/components/Text.tsx:100-141`） | `Style{fg,bg,underline_color,modifier}` + `Stylize` 宏生成 trait（`ratatui-core/src/style.rs:239-270`、`style/stylize.rs:114-192`） | `Cell` 里 9 个位域 + `Color`；`FgColor::Render` 只写字段（`include/ftxui/screen/cell.hpp:27-40`、`src/ftxui/dom/color.cpp:21-45`） |
| Unicode 宽度 | `string-width`/`wrap-ansi`，`Output` 内 Map 缓存（`src/output.ts:86-130`） | 自实现 `CellWidth`，**补偿半角浊音符号 U+FF9E/FF9F 的 0 宽判定**（`ratatui-core/src/buffer/cell_width.rs:8-66`） | 生成的区间表 + 二分（`Bisearch`，`src/ftxui/screen/string.cpp:69-115`、`string_unicode_tables.ipp` 约 50KB） |
| ANSI 注入防护 | **有**：用户文本经 `sanitize-ansi` 只放行 SGR/OSC，并把冒号形式 SGR 改写成分号形式（`src/sanitize-ansi.ts:47`、`src/ansi-tokenizer.ts:326`） | 无此概念（文本直接进 cell） | 无此概念 |
| 可访问性 | **有**：屏幕阅读器模式走第二条渲染路径，输出 role/state 文本而非 ANSI（`src/render-node-to-output.ts:36-100`、`src/components/AccessibilityContext.ts:4`、`Box.tsx:100-103` 映射 aria-*） | **无**：只有 widget 作者指南里的一句散文提醒（`ratatui/src/widgets.rs:594-598`） | **无**：全仓库 grep 不到（accessib/aria/screen-reader/NVDA/VoiceOver 均无命中） |
| 测试后端 | 三层：假流（sinon spy/EventEmitter）、`node-pty` 真 xterm、只重放 Ink 所用序列的极简终端状态归约器（`test/helpers/create-stdout.ts:10`、`term.ts:13`、`reconstruct-terminal.ts:21-27`） | `TestBackend`：同一 `Backend` trait 的内存实现，断言渲染结果（`ratatui-core/src/backend/test.rs:36-113`） | **无需专门后端**：`Screen` 本身就是 headless，`Screen s(2,1); Render(s, el); s.ToString()` 即测试（`src/ftxui/dom/text_test.cpp:17-25`） |
| 异步/并发 | React concurrent + `discreteUpdates` 提升输入优先级（`src/ink.tsx:506`、`src/hooks/use-input.ts:176`） | **无**：core 里没有任何 async（crossterm 的 event-stream 只是 dev-dependency，`ratatui/Cargo.toml:145`） | 线程安全任务队列 `Task = variant<Event, Closure, AnimationTask>`，任意线程 `Post`/`PostEvent`（`include/ftxui/component/task.hpp:14`、`src/ftxui/component/app.cpp:1577-1581`） |
| 滚动/虚拟化 | **无 viewport 抽象、无虚拟化**：靠终端 scrollback + `<Static>` 承担（`src/components/Static.tsx:65`） | widget 级 offset：`ListState.offset`、`Paragraph::scroll`（`ratatui-widgets/src/list/state.rs:41-45`、`paragraph.rs:235`） | `frame`/`focus`/`xframe`/`yframe` 节点做裁剪 + 焦点跟随（`src/ftxui/dom/frame.cpp:18-100`），**但没有虚拟化**：被裁剪的节点仍参与布局 |
| 动画 | 共享定时器 + 跳帧（`src/components/App.tsx:145-180`） | 无（调用者/第三方） | `animation.hpp` 的 `Animator` + `easing::*`（`include/ftxui/component/animation.hpp:130-186`） |
| 边框合成 | 自己拼字符 | `MergeStrategy{Replace,Exact,Fuzzy}`：把相邻/重叠边框合并成单字符（`┌`+`┐`→`┬`）（`ratatui-core/src/symbols/merge.rs:62-302`） | `ApplyShader` 合并 box 字符（`src/ftxui/screen/screen.cpp:590+`） |

三个可迁移的判断：

```text
1. 可访问性只有"另一条渲染路径"这一种实现方式
   —— ink 它不做在屏幕网格层，而是在树遍历层分流（render-node-to-output.ts:36）。
      这说明：可访问性不能靠后处理 ANSI 得到，必须在"语义仍然存在"的那一层输出。

2. 测试后端有三种成本递增的实现，选哪种取决于你要测什么
   内存 buffer（ratatui TestBackend / FTXUI Screen）→ 测布局与网格内容
   假流（ink create-stdout）                     → 测"库写了什么字节"
   真 PTY（ink term.ts 用 node-pty）              → 测"终端最终显示成什么样"
   ink 三层都有，因为 JS 生态里"库写的字节"和"终端显示的结果"经常不一致（擦除/滚动/宽字符）

3. ANSI 注入防护只有 ink 一家做
   原因：只有它的输出可以包含"用户可控的任意文本 + 用户可控的样式字符串"，
         而它的差分会话建立在"屏幕上只有我写的字节"这个假设上。
```

---

# I/O 层

把所有 I/O 混着看会看不清瓶颈，按来源分四类：

| 分类          | ink                                                         | ratatui                                                                        | FTXUI                                                                                                        |
| :---------- | :---------------------------------------------------------- | :----------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| 输入字节流       | `stdin` Node 流（`src/components/App.tsx:373`）                | 后端库自己管（crossterm 内部）                                                           | `read` / `ReadConsoleInput`（`src/ftxui/component/app.cpp:1328-1452`）                                         |
| 输出字节流       | `stream.write`（`src/log-update.ts:76,105`）                  | `Backend::draw` → crossterm `execute!`（`ratatui-crossterm/src/lib.rs:232-310`） | `TerminalSend`/`TerminalFlush`（`src/ftxui/component/app.cpp:1146-1153`）                                      |
| 终端能力/尺寸 I/O | `stdout.columns` + 探测序列往返（`src/ink.tsx:826-891`）            | `Backend::size()`（`ratatui-core/src/backend.rs`）                               | `ioctl`/`GetConsoleScreenBufferInfo` + DA1/DA2/XTVERSION 上报（`src/ftxui/screen/terminal.cpp:262-278,327-381`） |
| 进程/设备 I/O   | `suspendTerminal`：让子进程接管 TTY 后强制整屏重绘（`src/ink.tsx:893,954`） | 无（交给调用者）                                                                       | `printAbove` / `TerminalOutput` 模式                                                                           |

**性能分析时要区分**：

```text
画得慢（布局/遍历）
≠ 拼字节慢（序列化/diff）
≠ 写得慢（stdout backpressure —— 三家都没做背压控制）
```

三家的产物面都直接 `write`，没有一家做输出背压/丢弃策略——这是它们共同的空白格，也是"TUI 在高频刷新时卡住"的常见根因。

---

# 领域不变量（每一列都填满、且填法结构一致）

| # | 不变量 | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **终局表示一定是"字符网格"** | `Output` 的 `StyledChar[][]`（`output.ts:132`） | `Buffer` 的 `Vec<Cell>`（`buffer.rs:67-72`） | `Surface` 的 `vector<Cell>`（`surface.hpp:70`） |
| 2 | **必须处理"字符宽度 ≠ 1"** | `string-width` + 宽字符占位（`output.ts:225-260`） | 自实现 `CellWidth`（`cell_width.rs:8-66`） | 区间表 + 二分（`string.cpp:69-115,254-260`） |
| 3 | **必须有跨 chunk 的输入序列解析** | `input-parser`（`input-parser.ts:268`） | 外置给后端库（`lib.rs:272`） | `TerminalInputParser`（`terminal_input_parser.hpp:17`） |
| 4 | **必须有帧间差分或等价物** | 整帧/行差（`log-update.ts:36,180`） | `BufferDiff` 逐 cell（`diff.rs:5-30`） | 样式差分 + 光标归位（`screen.cpp:89-160,544-563`） |
| 5 | **必须测"终端最终显示什么"** | 三层测试后端（`test/helpers/*`） | `TestBackend`（`backend/test.rs:36`） | `Screen::ToString` 即测试（`text_test.cpp:17-25`） |
| 6 | **必须处理尺寸变化** | `use-window-size` + 全清回退（`ink.tsx:63-119`） | `autoresize`（`render.rs:184`） | resize 时重建 `cells_`（`app.cpp:1059-1067`） |
| 7 | **样式最终都要变成 SGR 序列** | `colorize`/`chalk`（`colorize.ts:16`） | crossterm `SetColors`/`SetAttribute`（`ratatui-crossterm/src/lib.rs:232-310`） | `UpdateCellStyle`（`screen.cpp:89-160`） |
| 8 | **状态归属必须在"库"和"调用者"之间明确划一条线** | 库持帧与终端状态，React 持应用状态 | 库持 Buffer 与终端，调用者持一切 widget 状态 | 库持 App/网格，组件持自身状态（或 `Ref` 外绑） |

第 8 条是最有启发性的一条：**三家都把"应用状态"划给了库外**——ratatui 用 `StatefulWidget::State`，FTXUI 用组件对象/`Ref<T>`，ink 用 React。库只拥有"终端 + 帧"这一小块状态。

---

# 设计空间（差异 → 选项 + 代价 + 决定因素）

| Q | 选项甲 | 选项乙 | 选项丙 | 决定因素 |
| :--- | :--- | :--- | :--- | :--- |
| UI 描述模型 | **具名树 + 引用**（ink React reconciler；FTXUI Component+Node） | **无树，立即模式**（ratatui Widget） | — | 是否需要"框架帮我保持状态与依赖" |
| 谁拥有循环 | **调用者**（ratatui）——可与任意异步栈组合，代价是每个应用写样板 | **库**（FTXUI `App`）——开箱即用，代价是 `App` 与 `Screen` 继承耦合、难嵌入 | **框架但不归库**（ink 由 React commit 驱动）——无稳定帧率 | 库是"应用框架"还是"积木" |
| 帧间 diff 粒度 | **逐 cell**（ratatui）——字节最省，依赖"屏幕只有我写" | **样式 + 全量内容**（FTXUI）——假设最少、最健壮 | **整帧/行**（ink）——能正确处理行数变化，字节最多 | 终端里是否还有别的东西在写 |
| 布局算法 | **复用 flexbox**（ink Yoga）——表达力强，WASM 依赖 + 手动释放 | **复用约束求解**（ratatui Cassowary）——多约束同时成立，浮点精度 + 缓存复杂度 | **自研整数两遍协议**（FTXUI）——零依赖、确定性，表达力靠自己堆 | 是否接受第三方依赖 |
| 内容是否参与布局 | **是**（ink/FTXUI：measure/Requirement） | **否**（ratatui：调用者给 Rect） | — | 是否要求"内容决定尺寸" |
| 布局结果是否缓存 | **是**（ratatui LRU / ink Yoga 脏节点） | **否**（FTXUI 每帧全量） | — | 每帧是否重建整棵树 |
| 元素树是否跨帧存活 | **存活**（ink，React 拥有） | **每帧重建**（FTXUI） | **不存在**（ratatui） | 是否有"组件自身状态"概念 |
| 终端抽象 | **trait + feature flag**（ratatui）——可嵌入、no_std 可行 | **进程流**（ink）——零配置、天然支持管道 | **无抽象 + #ifdef**（FTXUI）——零开销零依赖，不可插拔 | 是否要"被当积木用" |
| 输入解析位置 | **库内两层**（ink） | **库内一层**（FTXUI） | **完全外置**（ratatui） | 输入模型是否与渲染模型强绑定 |
| 可访问性 | **树遍历层第二条渲染路径**（ink） | **无**（ratatui/FTXUI） | — | 库是否面向"人类日常使用的应用" |

---

# 三个框架的核心差异

| 维度 | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 语言/生态 | TypeScript / React | Rust / crates.io | C++20 / 零依赖 |
| 版本（本机克隆） | 8.0.0（`package.json:3`） | 0.30.2（`Cargo.toml:54`） | 7.1.0（`CMakeLists.txt:33`） |
| 中心抽象 | React host 树（DOMElement ⊕ Yoga） | `Buffer`（Cell 网格）+ diff | `Node` 树（dom） |
| UI 模型 | 声明式 + 保留（React 状态驱动） | 立即模式 | 声明式 + 保留（组件对象） |
| 布局 | Yoga WASM flexbox | Cassowary 约束求解 + LRU | 两遍协议 + 迭代收敛（≤20 轮） |
| 事件循环 | 无（React commit 驱动 + 30fps 节流） | 调用者 | 库自带（`App`）+ 可嵌入 `Loop` |
| 输入 | 库内两层解析 + EventEmitter + 焦点注册表 | 无 | 库内解析器 + 惰性 OR + ActiveChild 焦点链 |
| 终端后端 | Node 流（1 种） | `Backend` trait（5 种实现） | 编译期 `#ifdef`（1 种，无抽象） |
| 产物 | ANSI 字符串（整帧/行差、BSU/ESU） | 变化 cell 迭代器（逐 cell 差） | 全量网格 + 样式差 + 光标归位 |
| 可访问性 | 有（第二条渲染路径） | 无 | 无 |
| no_std / 嵌入式 | 不适用 | `ratatui-core` 支持（`lib.rs:70-77`） | 不适用 |
| 最值得学习 | React reconciler 如何在非 DOM 宿主上落地；延迟绘制网格 + 操作队列 | 立即模式下的最小抽象：`Backend` trait + `Buffer` 双份 + trait 化 widget | 一个自洽栈如何分层：dom 无状态、component 有状态、App 管循环 |

---

# 各自的核心技术

## ink（8.0.0）

1. **React reconciler host config（mutation 模式）把终端 UI 变成 React host 树**——`src/reconciler.ts:238,510`。复用 React 的调度/上下文/并发，Ink 只实现 host 操作与提交后钩子。
2. **DOM 节点与 Yoga 节点一一对应，WASM 释放后把引用置空**——`src/dom.ts:97,208-212`。防止 `freeRecursive` 后残留 JS wrapper 仍为 truthy 而被解引用（use-after-free）。
3. **延迟绘制的虚拟网格：操作队列 + 可嵌套交集裁剪**——`src/output.ts:132,146,74`。让重叠写、overflow 裁剪、宽字符占位在同一网格上按确定顺序结算，而不是流式拼 ANSI。
4. **Yoga measure 回调里做 wrap/truncate 并缓存测量**——`src/dom.ts:266`、`src/measure-text.ts:11`。文本尺寸参与 flex，必须在布局期可测量；LRU 避免重复计算。
5. **ANSI 感知的单行增量更新**（SGR 前缀复用 + grapheme 比较 + 整行回退）——`src/line-update.ts:14`。
6. **standard / incremental 两种 log-update 策略 + 光标位置感知擦除**——`src/log-update.ts:36,180`、`src/cursor-helpers.ts:124`。
7. **同步输出 BSU/ESU + 全清回退判定**（全屏/溢出/缩行）——`src/write-synchronized.ts:3`、`src/ink.tsx:63`。
8. **跨 chunk 挂起的转义序列解析器**（含 bracketed paste、rxvt/legacy 序列、20ms 超时 flush 悬空 ESC）——`src/input-parser.ts:268,115`、`src/components/App.tsx:312`。
9. **kitty 键盘协议协商**：查询 `CSI ? u` + 200ms 超时，回复走普通输入管线——`src/ink.tsx:867`、`src/kitty-keyboard.ts:15`。不维护终端白名单即可探测增强键盘。
10. **`<Static>` 伪层**：独立 `staticNode` 子树单独渲染 + `previousStaticNode` 身份追踪——`src/reconciler.ts:245,262`、`src/renderer.ts:14`。让已完成内容永久滚入历史。
11. **ANSI 清洗 + 冒号子参数改写**（只放行 SGR/OSC）——`src/sanitize-ansi.ts:47`、`src/ansi-tokenizer.ts:326`。
12. **屏幕阅读器第二渲染路径**（role/state 文本替代 ANSI）——`src/render-node-to-output.ts:36`、`src/components/AccessibilityContext.ts:4`。
13. **终端交接 `suspendTerminal`**：暂停输入/退出备用屏/强制整屏重绘后恢复——`src/ink.tsx:893,954`。允许子进程（编辑器）临时接管 TTY。

## ratatui（0.30.2）

1. **双缓冲差分**：两块 Buffer，只把变化 cell 发后端；swap 前 reset 下一块——`ratatui-core/src/terminal/buffers.rs:97-124`。把"应用侧全量重绘"转成"输出侧最小字节"。
2. **Cassowary 约束布局**（kasuari 求解器）——`ratatui-core/src/layout/layout.rs:11,820-899`。`Min/Max/Length/Percentage/Ratio/Fill` 可同时满足，冲突按 strength 让步。
3. **布局 LRU 缓存**（thread_local，容量 500；no_std 降级 `critical_section`）——`layout.rs:49-57,220`。
4. **Grapheme 感知的写 cell**（过滤控制字符、多宽字符占位并 reset 尾随 cell）——`ratatui-core/src/buffer/buffer.rs:336-372`。
5. **VS16/宽字符 diff 与光标补偿**（后端在宽字形后显式 `MoveTo`）——`diff.rs:5-30,89-120`、`ratatui-crossterm/src/lib.rs:828-838`。终端对 VS16 光标前进量不可预测。
6. **Cell 级 escape/样式差分**（连续 cell 省 `MoveTo`，样式不变不发 SGR）——`ratatui-crossterm/src/lib.rs:232-310`。
7. **Inline viewport + `append_lines`**：视口锚定当前光标行，空间不足由后端追加行并补偿滚动——`ratatui-core/src/terminal/inline.rs:1-70`、`resize.rs:23-70`。
8. **Box-drawing 边框合并**（`MergeStrategy::Exact/Fuzzy`：`┌`+`┐`→`┬`）——`ratatui-core/src/symbols/merge.rs:62-302`。
9. **Unicode 宽度兼容层**：补偿 `unicode-width` 对半角浊音/半浊音（U+FF9E/FF9F）的 0 宽判定——`ratatui-core/src/buffer/cell_width.rs:8-66`。
10. **调用者持有的 `StatefulWidget::State`**——`stateful_widget.rs:124`、`list/state.rs:41-45`。库无全局可变状态、可重入。
11. **`Widget for &W` + `WidgetRef`**——`widget.rs:16-41`、`ratatui/src/widgets/widget_ref.rs:1`。控件可复用、可动态组合、零克隆。
12. **Feature-gated 后端 + crossterm 版本选择**（core 只依赖 trait，依赖倒置）——`ratatui/Cargo.toml`、`ratatui-crossterm/src/lib.rs:66-78`、`backend.rs:160`。
13. **工作区分层**（core / widgets / 各 backend / macros / main）——`ARCHITECTURE.md`。让 `ratatui-core` 保持 `no_std` 且无终端依赖。

## FTXUI（7.1.0）

1. **两遍布局协议**：`ComputeRequirement()`（子→父）再 `SetBox()`（父→子）——`include/ftxui/dom/node.hpp:75-85`、`src/ftxui/dom/node.cpp:105-127`。把"想要多大"与"分到多大"解耦。
2. **迭代式布局收敛**：`Status{iteration, need_iteration}`，上限 20 轮——`node.hpp:70-79`、`node.cpp:105-118`、`flexbox.cpp:150-160`。允许"内容决定尺寸又反过来影响换行"的循环依赖。
3. **一维 flex 分配**：`ComputeGrow`/`ComputeShrinkEasy`/`ComputeShrinkHard`，纯整数 `SafeRatio`——`src/ftxui/dom/box_helper.cpp:13-114`、`hbox.cpp:44-57`。
4. **完整 flexbox（换行 + 主轴/交叉轴对齐）**——`src/ftxui/dom/flexbox.cpp:69-160`、`flexbox_helper.cpp:369`、配置归一化 `flexbox.cpp:24-52`。
5. **Cell 位域样式 + SGR 差分输出**——`include/ftxui/screen/cell.hpp:27-40`、`src/ftxui/screen/screen.cpp:89-160`。
6. **光标归位复用而非清屏**——`src/ftxui/screen/screen.cpp:544-563`、`app.cpp:1119-1124`。避免闪烁与整屏滚动跳动。
7. **Screen 网格跨帧复用**（只在尺寸变化时重建；帧末 `Clear()` 不释放）——`app.cpp:1059-1067,1128`、`surface.cpp:72-74`。稳态每帧分配为 0。
8. **脏帧标记 `frame_valid_`**——`app.cpp:120,929,1013-1015`。无变化时零重绘、零输出。
9. **惰性 OR 事件分发 + 链式焦点**——`component.cpp:174-183,194-203,243-250`、`container.cpp:44-56`。组件无全局焦点注册表，组合即可。
10. **统一任务队列 `Task = variant<Event, Closure, AnimationTask>`**——`include/ftxui/component/task.hpp:14`、`task_runner.hpp:14-36`、`app.cpp:871-957`。任意线程 `Post`，统一 60fps 节流。
11. **终端能力运行时探测 + `Quirks` 覆盖**——`terminal.cpp:57-63,262-278,327-381`、`terminal.hpp:53-99`。
12. **Unicode 宽度区间表 + 二分查找 + ASCII 快路径**——`src/ftxui/screen/string.cpp:69-115,254-260,304+`、`string_unicode_tables.ipp`。
13. **Windows VT100 模拟**：启动时对 stdout 开 `ENABLE_VIRTUAL_TERMINAL_PROCESSING`，把两套平台代码统一到 ANSI 输出——`src/ftxui/screen/screen.cpp:48-81`。
14. **ABI 预留**：`ComponentBase`/`Node`/`Screen` 各有 `Reserved1..8()` 虚函数 + PImpl——`component_base.hpp:95-102,110-113`、`node.hpp:80-85`。跨版本混用共享库时不动 vtable 布局。

---

# 最小单元追踪（六问）

**最小完整单元**：*画一个带颜色的边框，显示 `hello`，并响应一次按键。*

六问问法在三家完全一致，答案才有对照价值。

| # | 问题 | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 外部输入在哪里进入？ | `render(<App/>)` → React root（`src/render.ts:201`、`src/ink.tsx:1006`）；按键从 `stdin` `'readable'`（`App.tsx:373`） | `Terminal::draw(closure)`（`render.rs:81`）；按键在**调用者的** `crossterm::event::read()`（`ratatui/src/lib.rs:272`） | `App::FitComponent()` + `screen.Loop(component)`（`app.cpp:1543`）；按键从 `FetchTerminalEvents`（`app.cpp:1328-1452`） |
| 2 | 第一次转换是什么？ | JSX → React element → reconciler `createInstance` 建 `ink-box`/`ink-text` 并挂 Yoga 样式（`reconciler.ts:292-334`）；文本经 `internal_transform` 变 SGR（`Text.tsx:100-141`） | 无转换：`Widget` 构造即最终形态（如 `Block::bordered()` / `Paragraph::new("hello")`） | 工厂函数构造 `Node` 子类：`FgColor(Border(Text))`（`elements.hpp:57,91,130`） |
| 3 | 内部表示对象是什么？ | `DOMElement` 树（每节点带 `yogaNode`，`dom.ts:24,97`）+ 一帧的 `Output` 网格（`output.ts:132`） | `Buffer`（`Vec<Cell>`），widget 直接写进去（`buffer.rs:67-72`） | `Node` 树（`node.hpp:38`）+ `Screen` 的 `Cell` 网格（`surface.hpp:70`） |
| 4 | 谁决定下一次计算？ | React commit：`resetAfterCommit` → `onRender`（30fps 节流）（`reconciler.ts:245`、`ink.tsx:362,437`） | **调用者**：处理完按键再调 `draw`（`render.rs:81`） | `App::RunOnce`：有任务执行才 `Draw`（`app.cpp:831-836`），事件把 `frame_valid_=false`（`app.cpp:929`） |
| 5 | 谁调用最底层（写 stdout）？ | `Ink.renderFrame` → `renderInteractiveFrame` → `log-update` 的 `stream.write`（`ink.tsx:547,713`、`log-update.ts:76,105`） | `Terminal::flush` → `Backend::draw(changed_cells)` → crossterm `execute!`（`buffers.rs:97`、`backend.rs:169`、`ratatui-crossterm/src/lib.rs:232`） | `Screen::ToString` → `TerminalFlush`（`screen.cpp:474-519`、`app.cpp:1146-1153`） |
| 6 | 结果在哪里变回外部形式？ | `Output.get()` 拼成 ANSI 字符串（行尾 `trimEnd`），由 log-update 擦行重写（`output.ts:355,394`、`log-update.ts:76-110`） | `CrosstermBackend::draw` 发 `MoveTo`/`SetColors`/`SetAttribute`/`Print`，末尾 `Backend::flush`（`ratatui-crossterm/src/lib.rs:232-310`） | `ToString` 逐 cell 生成转义序列 + 末尾追加 `'\0'` 再 flush（`screen.cpp:474-519,521-523`） |

**这张表的读法**（也就是"最短上手路径"）：

```text
想知道"我改了 state 之后画面什么时候更新" → 看第 4 行
   ink     : 由 React 提交决定，且有 30fps 节流（改两次可能只画一次）
   ratatui : 你调 draw 才画（画两次就是两帧）
   FTXUI   : 事件/任务处理完由 RunOnce 决定，无变化不画（frame_valid_）

想知道"我能不能在终端里同时打印日志" → 看第 5、6 行
   ratatui : 不能随便打印——backend 假设屏幕状态与它的 buffer 一致
   FTXUI   : 要打印得走它自己的机制（printAbove / TerminalOutput）
   ink     : 设计上支持（Static + console 补丁 + 整帧重写）
```

---

# 并排学习的关注点（怎么用这张表继续往下钻）

按"只研究一面"横切，每次回答固定的几个问题：

## 只研究布局

```text
1. 尺寸是谁决定的？（内容 → 布局，还是调用者 → 布局）
2. 冲突约束怎么让步？（Cassowary strength / Yoga flex-shrink / FTXUI 迭代收敛）
3. 结果缓存吗？缓存键是什么？
4. 文本测量发生在布局期还是渲染期？
推荐入口：ratatui-core/src/layout/layout.rs:820；src/dom.ts:266（ink）；src/ftxui/dom/box_helper.cpp:85（FTXUI）
```

## 只研究"帧"的生命周期

```text
1. 一帧从哪个函数开始、到哪个函数结束？
2. 上一帧存在哪？（字符串 / Buffer / 网格本身）
3. 无变化时会怎样？（跳过写入 / 不调用 draw / frame_valid_ 短路）
4. 尺寸变化时谁发现、怎么处理？
```

## 只研究"终端状态"这个隐含契约

```text
这三家对终端都有一个隐含假设："屏幕上显示的就是我上次写的东西。"
   ratatui 把它变成显式不变量（双 buffer diff）——所以最脆弱也最省字节
   FTXUI   用"每帧全量重写 + 光标归位"把它变弱——所以最健壮但字节最多
   ink     用"整帧字符串比较"把它变成本地判断——所以能容忍外部写入
问：这个库在什么情况下会认为自己"画错了"？它有没有提供恢复手段？
     （ink: suspendTerminal + 全清回退；ratatui: 只能靠调用者 clear()；FTXUI: 无）
```

## 只研究"输入到状态"的路径

```text
1. 字节在几个地方被解析？（0 / 1 / 2 层）
2. 事件是广播还是路由？（EventEmitter 广播 / ActiveChild 路由 / 无）
3. 焦点是真的有状态，还是每帧从树推导？（ink: 注册表 + activeId；FTXUI: 沿 ActiveChild 链推导）
4. 库抢答了哪些键？能不能关？
```

## 只研究平台适配

```text
沿同一条链追踪：
尺寸探测 → 能力探测（颜色/块字符/光标）→ 抽象层（有无）→ 输出编码 → Windows 特判
对照结论：
  ratatui 只抽象"输出+尺寸+光标"，输入与能力探测都推给后端；
  FTXUI 抽象最少但探测最细（DA1/DA2/XTVERSION + Quirks）；
  ink 不抽象终端，只抽象"三个流"，能力探测靠 isTTY/is-in-ci + 协议往返。
```

---

# 最终的认知

三个框架本质上都在解决同样三件事：

1. **语义正确性**：把声明式描述正确落到字符网格上——布局、宽字符、裁剪、样式叠加都不能出错。
2. **屏幕状态归属**：明确"上一帧屏幕内容"由谁记、"下一帧"由谁触发——这一条决定了库的并发模型、可重入性、以及能不能在终端里跟别的东西共存。
3. **字节与计算最小化**：每帧少算（缓存/脏节点）与少写（diff 粒度/节流）——三家的产物面差异全部来自这一条。

三个框架分别提供了三个最佳观察窗口：

```text
ink
  → 看"一个通用 reconciler 如何被移植到一个全新的宿主（终端）"
    以及"声明式模型被迫引入延迟绘制网格"这一后果

ratatui
  → 看"立即模式的最小抽象边界在哪里"
    一个 trait、一块 buffer、一份 diff —— 其余全部推给调用者

FTXUI
  → 看"一个自洽的三层栈怎么分层"
    dom 无状态、component 有状态、screen 是数据、App 是循环
```

最值得坚持的元学习问题不是"这个类做什么"，而是：

> 它管理什么状态、作出什么决策、消耗什么资源、把什么不稳定性隔离在了哪一层。

对 TUI 框架再补一问，因为它比推理框架更贴"人机交互"：

> **它对终端做了哪些假设？这些假设在什么条件下会破？破了之后它能自愈吗？**

---

# 本机怎么跑（Windows，实测）

本机工具链：MSVC **14.51.36231**（Visual Studio 18 BuildTools）＋ Windows SDK UCRT 10.0.28000.0，`cmake 3.29.2`、`ninja 1.12.0`、`cargo 1.99.0`、`node v24.16.0`、`bun`。MSVC 通过 `vsenv` 进入（`cl` 不在 PATH 上）。

一个通用陷阱先写在前面：

```text
三家的"headless 渲染"都不需要真实终端，但都可能被宿主环境变量影响配色：
本机 shell 默认带 NO_COLOR=1 和 TERM=dumb。FTXUI 在 NO_COLOR 非空时直接把颜色支持降为
Palette1（src/ftxui/screen/terminal.cpp:221）——这是规范行为，不是 bug。
验证色彩时用 env -u NO_COLOR 再跑一次，否则你会以为"颜色代码没生效"。
```

## FTXUI（7.1.0）— 全流程已实测通过

```bash
# 1) 进入 MSVC 环境（MSYS/Git-Bash 下必须加 MSYS_NO_PATHCONV=1，
#    否则 `cmd //c x.cmd` 只会打开一个交互式 cmd 而不执行脚本）
MSYS_NO_PATHCONV=1 cmd /c "call %LOCALAPPDATA%\VsEnvInjector\enter.cmd && <后续命令>"

# 2) 配置（首次配置 4.1s，零 Windows 特有问题）
cmake -S C:/Projects/FTXUI -B C:/Projects/Temp/ftxui-build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DFTXUI_BUILD_EXAMPLES=OFF -DFTXUI_BUILD_TESTS=OFF \
      -DFTXUI_BUILD_DOCS=OFF -DFTXUI_BUILD_MODULES=OFF

# 3) 构建（约 18s，产出 ftxui-screen.lib / ftxui-dom.lib / ftxui-component.lib，默认 STATIC）
cmake --build C:/Projects/Temp/ftxui-build --parallel
```

`-DFTXUI_BUILD_TESTS=OFF` 可以绕开 GoogleTest 的抓取；`-DFTXUI_BUILD_MODULES=OFF` 可以绕开 CMake ≥3.28 的 C++20 模块机制（正常构建的 `cmake_minimum_required` 只有 3.12）。

**最小 headless 程序**（dom + screen，不需要 `App`，不需要终端）：

```cpp
#include <iostream>
#include "ftxui/dom/elements.hpp"
#include "ftxui/screen/screen.hpp"

int main() {
  using namespace ftxui;
  Element element = text("hello") | border | color(Color::Red);
  Screen screen(20, 5);
  Render(screen, element);
  std::cout << screen.ToString();
}
```

```bash
cl /nologo /std:c++20 /EHsc /utf-8 /MD /O2 /I C:/Projects/FTXUI/include main.cpp /Fe:smoke.exe \
   /link /LIBPATH:C:/Projects/Temp/ftxui-build ftxui-dom.lib ftxui-screen.lib
env -u NO_COLOR ./smoke.exe > out.bin
```

实测产出（`out.bin`，304 字节，转义后）：

```text
\x1b[31m\x1b[49m╭──────────────────╮\x1b[39m\x1b[49m\r\r\n
\x1b[31m\x1b[49m│hello             │\x1b[39m\x1b[49m\r\r\n
\x1b[31m\x1b[49m│                  │\x1b[39m\x1b[49m\r\r\n
\x1b[31m\x1b[49m│                  │\x1b[39m\x1b[49m\r\r\n
\x1b[31m\x1b[49m╰──────────────────╯\x1b[39m\x1b[49m
```

可见形态：

```text
╭──────────────────╮
│hello             │
│                  │
│                  │
╰──────────────────╯
```

三个必须知道的细节：

| 细节 | 说明 |
| :--- | :--- |
| `/utf-8` 不可省 | FTXUI 把它设为 **PUBLIC** 编译选项，否则 MSVC 默认代码页会弄坏源码里的 UTF-8 字面量 |
| 静态库链接顺序 | `ftxui-component.lib` → `ftxui-dom.lib` → `ftxui-screen.lib`（依赖方向倒着写会链接失败） |
| `\r\r\n` 不是 bug | FTXUI 发 `\r\n`（`src/ftxui/screen/screen.cpp:481`），MSVC CRT 文本模式再把裸 `\n` 翻成 `\r\n`。要字节精确就 `_setmode(_fileno(stdout), _O_BINARY)` |

**真实终端（ConPTY）验证**——直接编译仓库自带的 `examples/component/print_key_press.cpp`（`App::TerminalOutput()` + `screen.Loop`）：

```text
首帧（逐字）：
╭────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────╮
│Codes                                   │Event                                                                        │
├────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
╰────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────╯

输入 "ab" + Enter 后：
│ 97   │Event::Character("a") │
│ 98   │Event::Character("b") │
│ 10   │Event::Return         │

写 0x03（ETX）→ Event::CtrlC → 进程干净退出
```

这四步正好把「最小单元追踪」的六问全部落到了实证上：`Render(screen, element)` 对应第 3、4 问（表示对象 + 变字节），PTY 那次对应第 5、6 问（谁拥有循环 + 谁决定下一帧）。仓库本身零改动（`git status --porcelain` 为空），所有临时文件都在 `C:/Projects/Temp/` 下。

## ratatui（0.30.2）— 全流程已实测通过

```bash
# 0) 不需要 vsenv：rustc 1.99 自带 MSVC 探测，会找到已装的 VS BuildTools 18.6.0 + Windows SDK
#    toolchain: stable-x86_64-pc-windows-msvc

# 1) 冷编译（依赖走 rsproxy-sparse 镜像）
cargo check -p ratatui-core          # 20.08s（冷）

# 2) 跑测试（这就是它的"渲染正确性"基线）
cargo test  -p ratatui-core          # 1474 passed / 0 failed + tests/rect.rs 5 + doctest 163 passed(20 ignored)
cargo test  -p ratatui-widgets block # 166 passed / 0 failed
```

`ratatui-core` 的测试里就有渲染路径的直接证据：`backend::test::tests::draw`、`backend::test::tests::assert_buffer`、`buffer::diff::tests::single_cell_change` 全部通过；`ratatui-widgets` 的 block 测试是拿真实渲染出的 cell 与 box-drawing 快照对比（如 `block::tests::render_merged_borders::case_1_replace`）。

**最小 headless 程序**（`TestBackend` 就是仓库自带的"内存终端"，且**不需要 feature flag**）：

```rust
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use ratatui::widgets::{Block, Gauge, Paragraph};

let mut terminal = Terminal::new(TestBackend::new(44, 8))?;
terminal.draw(|frame| {
    let [top, bottom] = ratatui::layout::Layout::vertical([
        ratatui::layout::Constraint::Length(6),
        ratatui::layout::Constraint::Length(2),
    ])
    .areas(frame.area());
    frame.render_widget(
        Paragraph::new("ratatui render path OK").block(Block::bordered().title("smoke")),
        top,
    );
    frame.render_widget(Gauge::default().block(Block::bordered().title("gauge")), bottom);
})?;
```

实测输出（44×8，逐字）：

```text
┌smoke─────────────────────────────────────┐
│ratatui render path OK                    │
│                                          │
└──────────────────────────────────────────┘
┌gauge─────────────────────────────────────┐
└──────────────────────────────────────────┘

```

第 0 行的码点验证：`['┌', 's', 'm', 'o', 'k', 'e', '─', … '─', '┐']`——真的 U+250C / U+2500，不是 ASCII 替代。最后两行空行是布局算术的直接体现（两个 `Length` 约束之外还剩 2 行）。

**真实终端（ConPTY）验证**——仓库自带的 `popup` 示例（按 `q` 退出）：

```text
FRAME 1（首帧，ConPTY 下约 3.5s 才出现）：
 0|                     Press 'p' to toggle popup, 'q' to quit|
 1|┌Content───────────────────────────────────────────────────────────────────────┐|
 2|│                                                                              │|
...
23|└──────────────────────────────────────────────────────────────────────────────┘|

原始 VT 头：\x1b[1t\x1b[c\x1b[?1004h\x1b[?9001h\x1b[?1049h\x1b[1;22HPress\x1b[1;28H'p'...
（\x1b[?1049h = 进备用屏，之后是光标定位写入 + UTF-8 box 字符）
按 'p' → 观察到帧 diff 重绘；按 'q' → 进程自行退出
```

**没有 TTY 时会怎样**（这一条是 ratatui 契约的关键实证）：

```text
把 stdout 重定向到文件、stdin=DEVNULL 运行 popup.exe：
  - 不报错、不 panic：正常开始，向管道写出 \x1b[?1049h + 定位文本（5s 写出 4367 字节），
    stderr 0 字节
  - 但它永远不退出，并且一直在重绘——因为 event::read() 拿不到按键

探针结果：
  is_terminal(stdin/stdout/stderr) = false false false
  crossterm::terminal::enable_raw_mode() -> Ok(())
  crossterm::terminal::size()            -> Ok((120, 30))
```

结论：**Windows 上 crossterm 0.29 的 raw mode / size 在没有控制台时并不失败**；真实 TTY 是"能收到正确输入"的必要条件，不是"能画帧"的必要条件。这正好对应它对终端的隐含假设——它假设的其实是**输入通道**，不是输出通道。

三个操作坑：

| 坑 | 说明 |
| :--- | :--- |
| 裸 exe 不能直接执行 | 本机 shell 对 `./x.exe` 报 `command not found`（exit 127）；用 `cargo run` 或 Python `subprocess` 启动 |
| ConPTY 首帧有延迟 | 约 3.5s 才开始出字节（两次独立复现都是 23 字节直到 3.5s）；抓帧要等 ≥4s，8s 稳定 |
| 示例是独立 crate | `examples/apps/*` 各自是 workspace member，要用 `cargo build -p popup` / `-p hello-world`，不是 `--example` |

## ink（8.0.0）— 全流程已实测通过

```bash
# 1) 装依赖（Node v24.16.0 / bun 1.4.2；bun 会顺带跑 prepare → tsc，生成 build/）
cd C:/Projects/ink && bun install          # 646 packages, 168.20s（1 个 postinstall 被 block，无害）

# 2) headless：用 tsx 直接跑仓库的裸 TypeScript 源码，无需先 build
FORCE_COLOR=1 node --import=tsx headless.mjs
```

`headless.mjs` 只要能解析 `react` 与仓库源码即可（`tsx` 会把 `src/index.js` 映射回 `.ts`）：

```js
import {createElement as h} from 'react';
import {renderToString, Box, Text} from '../../ink/src/index.js';

console.log(JSON.stringify(
  renderToString(h(Box, {borderStyle: 'round', borderColor: 'green'},
    h(Text, {bold: true, color: 'cyan', backgroundColor: 'blue'}, 'Hello Ink')))));
```

实测产出（`renderToString` 结果的转义形态，逐字）：

```text
"\u001b[32m╭──────────────────────────────────────╮\u001b[39m\n
 \u001b[32m│\u001b[39m \u001b[1m\u001b[44m\u001b[36mHello Ink\u001b[39m\u001b[49m\u001b[22m   …   \u001b[32m│\u001b[39m\n
 \u001b[32m╰──────────────────────────────────────╯\u001b[39m"
```

即：SGR 32 绿色圆角边框、SGR 1/44/36 粗体＋蓝底＋青字，末尾 39/49/22 复位。

**真实终端（ConPTY via node-pty）验证**——`node --import=tsx interactive.mjs`（含 `useInput`，按 `q` 调 `app.exit()`），8s 后向 PTY 写 `q`：

```text
EXIT_CODE: 0        ← useInput('q') 触发退出
抓到的主端字节（460 字节，节选）：
\x1b[?9001h\x1b[?1004h\x1b[?25l\x1b[2J\x1b[m\x1b[H … \x1b[?25h
\x1b[35m╭───────…───────╮\r\n
│ \x1b[33mpress q to quit\x1b[42X\x1b[35m\x1b[42C│\r\n
╰───────…───────╯\r\n
\x1b[m\r\n\x1b[?25l\x1b[8;1H\x1b[?25h
（= 备用屏/kitty 序列、隐藏光标、清屏、SGR35 品红边框、SGR33 黄字、
  用 cursor-forward 填空白、退出时恢复光标）
```

四个操作坑：

| 坑 | 说明 |
| :--- | :--- |
| `bun run` 渲染没颜色 | chalk 在无 TTY 且无 `FORCE_COLOR` 时不发 SGR；headless 一律用 `FORCE_COLOR=1 node --import=tsx` |
| 别想 patch `stdout` 来抓帧 | ink **不**经 `process.stdout.write` 输出（实测 patch 计数 = 0）；要真帧就用 ConPTY 抓主端字节 |
| 裸跑脚本要能解析 `react` | 在 scratch 目录里对 `C:/Projects/ink/node_modules` 建 junction（Windows 用 `New-Item -ItemType Junction`） |
| 仓库会留下构建产物 | `bun install` 触发 `prepare`，留下 `C:/Projects/ink/node_modules` 与 `build/`（都在 `.gitignore` 覆盖内，源码树未改动、无提交） |

> 顺带一个实证：**bash 工具的 `pty:true` service 模式抓不到 ink 的运行中帧**——它只在进程退出后才 flush 输出，且 `write proc://<id>` 注入的 stdin 到不了 `useInput`。要交互验证就绕开它，用 node-pty/ConPTY 驱动（ratatui 那边同理，用的是 pywinpty）。

## 三家跑法的横向对照

| | ink | ratatui | FTXUI |
| :--- | :--- | :--- | :--- |
| 装依赖 | `bun install`（168s，646 包） | 无（cargo 自动拉） | 无（零依赖） |
| 首次编译 | 无需（tsx 直跑源码；`bun install` 顺带 tsc） | `cargo check -p ratatui-core` 20s | cmake configure 4.1s + build 18s |
| headless 渲染 | `renderToString` | `Terminal::new(TestBackend::new(w,h))` | `Screen(w,h)` + `Render` + `ToString` |
| headless 是否需要改造代码 | 不需要（官方 API） | 不需要（`TestBackend` 非 feature-gated） | 不需要（仓库自己的测试就这么写） |
| 真终端验证 | node-pty（ConPTY） | pywinpty（ConPTY） | bash 工具 pty service（真 ConPTY） |
| 是否要 vsenv | 否 | 否（rustc 自带 MSVC 探测） | **是**（`cl` 不在 PATH） |
| 编译耗时量级 | 分钟级（npm 生态） | 20s~30s（core） | ~20s（全库） |
| 测试基线 | — | `cargo test -p ratatui-core`：1474 + 5 + 163 全绿 | — |

**一个结论**：**三家的 headless 路径都不需要真实终端**，而且都不是"为了测试硬开的洞"——ratatui 的 `TestBackend` 是 `Backend` trait 的普通实现，FTXUI 的 `Screen` 本来就是数据对象，ink 的 `renderToString` 是官方公共 API。这反过来印证了「产物面」那一节的判断：**它们的核心都是"把某个表示对象变成字节"，终端只是这个变换的一个消费者。**
