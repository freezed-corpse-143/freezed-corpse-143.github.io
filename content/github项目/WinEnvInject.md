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
# 配置加载模块

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

# 应用扫描模块

遍历应用层根目录（暂定为 `~/Applictions/`）：
- 一个子目录等于一个工具
- 有 bin，取 bin，无 bin 取子目录
- 不做验证
- 不排序
- 不过滤

# .env 加载模块

## 从那加载

| 项            | 事实                                                         |
| ------------- | ------------------------------------------------------------ |
| 路径来源      | 环境变量 `WEX_ENV_FILE`；未设或为空 → `~\.env`               |
| 没有 CLI flag | `--shim-dir` 有 flag，`.env` 没有；配置只认环境变量，避免命令行与 shell rc 打架 |
| 路径归一      | 只对 `WEX_ENV_FILE` 的值做 `~` 展开与 `/→\`；`.env` 内部另有一套规则（见第 4 节） |
| 读取          | `win::read_text_or`：UTF-8、剥 BOM、无效序列有损转码、上限 1 MiB |
| 何时读        | 只有 `wex env / check / shims` 构建 Env；`wex help` 不碰文件 |

## 怎么解析

一条流水线，两个存储目标：

```
文本 → 逐行 → trim → 跳过空行/# → 首个 '=' 切分 → 键名校验
                                              ├─ key == PATH → paths
                                              └─ 其它        → vars
```

### K=V

| 规则          | 行为                                                         |
| ------------- | ------------------------------------------------------------ |
| 行首尾空白    | trim                                                         |
| 空行 / # 开头 | 丢弃（不计入 skipped）                                       |
| 切分          | 第一个 `=`；其后全部是值                                     |
| 键名校验      | `[A-Za-z_][A-Za-z0-9_]*`，否则 `skipped: invalid key '...'`  |
| `export K=V`  | 不是语法；键变成 `export K` → 非法，带行号报告               |
| 引号          | 单引号 = 字面量（不展开）；双引号与裸值一样展开；仅"整体包裹"才生效，`a'b` 保持原样 |
| 空值          | `K=` 保留为空串                                              |
| 重复键        | 大小写不敏感；后者值胜，保留首次拼写                         |
| 顺序          | `vars` 按首次出现位置保序；`index: HashMap<小写键, 下标>` 只做加速 |

### PATH 单独分离

`Dotenv.paths: Vec<String>`，与 `vars` 完全分离，下游直接进 prepend。

每个条目依次经过：

