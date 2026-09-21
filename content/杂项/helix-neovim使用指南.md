# Helix / Neovim 代码导航配置指南

> 2026-09-20 于 C:\Users\\<user\> 实测编写。所有结论都有实机证据，标注在"验证证据"小节。
> 涉及路径均为本机路径（Windows）。

---

## 0. 一句话结论

| 需求 | Helix (hx 25.07.1) | Neovim (0.12.5 + LazyVim) |
|---|---|---|
| 看函数信息（hover） | `K`（或 `space k`） | `K`（或鼠标 **Ctrl+右键**） |
| 跳转到定义 | `gd` | `gd`（或鼠标 **Ctrl+左键**） |
| 鼠标点击跳转 | **不支持**（源码硬编码，见 §2.5） | 支持（自定义映射，已配好） |
| 环境体检 | `hx --health [lang]` | `:LspInfo` / `:checkhealth vim.lsp` |

---

## 1. 机制：编辑器本身不解析代码

```
buffer 打开 .rs
   │  按“根标记文件”往上找                    （Helix: languages.toml 的 roots;
   ▼                                          Neovim: lspconfig 的 root_dir）
项目根: Cargo.toml / pyproject.toml / package.json / go.mod ...
   │  stdio + JSON-RPC
   ▼
语言服务器: rust-analyzer / pyright / clangd / typescript-language-server / lua-language-server
   │
   ├─ textDocument/hover      → 弹窗显示签名、类型、文档      （"点函数出信息"）
   └─ textDocument/definition → 返回 file+line，光标跳过去     （"点函数跳位置"）
```

- **"自动解析项目/环境"** = 编辑器按语言配置里的**根标记文件**列表向上查找，找到就启动 LSP 并把它当工作区根。
- Hover / 跳转 / 引用 / 重命名 都是 LSP 请求，**键位只是绑定**；鼠标又是键位之外的额外绑定，终端与编辑器都得支持。

---

## 2. Helix

### 2.1 键位（从源码 `helix-term/src/keymap/default.rs` 核对，非道听途说）

| 键 | 作用 | 键 | 作用 |
|---|---|---|---|
| `gd` | 跳转定义 | `K` | **hover 弹窗（函数信息）**，本机改绑；默认 `space k` 仍可用 |
| `gD` | 跳转声明 | `space r` | 重命名符号（LSP） |
| `gy` | 跳转类型定义 | `space a` | code action |
| `gr` | 查引用（picker） | `space h` | 选中该符号的全部引用 |
| `gi` | 跳转实现 | `]d` / `[d` | 下一条 / 上一条诊断 |
| `C-o` / `C-i` | 跳回 / 跳前 | `]D` / `[D` | 最后 / 第一条诊断 |
| `space d` / `space D` | 文件 / 工作区 诊断 picker | `space f` / `space F` | 文件 picker |

注意：Helix **默认没有** `K` = hover（默认 `K` 是 `keep_selections`），和 Vim/Neovim 习惯不同。**本机已改为 `K` = hover**，见 `%APPDATA%\helix\config.toml`：

```toml
[keys.normal]
# K = 悬停显示函数签名/文档（Helix 默认是 space k；两边编辑器统一成 K）
K = "hover"
```

- `[keys.normal]` 只影响 normal 模式，select 模式的 `K`(=keep_selections) 不受影响（多光标操作仍在 select 模式做）。
- 默认的 `space k` **同时保留**，实测两者都能弹出 hover（§2.6）。

### 2.2 项目根识别规则（`helix/languages.toml` 的 `roots`）

| 语言 | roots |
|---|---|
| rust | `Cargo.toml`, `Cargo.lock` |
| python | `pyproject.toml`, `setup.py`, `poetry.lock`, `pyrightconfig.json` |
| typescript / javascript | `package.json`, `tsconfig.json` / `jsconfig.json` |
| go | `go.work`, `go.mod` |

### 2.3 体检命令

```powershell
hx --health                 # 全部语言一览，✓ / ✘
hx --health rust python lua # 只看几种
```

