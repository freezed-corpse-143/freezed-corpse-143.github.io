# 文件结构

apps/web
┌──────────────────────────────────────────────────────────────────────┐
│ apps/web                                                             │
├──────────────────────────────────────────────────────────────────────┤
│ 入口层                                                               │
│ ┌──────────────────────────────┐                                     │
│ │ index.html                   │  Vite HTML 入口，挂载 \#app          │
│ └──────────────────────────────┘                                     │
│                │                                                     │
│                ▼                                                     │
│ ┌──────────────────────────────┐                                     │
│ │ src/main.ts                  │  createApp(App).mount('#app')       │
│ └──────────────────────────────┘                                     │
├──────────────────────────────────────────────────────────────────────┤
│ src/                                                                 │
│ ┌──────────────────────────────┐ ┌──────────────────────────────┐    │
│ │ App.vue                      │ │ env.d.ts                     │    │
│ │ 根组件                       │ │ env 类型声明                 │    │
│ └──────────────────────────────┘ └──────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────┤
│ 页面与复用                                                           │
│ ┌──────────────────────────────┐ ┌──────────────────────────────┐    │
│ │ views/                       │ │ components/                  │    │
│ │ 13 个路由页面                │ │ 跨页复用组件                 │    │
│ └──────────────────────────────┘ └──────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────┤
│ 基建                                                                 │
│ ┌──────────────────────────────┐ ┌──────────────────────────────┐    │
│ │ router/                      │ │ stores/                      │    │
│ │ 路由 / 权限守卫              │ │ 登录态 / 全局状态            │    │
│ └──────────────────────────────┘ └──────────────────────────────┘    │
│ ┌──────────────────────────────┐                                     │
│ │ lib/                         │                                     │
│ │ 请求出口 / 文案 / 工具       │                                     │
│ └──────────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────────┘

# 初始化声明周期

从浏览器加载到页面可见，是第一次打开网站发生的事情，只走一遍。

```text
index.html
   │  ① 加载 <script type="module" src="/src/main.ts">
   ▼
main.ts
   │  ② createApp(App)
   │  ③ app.use(router)     ← 装路由插件
   │  ④ app.use(pinia)      ← 装状态管理（stores/）
   │  ⑤ app.mount('#app')   ← 挂载
   ▼
App.vue 根组件
   │  ⑥ 渲染根模板（里面通常有 <RouterView />）
   ▼
router/ (路由守卫)
   │  ⑦ beforeEach 守卫执行：读 stores/ 里的登录态
   │     - 已登录 / 无需鉴权 → next()
   │     - 未登录 → 重定向到 /login
   ▼
views/ 匹配到的页面组件
   │  ⑧ 页面 setup() 执行 → onMounted 触发
   │  ⑨ 需要数据 → 走 lib/ 的请求出口（axios 封装）拉接口
   ▼
components/ 子组件递归渲染
   ▼
🖥 页面可见
```

| 环节       | 位置         | 做的事                                           |
| ---------- | ------------ | ------------------------------------------------ |
| ① 加载入口 | `index.html` | 只保留一个 `<div id="app">` + 引入 `main.ts`     |
| ② 创建实例 | `main.ts`    | `createApp(App)` 生成应用实例                    |
| ③④ 装插件  | `main.ts`    | `router`、`pinia` 必须在 `mount` **之前**注册    |
| ⑤ 挂载     | `main.ts`    | `app.mount('#app')` 把虚拟 DOM 渲染到真实 DOM    |
| ⑥ 根组件   | `App.vue`    | 通常只有布局 + `<RouterView />`，不放业务        |
| ⑦ 路由解析 | `router/`    | `beforeEach` 做权限判断（登录态来自 `stores/`）  |
| ⑧ 页面挂载 | `views/`     | 对应路由的组件被创建，`onMounted` 发请求         |
| ⑨ 数据请求 | `lib/`       | 统一封装 axios：baseURL、拦截器、token、错误文案 |

> 关键点：**挂载顺序 = 插件 → mount → 路由守卫 → 页面组件**。`router` 和 `pinia` 没注册就 mount，页面里用 `useRouter()` / `useStore()` 会直接报错。

# 运行时生命周期

用户点击后的交互循环

初始化只走一次，之后每次**用户操作**都进入这个循环：

```
用户点击 / 输入 / 调接口
        │
        ▼
  触发响应式更新（ref / reactive 变化）
        │
        ▼
  路由跳转？──是──▶ router.push('/xxx')
        │                │
        │                ▼
        │          beforeEach 守卫（权限/登录态）
        │                │
        │           ┌────┴────┐
        │        放行        拦截→重定向
        │           │
        │           ▼
        │      旧组件 onUnmounted
        │           │
        │           ▼
        │      新组件 setup() → onMounted
        │           │
        │           ▼
        │      新页面渲染
        │
        └──否──▶ 组件内部状态变化 → 触发重新渲染（diff → patch）
                        │
                        ▼
                 只更新变化的最小 DOM
```

