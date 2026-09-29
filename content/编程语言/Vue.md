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

> 列表渲染

```vue
<ul>
  <li v-for="(item, index) in list" :key="index">
    {{ item }}
  </li>
</ul>
```

## v-bind

> 绑定属性

简写为 `:`，把数据绑定到 HTML 属性：

```vue
<img :src="imgUrl" />
<a :href="link">链接</a>
<div :class="{ active: isActive }"></div>
```

## v-on

>  绑定属性

简写为 `@`：

```vue
<button @click="handleClick">点击</button>
<button @click="count++">+1</button>
<input @input="onInput" />
```

## v-model

> 双向绑定

常用于表单：

```vue
<input v-model="username" />
<select v-model="selected"></select>
```

# 插槽

Slots，是 Vue 中的内容分发机制，它允许父组件向子组件传递模板内容。

## 出现原因

在没有插槽的情况下，子组件只能展示自己内部定义的内容。插槽让子组件变成了一个"容器"，父组件可以决定往里面放什么内容。

```vue
<!-- 子组件 MyButton.vue -->
<template>
  <button class="btn">
    <slot>默认内容</slot>  <!-- 插槽位置 -->
  </button>
</template>
```

```vue
<!-- 父组件使用 -->
<MyButton>点击我</MyButton>
<!-- 渲染结果：<button class="btn">点击我</button> -->
```

## 默认插槽

Default Slot

最基础的用法，父组件传入的内容会替换 `<slot>` 标签。

```vue
<!-- 子组件 Card.vue -->
<template>
  <div class="card">
    <slot>这里是默认内容</slot>
  </div>
</template>
```

```vue
<!-- 父组件 -->
<Card>
  <p>自定义内容</p>
</Card>
```

## 具名插槽

Named Slot

当一个组件需要多个插槽位置时，用 `name` 区分。

```vue
<!-- 子组件 Layout.vue -->
<template>
  <div class="layout">
    <header>
      <slot name="header"></slot>
    </header>
    <main>
      <slot></slot>  <!-- 默认插槽 -->
    </main>
    <footer>
      <slot name="footer"></slot>
    </footer>
  </div>
</template>
```

```vue
<!-- 父组件 -->
<Layout>
  <template #header>
    <h1>页面标题</h1>
  </template>

  <p>主体内容</p>

  <template #footer>
    <p>版权信息</p>
  </template>
</Layout>
```

> `#header` 是 `v-slot:header` 的简写。

动态插槽名

```vue
<template v-slot:[dynamicSlotName]>
  ...
</template>
```

## 作用域插槽

Scoped Slots

**核心用途**：让父组件能够访问子组件内部的数据。

```vue
<!-- 子组件 UserList.vue -->
<template>
  <ul>
    <li v-for="user in users" :key="user.id">
      <!-- 把 user 数据"传出去" -->
      <slot :item="user" :index="index"></slot>
    </li>
  </ul>
</template>

<script setup>
const users = [
  { id: 1, name: '张三', age: 20 },
  { id: 2, name: '李四', age: 25 }
]
</script>
```

```vue
<!-- 父组件 -->
<UserList>
  <!-- 通过 v-slot 接收子组件传出的数据 -->
  <template #default="{ item, index }">
    <span>{{ index }} - {{ item.name }} ({{ item.age }}岁)</span>
  </template>
</UserList>
```

**为什么需要作用域插槽？**
- 数据在子组件里（如 users 数组）
- 但渲染方式由父组件决定
- 这是一种"控制反转"的设计模式

# 动态组件

Vue 的动态组件（Dynamic Components）是指**在运行时根据条件动态切换不同组件**的一种机制。核心是通过 Vue 提供的 `<component>` 内置组件配合 `:is` 属性来实现。

```vue
<template>
  <button @click="currentComponent = ComponentA">A</button>
  <button @click="currentComponent = ComponentB">B</button>

  <component :is="currentComponent" />
</template>

<script setup>
import { shallowRef } from 'vue'
import ComponentA from './ComponentA.vue'
import ComponentB from './ComponentB.vue'

// 用 shallowRef 存组件对象
const currentComponent = shallowRef(ComponentA)
</script>
```

`:is` 的值可以是：
- **组件名字符串**（需已注册）
- **组件对象本身**（如 import 进来的组件）
- **HTML 标签名字符串**（如 `'div'`）

## 与 `v-if` / `v-show` 的区别

