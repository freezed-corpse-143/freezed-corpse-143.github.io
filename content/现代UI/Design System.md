# 总体类别：软件架构 vs UI 架构

```
Software Architecture        UI Architecture

Primitive Type               Design Token
      ↓                            ↓
   Utility                     Primitive
      ↓                            ↓
  Component                    Component
      ↓                            ↓
   Module                       Pattern
      ↓                            ↓
  Application                     Page
```

这个对照表想说明：

| 软件架构       | UI 架构      | 含义                       |
| -------------- | ------------ | -------------------------- |
| Primitive Type | Design Token | 最底层、不可再分的原子单位 |
| Utility        | Primitive    | 基础工具/基础组件          |
| Component      | Component    | 可复用的功能单元           |
| Module         | Pattern      | 由组件组合成的模式         |
| Application    | Page         | 最终交付给用户的产品       |

也就是说，**写 UI 和写软件一样，都是从原子 → 组合 → 应用逐层抽象**。Design System 就是 UI 世界的「架构规范 + 基础设施」。

# Design Token

Design Token 是设计系统里最小的、可命名的样式决策单元。它把「颜色、间距、圆角」等原始值抽象成有语义的名字，分三层：

```
Primitive Token（原始令牌）
    blue-500
    gray-900
    space-4
    radius-md
        ↓
Semantic Token（语义令牌）
    primary
    background
    foreground
    muted
    danger
        ↓
Component Token（组件令牌）
    button-primary-bg
    dialog-background
    input-border
```

## Primitive Token（原始令牌）
- 纯粹描述「值」本身，不带用途含义。
- 例如 `blue-500` 就是某个具体的蓝色，`space-4` 就是某个具体间距。
- 类似编程里的**原始类型**（string、int）。

## Semantic Token（语义令牌）
- 描述「用途/角色」，不绑定具体值。
- 例如 `primary`（主色）、`background`（背景）、`danger`（危险色）。
- 好处：换主题时只改映射关系，不用改每个组件。
- 类似编程里的**变量/接口**。

## Component Token（组件令牌）
- 针对具体组件的样式决策。
- 例如 `button-primary-bg`、`input-border`。
- 类似编程里的**具体实现**。

**关键价值**：改一层，全局生效；主题切换、暗色模式、品牌换肤都靠这套分层。

# Headless Component

这是现代前端/设计系统里非常重要的思想。

> Headless Component = 只负责「行为」，不负责「长相」。

研究 Radix UI 这类项目时，重点不是看它好不好看，而是看它封装了什么：

```
Behavior              （行为逻辑）
     +
Accessibility         （无障碍支持）
     +
State Machine         （状态机）
     +
Keyboard Interaction  （键盘交互）
     +
Focus Management      （焦点管理）

不负责：
Visual Style          （视觉样式）
```

也就是说，Headless Component 把「一个下拉菜单该怎么开、怎么关、键盘怎么导航、焦点怎么管理、屏幕阅读器怎么读」这些**复杂但通用的逻辑**封装好，但**完全不管它长什么样**。

样式交给使用方（产品团队）自己用 CSS、Tailwind、styled-components 等去写。

## 分层关系

```
Behavior Layer         行为层（交互逻辑、状态、无障碍）
      ↓
Headless Component     无头组件（暴露行为，不带样式）
      ↓
Design System          设计系统（Token + 样式 + 规范）
      ↓
Product UI             产品界面（最终业务页面）
```

这个分层非常漂亮，因为：

1. **行为可复用**：同一个 Headless 组件，可以被无数种视觉风格复用。
2. **样式可替换**：换设计语言不影响交互逻辑。
3. **无障碍内建**：复杂但容易写错的 a 11 y 逻辑被集中维护。
4. **职责单一**：行为归行为，样式归样式，符合软件工程的关注点分离原则。

# 总结

Design System 的本质，是把 UI 当成软件系统来架构：

- **Design Token** 是 UI 的「类型系统 / 变量层」，负责统一视觉决策；
- **Headless Component** 是 UI 的「逻辑层」，负责行为与无障碍；
- 二者合流后，形成 `Behavior → Headless → Design System → Product UI` 的清晰分层。

这正是现代 UI 架构和软件架构「合流」的体现：**抽象分层、关注点分离、可复用、可替换**。