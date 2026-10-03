# Flexbox

## 你现在的水平 vs 目标水平

**初级理解**（够用但脆）：
```css
display: flex;
justify-content: center;
align-items: center;
```
这只是"把东西居中"，一旦内容变长、容器变窄、需要换行，就崩了。

**工程师级理解**：Flexbox 是一个 **一维空间分配算法**，你要能回答："当空间不够时，谁让步？当空间多余时，谁扩张？"

## 两条轴（一切的起点）

```
main axis  →  flex-direction 决定的主方向
cross axis →  与主轴垂直的方向
```

- `justify-content` 作用于 **主轴**
- `align-items` 作用于 **交叉轴**

很多人记不住，是因为没先确认 `flex-direction`。**轴一变，两个属性作用的方向就交换了。**

## 三个核心概念

| 概念          | 含义                         | 直觉       |
| ------------- | ---------------------------- | ---------- |
| `flex-basis`  | 元素在分配前的**初始尺寸**   | "起点大小" |
| `flex-grow`   | 有**剩余空间**时，按比例扩张 | "分蛋糕"   |
| `flex-shrink` | 空间**不够**时，按比例收缩   | "谁先瘦"   |

`flex: 1 1 auto` = grow 1, shrink 1, basis auto
`flex: 0 0 240px` = 不长大、不缩小、固定 240px

## 三个隐藏概念

**① intrinsic sizing（内在尺寸）**
元素"天生"想多大：文字长度、图片原始尺寸、内容最小宽度。Flex 布局是在 **外在约束** 和 **内在尺寸** 之间谈判。

**② available space（可用空间）**
父容器能提供的总宽度。

**③ free space（剩余空间）**
`available space − 所有子项 flex-basis 之和`
- free space > 0 → 按 `flex-grow` 分
- free space < 0 → 按 `flex-shrink` 扣

## 经典代码

```css
.sidebar {
    flex: 0 0 240px;
}

.content {
    flex: 1 1 auto;
    min-width: 0;
}
```

**为什么这样写？**

- `.sidebar` 固定 240 px，**永不伸缩** → 侧边栏是"锚点"，稳定不跳。
- `.content` 吃掉所有剩余空间 → 主内容自适应。
- `min-width: 0` 是**关键中的关键**：
  - Flex 子项默认 `min-width: auto`，意味着它至少要和内容一样宽。
  - 内容里有长文本 / `<pre>` / 表格时，会**撑破容器**导致布局溢出。
  - 设成 `0` 后，允许它收缩到比内容更窄，从而触发内部换行 / 省略号 / 滚动。

**一句话**：`flex: 0 0 240px` + `flex: 1 1 auto` + `min-width: 0` 是"固定侧栏 + 弹性主区"的标准范式。

# CSS Grid

Flexbox 是**一维**（一行或一列），Grid 是**二维**（行和列同时控制）。现代 UI 布局（仪表盘、卡片墙、后台管理系统）几乎都靠 Grid。

## 核心属性

```
grid-template-columns / rows  → 定义显式网格轨道
fr                            → 剩余空间的份数单位
minmax(min, max)              → 轨道尺寸范围
repeat(n, ...)                → 重复轨道
auto-fill / auto-fit          → 自动决定列数
grid-area                     → 一个元素占据的区域
implicit grid                 → 超出显式定义时自动生成的行/列
explicit grid                 → 你显式声明的行列
subgrid                       → 子网格继承父网格轨道
```

## fr

`1fr` = "一份剩余空间"。它**不是百分比**：
```css
grid-template-columns: 200px 1fr 2fr;
/* 200px 固定，剩下按 1:2 分 */
```

## minmax()+repeat()+auto-fit() 三件套

```css
grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
```

**逐层解读：**
- `minmax(280px, 1fr)`：每列至少 280 px，最多 1 fr（可扩张）
- `auto-fit`：**能塞几列就塞几列**，塞不满时把空轨道合并，让已有列拉伸占满
- `auto-fill`：同样塞列，但**保留空轨道**，不拉伸

**一句话**：
> "这是一个会根据空间自动改变列数的 responsive card grid。"
> 容器变宽 → 列数自动增加；变窄 → 自动减少；永远不溢出、不留白。