- `v-if` / `v-show` 是**条件渲染**，通常针对固定组件
- 动态组件更适合**组件类型不确定、需要按逻辑切换**的场景，代码更简洁，扩展性更好

# Vue Router

Vue Router 是 Vue 官方的路由管理器，用于在单页应用（SPA）中实现页面之间的导航，让应用看起来像多页面网站，但实际不刷新浏览器。

**核心概念**：
- **路由配置**：定义 URL 路径与组件的映射关系，支持动态路由（如 `/goods/:id`）和嵌套路由。
- ** `<RouterView>` 与 `<RouterLink>` **：前者是路由匹配组件的渲染出口，后者是声明式导航链接。
- **路由守卫**：通过 `beforeEach` 等钩子实现权限控制，比如未登录用户重定向到登录页。
- **懒加载**：用 `() => import('./views/GoodsDetail.vue')` 按需加载路由组件，优化首屏加载速度。

**使用方式**（Vue 3）：
```javascript
// router/index.js
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: GoodsList },
    { path: '/goods/:id', component: GoodsDetail } // 动态路由
  ]
});

export default router;
```

# Pinia

Pinia 是 Vue 官方推荐的下一代状态管理库，替代了 Vuex。它的核心价值在于**跨组件共享状态**，避免通过 props 层层传递数据。

**为什么用 Pinia**：
- **更简洁的 API**：没有了 Vuex 中繁琐的 mutations，只有 state、getters、actions。
- **完善的 TypeScript 支持**：类型推断非常自然，几乎无需额外标注。
- **Devtools 支持**：可以在 Vue Devtools 中追踪状态变化、进行时间旅行调试。

**使用示例**（Setup 语法）：
```javascript
// stores/goodsStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useGoodsStore = defineStore('goods', () => {
  const list = ref([]);           // state
  const total = computed(() => list.value.length); // getter
  async function fetchList() {    // action
    // 调用 API 获取数据
  }
  return { list, total, fetchList };
});
```

# UI 库

Vue 生态中有多个成熟的 UI 组件库，选择哪一个往往取决于项目类型和设计风格。

**Element Plus**：继承自 Element UI，组件功能稳定，API 设计成熟，适合**企业级后台管理系统**。风格较为传统，性能在大型应用中稍弱。安装后可直接在 `main.js` 中全局引入，也支持配合 `unplugin-vue-components` 做按需自动导入。

**Naive UI**：一个较新的现代化框架，设计灵活，可高度自定义，组件配置粒度细。尤雨溪曾推荐过，适合 **Vue 3 新项目**，生态虽较新但已趋于成熟。

**Vuetify**：老牌国际框架，基于 Material Design，组件库非常完备，稳定性强。但视觉风格相对过时，需要权衡现代 UI 需求与成熟度的取舍。

**选型建议**：后台管理选 Element Plus，新项目追求现代感和灵活性选 Naive UI，已有 Material Design 设计规范或需要极度成熟的组件生态选 Vuetify。

# Axios

Axios 是一个基于 Promise 的 HTTP 客户端，在 Vue 项目中承担与后端接口通信的职责。

**标准用法**是创建一个封装实例，统一配置 `baseURL`、超时时间，并通过拦截器处理 token 和错误：

```javascript
// utils/request.js
import axios from 'axios';

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
});

// 请求拦截器：自动携带 token
service.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截器：统一处理错误
service.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) { /* 重定向登录 */ }
    return Promise.reject(error);
  }
);

export default service;
```

然后在 `api/` 目录中按业务模块定义接口函数，组件中直接调用即可。

# Vite 插件

Vite 插件基于 Rollup 的插件接口，用于扩展开发服务器和生产构建的能力。

**使用方式**：安装插件后，在 `vite.config.js` 的 `plugins` 数组中引入：

```javascript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import legacy from '@vitejs/plugin-legacy';

export default defineConfig({
  plugins: [
    vue(), // 提供 Vue 单文件组件支持（官方插件）
    legacy({ targets: ['defaults', 'not IE 11'] }) // 传统浏览器兼容
  ]
});
```

**关键机制**：
- ** `enforce` 修饰符**：`pre` / `post` 控制插件执行顺序。
- ** `apply` 属性**：指定插件仅在 `'serve'` 或 `'build'` 模式下生效。

**常用官方插件**：`@vitejs/plugin-vue`（Vue SFC 支持）、`@vitejs/plugin-vue-jsx`（JSX 支持）、`@vitejs/plugin-legacy`（旧浏览器兼容）。