| 步骤 | 规则                                                         |
| ---- | ------------------------------------------------------------ |
| 拆分 | 只按 `;`（盘符的 `:` 不参与）                                |
| 标记 | 尾部 `$PATH` 去掉，并只去掉连接它的一个 `:` / `;`；单独的 `$PATH` 不入列 |
| `~`  | 仅当 `~` 是条目首字符且后面是 `\`、`/` 或结尾 → 替换为用户目录 |
| 展开 | 含 `$` 时按四段查找（见 2.3）                                |
| 归一 | `/ → \`                                                      |
| 校验 | 必须是已存在目录，否则 `skipped: not a directory: ...`       |
| 去重 | 与已有条目大小写不敏感比较，保留首次                         |

解析期就访问文件系统，这是这一层唯一不纯的地方，也是主要成本（约 22 µs/条目）。

### 值的变量展开

HashMap 不是存储结构：值存在 `Vec` 里保序，HashMap 只提供「小写键 → 下标」。`$NAME` 四段查找：

| 序   | 来源                   | 备注                                              |
| ---- | ---------------------- | ------------------------------------------------- |
| 1    | `HOME` / `USERPROFILE` | 恒等于 `%USERPROFILE%`，文件里写 `HOME=` 不改变它 |
| 2    | 本文件更早的键         | O(1)；自上而下单向，不能引用后面的键              |
| 3    | 进程环境               | 每次未命中一次 `GetEnvironmentVariableW`          |
| 4    | 都没有                 | 原样保留 `$NAME`（含 `$`）                        |

不支持：`${NAME}`、`$$` 转义、默认值语法、`\$` 转义（Windows 的 `C:\$Recycle.Bin` 会冲突）。

安全写法：`KEY='...'` 单引号字面量。双引号不安全——POSIX 语义下双引号仍然展开。

```
A=abc$PATH      -> abcC:\Users\...\aria2;...   ← 危险：命中进程环境
B='abc$PATH'    -> abc$PATH                    ← 安全
C="$PATH"       -> 整条 PATH                    ← 双引号不保护
D=p@$$w0rd      -> p@$$w0rd                    ← 未命中，原样
E=sk-live$9fK   -> sk-live$9fK                 ← `$` 后是数字，不展开
```

快速路径：值里没有 `$` 直接拷贝，不进扫描器。

### `;` 拼接

`;` 只对 PATH 成立，不是通用拼接符：

| 写法             | 结果                                         |
| ---------------- | -------------------------------------------- |
| `A=x;y`          | 变量值就是 `x;y`（一个标量）                 |
| `A=$B;$C`        | 展开后仍是一个字符串                         |
| `PATH=A;B`       | 拆成两个目录条目                             |
| `PATH=A;B;$PATH` | 同上；`$PATH` 只是"继承 PATH 仍在后面"的标记 |

语义来自键名（PATH 的值是列表），不来自值本身。

## 错误处理

解析层没有硬错误，只有降级：

| 级别 | 情况                           | 结果                                                         |
| ---- | ------------------------------ | ------------------------------------------------------------ |
| 文件 | 不存在 / 是目录 / 无权限       | `found = false`，0 变量，静默                                |
| 文件 | > 1 MiB                        | `found = true` + `skipped: file is N bytes; the limit is 1048576` |
| 行   | 无 `=` / 非法键 / 条目不是目录 | 记入 `skipped`（行号 + 原因），继续下一行                    |
| 编码 | 无效 UTF-8                     | 有损转码为 U+FFFD，不报错                                    |

呈现策略：

- `skipped` 只在 `wex check` 显示（最多 5 条 + `... N more`）。
- `wex env` 的 stderr 保持干净——它挂在每次 shell 启动上。
- 解析问题不影响退出码；exit 2 只来自 CLI 参数错误或 `WEX_SHIMS` 非法。
- 失败隔离：`.env` 出问题不会让 PATH 丢东西，只是少几个变量/条目。

### `/` 与 `\`

| 位置                  | 处理                                                       |
| --------------------- | ---------------------------------------------------------- |
| PATH 条目             | 展开之后 `/ → \`                                           |
| 普通变量值            | 原样保留（URL、base64、正则不会被改写）                    |
| 配置层路径（`WEX_*`） | `/ → \`                                                    |
| `.env` 里的 `~`       | 只有 PATH 条目首位才展开；普通值原样                       |
| 重复分隔符            | 不折叠：`C:/x//target → C:\x\\target`                      |
| 尾部反斜杠            | 不去除：`C:\x` 与 `C:\x\` 是两条不同条目（去重是字符串级） |

实测边界：

```
TOKEN=a/b//c          -> a/b//c                  ← 非 PATH 不动
H=$HOME/bin           -> C:\Users\y86133/bin     ← 非 PATH 保留混合分隔符
PATH=C:/x:$PATH       -> C:\x
PATH=C:\PROGRA~1      -> C:\PROGRA~1             ← 8.3 短名不被当 ~ 展开
PATH=~/Applications   -> C:\Users\...\Applications
PATH=~/nope           -> skipped: not a directory: C:\Users\...\nope
```

# shim 决策模块

## shim 技术是什么？

一句话：在一个统一目录里放"命令名"，让 PATH 只需要指向这个目录。

实现上不是给每个目标 exe 建硬链接，而是把同一个启动器 `wex-shim.exe` 硬链接成 294 个文件名，旁边一张表记录"名字 → 真实全路径"。

```
%LOCALAPPDATA%\wex\shims\git.exe   ──硬链接──┐
%LOCALAPPDATA%\wex\shims\rg.exe    ──硬链接──┤  同一个 inode
...294 个名字                                │  = 安装目录里的 wex-shim.exe
%LOCALAPPDATA%\wex\shims\wex-shims.tsv        名字 → 目标
```

启动时读自己的文件名（`git.exe`）查表，用全路径 `CreateProcessW` 启动真实程序，参数原样转发，退出码原样返回。

为什么 link 启动器而不是直接 link 目标 exe？直接 link 也能启动，但工具升级替换文件后旧链接仍指向旧 inode；而"启动器 + 表"只需改一行表。代价是每次调用多一次进程创建（约 10 ms）。

## 为什么需要 shim?

Windows 的 PATH 是一条字符串，cmd.exe 有硬上限（真实悬崖 8139 字符，工作预算 8100）。62 个工具目录总共约 4 KB，再加上用户已有的 PATH，很快就撞线。

shim 把 62 个目录压成 1 个条目（本机实测：4113 → 4153 字符，只多 40）。这既是长度问题，也是"注入点唯一"的问题——shell 启动时只需要把一个目录放进 PATH。

## 哪些东西需要 shim？

准确说是 PATH 条目（目录），不是环境变量：

| 来源 | 是否 shim | 原因 |
|---|---|---|
| `~/Applications` 扫描出的 62 个目录（或其 `bin`） | ✅ | 数量多、路径长，是长度问题的主体；扫描层存在的意义就是找出它们 |
| `.env` 里的 `PATH=` 条目 | ❌ 原样追加 | 数量少、是用户显式写的顺序，保持可见 |
| `.env` 里的普通变量 | ❌ | 与 PATH/shim 无关，原样注入 |

所以当前 shim 目录排在 PATH 最前，`.env` 的真实目录紧随其后，继承 PATH 垫底。

## 为哪些文件建 shim？

只认 Windows 能直接当命令解析的 5 种扩展名：

| 扩展名 | shim 形态 | 内容/原因 |
|---|---|---|
| `.exe` `.com` | 硬链接到 `wex-shim.exe` | 启动器转发，子进程看到的仍是真实目录（DLL/资源查找正确） |
| `.cmd` `.bat` | 两行包装脚本 | `@call "真实路径" %*`；脚本里的 `%~dp0` 必须仍是真实目录，硬链接会把目录变成 shim 目录 |
| `.ps1` | 两行包装脚本 | `& '真实路径' @args`；PowerShell 按扩展名解析，且 `$PSScriptRoot` 同理 |
| 其他（dll、lnk、py…） | 忽略 | 不会被当作命令解析 |

扩展名必须保留：cmd 靠 `PATHEXT` 选名字，PowerShell 对同名优先选 `.ps1`，统一改成 `.exe` 会选错目标。

## 路径冲突、重复、顺序怎么处理？

分两层。

**目录层（PATH 合并）**

- 去重大小写不敏感；继承 PATH 里已有的目录不再加（加了只会占长度）。
- 顺序固定：shim 目录 → `.env` 条目 → 继承 PATH。
- `~/Applications` 子目录按小写名排序后再进 PATH，保证优先级不随文件系统枚举顺序变化。

**名字层（shim 目录是扁平的，必须模拟"按目录顺序搜索"）**

| 冲突 | 规则 | 本机现状 |
|---|---|---|
| 同名同扩展名出现在多个目录 | PATH 顺序靠前的胜 | 0 例 |
| 同名 `.ps1` 与 `.cmd`/`.bat` 并存 | 丢 `.ps1`（Node 生成的 `.ps1` 重解析 `$MyInvocation.Statement`，经包装会丢参数） | 9 例 |
| 后目录的 `.exe` 会抢占前目录的 `.cmd` 名字 | 按 `PATHEXT` 排名丢弃抢占者 | 0 例 |

## shim 的具体步骤？

**A. 建表（`shim::scan`）**

1. 按 PATH 顺序遍历 62 个目录，只收 5 种扩展名；
2. 同名同扩展名去重（先到者胜，计数）；
3. 应用两条"名字层"规则（`.ps1` 有搭档则丢、`PATHEXT` 抢占则丢）；
4. 得到 294 条：277 个 launcher + 17 个包装脚本。

**B. 落盘（`shim::ensure`）**

1. 读 `wex-shim.exe` 的卷号+文件索引；
2. 读 `.wex-stamp`（版本/指纹/身份/条数/目录签名），全等则直接返回；
3. 先原子写 `wex-shims.tsv`（先表后链接，刷新中途启动的 shim 也能查到完整目标）；
4. 逐条写：exe/com → `DeleteFileW` + `CreateHardLinkW`（失败退化为复制）；脚本 → 原子写两行包装；
5. 列一次 shim 目录，删掉不在 keep 集合里的旧文件；
6. 最后写 stamp（stamp 存在 ⇒ 上一轮完整跑完，这是快路径可信的依据）。

**C. 运行期转发（`wex-shim.exe`）**

1. 取自身 leaf（`git.exe`）
2. 查 TSV（大小写不敏感、保留扩展名）
3. 取 `GetCommandLineW` 跳过 `argv[0]`、其余原样
4. `CreateProcessW` 全路径启动、继承 stdio、等待、`ExitProcess(子进程码)`。

## 用了哪些优化技巧？

| 技巧 | 效果（实测） |
|---|---|
| 硬链接而不是复制 | 294 个名字共享 1 个 inode，额外磁盘占用 0 |
| 一个目录替代 62 个 | PATH 从约 +4 KB 变成 +40 字符 |
| 目录 mtime 签名跳过扫描 | 命中时不做 62 次枚举：17.0 → 11.5 ms |
| 增量写入（已正确的条目不重建） | 300 条目录上新增一条：127 → 34 ms |
| `FindFirstFile` 的目录时间不用 | 实测滞后，会漏检新工具；改用 `GetFileAttributesExW`（+1 ms 换正确性） |
| 不并行 | 实测 294 个链接：单线程 96–119 ms，4 线程 1.3 s（Defender 回调 + 目录锁） |
| 不异步 | 元数据调用无等待可重叠，纯 syscall 开销 |
| 一次枚举同时拿名字和属性 | `scan_apps` 一次根枚举 + 每个目标一次 `dir_meta` |
| 表先写、stamp 后写 | 刷新中断不会留下"表说有条目、盘上没有"的状态 |
| 原子写（临时文件 + 替换） | 包装脚本/TSV/stamp 不会出现半截内容 |
| `--force` 逃生口 | 需要"无论如何重建"时不依赖任何缓存判断 |

明确不做的：并行、用旧 TSV 做差量、把 shim 目录加进 Defender 排除——前两个收益不抵复杂度，第三个是安全策略变更。

# 适配模块

## 为什么需要适配层

三个不可回避的差异决定了它必须存在：

| 差异 | 事实 |
|---|---|
| 注入机制 | 子进程改不了父 shell。唯一通道是"输出文本、让 shell 自己 eval"，而 eval 的语法由 shell 决定 |
| 语法 | cmd 用 `set "K=V"`，PowerShell 用 `$env:K = '...'`，nushell 用 `$env.K = '...'`；PATH 在 cmd/pwsh 是字符串，在 nushell 是列表 |
| 编码与换行 | Windows PowerShell 5.1 读无 BOM 的 UTF-8 会乱码；cmd 按 OEM 代码页读；nushell/json/dotenv 都是 UTF-8 |

没有这一层，方言判断会散进 main 和 model，转义规则和长度预算会被复制到每个调用点，Env 的结构化契约也会被 shell 细节污染。所以边界定得很死：

```
输入: Env { vars, prepend, current, ... }        （结构化）
输出: (String, skipped)                           （纯文本）
```

不读盘、不做决策、不写文件——写文件（原子写、BOM、目录 ACL）由 main 负责。

## 适配了哪些？

| 方言 | 消费者 | 为什么存在 | PATH 形态 |
|---|---|---|---|
| cmd | `Command.cmd AutoRun → call env.cmd` | cmd 无法 source PowerShell 语法；还受 8191 行宽限制 | 一条字符串赋值 |
| pwsh | `$PROFILE → . env.ps1` | PowerShell 5.1 需要 BOM；7 兼容 | 一条字符串拼接 |
| nu | `nushell config.nu → source wex.nu` | nushell 的 `$env.PATH` 是 list，字符串赋值会被当成单元素 | 一个列表表达式 |
| json | 脚本/jq/其它工具 | 结构化消费，避免解析 shell 语法 | 增量数组（不含继承 PATH） |
| dotenv | 任意读 `.env` 的工具/人 | 可复用的行式格式 | 每个目录一行（见缺陷） |
## 怎么适配的？

统一骨架：先按 `.env` 文件顺序输出变量，最后输出 PATH；prepend 为空就不输出 PATH（不覆盖继承值）。

**逐方言的产物**

```bat
:: cmd —— 值不含 " 时用引号形式
set "KEY=VALUE"
set "PATH=C:\...\wex\shims;C:\...\.env\bin;%PATH%"
```

```powershell
# pwsh —— 单引号字面量，PATH 用前置串拼接
$env:KEY = 'VALUE'
$env:PATH = 'C:\...\wex\shims;' + $env:PATH
```

```nu
# nu —— PATH 是 list
$env.KEY = 'VALUE'
$env.PATH = (['C:\...\wex\shims'] | append $env.PATH | uniq)
```

```json
{ "path": ["C:\\...\\wex\\shims"], "vars": {"KEY": "VALUE"} }
```

```dotenv
KEY=VALUE
PATH=C:\...\wex\shims
```

**转义规则（每种语法的最小区）**

| 方言 | 规则 | 实现位置 |
|---|---|---|
| cmd 值含 `"` | 退化为无引号 `set K=...`，`^ & < >` 前加 `^`，`%→%%` | — |
| cmd 值不含 `"` | `set "K=V"`，理论上仍需 `%→%%` | `cmd_var`（现缺） |
| pwsh / nu | 单引号内除 `'` 外全字面，`'→''` | `sq_escape` |
| json | `"` `\` 控制字符标准转义 | `json_escape` |
| dotenv | 不转义（按行原样，值不能含换行—— `.env` 解析器保证了这点） | — |

**换行与编码**

| 方言 | 换行 | BOM |
|---|---|---|
| cmd / pwsh / nu | CRLF | 只有 `pwsh --out` 加（PS 5.1 的要求） |
| json / dotenv | LF | 不加 |

**边界语义**

- cmd 超预算时返回 `skipped=true`、不写 PATH 行——现在决策层已提前报错，这是防御性兜底。
- `--out` 由 main 原子写；目录首次创建时加固 ACL。

# 平台适配层
win.rs 是平台层：把“Windows 上只有 Win 32 能做、或只有 Win 32 才能做得对”的操作，包成不暴露 unsafe、失败可见的安全函数。上层四个模块不直接碰 FFI。

 ┌──────────────────────┐
 │                      │
 │       model.rs       │
 │ 配置 / 扫描 / .env / ├────────┐
 │         PATH         │        │
 │                      │        │
 └──────────────────────┘        │
                                 │
                                 │
                                 │
                                 │
                                 ▼
 ┌──────────────────────┐     ┌─────┐     ┌──────────┐
 │                      │     │     │     │          │
 │                      │     │     │     │          │
 │       shim.rs        ├────►│ win ├────►│kernel 32 │
 │     建表 / 落盘      │     │     │     │          │
 │                      │     │     │     │          │
 └──────────────────────┘     └──┬──┘     └──────────┘
                                 ▲
                                 │
                                 │
                                 │
                                 │
 ┌──────────────────────┐        │        ┌──────────┐
 │                      │        │        │          │
 │                      │        │        │          │
 │       main.rs        ├────────┼───────►│advapi 32 │
 │   输出文件 / 诊断    │        │        │          │
 │                      │        │        │          │
 └──────────────────────┘        │        └──────────┘
                                 │
                                 │
                                 │
                                 │
                                 │
 ┌──────────────────────┐        │
 │                      │        │
 │                      │        │
 │     wex-shim.rs      ├────────┘
 │      运行期转发      │
 │                      │
 └──────────────────────┘
## 哪些暴露的能力

| 使用方 | 用到的能力 | 为什么必须自己做 |
|---|---|---|
| `model.rs` | `env_var`、`join/last_sep`、`list_dir`、`dir_meta`、`is_dir`、`read_text/read_text_or` | 环境变量要 W 版避免编码转换；枚举要 `FindFirstFileEx + LARGE_FETCH`；目录变化判断要 `GetFileAttributesExW`，枚举返回的时间会滞后；读文件要有 1 MiB 上限、BOM 剥离、非法 UTF-8 回落 ANSI |
| `shim.rs` | `ensure_dir`、`harden_dir`、`write_file_atomic`、`file_identity`、`DeleteFileW/CreateHardLinkW/CopyFileW`、`list_dir` | 硬链接 + 失败退化复制；"这个 shim 是否已指向当前启动器"只能比 inode（卷号+文件索引）；TSV/脚本/stamp 必须原子替换；SDDL 收窄 ACL |
| `main.rs` | `write_file_atomic`（含 BOM）、`ensure_parent_dirs`、`harden_dir`、`last_sep` | `--out` 生成的脚本会被 shell 启动时读取，不能出现半截；`.env` 里有变量值，落盘目录要先加固 |
| `wex-shim.rs` | `module_path`、`read_text`、`GetCommandLineW`、`CreateProcessW`、`WaitForSingleObject`、`GetExitCodeProcess`、`ExitProcess`、`SetConsoleCtrlHandler`、`GetStdHandle/WriteFile` | 用全路径启动目标、原样转发参数、继承 stdio、把子进程退出码带回来；自身路径超长时不能截断 |
| `cli.rs` / `emit.rs` | 无 | 纯字符串处理——这正是分层成立的证据 |

## 三条隐含契约

1. **失败必须能被看到**：`read_file → Result<_, ReadError>`（区分 missing / too-large / io）、`harden_dir → bool`、`write_file_atomic → bool`。调用方不能"以为成功了"。
2. **不替用户猜编码**：UTF-8 优先（有 BOM 就剥掉），只有真的不是 UTF-8 才用 ANSI 代码页；值本身一个字节都不改写。
3. **写盘要么全有要么全无；身份判断只认 inode**：临时文件 + rename（带并发重试）、硬链接身份用卷号+64 位索引，不用 mtime/大小。

## 边界

`win.rs` 不做：`.env` 语法、PATH 合并、shim 分类规则、shell 方言、任何输出格式。它只回答"Windows 上这一步怎么做才正确"，不回答"这一步该不该做"。

# shim 转发模块

## 转发层在整条链路里的位置？

```
shell 输入 git -v
        │
        ▼