**auto-fit vs auto-fill 的区别**：当卡片少、容器宽时：
- `auto-fit`：卡片被拉大，铺满整行
- `auto-fill`：卡片保持 280 px，右侧留空

## 显式 vs 隐式网格

- 显式：你写了 `grid-template-rows: 100px 100px` → 就是这两行
- 隐式：内容超了，Grid 自动"补"出行，由 `grid-auto-rows` 控制
- **陷阱**：不设 `grid-auto-rows` 时，隐式行高度由内容决定，容易长短不一。

## subgrid

子网格可以让子元素的网格线**对齐父网格**，解决"卡片内标题高度不齐"这类问题（现代浏览器已支持）。

# Positioning

## 5 种 position

| 值         | 参照物             | 是否脱离文档流   | 典型用途              |
| ---------- | ------------------ | ---------------- | --------------------- |
| `static`   | 无                 | 否               | 默认                  |
| `relative` | 自身原位置         | 否               | 微调 + 做绝对定位的锚 |
| `absolute` | 最近的**定位祖先** | 是               | 浮层、角标            |
| `fixed`    | **视口**           | 是               | 固定导航、悬浮按钮    |
| `sticky`   | **最近滚动容器**   | 否（临界时粘住） | 吸顶表头、吸边侧栏    |

## 三个需要精细的概念

**① containing block（包含块）**
`absolute` 不是相对"父元素"，而是相对**最近的 position ≠ static 的祖先**。找不到就相对初始包含块（≈视口）。这是"absolute 乱飞"的根因。

**② scroll container（滚动容器）**
`sticky` 是相对**最近的滚动祖先**粘住的，不是相对视口。父级只要有 `overflow: hidden/auto/scroll`，sticky 就可能失效或行为异常。

**③ stacking context（层叠上下文）**
`z-index` 不是全局的，只在**同一个层叠上下文内**比较。触发条件包括：`position + z-index`、`transform`、`opacity < 1`、`filter`、`will-change` 等。这就是"我 z-index 明明很大却被盖住"的原因。

## 练习清单

- **Sticky Header**：`position: sticky; top: 0`
- **Sticky Sidebar**：`position: sticky; top: 1rem`
- **Floating Toolbar**：`fixed` + 安全区
- **Dropdown**：`relative` 父 + `absolute` 子
- **Tooltip**：`absolute` + 箭头（伪元素）
- **Popover**：`absolute` + 点击外部关闭
- **Context Menu**：跟随鼠标坐标
- **Modal**：`fixed` 全屏遮罩 + 居中
- **Command Palette**：`fixed` 居中 + 键盘导航 + 焦点陷阱

## Responsive Design

响应式涉及

## 从 breakpoint 到容器

**旧思维**：
> PC 做一个版本，手机再写一个版本。

**新思维**：
```
Viewport → Page → Container → Component
```
组件应该**关心自己所在的容器有多大**，而不是"屏幕有多宽"。

## 工具清单

```css
@media (min-width: 768px) { ... }      /* 传统断点 */

@container (min-width: 400px) { ... }  /* 容器查询，组件级响应式 */

min() / max() / clamp()                /* 流体尺寸 */

minmax() / auto-fit / auto-fill        /* 网格自适应 */

vw / vh / dvh                          /* 视口单位（dvh 解决移动端地址栏问题） */

rem                                    /* 相对根字号，可访问性友好 */
```

## Fluid UI 的核心：clamp()

```css
font-size: clamp(1rem, 2vw, 1.5rem);
```

- 最小值 `1rem`
- 理想值 `2vw`（随视口缩放）
- 最大值 `1.5rem`

**含义**：字号在 1 rem 到 1.5 rem 之间**平滑变化**，不需要任何断点。

同理可用于 `padding`、`gap`、`width`、`margin`：
```css
padding: clamp(1rem, 3vw, 2.5rem);
```

## 目标：Fluid UI

- 布局用 **Grid + minmax + auto-fit** 自动列数
- 间距 / 字号用 **clamp()** 平滑缩放
- 组件内部用 **@container** 感知自身宽度
- 少量 **@media** 只处理"结构性"变化（如侧栏折叠成抽屉）

**最终效果**：不是"两套版本"，而是**一套连续适应所有尺寸的界面**。
