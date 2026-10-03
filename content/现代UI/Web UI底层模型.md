
# DOM 与 CSSOM

**DOM（Document Object Model）**
浏览器把 HTML 解析成一棵节点树。每个标签、文本、属性都变成对象节点。JS 可以通过它读写页面结构。

**CSSOM（CSS Object Model）**
浏览器把 CSS（外部、内联、`<style>`）解析成另一棵树，描述每个节点该长什么样。CSS 有层叠和继承，所以 CSSOM 的计算比 DOM 复杂。

> 渲染树（Render Tree）≈ DOM + CSSOM 结合后，只保留可见节点。

# Box Model

盒模型

每个元素被看成一个矩形盒子，由内到外：

```
margin（外边距）
  border（边框）
    padding（内边距）
      content（内容）
```

- `box-sizing: content-box`（默认）：`width` 只指 content 宽度。
- `box-sizing: border-box`：`width` 包含 content + padding + border。

# Normal Flow

正常流

默认的布局方式：块级元素从上到下排列，行内元素从左到右排列。脱离正常流的方式有 `float`、`position: absolute/fixed` 等。

# Block / Inline

**Block（块级）**
- 独占一行，宽度默认撑满父容器
- 可设 `width/height`、上下 margin 生效
- 例：`div`、`p`、`h1`

**Inline（行内）**
- 不换行，宽度由内容决定
- `width/height` 无效，上下 margin 不生效
- 例：`span`、`a`、`em`

还有 `inline-block`：像行内元素一样排列，但内部像块级一样可设宽高。

# Containing Block

一个元素计算百分比宽度、定位时的参照矩形。规则：

- 普通流元素：最近的**块级祖先**的内容盒
- `position: absolute`：最近的**定位祖先**（`position` 非 static）的 padding 盒
- `position: fixed`：视口
- `position: relative`：自身原来的位置

# Formatting Conext

格式化上下文

一块独立的布局环境，内部布局规则与外部隔离。

**BFC（Block Formatting Context）** 最常见：
- 内部块级元素垂直排列
- 不与外部 float 重叠
- 包含内部浮动（清除浮动）
- margin 不与外部折叠

触发方式：`overflow` 非 visible、`display: flow-root`、`float`、`position: absolute/fixed`、`display: flex/grid` 等。

还有 IFC（行内）、FFC（flex）、GFC（grid）等。

# Intrinsic Size

固有尺寸

元素内容本身决定的尺寸，与外部约束无关。

- **min-content**：最窄能到多少（不溢出内容），比如最长的单词宽度。
- **max-content**：内容完全不换行时的宽度。
- **fit-content**：介于两者之间，`min(max-content, max(min-content, 可用空间))`。

常用于 `width: min-content | max-content | fit-content(...)`。

# Stacking Context

层叠上下文

决定元素在 Z 轴上如何堆叠的独立环境。触发方式：
- 根元素
- `position` + `z-index` 非 auto
- `opacity < 1`
- `transform`、`filter`、`will-change` 等
- `display: flex/grid` 的子元素 + z-index

**z-index** 只在同一层叠上下文内比较。子元素的 z-index 再大，也跳不出父级上下文。

# Overflow 与 Scroll Container

**Overflow**：内容超出盒子时的处理，`visible`（默认，溢出显示）、`hidden`、`scroll`、`auto`。

**Scroll Container（滚动容器）**：当 `overflow` 为 `scroll/auto/hidden` 且内容溢出时，元素成为可滚动容器。它会影响包含块、粘性定位 `position: sticky` 的参照等。

# Layout / Pain / Composite

浏览器渲染的三个阶段：

1. **Layout（布局/回流）**：计算每个元素的位置和大小。改变宽高、字体、DOM 结构会触发，代价高。
2. **Paint（绘制）**：把元素画成像素，填充颜色、文字、阴影等。改变颜色、背景会触发。
3. **Composite（合成）**：把各层合并成最终画面，由 GPU 完成。`transform`、`opacity` 动画通常只走这一步，性能最好。

现代浏览器把页面分成多个图层（layer），合成阶段单独处理，避免整页重绘。