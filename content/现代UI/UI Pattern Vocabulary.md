**UI Pattern Vocabulary** 可以理解成前端/UI 设计里的“设计模式词典”：看到需求 → 识别交互问题 → 想到成熟 Pattern → 再决定用什么组件实现。

而且最好不要只背组件名，而是形成：

> **用户意图 → Pattern → 行为模型 → 适用/不适用场景**

下面给你一套偏现代 Web / Desktop / SaaS 应用的词表。

---

# 1. Navigation 导航模式

|Pattern|中文理解|典型用途|
|---|---|---|
|**Navbar / Top Nav**|顶部导航|网站一级入口|
|**Sidebar**|侧边导航|后台、IDE、复杂应用|
|**Navigation Rail**|窄侧栏|图标级一级导航|
|**Tab Bar**|标签导航|同级页面切换|
|**Tabs**|页签|同一上下文内容切换|
|**Breadcrumbs**|面包屑| `Projects / Foo / Settings` |
|**Drawer Navigation**|抽屉导航|移动端隐藏导航|
|**Mega Menu**|巨型菜单|电商、文档站大量分类|
|**Tree Navigation**|树形导航|文件、组织结构|
|**Accordion Navigation**|折叠导航|多层级菜单|
|**Pagination**|分页|大量结果|
|**Infinite Scroll**|无限滚动|Feed、图片流|
|**Load More**|加载更多|分批加载|
|**Anchor Navigation**|锚点导航|长文档|
|**Scrollspy**|滚动位置导航|当前章节自动高亮|
|**Back to Top**|回到顶部|长页面|
|**Stepper**|步骤导航|注册、结账|
|**Wizard**|向导|复杂多步骤任务|

一个重要区别：

**Tabs 是切换同级上下文；Stepper/Wizard 是完成一个有顺序的流程。**

---

# 2. Search / Jump / Discovery 查找与快速跳转

这是现代生产力软件非常重要的一组。

|Pattern|心智模型|
|---|---|
|**Search Box**|搜索|
|**Autocomplete**|输入 → 自动补全|
|**Typeahead**|边输入边给候选|
|**Search Suggestions**|推荐搜索项|
|**Faceted Search**|按属性筛选|
|**Filter Bar**|条件过滤|
|**Filter Chips**|当前过滤条件|
|**Command Palette**| `Ctrl/Cmd + K` 万能操作入口|
|**Quick Switcher**|快速切换文件/项目/页面|
|**Spotlight Search**|全局搜索+操作|
|**Omnibox**|一个输入框承担多种任务|
|**Jump to...**|快速跳转到实体|
|**Recent Items**|最近访问|
|**Fuzzy Search**|模糊匹配|

这里可以形成一个非常有用的模式：

> **用户知道“我要去哪”但层级导航太慢 → Quick Switcher / Command Palette**

这就是为什么 IDE、Linear、Notion、VS Code 一类产品大量采用它。

---

# 3. Feedback 用户反馈

你举的 Toast 就属于这里。

|Pattern|强度|用途|
|---|---|---|
|**Inline Feedback**|很低|输入框旁提示|
|**Badge**|很低|状态/数量|
|**Status Indicator**|很低|Online / Syncing|
|**Toast**|低|“Saved successfully”|
|**Snackbar**|低|Toast + 简单 Action|
|**Banner**|中|页面级通知|
|**Callout**|中|局部重要信息|
|**Alert**|中|需要用户注意|
|**Modal Alert**|高|必须处理|
|**Confirmation Dialog**|高|删除等危险操作|
|**Progress Bar**|—|确定进度|
|**Spinner**|—|未知进度|
|**Skeleton**|—|内容正在加载|
|**Optimistic Feedback**|—|先表现成功，后台执行|

你可以建立一个非常重要的“打扰程度梯度”：

**Inline → Toast → Banner → Dialog**

不要动不动就 Modal。

---

# 4. Overlay / Layer 浮层模式

很多人学 CSS 后真正缺的是这一层 vocabulary。

|Pattern|特征|
|---|---|
|**Tooltip**|hover/focus 后解释|
|**Popover**|锚定元素的小浮层|
|**Dropdown**|下拉内容|
|**Dropdown Menu**|操作菜单|
|**Context Menu**|右键菜单|
|**Overflow Menu**| `⋯` 更多操作|
|**Modal / Dialog**|阻塞当前流程|
|**Non-modal Dialog**|非阻塞浮窗|
|**Drawer / Sheet**|从边缘滑入|
|**Bottom Sheet**|移动端底部面板|
|**Side Panel**|侧面详情/操作面板|
|**Lightbox**|图片/媒体聚焦|
|**Hover Card**|Hover 后显示丰富信息|
|**Preview Pane**|不离开当前页面进行预览|