输出会直接告诉你：服务器解析到的 exe 全路径、DAP、formatter、tree-sitter parser / query 是否齐全。
这是 Helix 侧唯一需要的"环境自检"。

Helix 常用 LSP 命令：`:lsp-restart`、`:lsp-stop`、`:lsp-workspace-command`。

### 2.4 本机配置与安装（本次改动）

| 动作 | 结果位置 |
|---|---|
| `uv tool install pyright` | `~/.local/bin/pyright-langserver.exe` |
| `mise use -g lua-language-server` | `~/AppData/Local/mise/shims/lua-language-server.exe` |
| PATH 接入 mise shim | `~/.env`（**放在文件最前面** = 最终 PATH 优先级最低，避免遮蔽 `~/Applications` 下的同名工具） |
| python 服务器改为 pyright | `%APPDATA%\helix\languages.toml` |

`%APPDATA%\helix\languages.toml` 当前内容要点：

```toml
# Helix 上游 python 默认服务器是 ["ty", "ruff", "jedi", "pylsp", "zuban"]，没有 pyright
[[language]]
name = "python"
language-servers = ["pyright", "ruff"]

# JS/TS：typescript-language-server 管类型与跳转，biome 管 lint/format
[[language]]
name = "javascript"
language-servers = ["typescript-language-server", "biome-lsp-proxy"]
# （typescript / jsx / tsx 同此）
```

`~/.env` 新增行（置于文件顶部）：

```sh
export PATH=$HOME/AppData/Local/mise/shims:$PATH
```

### 2.5 Helix 的鼠标：做不到（硬限制）

源码证据：

- `helix-view/src/input.rs`：`MouseEvent` 是独立于 keymap 的事件类型，**不参与 keymap 解析**，所以无法 `config.toml` 绑定。
- `helix-term/src/ui/editor.rs::handle_mouse_event` 把行为写死：左键 = 移动光标/选择，中键 = 粘贴，右键 = 行号区（git hunk/diagnostic）菜单，滚轮 = 滚动。

结论：**Helix 里只能用键盘**；要"鼠标点击函数跳转"请用 Neovim（§3.4）。

### 2.6 验证证据

| 验证项 | 操作 | 结果 |
|---|---|---|
| rust hover | 光标在 `add(1, 2)` 上按 `space k` | 弹出 `fn add(a: i32, b: i32) -> i32`；同行 inlay hint 显示 `let s: i32 = add(a: 1, b: 2)` |
| **`K` = hover 生效**（`[keys.normal]` 配置项） | 光标在 `add` 上按 `K` | 弹出 `fn add(a: i32, b: i32) -> i32`（配置解析无误；`space k` 同时仍可用） |
| rust 跳转 | 光标 6:15 按 `gd` | 跳到 **1:4**（`fn add`） |
| python hover（pyright 覆盖生效） | 光标在 `print(` 上按 `space k` | 弹出 `(function) def print(*values: object, sep: str \| None = " ", ...)` |
| lua 服务器 | `hx --health lua` | ✓ `...\mise\shims\lua-language-server.exe` |
| 环境优先级 | `wex env` 后 `where` | `lua-language-server` 走 shim，`ruff` / `biome` 仍是 `~/Applications` 的原件（未被遮蔽） |

---

## 3. Neovim（LazyVim）

### 3.1 关键坑：LazyVim 只启用你显式列出的服务器

`~/AppData/Local/nvim-data/lazy/LazyVim/lua/lazyvim/plugins/lsp/init.lua` 的 `configure()` 只遍历 `vim.tbl_keys(opts.servers)`；而 LazyVim 默认 `servers` 表里**只有 `["*"]`、`stylua`(禁用)、`lua_ls`**。

=> 即使 `rust-analyzer` 已经在 PATH 里，**不写进 `opts.servers` 就不会启动**，`gd` 由于没有 `LspAttach` 也没有映射。

实测（改配置前）：`vim.lsp.get_clients()` 返回空，`vim.fn.maparg("gd","n")` 也是空。

### 3.2 本次新增：`~/AppData/Local/nvim/lua/plugins/lsp.lua`

