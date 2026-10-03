
# Spacing

间距

## Spacing Scale

```
4
8
12
16
20
24
32
40
48
64
```

意思是：不要随便写 `margin: 13px`、`padding: 7px`，而是用一套**有限的、成体系的间距值**。

好处：

- 视觉上更统一
- 团队协作有共识
- 容易转成 design token
- 代码里也好维护

这跟 Tailwind 的 `p-1 / p-2 / p-4`、Ant Design 的 spacing token 是一个思路。

## 观察间距的三种角色

```
元素内部距离 → padding
同组元素距离 → gap
不同 section 距离 → section spacing
```

这是在说：**不同层级的距离，表达不同的关系。**

- **padding**：元素自己内部的呼吸感，比如按钮文字和按钮边框之间。
- **gap**：同一组元素之间的距离，比如一排按钮之间、一个表单里 label 和 input 之间。
- **section spacing**：不同内容区块之间的距离，比如「标题区」和「正文区」之间。

## 核心概念

> **Proximity creates grouping.**
> 接近性产生分组。

这是格式塔心理学（Gestalt）的基本原则：**靠得近的东西，会被大脑自动认为是一组的。**

所以间距不是审美问题，而是**信息结构问题**。你不需要画线、加框，只要调整距离，用户就能感知「哪些是一伙的，哪些是分开的」。

# Typography

字体排印

## 系统理解字体

```
font family      字体族
font size        字号
font weight      字重
line height      行高
letter spacing   字间距
line length      行宽（一行多少字）
```

这六个是排版的基本变量。任何一个变了，阅读体验都会变。

## 建立文字层级

```
Display      展示级（最大，用于 hero 区）
Heading      标题
Subheading   副标题
Body         正文
Label        标签
Caption      说明文字
Code         代码
```

这是按**信息重要性**分的层级，不是按大小随便起的名字。

## 建立 typography scale

例如：

```
Display       36
Heading 1     30
Heading 2     24
Heading 3     20
Body          16
Small         14
Caption       12
```

## 重点

> **Typography 本身就是信息架构。**
> 字体排印本身就是信息架构。

意思是：用户还没读内容，光看**字号大小、字重粗细、层级关系**，就已经知道：

- 哪个是标题
- 哪个是正文
- 哪个是次要说明
- 信息的主次顺序是什么

所以排版不是「把字放好看」，而是**用视觉手段表达内容结构**。

# Color

## 不要沉迷配色

很多人一上来就纠结「这个蓝色好不好看」「渐变怎么调」，这是美术思维。

工程师/系统设计更需要的是 **Semantic Color（语义化颜色）**。

## 三层配色体系

### primitive（原始色）

```
gray-100
gray-200
blue-500
red-500
```

这是调色板，是原材料，**不带含义**。`blue-500` 只是「第 5 档蓝色」，它不告诉你用在哪。

### semantic（语义色）
```
background      背景
foreground      前景/文字
muted           弱化
primary         主色
secondary       次要色
danger          危险
warning         警告
success         成功
border          边框
```

这一层开始**带含义**。比如 `danger` 不是「红色」，而是「表示危险的颜色」。哪天品牌色变了，`danger` 还是 `danger`，只是底层 primitive 换了。

### component（组件色）

```
button-background
input-border
card-background
```

这一层是**具体组件用的颜色**，直接对应代码里的变量。

## 意义

```
primitive → semantic → component
```

这个链路会直接通向 **Design Token**。

Design Token 就是：**把设计决策变成可复用的变量**，让设计和代码共享同一套语言。比如：

```css
--color-danger: var(--red-500);
--button-background: var(--color-primary);
```

换主题、换品牌、做暗色模式，都只改 token，不用改组件。


# Visual Hierarchy

视觉层级

## 学习要素


```
Contrast      对比
Proximity     接近
Alignment     对齐
Repetition    重复
Whitespace    留白
Scale         尺度
Density       密度
```

这些是控制「用户先看什么、后看什么」的工具。

## 核心问题

> 为什么我第一眼先看到这里？

每看到一个界面，都问自己这个问题。

如果你能回答出来，说明你理解了它的视觉层级；如果你回答不出来，说明这个界面的层级是混乱的，或者你没看懂。

视觉层级的目的就是：**让用户的眼睛按你设计的顺序移动。**