特别容易混：

**Tooltip ≠ Popover ≠ Dialog**

Tooltip 通常只是简短解释，Popover 可以交互，Dialog 是一个相对完整的任务上下文。

---

# 5. Selection 选择模式

|Pattern|用途|
|---|---|
|**Checkbox**|多选|
|**Radio Group**|单选|
|**Switch / Toggle**|开/关|
|**Segmented Control**|少量互斥选项|
|**Select / Dropdown Select**|多个选项|
|**Combobox**|输入 + 选择|
|**Multi-select**|多选|
|**Chip / Tag Selection**|标签式选择|
|**Listbox**|列表选择|
|**Transfer List**|左右移动选择|
|**Dual Listbox**|两组集合间转移|
|**Cascader**|层级选择|
|**Tree Select**|树结构选择|
|**Date Picker**|日期|
|**Date Range Picker**|日期区间|
|**Time Picker**|时间|
|**Color Picker**|颜色|
|**Slider**|连续值|
|**Range Slider**|范围|

值得形成条件反射：

> 2–5 个互斥选项 → Radio / Segmented Control  
> 很多选项 → Select  
> 很多选项且需要搜索 → Combobox  
> boolean 设置 → Switch  
> “选中一些对象” → Checkbox

---

# 6. Data Display 数据展示

后台/SaaS 极其重要。

|Pattern|用途|
|---|---|
|**Card**|信息单元|
|**List**|纵向实体集合|
|**Grid**|网格|
|**Data Table**|结构化数据|
|**Tree Table**|层级数据表|
|**Master–Detail**|左列表右详情|
|**Split View**|分屏|
|**Description List**|Key–Value 信息|
|**Timeline**|时间事件|
|**Activity Feed**|动态记录|
|**Kanban Board**|状态流|
|**Calendar View**|时间安排|
|**Gallery**|视觉对象|
|**Carousel**|横向轮播|
|**Stat / KPI Card**|单指标|
|**Dashboard**|多指标总览|
|**Sparkline**|微型趋势图|
|**Heatmap**|密度/强度|
|**Avatar Stack**|多用户|
|**Tag / Badge / Pill**|分类、状态|

其中一个很经典的业务 Pattern 是：

**Master → Detail**

例如：

```
Email List       Email Detail
─────────────    ──────────────────
Alice            Subject...
Bob        →     Content...
Carol
```

邮件、文件管理器、数据库管理器、IDE 都大量使用。

---

# 7. Form 表单模式

|Pattern|用途|
|---|---|
|**Inline Form**|原地编辑|
|**Inline Editing**|点击文本直接编辑|
|**Progressive Disclosure**|高级选项逐渐展开|
|**Conditional Fields**|根据选择显示字段|
|**Form Sections**|表单分组|
|**Fieldset**|语义分组|
|**Floating Label**|浮动标签|
|**Helper Text**|输入说明|
|**Inline Validation**|实时校验|
|**Password Strength Meter**|密码强度|
|**Character Counter**|字数限制|
|**Autosave**|自动保存|
|**Draft State**|草稿|
|**Dirty State**|有未保存修改|
|**Unsaved Changes Guard**|离开前提示|
|**Multi-step Form**|多步骤表单|

现代应用里尤其应该认识：

**Progressive Disclosure**

不要一次把 50 个设置全部扔给用户，而是：

```
Basic Settings

[x] Enable proxy

    Advanced settings ▸
```

这是降低认知负担的重要模式。

---

# 8. Actions 操作模式

|Pattern|含义|
|---|---|
|**Primary Action**|当前最主要操作|
|**Secondary Action**|次要操作|
|**Destructive Action**|删除/覆盖|
|**CTA**|Call to Action|
|**Icon Button**|图标按钮|
|**Split Button**|主按钮 + 下拉|
|**Button Group**|一组操作|
|**Floating Action Button / FAB**|悬浮主操作|
|**Toolbar**|工具集合|
|**Action Bar**|上下文操作|
|**Bulk Actions**|批量操作|
|**Contextual Actions**|根据当前选择出现|
|**Swipe Actions**|移动端滑动操作|
|**Undo**|撤销|
|**Redo**|重做|