```lua
-- LSP: 打开项目文件后自动挂上语言服务器（悬停看信息 / 跳转定义 / 引用 / 重命名）
-- 说明：LazyVim 默认只启用 lua_ls，其它服务器必须在下面显式列出，否则不会启动。
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- PATH 里已有二进制（cargo / LLVM / uv / npm 装的）：mason = false，不再下载一份
        rust_analyzer = { mason = false },
        clangd        = { mason = false },
        pyright       = { mason = false },
        ts_ls         = { mason = false }, -- typescript-language-server
        lua_ls        = {},                -- 交给 mason 管理（已装）

        -- 想再加：先 :Mason 装，或自己放进 PATH，然后补一行（名字见 nvim-lspconfig/lsp/*.lua）
        -- gopls = { mason = false },
        -- bashls = {}, jsonls = {}, yamlls = {}, html = {}, cssls = {},
        -- marksman = {}, taplo = {}, cmake = {},
      },
    },
  },
}
```

### 3.3 键位（LazyVim 默认，实测 `maparg` 来源确认）

| 键 | 作用 |
|---|---|
| `gd` | 跳转定义（单结果直接跳；多结果弹 picker） |
| `gr` | 引用列表 |
| `gI` | 跳转实现（**不是** `gi`） |
| `gy` / `gD` | 类型定义 / 声明 |
| `K` / `gK` | hover 文档 / 函数签名（insert 模式 `<C-k>`） |
| `<leader>cr` | 重命名 |
| `<leader>ca` | code action |
| `<leader>cl` | Lsp Info（Snacks picker） |
| `]]` / `[[` | 上/下一条同符号引用 |

诊断命令：`:LspInfo`（等价 `:checkhealth vim.lsp`）、`:LspRestart`、`:LspStop`、`:LspStart`（由 nvim-lspconfig 提供）。

### 3.4 鼠标点击（本次新增，已实测）

追加到 `~/AppData/Local/nvim/lua/config/keymaps.lua`：

```lua
-- LSP 鼠标操作（键盘党用 gd / K 即可；set mouse=a 已由 LazyVim 设好）
local function mouse_lsp(fn)
  return function()
    local m = vim.fn.getmousepos() -- 点击位置：窗口 + 行列（column 已剔除 gutter）
    if m.line > 0 and vim.api.nvim_win_is_valid(m.winid) then
      vim.api.nvim_set_current_win(m.winid)
      vim.api.nvim_win_set_cursor(m.winid, { m.line, math.max(m.column - 1, 0) })
      fn()
    end
  end
end

vim.keymap.set("n", "<C-LeftMouse>",  mouse_lsp(vim.lsp.buf.definition), { desc = "Ctrl+左键 → 跳转定义" })
vim.keymap.set("n", "<C-RightMouse>", mouse_lsp(vim.lsp.buf.hover),      { desc = "Ctrl+右键 → 显示函数信息" })

-- 不想按 Ctrl：注释掉上面两行，改用双击（会覆盖"双击选词"）
-- vim.keymap.set("n", "<2-LeftMouse>", mouse_lsp(vim.lsp.buf.definition), { desc = "双击 → 跳转定义" })
```

实现要点：

- `<C-LeftMouse>` / `<C-RightMouse>` 是终端 SGR 鼠标协议里标准可达的事件（左键 code 0、右键 2，Ctrl 修饰 +16）。
- `vim.fn.getmousepos()` 返回的是 **buffer 列**（屏幕列已减去 gutter/行号宽度），映射里再 `-1` 转成 0-based 给 `nvim_win_set_cursor`。
- 实测坐标映射：点击 `screencol=19, screenrow=6` → `column=13, line=6`（6 列 gutter 被正确剔除）。

### 3.5 终端注意（Windows Terminal）

Windows Terminal 把 **Ctrl+click 保留给超链接检测**（悬停识别到 URL 才拦截并下划线）。普通代码标识符不是 URL，一般能透传（本次 pty 实测正常）。若被吞掉，二选一：

1. Windows Terminal 设置里关闭 URL 检测：`settings.json` → `"experimental.detectURLs": false`（或设置 UI 里的 "Detect URLs"）。
2. 改用**双击**映射（终端一律能发出双击事件）。