**三种常见的"运行周期"触发源：**

1. **路由跳转**（页面级切换）→ 走 `router/` 守卫 → 卸载旧页面 → 挂载新页面
2. **组件状态变化**（`ref` / `reactive` / `props` 变化）→ Vue 响应式系统 → 局部重渲染
3. **接口数据回来**（`lib/` 请求 resolve）→ 更新 `stores/` 或组件内 state → 触发渲染

# 页面跳转方式

Vue 是 **SPA（单页应用）**，跳转不会刷新浏览器，只是替换 `<RouterView />` 里渲染的组件。

**1）声明式 —— `<RouterLink>`（模板里用）**
```vue
<RouterLink to="/user">用户中心</RouterLink>
```
渲染成 `<a>`，点击被 Vue 拦截，调用 `router.push`。

**2）编程式 —— `router.push`（JS 里用）**
```ts
import { useRouter } from 'vue-router'
const router = useRouter()

router.push('/user')                    // 普通跳转
router.push({ name: 'user', params: { id: 1 } })
router.replace('/login')                // 不留历史记录
router.back()                           // 返回
```

**3）守卫里 —— `next('/login')` **
```ts
router.beforeEach((to, from, next) => {
  if (需要登录 && !store.token) next('/login')
  else next()
})
```

## 跳转的完整链路

```
点击 / router.push
   ▼
匹配路由表 → 找到目标组件
   ▼
beforeEach 全局前置守卫（router/）
   ▼
组件内 beforeRouteLeave（可选）
   ▼
旧组件 onUnmounted → 新组件 setup → onMounted
   ▼
<RouterView /> 渲染新组件
```

# 页面渲染方式

Vue 的渲染是 **"数据驱动"**，你不操作 DOM，只改数据。

渲染三阶段

```
① 编译：template → render 函数 → 虚拟 DOM（VNode）
② 挂载：VNode → 真实 DOM（首次渲染）
③ 更新：数据变 → 生成新 VNode → diff 对比 → 只 patch 变化的 DOM
```

## 与目录的关系

| 层级  | 文件            | 渲染职责                                  |
| --- | ------------- | ------------------------------------- |
| 根   | `App.vue`     | 渲染全局布局 + `<RouterView />`             |
| 路由  | `router/`     | 决定 `<RouterView />` 里渲染哪个 `views/` 页面 |
| 页面  | `views/`      | 页面级渲染，编排 `components/`                |
| 复用  | `components/` | 接收 `props`，通过 `emit` 向上通信             |
| 数据  | `stores/`     | 全局状态，变化即触发依赖它的组件重渲染                   |
| 请求  | `lib/`        | 拉数据 → 写进 store / 组件 state → 触发渲染      |
# 一个典型渲染流

```ts
// views/UserList.vue
const list = ref([])
onMounted(async () => {
  list.value = await lib.getUsers()   // ① 请求回来
})                                     // ② list 变化
```

```vue
<template>
  <UserCard v-for="u in list" :key="u.id" :user="u" />
</template>
```
`list` 一变 → Vue 重新执行 `render` → diff 出新增的 `UserCard` → 只创建这几张卡片 DOM。删除同理，只移除对应节点。


# 总结

```
【初始化，只走一次】
index.html → main.ts → App.vue → router 守卫 → views 页面 → components

【运行时，循环往复】
用户操作 → 数据变化 ─┬─ 路由跳转 → 守卫 → 卸载旧页 → 挂载新页
                    └─ 状态更新 → diff → patch 局部 DOM

【跳转】RouterLink / router.push / next()
【渲染】template → VNode → 真实 DOM；数据变 → diff → 最小更新
```

**一句话记住：**
> `main.ts` 负责"起"，`router/` 负责"去哪"，`stores/` 负责"记什么"，`lib/` 负责"取什么"，`views/` 和 `components/` 负责"画什么"；数据一变，Vue 自动把变化的地方重画一遍。

# .vue 文件模板

```vue
<template>
  <!-- HTML 模板 -->
</template>

<script>
export default {
  // 逻辑
}
</script>

<style>
/* 样式 */
</style>
```

# 文本插值

使用双大括号 `{{ }}` 输出数据：

```vue
<template>
  <p>{{ message }}</p>
  <p>{{ count + 1 }}</p>
  <p>{{ user.name }}</p>
</template>
```

# 常用指令

## v-if/v-else-if/v-else

条件渲染：

```vue
<p v-if="score >= 90">优秀</p>
<p v-else-if="score >= 60">及格</p>
<p v-else>不及格</p>
```

## v-for