一个非常值得掌握的思想：

> **Confirmation 和 Undo 是两种不同的防误操作策略。**

传统：

`Delete → Are you sure? → Yes`

现代很多场景更适合：

`Delete → Deleted [Undo]`

后者减少操作阻力。

---

# 9. Empty / Error / Edge States 边界状态

真正成熟的 UI 设计和“只会画正常页面”的差别经常在这里。

|Pattern|含义|
|---|---|
|**Empty State**|没有数据|
|**Zero State**|用户第一次使用|
|**No Results State**|搜索无结果|
|**Loading State**|加载中|
|**Error State**|加载失败|
|**Offline State**|离线|
|**Permission State**|无权限|
|**Disabled State**|不可操作|
|**Read-only State**|只读|
|**Partial Failure**|部分失败|
|**Retry Pattern**|重试|
|**Fallback UI**|降级界面|
|**Error Boundary**|局部错误隔离|

因此设计一个页面时，不应该只画：

`Normal`

而应该开始习惯考虑：

**Loading → Empty → Normal → Error → Offline → Permission denied**

这是一种非常重要的工程化 UI 思维。

---

# 10. Onboarding / Guidance 引导模式

|Pattern|用途|
|---|---|
|**Onboarding Flow**|首次使用|
|**Product Tour**|产品导览|
|**Coach Marks**|指向具体控件|
|**Feature Discovery**|新功能发现|
|**Spotlight**|聚焦某区域|
|**Checklist**|新手任务|
|**Setup Wizard**|初始化配置|
|**Template Gallery**|从模板开始|
|**Sample Data**|示例数据|
|**Empty-state CTA**|空页面引导下一步|
|**Progressive Onboarding**|使用过程中逐步教学|

---

# 11. Layout 布局模式

这部分正好是你之前说的“Vue 学完之后缺的跨框架能力”。

|Pattern|结构|
|---|---|
|**Single Column**|单栏|
|**Two-column Layout**|双栏|
|**Three-pane Layout**|三栏|
|**Holy Grail Layout**|Header + 两侧栏 + Content|
|**App Shell**|应用整体骨架|
|**Dashboard Layout**|仪表盘|
|**Split Pane**|可分割面板|
|**Resizable Panels**|可调整尺寸|
|**Sticky Header**|吸顶|
|**Sticky Sidebar**|固定侧栏|
|**Fixed Toolbar**|固定工具栏|
|**Masonry**|瀑布流|
|**Responsive Grid**|响应式网格|
|**Container Layout**|内容宽度约束|
|**Full Bleed**|内容突破容器|
|**Centered Content**|居中内容|
|**Rail Layout**|主内容 + 辅助窄栏|

现代 Desktop/Web App 一个非常经典的结构就是：

```
┌─────────────────────────────────────────────┐
│ Global Header                               │
├──────────┬─────────────────────┬────────────┤
│          │                     │            │
│ Sidebar  │    Main Content     │ Inspector  │
│          │                     │            │
│          │                     │            │
└──────────┴─────────────────────┴────────────┘
```

这里又能衍生出 **App Shell、Sidebar、Inspector、Split Pane、Resizable Panel** 等模式。

---

# 12. Direct Manipulation 直接操作

这是做“高级感 Web App”特别重要的一类。

|Pattern|用途|
|---|---|
|**Drag and Drop**|拖放|
|**Sortable List**|拖动排序|
|**Resize Handle**|调整大小|
|**Selection Box / Marquee**|框选|
|**Multi-selection**|多选|
|**Pan**|平移|
|**Zoom**|缩放|
|**Pinch Zoom**|双指缩放|
|**Canvas Interaction**|画布操作|
|**Snap to Grid**|网格吸附|
|**Snap Lines**|对齐辅助线|
|**Handles**|控制点|
|**Inline Rename**|原地重命名|
|**Keyboard Nudge**|方向键微调|

Figma、IDE、Notion、文件管理器这类产品里会大量遇到。

---

# 13. Keyboard / Power User Patterns

如果你以后做专业工具，这组词尤其值得记住。

**Keyboard Shortcuts、Shortcut Hint、Command Palette、Quick Switcher、Focus Ring、Focus Trap、Roving Tabindex、Keyboard Navigation、Shortcut Chord、Keybinding、Vim-style Navigation、Mnemonic、Typeahead Selection、Escape to Dismiss、Enter to Confirm。**

例如一个成熟产品通常会形成：