### 3.6 验证证据

| 验证项 | 操作 | 结果 |
|---|---|---|
| 自动挂服务器 + 自动识别项目根 | 打开纯文件 `lsptest/src/main.rs` | `vim.lsp.get_clients()` → `rust_analyzer (root=C:/Users/<user>/tmp/lsptest)`（靠 Cargo.toml 找到根） |
| Ctrl+左键点击 `add` | 注入 SGR `\e[<16;19;6M` | 光标 6:13 → **1:4**，状态栏 breadcrumb 变 `main › add` |
| Ctrl+右键点击 `add` | 注入 SGR `\e[<18;19;6M` | 弹出 `fn add(a: i32, b: i32) -> i32` |
| 键盘 `gd` | 光标在 `add` 上 | 直接跳到 1:4 |
| 鼠标坐标 | 映射内打印 `getmousepos()` | `screencol=19 → column=13`（gutter 已剔除） |

---

## 4. 新增语言的固定套路

### 4.1 把服务器装进 PATH

```powershell
uv tool install pyright              # Python（已装）
uv tool install ty                   # Python 备选（Helix 默认列表里就有）
mise use -g lua-language-server      # Lua（已装）
bun add -g intelephense              # PHP
mise use -g go; go install golang.org/x/tools/gopls@latest   # Go（还需把 ~/go/bin 加进 ~/.env）
```

已在 PATH 的：`rust-analyzer`(cargo)、`clangd`(LLVM)、`typescript-language-server`(npm/node)、`pyright`、`lua-language-server`(mise shim)。

### 4.2 两边分别接上

- **Helix**：`hx --health <lang>` 看到 ✓ 即完事（上游 `languages.toml` 已内置绝大多数语言的服务器表；只在不默认时才需要写 `[[language]]` 覆盖，如本次的 python→pyright）。
- **Neovim**：在 `lua/plugins/lsp.lua` 的 `servers` 加一行：
  - 二进制在 PATH 里 → `gopls = { mason = false }`
  - 想交给 mason 管 → `:Mason` 里装好后写 `gopls = {}`
  - 服务器名查 `~/AppData/Local/nvim-data/lazy/nvim-lspconfig/lsp/*.lua` 的文件名。

### 4.3 未装的重型工具链

本机**没有** `go` / `java` / `php` / `jdtls`。装 Go/Java 工具链属于另一个量级的动作，需要时再单独处理。

---

## 5. 文件改动清单（本次）

| 文件 | 改动 |
|---|---|
| `~/.env` | 顶部新增 `export PATH=$HOME/AppData/Local/mise/shims:$PATH`（最低优先级，避免遮蔽 `~/Applications`） |
| `%APPDATA%\helix\languages.toml` | 新增 python → `["pyright","ruff"]` 覆盖；更新注释 |
| `%APPDATA%\helix\config.toml` | 新增 `[keys.normal] K = "hover"`（对齐 Neovim；`[editor.lsp] display-inlay-hints / auto-signature-help` 原本已开，inlay hint 实测生效） |
| `~/AppData/Local/nvim/lua/plugins/lsp.lua` | **新建**：5 个语言服务器 |
| `~/AppData/Local/nvim/lua/config/keymaps.lua` | 新增 Ctrl+左键 / Ctrl+右键 鼠标映射 |
| 安装 | `pyright`（uv tool）、`lua-language-server@3.19.1`（mise） |

未改动：`%APPDATA%\helix\config.toml` 里的 `[editor]` / `[editor.word-completion]` 段落（保持原样）。

---

## 6. 速查

```powershell
# Helix
hx --health rust python lua      # 环境体检
# 编辑时：gd 跳定义 / K 看信息（默认 space k 也行）/ gr 引用 / space r 重命名 / C-o 跳回

# Neovim
nvim +':LspInfo'                 # 看当前挂了哪些服务器（= :checkhealth vim.lsp）
# 编辑时：gd 跳定义 / K 看信息 / gr 引用 / <leader>cr 重命名 / <leader>cl Lsp Info
# 鼠标：Ctrl+左键 跳定义，Ctrl+右键 看信息
```
