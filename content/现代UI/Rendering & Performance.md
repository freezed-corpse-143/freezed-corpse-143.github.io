# 渲染管线：从 JavaScript 到 Composite


浏览器把代码变成屏幕像素，大致经过这几个阶段：

```
JavaScript → Style → Layout → Paint → Composite
```

## 1. JavaScript
执行 JS，可能修改 DOM、CSSOM、类名、样式属性等。这是“触发渲染变化”的源头。

## 2. Style（样式计算 / Recalculate Style）
浏览器根据 CSS 选择器，计算出每个元素最终生效的样式值（computed style）。比如 `.box { width: 100px }` 最终作用到哪个元素上。

## 3. Layout（布局 / 回流 / Reflow）
根据样式计算每个元素的**几何信息**：位置、大小、边距、换行等。  
输出的是每个元素在页面中的精确坐标和尺寸。

## 4. Paint（绘制 / Repaint）
把元素画成像素。比如背景色、边框、文字、阴影、圆角等，生成绘制指令，通常分层进行。

## 5. Composite（合成）
把各个图层（layer）合并成最终屏幕图像。现代浏览器大量使用 GPU 来做这一步。

> 关键点：**不是每次修改都会走完整个管线**。改的属性不同，触发的阶段不同，成本也不同。

# transform / opacity 适合动画

因为它们**可以跳过 Layout 和 Paint，直接进入 Composite**。

- `transform`：平移、缩放、旋转。它改变的是元素的“变换矩阵”，不影响文档流中其他元素的位置和大小。
- `opacity`：透明度。它不改变几何布局，也不一定需要重绘内容。

当元素被提升为**独立合成层（compositing layer）**后，浏览器可以只让 GPU 重新合成这一层，而不必重新布局和重绘整个页面。

所以动画用：

```css
transform: translateX(100px);
opacity: 0.5;
```

通常比用 `left`、`top`、`width`、`height` 更流畅。

> 注意：`transform` / `opacity` 也不是绝对免费。层太多会占显存，合成本身也有成本。但在动画场景下，它们通常是更优选择。

# 频繁修改 width / height / top / left 成本高

这些属性属于**几何属性**，会影响布局。

- 修改 `width` / `height`：元素尺寸变了，可能影响周围元素、父元素、甚至整页排版。
- 修改 `top` / `left`（在非 `position: fixed` 的普通定位中）：元素位置变了，浏览器需要重新计算布局。
- 一旦布局变化，往往紧接着要 **Paint**，再 **Composite**。

也就是说，改这些属性可能触发：

```
Layout → Paint → Composite
```

而 `transform` / `opacity` 往往只需要：

```
Composite
```

所以频繁改 `width` / `height` / `top` / `left` 做动画，容易造成卡顿，尤其是在低端设备上。

# Reflow / Repaint / Composite

## Reflow（回流 / Layout）
重新计算布局。成本最高，因为它可能影响一大片 DOM。  
常见触发：修改宽高、位置、字体大小、添加删除 DOM、读取某些布局属性（如 `offsetTop`、`getBoundingClientRect()`）等。

## Repaint（重绘）
不改变布局，只重新画像素。比如改 `background-color`、`color`、`visibility`。  
成本低于 Reflow，但仍然可能很贵。

## Composite（合成）
只重新合成图层，通常由 GPU 完成，成本最低。  
`transform`、`opacity` 动画通常走这条路。

> 一句话：**Reflow 最贵，Repaint 次之，Composite 最便宜。**

# GPU acceleration

浏览器可以把某些元素提升为独立图层，交给 GPU 合成。  
常见触发方式：

```css
transform: translateZ(0);
will-change: transform;
```

好处：动画更流畅。  
坏处：图层过多会消耗显存、增加合成开销，反而变慢。所以要**按需使用**，不要滥用 `will-change`。

# requestAnimationFrame


`requestAnimationFrame`（rAF）是浏览器提供的动画调度 API。

```js
function animate() {
  // 更新动画状态
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

它的特点：

- 回调在浏览器**下一次重绘之前**执行。
- 与屏幕刷新率对齐（通常是 60 Hz、120 Hz 等）。
- 页面不可见时会自动暂停，节省资源。

比 `setTimeout` / `setInterval` 更适合做动画和视觉更新。

# ResizeObserver

监听元素尺寸变化。

```js
const ro = new ResizeObserver(entries => {
  for (const entry of entries) {
    console.log(entry.contentRect);
  }
});
ro.observe(document.querySelector('.box'));
```

用途：响应式组件、图表重绘、虚拟列表容器尺寸变化等。  
比监听 `window.resize` 更精确，因为它能监听**任意元素**的尺寸变化。

# IntersectionObserver

监听元素是否进入视口（或某个祖先容器）。

```js
const io = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // 元素进入视口
    }
  });
});
io.observe(document.querySelector('.item'));
```

用途：

- 图片懒加载
- 无限滚动
- 曝光埋点
- 动画触发

它比监听 `scroll` 事件手动计算位置更高效，因为浏览器内部优化了可见性判断。

# Virtual List


只渲染视口内可见的列表项，而不是渲染成千上万条 DOM。

原理：

- 监听滚动位置
- 计算当前应该显示哪几项
- 只渲染这几项，并用占位撑起总高度

优点：大幅减少 DOM 数量，提升长列表性能。  
常见库：`vue-virtual-scroller`、`react-window`、`react-virtualized`。

# Lazy Loading

延迟加载非关键资源，比如图片、组件、路由模块。

```html
<img src="placeholder.jpg" data-src="real.jpg" loading="lazy" />
```

或动态 `import()`：

```js
const module = await import('./heavy-module.js');
```

目的：减少首屏加载量，加快初始渲染。

# CLS / LCP / INP

这是 **Core Web Vitals**（核心网页指标），衡量真实用户体验。

## CLS（Cumulative Layout Shift）
累计布局偏移。  
衡量页面加载过程中，内容是否突然“跳动”。  
比如图片没设宽高，加载后把文字挤下去，CLS 就差。

优化：给图片/广告位预留尺寸，避免动态插入内容导致布局偏移。

## LCP（Largest Contentful Paint）
最大内容绘制。  
衡量首屏最大可见内容（大图、大标题等）何时渲染完成。  
目标：2.5 秒内。

优化：优化图片、字体、关键 CSS、减少阻塞资源。

## INP（Interaction to Next Paint）
交互到下一次绘制。  
衡量用户点击、输入后，页面多久给出视觉反馈。  
目标：200 毫秒内。

优化：减少长任务、拆分 JS、避免主线程阻塞。

> 早期还有 FID（First Input Delay），现在逐渐被 INP 取代。

# 总结

这张图/清单的核心逻辑是：

1. **理解浏览器渲染管线**：JS → Style → Layout → Paint → Composite。
2. **知道不同 CSS 属性触发哪些阶段**：`transform` / `opacity` 走合成，`width` / `height` / `top` / `left` 容易触发 Layout。
3. **掌握性能工具与 API**：rAF、ResizeObserver、IntersectionObserver。
4. **掌握优化手段**：虚拟列表、懒加载、GPU 加速。
5. **用指标衡量体验**：CLS、LCP、INP。