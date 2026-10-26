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
## 配置加载模块

## 为什么需要配置

有状态程序的标配。

## 从哪里加载

 结论：参数（已校验）+ 环境变量（唯一真相）+ 文件（不是配置）。

| 来源 | 归属 | 现状 |
|---|---|---|
| 参数 | cli 负责形式与值域；配置层只做优先级 | `Config::load(mode, shim_dir)` 接收 Option，不再校验 |
| 环境变量 | `Config::load` 是唯一读者 | WEX_ENV_FILE / WEX_APPS_DIR / WEX_SHIM_DIR / WEX_SHIMS + USERPROFILE / LOCALAPPDATA |
| 文件 | dotenv 是数据，不是配置 | 在配置解析之后才读，所以 .env 里的 WEX_* 永远不生效——现在 check 会点名 |
1. 自举：配置文件的位置本身要先被配置（这里由 `WEX_ENV_FILE` 指），多一个来源就多一层"先有鸡还是先有蛋"。
2. 优先级链：flag > env > file > default 四级链必须写进文档并被测试，而收益是零——现有 4 个值放在环境里已经够用。
3. 失败语义：文件缺失、格式错、权限错都要定义行为；环境变量缺失天然等价于"未设"，语义免费。

## 加载后怎么存

结论：Config 存"外部输入"，Env 存"计算结果"，用 Option 证明来源。

 ```rust
pub struct Config {
    pub home: String,
    pub env_file: Option<String>,   // None = 默认 ~\.env
    pub apps_root: Option<String>,  // None = 默认 ~\Applications
    pub shim_dir: Option<String>,   // None = %LOCALAPPDATA%\wex\shims
    pub mode: Mode,
}
 ```

 - env_file_path() / apps_root_path() / shim_dir_path() 在取用处补默认。
 - 加载后不可变。
 - Env::build(&Config, refresh, force, want_map)：Config 是输入，Env 是产物。

## 加载过程的错误处理

| 类别 | 判据 | 处理 | 例子 |
|---|---|---|---|
| 缺失 | 未设或为空 | 用默认，正常路径 | `WEX_APPS_DIR=` |
| 非法 | 值在闭集外 | exit 2，消息带期望集合 | `WEX_SHIMS=maybe` |
| 不可用 | 路径不存在 / 读不了 | 降级继续，只在 check 暴露 | 删掉的 `~/Applications` 子目录 |

## 加载是否涉及 I/O 的时序

**结论：不用异步，模型不成立；真正的约束是顺序与惰性。**

本机 debug 构建实测（各 25 次）：

| 调用 | min | median |
|---|---|---|
| wex help（进程地板） | 8.2 ms | 8.6 ms |
| wex env --shell json --shims never | 10.6 ms | 11.0 ms |
| wex check（62 目录 + dotenv + 294 个名字） | 21.5 ms | 22.4 ms |

配置读取（4~6 次 `GetEnvironmentVariableW`）在 0.1 ms 以下，测不出来。成本中心是进程创建和目录枚举。

时序规则：

1. 先便宜后昂贵：配置解析完 → 非法立刻退出，不碰磁盘。
2. 惰性：`use_shims` 决定要不要 `is_dir` / `ensure`；`want_map` 决定要不要扫 shim 表。`env --shims never` 完全不扫。
3. 不取消、不超时：单次调用，毫秒级，没有可取消的等待。

> 反驳"异步是否必要"：异步解决的是"等待期间能做别的事"。这里的调用模型是 shell 阻塞等待我们退出，期间无事可做；引入 runtime 只会把 8.6 ms 的地板抬高。若将来要并行枚举多个目录，线程池足够，仍然不需要 async。

> 补充一条容易被忽略的时序：`wex-shim` 是唯一需要关心信号的地方——它把 Ctrl+C 转发给子进程并等待退出码，然后再 `ExitProcess`。配置加载完全不需要这种处理。

## 加载是否需要缓存

**结论：配置不缓存；缓存只用于派生工件；版本号只对持久化产物有意义。**

> 反驳"配置能否缓存加速"：缓存要成立，必须满足两条——被缓存的工作比缓存本身贵；被缓存的值有可靠的失效信号。配置两条都不满足：读 4 个环境变量比"打开缓存文件 + 解析 + 校验"更便宜；进程环境没有版本、没有 mtime、没有通知，跨进程缓存必然产生"读到过期配置"。加缓存是净负收益。

正确的缓存对象是派生工件，项目里的 `.wex-stamp` 是可复制的模板：

| 键 | 作用 |
|---|---|
| 格式版本（本轮新增） | 布局变化 → 强制重建 |
| fp（命令集 FNV-1 a） | 命令增删改名 → 失效 |
| vol + idx（wex-shim.exe 卷号 + 文件索引） | 换二进制 → 失效 |
| count | 枚举漂移兜底 |

> 注意第三条：缓存键里包含源的身份，这是它正确的根本原因。反例是把 `~/Applications` 的扫描结果缓存起来——目录内容随时变，要判断"没变"就得再枚举一遍，和扫描同价（实测 2.5 ms）。缓存不能比被缓存的工作更贵。

> 反驳"给配置加版本号/校验"：进程环境是一次性的（每次启动重新读），没有"版本"这个概念。版本化只对持久化产物成立：
>
> - `.wex-stamp`：已加首行版本；未知版本直接重建（实测 4 行旧格式被重写）。
> - `wex-shims.tsv`：不单独加版本，靠 stamp 版本兜住——两者在同一次 ensure 里一起重写，格式变更必须同时改 `STAMP_VERSION`。这是一条约定，不是机制，写在这里提醒将来的人。
> - 输出文本（cmd/pwsh/json…）：不加版本头。它被 eval，头部是噪声且改变字节。

> 若将来真的加配置文件，正确形态是：`version = 1`、未知键 fail-closed、环境变量覆盖文件、不做热重载。不是现在。

# 应用扫描层

遍历应用层根目录（暂定为 `~/Applictions/`）：
- 一个子目录等于一个工具
- 有 bin，取 bin，无 bin 取子目录
- 不做验证
- 不排序
- 不过滤

