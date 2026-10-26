# 参数解析模块

我们必须回答一些问题：

## 参数有哪些：为什么必须是闭集？

"无限参数不现实"的真实原因是：闭集是"报错"的前提。如果选项集合是开放的，--shimsx 就无法和"某个值"区分，未知选项错误也就不存在。

 本项目有三层闭集：

| 闭集 | 内容 | 开放的那部分 |
|---|---|---|
| 命令 | env / shims / check / help | — |
| 选项 | 7 个 Opt 变体 | — |
| 值域 | Dialect 5 个、Mode 3 个 | — |
| 位置参数 | 由命令声明槽位数 | help [COMMAND] 是唯一 0..1 的 |
位置参数是唯一"开放"的东西，而它也被每个命令的 positional.len() 夹住了。没有闭集就没有解析器，只有字符串搜索。

## 怎么描述参数：名称是键，描述是数据

| 属性 | 归属 | 依据 |
|---|---|---|
| 名称 | Opt 枚举 + Opt::parse 单向映射 | 唯一性由枚举保证，不可能两个名字指同一个选项 |
| 描述 | CmdSpec.about、Opt::meta | 纯数据，供 usage_text 生成文档 |
| 形式 | Opt::takes_value | 唯一来源，词法器只查这一处 |
| 值域 | Dialect / Mode | 有限枚举，解析期就能判定 |
| 归属命令 | CmdSpec.opts | 选项收窄用 |
| 必填 | CmdSpec.required | 组合校验用 |
表是数据（可遍历、可生成文档、可静态校验）。

## 怎么解析：只判断形式，不判断语义

**先分形式，再谈实现：**

| 形式       | 本项目                              | 表示                       |
| -------- | -------------------------------- | ------------------------ |
| 开关（无值）   | --force、--verbose                | takes_value == false     |
| 取值（恰好一个） | --shell、--out、--shims、--shim-dir | takes_value == true      |
| 位置、定长    | 无                                | positional: &[]          |
| 位置、0..1  | help [COMMAND]                   | positional: &["COMMAND"] |
| 变长       | 不需要                              | 要时加 rest 字段，别用"多收几个裸词"代替 |

**"解析只满足形式的范围"——对，但要划清形式与语义的界：**

| 层 | 例子 | 在哪判 |
|---|---|---|
| 形式 | --out 后面有没有 token | cli::parse |
| 值域（语法内） | --shims=maybe | cli::parse（有限枚举） |
| 语义/资源 | --out 的目录能不能写 | win::write_file_atomic |

> 值域放解析器的理由：有限枚举报错能统一、能列期望集；而"目录是否可写"必须等到真正写，提前检查反而是 TOCTOU。

**实现上只有两个阶段，中间态刻意是"脏"的：**

```
argv ──tokenize──> (Vec<(Opt, Option<String>)>, Vec<&str>) ──bind──> Command
```

> 中间态不跨模块边界，所以允许字符串、允许重复、允许非法值。跨边界的只有 Command。

## 参数如何影响执行

| 类别 | 参数 | 机制 |
|---|---|---|
| 选择（改输出内容） | --shell、--shims、--shim-dir | 填入 Env，决定 emitter 与 PATH 形态 |
| 副作用（改 IO） | --out、--force、--verbose | 决定写到哪、是否绕过缓存、是否打点 |
| 短路 | --help | 根本不构建 Env，直接返回 |
表决定能说什么（合法性与文档），match 决定做什么（控制流）。两者之间唯一的强约束是那个穷尽 match；其余靠测试或 review。加命令的成本因此不在解析器——tokenize/bind一行都不用改——而在"表 + 变体 + 一条 dispatch"这三处同步。

## 怎么组合：累积+收窄+必填

 四个组合规则，全在 bind 里：

 1. 累积：同选项重复 → 后者覆盖（GNU 惯例）。
 2. 顺序无关：wex --shims always check 与 wex check --shims always 等价。
 3. 收窄：选项必须在该命令的 opts 里，否则 not accepted by。
 4. 必填：required 里每一项都要出现。

## 错误处理：按层分类，不是按“用户哪里错了”

| 层   | 用户做错了什么                | 现在的消息                                                                                           | 检测点           |
| --- | ---------------------- | ----------------------------------------------------------------------------------------------- | ------------- |
| 名字  | 写了个不存在的选项/命令           | unknown option '--x' / unknown command 'x' (expected ...)                                       | tokenize / 查表 |
| 形式  | 该带值没带、不该带值却带了          | --shims needs a value / --force does not take a value                                           | tokenize      |
| 值域  | 值不在闭集里                 | --shims must be auto\|always\|never                                                             | bind          |
| 组合  | 缺必填、给了该命令不接受的东西、位置参数超量 | 'env' needs --shell / --shell is not accepted by 'check' / unexpected argument 'pwsh' for 'env' | bind          |

三条规则：

- 一条错误点名一个 token，并给期望集合。不要 "invalid arguments"。
- 用户输入不 panic：必填项在 required 检查通过后用 `unwrap_or_default()`，再由值域校验兜底。
- exit 2 / stderr；显式 help 走 stdout、exit 0，便于重定向导出。

## 正交性：避免参数之间的冲突

| 检查项                                  | 性质  | 现状                                         |
| ------------------------------------ | --- | ------------------------------------------ |
| 选项名唯一                                | 机械  | ✅ 枚举保证                                     |
| 命令名唯一                                | 机械  | ⚠️ 手工维护，4 条太少没出事；表变大要加 debug_assert        |
| required ⊆ opts                      | 机械  | ⚠️ 目前靠人看。漏了会得到"永远无法满足"的死规则                 |
| 同命令 opts 内无重复                        | 机械  | ⚠️ 同上，重复无害但表明表写错了                          |
| 位置参数槽位不与选项冲突                         | 机械  | ✅ 槽位只吃裸词，选项 token 已被消费                     |
| 选项归属正交                               | 半机械 | ✅ 表里一眼可见：--out 只属 env，--force 只属 env/shims |
| 语义互斥（--shims never + --shim-dir DIR） | 人工  | ❌ 现在静默接受，--shim-dir 被忽略                    |