```
Ctrl/Cmd + K      Command Palette
Ctrl/Cmd + P      Quick Open
Ctrl/Cmd + ,      Settings
/                 Search
?                 Shortcut Help
Esc               Dismiss
↑ ↓               Navigate
Enter             Select
```

这已经不只是“快捷键”，而是一整套 **Power User Interaction Model**。

---

# 14. Motion / Animation Patterns

你之前特别提到动画经验，这里也应该形成 vocabulary。

|Pattern|含义|
|---|---|
|**Enter / Exit Transition**|出现/消失|
|**Fade**|淡入淡出|
|**Slide**|滑动|
|**Scale**|缩放|
|**Collapse / Expand**|展开折叠|
|**Crossfade**|内容交叉淡化|
|**Shared Element Transition**|元素跨页面连续运动|
|**Layout Transition**|布局变化动画|
|**Microinteraction**|微交互|
|**Hover Transition**|Hover 动画|
|**Press Feedback**|按压反馈|
|**Loading Animation**|加载动画|
|**Progress Animation**|进度动画|
|**Skeleton Shimmer**|骨架屏流光|
|**Spring Animation**|弹簧动画|
|**Stagger**|元素依次出现|

更重要的是理解：

> 动画不是 Decoration，而经常承担 **Spatial Continuity（空间连续性）**。

例如点击 Card 后它扩展成详情页，比“详情页凭空出现”更容易让用户理解**我现在在哪里**。

---

# 15. Responsive / Adaptive Patterns

不要把 Responsive 简单理解成 `@media`。

需要认识：

**Breakpoints、Fluid Layout、Responsive Grid、Container Queries、Reflow、Stacking、Collapsing Navigation、Off-canvas Navigation、Adaptive Sidebar、Responsive Table、Priority+ Navigation、Touch Target Adaptation、Content Density、Compact / Comfortable Mode。**

例如：

```
Desktop
Sidebar | Content | Inspector

Tablet
Sidebar | Content
             ↓
        Inspector Drawer

Mobile
Content
  ↓
Navigation → Bottom Tab
Inspector  → Bottom Sheet
```

这叫 **Pattern Transformation**，不是简单把元素缩小。

---

# 16. 更高阶：Application Patterns

再往上就不再是一个组件，而是整个应用的交互架构：

**CRUD、Master–Detail、Inbox、Feed、Dashboard、Workspace、Editor、Canvas、IDE Layout、File Explorer、Settings、Search Results、Command Center、Activity Stream、Kanban、Calendar、Timeline、Chat Interface、Multi-pane Workspace、Document-centric UI、Object-centric UI。**

例如 VS Code 可以拆成：

```
App Shell
 ├─ Activity Bar
 ├─ Sidebar
 │   └─ Tree View
 ├─ Editor
 │   └─ Tabs
 ├─ Bottom Panel
 │   ├─ Terminal
 │   └─ Problems
 ├─ Status Bar
 ├─ Command Palette
 ├─ Quick Open
 ├─ Context Menu
 ├─ Toast / Notifications
 └─ Settings
```

当你达到这个阶段，你看到一个软件时，就不再是：

> “这个 UI 挺漂亮。”

而会自动解构成：

> **App Shell + Navigation Rail + Tree View + Tabs + Split Pane + Command Palette + Context Menu + Status Bar + Toast……**

这就是 **UI Pattern Vocabulary 真正形成了**。

---

## 我建议你把 UI 知识进一步建立成 4 层

你之前已经学 Vue，所以接下来不要继续单纯“学组件库”。更好的知识结构是：

**Level 1 — Primitive**

`Box / Text / Icon / Button / Input / Image / Divider`

↓

**Level 2 — Component**

`Select / Dialog / Tooltip / Table / Tabs / Menu`

↓

**Level 3 — Pattern**

`Command Palette / Master-Detail / Wizard / Progressive Disclosure / Infinite Scroll / Undo`

↓

**Level 4 — Application Architecture**

`Dashboard / IDE / Editor / Inbox / Workspace / Canvas / Admin Console`

真正跨 **Vue / React / Svelte / Flutter / SwiftUI / Web Components** 的，是后面两层。

所以你之前说的“我至少需要知道能做到什么”非常适合用这种方式学：**CSS/JS 是你的招式实现能力，Pattern Vocabulary 是你脑中的招式库，而 Information Architecture、Interaction Design、Visual Design、Ergonomics 则是决定什么时候出什么招的原则。**