一个典型的 Vue 3 项目会这样组织：Vite 作为构建工具，通过插件引入 Vue 支持；Vue Router 定义页面结构和跳转；Pinia 管理跨页面共享的数据（如用户信息、购物车）；Axios 封装好请求层，在 Pinia 的 action 或组件中被调用；UI 库提供现成的表单、表格、弹窗等组件，大幅减少手写样式和交互逻辑的工作量。

# 路由跳转

路由跳转是指从当前 URL/视图切换到另一个路由对应的视图。Vue Router 中常见的跳转方式：

## 声明式跳转

```html
<router-link to="/user/123">用户</router-link>
```
底层会渲染成 `<a>`，点击后由 Vue Router 接管，避免整页刷新。

## 编程式跳转

```js
router.push('/user/123')
router.replace('/user/123')   // 不留历史记录
router.go(-1)                 // 前进/后退
```

## 访问拦截

在跳转真正发生前，判断“能不能去”。例如：
- 未登录用户访问 `/admin` → 拦截并重定向到 `/login`
- 已登录用户访问 `/login` → 拦截并跳回首页

这通常由**路由守卫**实现。

## 转发/重定向

```js
{ path: '/old', redirect: '/new' }
{ path: '/home', redirect: { name: 'dashboard' } }
```
也可以动态重定向：
```js
{ path: '/a', redirect: to => ({ path: '/b', query: to.query }) }
```
重定向会改变 URL，并重新匹配目标路由。

## 参数解析

路由参数分为三类：

| 类型         | 示例            | 获取方式          |
| ------------ | --------------- | ----------------- |
| 动态路径参数 | `/user/:id`     | `route.params.id` |
| 查询参数     | `/search?q=vue` | `route.query.q`   |
| 路由 props   | `props: true`   | 组件 props 接收   |

```js
const routes = [
  { path: '/user/:id', component: User, props: true }
]
```
组件中：
```js
props: ['id']
```
参数解析还包括：类型转换、可选参数 `:id?`、通配符 `*`、正则约束等。

# 路由守卫

路由守卫是 Vue Router 提供的**导航拦截机制**，按执行顺序分为：
## 全局守卫

```js
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isLogin()) {
    next('/login')
  } else {
    next()
  }
})

router.beforeResolve(...)   // 所有组件内守卫和异步路由组件解析后
router.afterEach((to, from) => { ... })  // 无 next，不能拦截
```

## 路由独享守卫

```js
{
  path: '/admin',
  component: Admin,
  beforeEnter: (to, from, next) => { ... }
}
```

## 组件内

```js
beforeRouteEnter(to, from, next) { ... }   // 组件实例还未创建
beforeRouteUpdate(to, from, next) { ... }  // 同一组件复用，参数变化时
beforeRouteLeave(to, from, next) { ... }   // 离开当前组件
```

## 完整导航解析流程简化

1. 触发导航
2. 调用失活组件的 `beforeRouteLeave`
3. 调用全局 `beforeEach`
4. 调用复用组件的 `beforeRouteUpdate`
5. 调用路由独享 `beforeEnter`
6. 解析异步路由组件
7. 调用被激活组件的 `beforeRouteEnter`
8. 调用全局 `beforeResolve`
9. 导航确认
10. 调用全局 `afterEach`
11. DOM 更新
12. 调用 `beforeRouteEnter` 的 `next` 回调

# 响应式更新

Vue 的核心特性：数据变化 → 视图自动更新。在路由场景中，响应式更新体现在：

## 路由对象是响应式

```js
import { useRoute } from 'vue-router'
const route = useRoute()
watch(() => route.params.id, (newId) => {
  fetchData(newId)
})
```
当 URL 参数变化时，`route.params`、`route.query` 会触发依赖更新。

## 组件复用问题

当 `/user/1` → `/user/2` 时，**同一个 User 组件会被复用**，不会重新创建。此时：
- `created` / `mounted` 不会再次执行
- 需要用 `watch` 监听 `$route` 或使用 `beforeRouteUpdate`

```js
watch(() => route.params.id, (id) => {
  loadUser(id)
})
```

## 响应式原理

- `ref` / `reactive` 创建响应式数据
- 依赖收集：渲染函数读取数据时收集依赖
- 触发更新：数据变化 → 触发 `effect` → 重新渲染组件
- 路由内部用 `reactive` 包装 currentRoute，所以路由变化能驱动视图更新

## 与路由跳转的关系


