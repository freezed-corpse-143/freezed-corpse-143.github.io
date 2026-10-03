# Motion == Communication

意思是：动效的首要目的不是"炫酷"，而是**传达信息**。比如：

- 一个按钮点击后微微下沉 → 告诉用户"我收到了你的操作"
- 弹窗从中心放大出现 → 告诉用户"这是当前焦点"
- 列表项滑出删除 → 告诉用户"它被移除了"

所以学习顺序是：**先理解动效在"说什么"，再去研究怎么做得好看**。一上来就沉迷粒子爆炸、3D 翻转，容易学成"特效堆砌"，而不是设计。

# CSS Motion

## 五个核心属性/规则

| 名称         | 作用                                        |
| ------------ | ------------------------------------------- |
| `transition` | 状态 A → 状态 B 的**过渡**（如 hover 变色） |
| `transform`  | 对元素做**形变**（位移、缩放、旋转）        |
| `opacity`    | **透明度**，常用于淡入淡出                  |
| `@keyframes` | 定义**关键帧**，描述动画的多个阶段          |
| `animation`  | 把 `@keyframes` **应用到元素**上并控制播放  |

简单区分：
- `transition` = 两个状态之间的补间（被动触发）
- `animation` = 多关键帧的主动播放（可循环、可自动）

## transform 的三个常用函数

```
translate  → 位移（x/y/z）
scale      → 缩放
rotate     → 旋转
```

这三个是**性能最好**的动画属性，因为它们通常只触发 GPU 合成，不引起重排（reflow）。

# Timing - Motion 的手感

## 常见时长挡位

```
100ms  → 极快，微反馈（按钮按下、图标切换）
150ms  → 快，hover、小元素
200ms  → 常用默认值
300ms  → 中等，弹窗、面板
500ms  → 较慢，页面级、大幅位移
```

规律：**元素越大、位移越远、越重要 → 时长越长**。反之则越短。

## 三个时间参数

| 参数       | 含义                      |
| ---------- | ------------------------- |
| `duration` | 动画持续多久              |
| `delay`    | 延迟多久开始              |
| `easing`   | 速度曲线（怎么加速/减速） |

## 缓动函数（Easing）

```
ease-in       → 慢起快停（适合"离开"）
ease-out      → 快起慢停（适合"进入"，最自然）
ease-in-out   → 两头慢中间快（适合往复运动）
cubic-bezier  → 自定义曲线，精确控制
spring        → 弹簧效果，带过冲/回弹（更"物理"）
```

经验法则：
- **进入画面**用 `ease-out`（快速出现，温柔停下）
- **离开画面**用 `ease-in`（缓慢启动，快速消失）
- **原地变化**用 `ease-in-out`

`spring` 不是 CSS 原生曲线，通常靠 JS 动画库（如 Framer Motion、React Spring）实现，手感更活泼。

# Motion Pattern

这些是**常见的动效"套路"**，也就是"什么场景该用什么动画"。

## 基础进出

```
Enter        → 元素出现（淡入、上滑进入）
Exit         → 元素消失（淡出、下滑离开）
Crossfade    → 两个元素交叉淡入淡出（内容切换）
```

## 尺寸变化

```
Expand       → 展开（如手风琴、下拉菜单）
Collapse     → 收起
```

## 高级模式

```
Shared Element   → 共享元素：一个元素从 A 位置"飞"到 B 位置
                   （如列表缩略图 → 详情大图）
Layout Animation → 布局变化时，其他元素自动平滑让位
Gesture          → 手势驱动（拖拽、滑动、长按）
Drag             → 拖拽
Scroll Animation → 滚动触发的动画（视差、进度条）
Page Transition  → 页面之间的转场
```

这些模式是**产品级动效的通用语言**，掌握后就能应对绝大多数 UI 场景。

# 进阶 API(现代 Web 动画能力)

```
Web Animations API (WAAPI)
```
JS 原生的动画接口，`element.animate(...)`，比 CSS 更灵活，能动态控制播放、暂停、反转。

```
View Transitions API
```
浏览器原生支持的**页面/视图转场**，能自动做共享元素、淡入淡出，写很少代码就实现 App 级转场。

```
Scroll-driven Animations
```
用**滚动进度**直接驱动动画（纯 CSS，`animation-timeline: scroll()`），替代过去靠 JS 监听 scroll 的写法，性能更好。

## 总结

| 层次  | 内容                                       | 目标         |
| --- | ---------------------------------------- | ---------- |
| 观念  | Motion = Communication                   | 动效是信息，不是装饰 |
| 工具  | CSS transition/transform/animation       | 会写基础动画     |
| 手感  | duration / easing / spring               | 做出"舒服"的动效  |
| 模式  | Enter/Exit/Shared Element…               | 应对常见 UI 场景 |
| 进阶  | WAAPI / View Transitions / Scroll-driven | 做产品级、高性能动效 |