PATH 解析：命中 shims\git.exe
        │
        ▼
wex-shim.exe（硬链接）
        │
        ▼
读 wex-shims.tsv
        │
        ▼
CreateProcessW 全路径启动真 git
        │
        ▼
等待 + 转发退出码
```

它是"命令名 → 真实程序"的唯一运行时环节。上游（决策层/建表层）负责让 `git.exe` 这个名字存在且可解析，转发层负责名字被敲下之后发生的事。

## 为什么必须是独立 exe，不能是 DLL 或钩子？

要让一个裸命令名能被解析，PATH 目录里必须有一个 `CreateProcess` / `ShellExecute` 能直接执行的文件。DLL 需要注入到宿主（shell）进程，属于不受支持的代码注入，还要处理位数、UIPI、卸载；钩子同理。独立 PE + 硬链接是唯一"受支持且零注入"的形态。

##  它怎么知道自己是谁？

用 `GetModuleFileNameW` 取自身路径，再取 leaf，不读 `argv[0]`。因为裸名调用时 `argv[0]` 只是 `git`，没有目录信息；而 TSV 在 exe 旁边，必须知道目录。leaf 是 `wex-shim(.exe)` 时直接拒绝运行——防止有人误调启动器本身。

## 它怎么找到目标？为什么查表要保留扩展名？

读同目录 `wex-shims.tsv`（名字\<TAB\>全路径），按**完整文件名**大小写不敏感匹配。

保留扩展名是因为同一个名字可能有多个真实目标：`noctty.com` 与 `noctty.exe` 是不同程序；cmd 的 `PATHEXT` 也会按扩展名决定胜负。表由建表层一次性写好，转发层只读——查表成本实测可忽略（TSV 追加到 100 KB 也无差别）。

## 为什么参数是"原样转发"，而不是解析后重组？

Windows 没有 argv 数组，只有一条命令行；argv 是 CRT 自己拆的，拆法有十几种引号/反斜杠规则。任何"解析再重排"都会引入引号地狱（`"a b"`、空串、`&`、`%PATH%`）。

所以：取 `GetCommandLineW`，跳过 `argv[0]`（识别引号形式），剩下的 u 16 序列一字节不改地接在目标路径后面。实测 `["a b","","x&y","中 文"]` 全部原样到达子进程。

## 怎么启动目标？

`CreateProcessW`：

| 参数                | 值                          | 原因                                                         |
| ------------------- | --------------------------- | ------------------------------------------------------------ |
| `lpApplicationName` | NULL                        | 让 Windows 从命令行首个（带引号的）token 解析模块名          |
| 命令行              | `"<目标全路径>" <原样参数>` | 全路径避免二次 PATH 解析                                     |
| `bInheritHandles`   | TRUE                        | 子进程拿到 stdin/stdout/stderr，重定向与管道才有意义（实测三者都透传） |
| 环境 / cwd          | NULL                        | 继承 shim 的环境与当前目录——相对路径参数因此仍然正确         |

## 退出码和 Ctrl+C 怎么处理？

`WaitForSingleObject(INFINITE)` → `GetExitCodeProcess` → `ExitProcess(code)`，一比一返回（实测子进程 42 → shim 42）。

同时注册一个 `SetConsoleCtrlHandler`，对 CTRL_C/CTRL_BREAK 返回"已处理"。目的不是吞掉信号，而是让自己活到能读到子进程退出码——子进程在同一个控制台里，会自己收到 Ctrl+C。代价是：如果子进程忽略 Ctrl+C，shim 也无法用 Ctrl+C 强杀。

## 失败时发生什么？

统一：写一行 stderr，退出 127。

| 失败           | 消息                                                         |
| -------------- | ------------------------------------------------------------ |
| 取不到自身路径 | cannot determine the running path                            |
| 直接调用启动器 | invoked directly; run it through a shim name instead         |
| 读不到 TSV     | cannot read wex-shims.tsv next to the shim                   |
| 名字未登记     | no target registered for this name                           |
| 目标起不来     | cannot start the registered target (error 2) ← 现在带系统错误码 |
| 命令行超限     | command line too long (32794 characters; the limit is 32766) |

127 是"命令不可用"的自定义约定（cmd 自己的"未找到"是 9009），与"启动失败"区分得开。

## 每次调用多花多少？

实测 `git --version`：直连 35.3 ms，经 shim 45.5 ms → +10.2 ms。构成：

| 部分                               | 量级                           |
| ---------------------------------- | ------------------------------ |
| 额外一次进程创建（含安全软件回调） | ~8–9 ms                        |
| 读 TSV（约 15 KB）+ 线性查找       | ~0.1 ms（100 KB 也无可测差异） |
| 等待与退出码转发                   | < 0.5 ms                       |

所以不再优化查表结构——瓶颈在进程创建，不在我们的代码。

## 它明确不做什么？

| 不做                      | 原因                                                         |
| ------------------------- | ------------------------------------------------------------ |
| 改父 shell 的环境变量     | 进程环境不可跨进程写，只有 shell 自己 eval 才有效            |
| 给工具注入 `.env` 变量    | 只覆盖"经 shim 启动"的命令，会出现时有时无；PATH 解析发生在 shell，注入太晚 |
| 缓存查表结果              | 每次都是新进程，进程内缓存无意义                             |
| 解析/改写参数             | 保真是唯一不会错的选择                                       |
| 自动修复 TSV 与文件不一致 | TSV 与硬链接由建表层原子写+顺序保证；异常状态用 `wex shims --force` 修 |
