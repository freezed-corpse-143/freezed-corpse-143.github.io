# 环境变量管理

## 快速进入面板

```cmd
@echo off
rundll32.exe sysdm.cpl,EditEnvironmentVariables
```

保存在`open_var.bat`文件中。
- 用户变量：直接双击
- 系统变量：右键以管理员身份运行。

## 查看

cmd

```cmd
# 查看所有环境变量
set

# 查看特定变量
echo %PATH%
```

powershell

```powershell
# 查看所有环境变量
dir env:
# 或
Get-ChildItem Env:

# 查看特定变量
$env:PATH
# 或
Get-ChildItem Env:PATH
```

## 临时设置

cmd

```powershell
# 设置临时变量
set MY_VAR=value

# 验证
echo %MY_VAR%
```

powershell

```powershell
# 设置临时变量
$env:MY_VAR = "value"

# 验证
$env:MY_VAR
```

## 永久设置

cmd 使用 setx

```cmd
# 设置用户环境变量
setx MY_VAR "value"

# 设置系统环境变量（需要管理员权限）
setx MY_VAR "value" /m
```

powershell

```powershell
# 删除用户环境变量
[Environment]::SetEnvironmentVariable("MY_VAR", $null, "User")

# 删除系统环境变量（需要管理员权限）
[Environment]::SetEnvironmentVariable("MY_VAR", $null, "Machine")

```

## 编辑 PATH 环境变量

```bash
# CMD - 临时
set PATH=%PATH%;C:\new\path

# CMD - 永久
setx PATH "%PATH%;C:\new\path"

# PowerShell - 临时
$env:PATH += ";C:\new\path"

# PowerShell - 永久
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\new\path", "User")

```

## 注意事项

1. **setx vs set**：
   - `set`：临时变量，仅当前会话有效
   - `setx`：永久变量，写入注册表，需要新开窗口才能生效
2. **权限要求**：
   - 用户环境变量：普通用户权限
   - 系统环境变量：管理员权限
3. **立即生效**：
   - 永久环境变量更改后，需要重新启动命令窗口或应用程序才能生效
   - 临时变量立即在当前会话生效
4. **setx限制**：
   - `setx MY_VAR ""` 只能清空值，不能完全删除变量
   - 完全删除需要使用REG命令

# 删除 WindowsApp 下的冗余文件

举例来说

```cmd
del /f/s/q python.exe
```

# 字体文件所在

`C:\Windows\Fonts`

# 默认展开更多选项

右键以管理员身份运行cmd

```cmd
reg.exe add "HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32" /f /ve
```

重启资源管理器

```powershll
taskkill /f /im explorer.exe & start explorer.exe
```

恢复默认右键

```cmd
reg.exe delete "HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32" /va /f
```

# 显示在桌面

目标：此电脑、控制面板

操作系统：win11

操作：桌面右键→个性化→主题→桌面图标设置→勾选计算机和控制面板

# 更新回滚

设置→windows更新→高级选项→恢复→返回

## 安装 gpedit.msc

新建gpedit.bat文件，粘贴输入：

```cmd
@echo off

pushd "%~dp0"

dir /b %systemroot%\Windows\servicing\Packages\Microsoft-Windows-GroupPolicy-ClientExtensions-Package~3*.mum >gp.txt

dir /b %systemroot%\servicing\Packages\Microsoft-Windows-GroupPolicy-ClientTools-Package~3*.mum >>gp.txt

for /f %%i in ('findstr /i . gp.txt 2^>nul') do dism /online /norestart /add-package:"%systemroot%\servicing\Packages\%%i"

pause
```

# 组策略关闭更新

1. `win`+`r`，输入`gpedit.msc`，如果找不到gpedit.msc找不到gpedit.msc，旧参考[[windows#安装 gpedit.msc]]
2. 点击：计算机配置→管理模板→Windows组件→Windows更新→管理最终用户体验
3. 找到右边：配置自动更新，双击，改为“已禁用”。
4. 确定

# 文件树

字符编码：

- `├`: `Alt`+`195`
- `─`: `Alt`+`196`
- `└`: `Alt`+`192`
- |: 直接输出

文件树的生成脚本

```python
def generate_file_tree(root_dir, prefix="", is_last=True):
    items = os.listdir(root_dir)
    items.sort()
    root_dir_name = os.path.basename(root_dir)

    tree_str = prefix + ("└─ " if is_last else "├─ ") + root_dir_name + "\n"
    new_prefix = prefix + ("   " if is_last else "│  ")

    for i, item in enumerate(items):
        item_path = os.path.join(root_dir, item)
        is_item_last = (i == len(items) - 1)
        if os.path.isdir(item_path):
            tree_str += generate_file_tree(item_path, new_prefix, is_item_last)
        else:
            tree_str += new_prefix + ("└─ " if is_item_last else "├─ ") + item + "\n"
    return tree_str
```

# 查看本机配置信息

`win+`R`，输入`dxdiag`

# 查看当前用户的权限

cmd输入`netplwiz`

# 微软输入法

位置：`C:\Windows\System32\InputMethod`

# 在公网中暴露端口

1. 打开“控制面板” > “系统和安全” > “Windows Defender防火墙”。
2. 点击左侧的“高级设置”。
3. 在“入站规则”部分，点击右侧的“新建规则...”。
4. 选择“端口”，然后点击“下一步”。
5. 选择适当的协议（TCP/UDP），并指定要开放的端口号。
6. 允许连接，并根据需要选择应用此规则的网络位置（域、专用、公共）。
7. 给规则一个名称以便识别。

# 结束 Explorer.exe

任务管理器→性能→资源管理器→搜索管理句柄`explorer.exe`→点击终止进程

# win10更改为密码登录

`win`+`I`→账户→改为本地账户登陆→输入`PIN`值和新密码→重启→输入密码界面，点击下面的登录选项→选择密码登录

# cmd 搜索带有某个字符串的文件

```cmd
findstr /s /i /m "arxiv" *.*
```

# 快速进入某个目录的Powershell

1. 按住shift
2. 右键资源管理目录的空白处，右键，打开Powershell。

# 删除设备和驱动器中的残余项

1. `win`+`r`，输入`regedit`，进入注册表。
2. 搜索`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\MyComputer\NameSpace`，选择对应的项删除。

# win11 查看系统版本

设置→系统→系统信息

# win11 禁用更新

使用非家庭版

1. 按 Windows 键，输入 gpedit，选择 gpedit.msc 或编辑组策略
2. 选择 计算机配置 → 管理模板 → Windows 组件 → Windows 更新 → 管理最终用户体验
3. 双击 配置自动更新，选择 已禁用。
4. 禁用 windows modules installer worker
5. 重启。

# win 11 禁用 windows modules installer worker

> 后台运行，占用CPU和读写磁盘

1. 按 Windows 键，输入 services.msc
2. 在服务列表中找到 Windows Modules Installer，右击，选择属性，选择禁用。

# 删除 NUL 文件

保留设备名称文件（NUL、CON、PRN、AUX等）

Windows 中这些是保留名称，无法直接删除：

```powershell
del "\\?\C:\path\to\nul"
```

# 设置代理

```cmd
set http_proxy=http://127.0.0.1:7890
set https_proxy=http://127.0.0.1:7890
```

# 命令行自动补全

1. 安装：

```bash
bun add -g @microsoft/inshellisense
is init
```

2. 使用

```cmd
# 对于Windows CMD
is -s cmd

# 对于Windows PowerShell
is -s powershell

# 对于PowerShell Core (pwsh)
is -s pwsh
```
# Windows 下脚本的中文乱码

将脚本另存为`ANSI`格式。

# 缓解梯子 DNS 劫持

## 启用阿里云 DNS

1. 按 **Win + R** 键，输入下方极速指令并回车：

`ncpa.cpl`复制

2. 右键点击你正在连接的网卡 (Wi-Fi 或 以太网) -> **属性**。
3. 双击 **Internet 协议版本 4 (TCP/IPv4)**。
4. 选择“使用下面的 DNS 服务器地址”，填入：

首选 DNS：**223.5.5.5**
备用 DNS：**223.6.6.6**

## 清除 DNS 缓存 (刷新生效)

修改后需强制刷新才能立即生效：

```
ipconfig /flushdns
```

复制

**💡 提示：**如果问题依旧，可运行重置网络堆栈命令：
`netsh winsock reset`(需重启)

## 重启设备（必须执行）

# WSL

## WSL 迁移

```
wsl --shutdown
mkdir D:\WSL\Ubuntu-24.04
wsl --manage Ubuntu-24.04 --move D:\WSL\Ubuntu-24.04
```
## 避免 WSL 继承宿主机环境变量

1. 修改`/etc/wsl.conf`，增加

```conf
[interop]
enabled=false
appendWindowsPath=false
```

2. 重启 WSL

```cmd
wsl --shutdown
```

## WSL 使用主机端口

> 查看主机代理端口，青云梯不是默认的 7890 端口，记得修改

在WSL中，编写`~/.bashrc`，添加

```
HOST_IP=$(ip route | awk '/default/ {print $3}')
export HTTP_PROXY="http://${HOST_IP}:7890"
export HTTPS_PROXY="http://${HOST_IP}:7890"
```

## WSL 使用镜像网络

修改`~\.wslconfig`，增加

```
[wsl2]
networkingMode=mirrored
```

然后运行

```cmd
wsl --shutdown
```

# 自动扫描添加环境变量

## cmd

安装 `clink`，参考[[环境配置#cmd]]，在`C:\Users\<user\AppData\Local\clink`，添加`auto_applications_path.lua`

```lua
local function add_to_path(new_path)
    -- Get current PATH
    local current_path = os.getenv("PATH") or ""

    -- Check if path already exists (avoid duplication)
    local path_exists = false
    for path in string.gmatch(current_path, "[^;]+") do
        if path == new_path then
            path_exists = true
            break
        end
    end

    -- Add to PATH beginning if not exists
    if not path_exists then
        os.setenv("PATH", new_path .. ";" .. current_path)
        print("[Auto PATH] Added: " .. new_path)
    end
end

local function setup_applications_path()
    local username = os.getenv("USERNAME")
    local applications_root = "C:\\Users\\" .. username .. "\\Applications"

    -- Check if root directory exists
    local handle = io.popen('if exist "' .. applications_root .. '" (echo 1) else (echo 0)')
    local result = handle:read("*l")
    handle:close()

    if result ~= "1" then
        print("[Auto PATH] Directory not found, skipped: " .. applications_root)
        return
    end

    -- Use dir command to traverse all subfolders
    local command = 'for /d %i in ("' .. applications_root .. '\\*") do @echo %i'
    local handle_dir = io.popen(command)

    local paths_added = 0
    for folder in handle_dir:lines() do
        -- Remove carriage return and trim whitespace
        folder = folder:gsub("[\r\n]", ""):gsub("^%s*(.-)%s*$", "%1")

        if folder ~= "" then
            -- Check if bin subfolder exists
            local bin_path = folder .. "\\bin"
            local check_bin = io.popen('if exist "' .. bin_path .. '" (echo 1) else (echo 0)')
            local has_bin = check_bin:read("*l")
            check_bin:close()

            if has_bin == "1" then
                -- Has bin folder, add bin path
                add_to_path(bin_path)
                paths_added = paths_added + 1
            else
                -- No bin folder, add folder itself
                add_to_path(folder)
                paths_added = paths_added + 1
            end
        end
    end
    handle_dir:close()

    if paths_added > 0 then
        print("[Auto PATH] Total " .. paths_added .. " path(s) added to current session PATH")
    else
        print("[Auto PATH] No subfolders found")
    end
end

-- Execute main function
setup_applications_path()

```

## powershell

修改`C:\Users\<user>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`或`C:\Users\<user>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`

```ps1
function Add-ToPath {
    param(
        [string]$NewPath
    )
    
    # Get current PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Process")
    
    # Check if path already exists (avoid duplication)
    $pathExists = $currentPath -split ";" | Where-Object { $_ -eq $NewPath }
    
    # Add to PATH beginning if not exists
    if (-not $pathExists) {
        [Environment]::SetEnvironmentVariable("PATH", "$NewPath;$currentPath", "Process")
        Write-Host "[Auto PATH] Added: $NewPath" -ForegroundColor Green
    }
}

function Setup-ApplicationsPath {
    $username = $env:USERNAME
    $applicationsRoot = "C:\Users\$username\Applications"
    
    # Check if root directory exists
    if (-not (Test-Path $applicationsRoot)) {
        Write-Host "[Auto PATH] Directory not found, skipped: $applicationsRoot" -ForegroundColor Yellow
        return
    }
    
    # Get all subdirectories (first level only)
    $folders = Get-ChildItem -Path $applicationsRoot -Directory
    
    if ($folders.Count -eq 0) {
        Write-Host "[Auto PATH] No subfolders found" -ForegroundColor Yellow
        return
    }
    
    $pathsAdded = 0
    
    foreach ($folder in $folders) {
        $binPath = Join-Path -Path $folder.FullName -ChildPath "bin"
        
        # Check if bin subfolder exists
        if (Test-Path $binPath) {
            # Has bin folder, add bin path
            Add-ToPath -NewPath $binPath
            $pathsAdded++
        } else {
            # No bin folder, add folder itself
            Add-ToPath -NewPath $folder.FullName
            $pathsAdded++
        }
    }
    
    if ($pathsAdded -gt 0) {
        Write-Host "[Auto PATH] Total $pathsAdded path(s) added to current session PATH" -ForegroundColor Green
    }
}

# Execute main function
Setup-ApplicationsPath

```

# 自动配置代理

## cmd

在`%APPDATA\Local\Clink`下编辑`proxy.lua`

```lua
local DefaultProxyServer = "http://proxy.nioint.com:8080"

local function set_proxy_env(proxy)
    os.setenv("HTTP_PROXY", proxy)
    os.setenv("HTTPS_PROXY", proxy)
    os.setenv("http_proxy", proxy)
    os.setenv("https_proxy", proxy)
end

local function unset_proxy_env()
    os.setenv("HTTP_PROXY", "")
    os.setenv("HTTPS_PROXY", "")
    os.setenv("http_proxy", "")
    os.setenv("https_proxy", "")
end

local function pon(proxy_server)
    if not proxy_server or proxy_server == "" then
        proxy_server = DefaultProxyServer
    end

    set_proxy_env(proxy_server)
    print("\27[32m[OK] Proxy enabled for current session: " .. proxy_server .. "\27[0m")
end

local function poff()
    unset_proxy_env()
    print("\27[32m[OK] Proxy disabled for current session\27[0m")
end

local function pstatus()
    print("\27[36m")
    print("=== Proxy Status (Current Session Only) ===")
    print("\27[0m")

    local hp = os.getenv("HTTP_PROXY") or ""
    if hp ~= "" then
        print("\27[32mHTTP_PROXY: " .. hp .. "\27[0m")
        print("\27[32mHTTPS_PROXY: " .. (os.getenv("HTTPS_PROXY") or "not set") .. "\27[0m")
    else
        print("\27[31mProxy: Not set in current session\27[0m")
    end
end

clink.onfilterinput(function(line)
    local cmd, arg = line:match("^%s*(%S+)%s*(.-)%s*$")

    if cmd == "pon" then
        if arg == "" then arg = nil end
        pon(arg)
        return "", false
    end

    if cmd == "poff" then
        poff()
        return "", false
    end

    if cmd == "pstatus" then
        pstatus()
        return "", false
    end
end)
```

## powershell

在`$USERPROFILE\Documents\WindowsPowerShell`下编辑`Microsoft.PowerShell_profile.ps1`

```powershell
# Default proxy configuration
$DefaultProxyServer = "http://proxy.nioint.com:8080"

# Function: Enable proxy (current session only)
function pon {
    param(
        [string]$ProxyServer = $DefaultProxyServer
    )

    # Set environment variables for proxy (current session only)
    $env:HTTP_PROXY = "$ProxyServer"
    $env:HTTPS_PROXY = "$ProxyServer"
    $env:http_proxy = "$ProxyServer"
    $env:https_proxy = "$ProxyServer"

    Write-Host "[OK] Proxy enabled for current session: $ProxyServer" -ForegroundColor Green
}

# Function: Disable proxy (current session only)
function poff {
    # Clear environment variables
    Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
    Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
    Remove-Item Env:http_proxy -ErrorAction SilentlyContinue
    Remove-Item Env:https_proxy -ErrorAction SilentlyContinue

    Write-Host "[OK] Proxy disabled for current session" -ForegroundColor Green
}

# Function: Show proxy status
function pstatus {
    Write-Host "`n=== Proxy Status (Current Session) ===" -ForegroundColor Cyan

    # Check environment variables only
    if ($env:HTTP_PROXY) {
        Write-Host "HTTP Proxy: $env:HTTP_PROXY" -ForegroundColor Green
        Write-Host "HTTPS Proxy: $env:HTTPS_PROXY" -ForegroundColor Green
    } else {
        Write-Host "Proxy: Not set in current session" -ForegroundColor Red
    }
    Write-Host ""
}
```

# 窗口操纵

- 切换屏幕：`alt+tab`，然后通过方向键选择屏幕
- 切换至半屏：`win+方向键`
- 切换至全屏：`win+↑`→`win+↓→`win+↑`
# 浏览器操纵

- 切换标签页：`ctrl+tab`或`ctrl+shift+tab`

# windows 环境变量注入 1

## powershell

修改 `$env:USERPROFILE\documents\( PowerShell | WindowsPowerShell )\Microsoft.PowerShell_profile.ps1`

增加
```powershell
function Import-UserEnvFile {
    $envFile = Join-Path $env:USERPROFILE ".env"

    if (-not (Test-Path $envFile)) {
        Write-Host "[Auto ENV] .env not found, skipped: $envFile" -ForegroundColor Yellow
        return
    }

    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()

        # 跳过空行和注释
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
            return
        }

        # 兼容 Linux shell: export KEY=value
        $line = $line -replace '^\s*export\s+', ''

        # 只处理 key=value
        if ($line -notmatch "^\s*([^=]+?)\s*=\s*(.*)\s*$") {
            Write-Host "[Auto ENV] Invalid line skipped: $line" -ForegroundColor Yellow
            return
        }

        $key = $matches[1].Trim()
        $value = $matches[2].Trim()

        # 去掉首尾引号
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        # 注入当前 PowerShell 进程
        [Environment]::SetEnvironmentVariable($key, $value, "Process")

        Write-Host "[Auto ENV] Loaded: $key" -ForegroundColor Green
    }
}

Import-UserEnvFile
```

## cmd 注入

```lua
-- File path: C:\Users\<YourUsername>\AppData\Local\clink\auto_env.lua
-- Description: Read %USERPROFILE%\.env and inject environment variables into current CMD session
-- Supported format:
--   KEY=value
--   export KEY=value
--   KEY="value"
--   KEY='value'
--   # comment

local function trim(s)
    return (s:gsub("^%s*(.-)%s*$", "%1"))
end

local function remove_quotes(value)
    if #value >= 2 then
        local first = value:sub(1, 1)
        local last = value:sub(-1)

        if (first == '"' and last == '"') or (first == "'" and last == "'") then
            return value:sub(2, -2)
        end
    end

    return value
end

local function import_user_env_file()
    local userprofile = os.getenv("USERPROFILE")

    if not userprofile or userprofile == "" then
        print("[Auto ENV] USERPROFILE not found, skipped")
        return
    end

    local env_file = userprofile .. "\\.env"

    local file = io.open(env_file, "r")
    if not file then
        print("[Auto ENV] .env not found, skipped: " .. env_file)
        return
    end

    local loaded_count = 0

    for line in file:lines() do
        line = trim(line)

        -- Skip empty lines and comments
        if line ~= "" and not line:match("^#") then

            -- Compatible with Linux shell syntax: export KEY=value
            line = line:gsub("^export%s+", "")

            -- Parse KEY=value
            local key, value = line:match("^([^=]+)=(.*)$")

            if key and value then
                key = trim(key)
                value = trim(value)
                value = remove_quotes(value)

                if key ~= "" then
                    os.setenv(key, value)
                    loaded_count = loaded_count + 1
                    print("[Auto ENV] Loaded: " .. key)
                else
                    print("[Auto ENV] Invalid line skipped: " .. line)
                end
            else
                print("[Auto ENV] Invalid line skipped: " .. line)
            end
        end
    end

    file:close()

    if loaded_count > 0 then
        print("[Auto ENV] Total " .. loaded_count .. " variable(s) loaded into current CMD session")
    else
        print("[Auto ENV] No variables loaded")
    end
end

-- Execute main function
```

# c++ 环境 安装

1. 官网 https://aka.ms/vs/stable/vs_BuildTools.exe  下载，安装 Visual Studio Installer
2. 运行安装
	1. Windows11SDK (10.0.28000.1839)
	2. MSVC v143 - VS2022 C++ x64/x86 生成工具 (v14.44-17.14)
3. 在 `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build` 下新建 `Microsoft.VCToolsVersion.default.txt`

```text
14.44.35207
```
4. 命令行运行：

```cmd
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
```

# msvc 变量注入

## cmd 注入

`auto_msvc_env.lua`

```lua
-- Auto load MSVC Build Tools environment for clink/cmd

local loaded = os.getenv("MSVC_ENV_LOADED")
if loaded == "1" then
    return
end

local vsdevcmd = [[C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat]]

local cmd = string.format(
    [[cmd /c ""%s" -arch=x64 -host_arch=x64 >nul && set"]],
    vsdevcmd
)

local pipe = io.popen(cmd)
if pipe then
    for line in pipe:lines() do
        local key, value = line:match("^([^=]+)=(.*)$")
        if key and value then
            os.setenv(key, value)
        end
    end
    pipe:close()
end

os.setenv("MSVC_ENV_LOADED", "1")
print("[MSVC] Visual Studio Build Tools environment loaded.")
```

## powershell 注入

```powershell
function Import-MSVCEnv {
    $vsDevCmd = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat"

    if (-not (Test-Path $vsDevCmd)) {
        Write-Host "[MSVC ENV] VsDevCmd.bat not found, skipped: $vsDevCmd" -ForegroundColor Yellow
        return
    }

    # 避免重复注入
    if ($env:MSVC_ENV_LOADED -eq "1") {
        return
    }

    cmd /c "`"$vsDevCmd`" -arch=x64 -host_arch=x64 >nul && set" | ForEach-Object {
        if ($_ -match '^(.*?)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }

    $env:MSVC_ENV_LOADED = "1"

    if (Get-Command cl -ErrorAction SilentlyContinue) {
        Write-Host "[MSVC ENV] Loaded: cl available" -ForegroundColor Green
    } else {
        Write-Host "[MSVC ENV] Loaded but cl not found" -ForegroundColor Yellow
    }
}

Import-MSVCEnv
```

# cmd 默认进入 pwsh

1. `win+r` 输入 `regedit`，进入注册表
2. `HKEY_CURRENT_USER\Software\Microsoft\Command Processor` 下新建 字符串值，键为 `AutoRun`，值为 `@<pwsh_file>`

# 配置 msvc 开发环境

```powershell
<#
.SYNOPSIS
    Optimized VsDevCmd.ps1 — with built-in profiling and incremental fixes.
    Run with -Profile to see per-phase timings; compare against original.
#>

[CmdletBinding()]
param(
    [ValidateSet('x86', 'amd64', 'arm', 'arm64')]
    [string]$Arch,

    [ValidateSet('x86', 'amd64', 'arm', 'arm64')]
    [string]$HostArch,

    [string]$WinSdk,
    [ValidateSet('Desktop', 'UWP')]
    [string]$AppPlatform = 'Desktop',

    [switch]$NoExt,
    [switch]$NoLogo,
    [string]$StartDir,
    [string]$VcVarsVer,
    [ValidateSet('spectre')]
    [string]$VcVarsSpectreLibs,
    [switch]$CleanEnv,
    [switch]$Test,
    [switch]$Help,

    [switch]$Profile,

    [switch]$RefreshCache   # Skip cache, re-probe all registry keys, save fresh cache
)

# ============================================================================
# Profiling infrastructure (zero overhead when -Profile not set)
# ============================================================================
$script:_ProfileData = [System.Collections.Generic.List[object]]::new()
$script:_ProfileStack = [System.Collections.Generic.Stack[object]]::new()

function Enter-Phase { param([string]$Name)
    if (-not $Profile) { return }
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $script:_ProfileStack.Push(@{ Name = $Name; Timer = $timer })
}

function Exit-Phase {
    if (-not $Profile) { return }
    $entry = $script:_ProfileStack.Pop()
    $entry.Timer.Stop()
    [void]$script:_ProfileData.Add(@{
        Phase = $entry.Name
        ElapsedMs = $entry.Timer.ElapsedMilliseconds
        Ticks = $entry.Timer.ElapsedTicks
        RegReads = $script:_RegReads
        ExtProcs = $script:_ExtProcs
        FsEnums = $script:_FsEnums
    })
}

function Show-Profile {
    if (-not $Profile) { return }
    Write-Host "`n========== Profile Report ==========" -ForegroundColor Cyan
    $fmt = "{0,-45} {1,8} ms"
    Write-Host ($fmt -f "Phase", "Time")
    Write-Host ("-" * 58)
    $total = 0
    foreach ($p in $script:_ProfileData) {
        Write-Host ($fmt -f $p.Phase, $p.ElapsedMs)
        $total += $p.ElapsedMs
    }
    Write-Host ("-" * 58)
    Write-Host ($fmt -f "TOTAL", $total)
    Write-Host "`nCounters:" -ForegroundColor DarkYellow
    Write-Host "  Registry probes : $script:_RegReads  (from cache: $script:_CacheLoaded)"
    Write-Host "  External procs  : $script:_ExtProcs"
    Write-Host "  FS enumerations : $script:_FsEnums"
    Write-Host ("  Cache file      : {0}" -f $script:_CacheFile)
    Write-Host "====================================`n" -ForegroundColor Cyan
}

$script:_RegReads = 0
$script:_ExtProcs = 0
$script:_FsEnums  = 0
$script:_CacheLoaded = 0  # entries loaded from persistent cache file
$script:_CacheFile  ="$PSScriptRoot\regcache.json"

# ============================================================================
# OPT #0: Persistent registry probe cache
# Saves all probe results to a JSON file. Subsequent runs skip probing
# entirely for cached keys. Invalidated when VS installation path changes.
# ============================================================================
function Load-RegCache {
    param([string]$VsPath)
    if ($RefreshCache) { Write-Dbg 1 "Cache: refresh forced, skipping load"; return @{} }
    if (-not (Test-Path $script:_CacheFile)) { Write-Dbg 1 "Cache: no cache file found"; return @{} }
    try {
        $data = Get-Content $script:_CacheFile -Raw | ConvertFrom-Json
        if ($data.version -ne 1) { Write-Dbg 1 "Cache: wrong version"; return @{} }
        if ($data.vsPath -ne $VsPath) { Write-Dbg 1 "Cache: VS path changed ($($data.vsPath) -> $VsPath)"; return @{} }
        $cache = @{}
        foreach ($prop in $data.entries.PSObject.Properties) {
            $v = $prop.Value
            $cache[$prop.Name] = if ($v -is [string]) { $v } else { $null }
        }
        Write-Dbg 1 "Cache: loaded $($cache.Count) entries for $VsPath"
        $script:_CacheLoaded = $cache.Count
        return $cache
    } catch { Write-Dbg 1 "Cache: load error: $_"; return @{} }
}

function Save-RegCache {
    param([string]$VsPath)
    try {
        $dir = Split-Path $script:_CacheFile -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        # Only persist non-null lookups and explicit nulls (skip transient entries)
        $entries = @{}
        foreach ($kv in $script:_RegCache.GetEnumerator()) {
            $entries[$kv.Key] = $kv.Value
        }
        $data = @{ version = 1; vsPath = $VsPath; created = (Get-Date -Format 'o'); entries = $entries }
        $data | ConvertTo-Json -Depth 3 -Compress | Set-Content $script:_CacheFile -Encoding UTF8
        Write-Dbg 1 "Cache: saved $($entries.Count) entries"
    } catch { Write-Dbg 1 "Cache: save error: $_" }
}

# ============================================================================
# OPT #1: Registry reads with Test-Path guard + persistent cache
# Test-Path miss = ~22ms | Get-ItemProperty on existing key = ~8ms
# Cache hit = ~0ms (in-memory dictionary lookup)
# vs. Get-ItemProperty + throw/catch on miss = ~112ms
# ============================================================================
# Cache is loaded AFTER VS detection (we need the VS path for validation)
$script:_RegCache = @{}

function Get-RegValue {
    param([string]$Path, [string]$Name, [string]$DefaultValue)
    $ckey = "$Path|$Name"
    if ($script:_RegCache.ContainsKey($ckey)) {
        return $script:_RegCache[$ckey]
    }
    $script:_RegReads++
    # Guard: Test-Path avoids the 112ms exception path on missing keys
    if (-not (Test-Path $Path)) {
        $script:_RegCache[$ckey] = $DefaultValue
        return $DefaultValue
    }
    try {
        $val = (Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop).$Name
        $script:_RegCache[$ckey] = $val
        return $val
    } catch {
        # Key exists but specific value doesn't — rare, but handle gracefully
        $script:_RegCache[$ckey] = $DefaultValue
        return $DefaultValue
    }
}

function Get-RegValuesAll {
    param([string]$Path)
    if ($script:_RegCache.ContainsKey("__BULK__$Path")) {
        return $script:_RegCache["__BULK__$Path"]
    }
    $script:_RegReads++
    if (-not (Test-Path $Path)) {
        $script:_RegCache["__BULK__$Path"] = @{}
        return @{}
    }
    $result = @{}
    try {
        $all = Get-ItemProperty -Path $Path -ErrorAction Stop
        foreach ($prop in $all.PSObject.Properties) {
            $n = $prop.Name
            if ($n -in @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider')) { continue }
            $v = $prop.Value
            $result[$n] = $v
            $script:_RegCache["$Path|$n"] = $v
        }
    } catch { }
    $script:_RegCache["__BULK__$Path"] = $result
    return $result
}

# ============================================================================
# Shared helpers (unchanged core logic, Test-Path on the hot path is OK)
# ============================================================================
function Write-Dbg { param([int]$Level, [string]$Message)
    $d = try { [int]$env:VSCMD_DEBUG } catch { 0 }
    if ($d -ge $Level) { Write-Host "[DEBUG:VsDevCmd.ps1] $Message" -ForegroundColor Gray }
}

function AddTo-Path { param([string]$Dir)
    if (-not $Dir) { return }
    if (-not (Test-Path $Dir -ErrorAction SilentlyContinue)) { return }
    Write-Dbg 2 "PATH += $Dir"
    $env:PATH = "$Dir;$env:PATH"
}

function AddTo-Lib { param([string]$Dir)
    if (-not $Dir) { return }
    if (-not (Test-Path $Dir -ErrorAction SilentlyContinue)) { return }
    Write-Dbg 2 "LIB += $Dir"
    $env:LIB = "$Dir;$env:LIB"
}

function AddTo-LibPath { param([string]$Dir)
    if (-not $Dir) { return }
    if (-not (Test-Path $Dir -ErrorAction SilentlyContinue)) { return }
    Write-Dbg 2 "LIBPATH += $Dir"
    $env:LIBPATH = "$Dir;$env:LIBPATH"
}

function AddTo-Var {
    param([string]$VarName, [string]$Dir)
    if (-not $Dir) { return }
    if (-not (Test-Path $Dir -ErrorAction SilentlyContinue)) { return }
    Write-Dbg 2 "$VarName += $Dir"
    $cur = Get-Variable -Name $VarName -ValueOnly -Scope Script -ErrorAction SilentlyContinue
    if ($cur) { Set-Variable -Name $VarName -Value "$Dir;$cur" -Scope Script }
    else       { Set-Variable -Name $VarName -Value $Dir -Scope Script }
}

function Normalize-PathVar {
    param([string]$Name)
    $v = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($v -and $v.EndsWith(';')) {
        [Environment]::SetEnvironmentVariable($Name, $v.TrimEnd(';'), 'Process')
    }
}

# ============================================================================
# Architecture resolution
# ============================================================================
$currentArch = if ([Environment]::Is64BitProcess) { 'x64' } else { 'x86' }
$script:TgtArch = if ($Arch -eq 'amd64') { 'x64' } elseif ($Arch) { $Arch } else { $currentArch }
$script:HostArchE = if ($HostArch -eq 'amd64') { 'x64' } elseif ($HostArch) { $HostArch } else { $script:TgtArch }

if ($Help) {
@"
** Visual Studio 2026 Developer PowerShell v18.0 (Optimized) **

Syntax: . .\VsDevCmd.Optimized.ps1 [options]

Options:
  -Arch=arch          Target architecture
  -HostArch=arch      Host compiler arch
  -WinSdk=version     Windows SDK version
  -AppPlatform=plat   Desktop (default) or UWP
  -NoExt              Skip extension scripts
  -NoLogo             Suppress banner
  -VcVarsVer=version  VC++ Toolset version override
  -VcVarsSpectreLibs=spectre  Use spectre-mitigated libraries
  -CleanEnv           Restore pre-init environment
  -Test               Run smoke tests
  -Help               Show this help
  -Profile            Show per-phase timing breakdown
  -RefreshCache       Skip cache, re-probe all registry keys, save fresh cache
"@
    return
}

# ============================================================================
# Save pre-init environment
# ============================================================================
$script:_preInitPath      = $env:PATH
$script:_preInitInclude   = $env:INCLUDE
$script:_preInitLib       = $env:LIB
$script:_preInitLibPath   = $env:LIBPATH
$script:_preInitExtInc    = $env:EXTERNAL_INCLUDE
$script:_preInitVS180Tools = $env:VS180COMNTOOLS
$script:_errCount = 0

# ============================================================================
# Locate VS Installation
# ============================================================================
function Find-VSInstallation {
    # OPT #2: Single vswhere call gets both path AND version
    # Original made 2 separate vswhere calls (lines 197 + 334); we do 1.

    # 1) VS180COMNTOOLS
    if ($env:VS180COMNTOOLS) {
        $candidate = $env:VS180COMNTOOLS.TrimEnd('\')
        if (Test-Path "$candidate\VsDevCmd.bat") {
            Write-Dbg 1 "Using VS180COMNTOOLS: $candidate"
            $vsDir = (Split-Path (Split-Path $candidate -Parent) -Parent)
            return @{
                ToolsDir  = "$candidate\"
                VSInstall = "$vsDir\"
                SemVer    = $null
            }
        }
    }

    # 2) Single vswhere call — OPT #2: get both installationPath + version at once
    $vswherePath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswherePath) {
        try {
            $script:_ExtProcs++
            $raw = & $vswherePath -latest -products '*' -property installationPath catalog_productSemanticVersion -format json 2>$null
            if ($raw) {
                $parsed = $raw | ConvertFrom-Json
                $vsPath = ($parsed | Select-Object -First 1).installationPath
                $semVer = ($parsed | Select-Object -First 1).catalog_productSemanticVersion
                if ($vsPath) {
                    $vsPath = $vsPath.Trim()
                    $toolsDir = "$vsPath\Common7\Tools\"
                    if (Test-Path "$toolsDir\VsDevCmd.bat") {
                        Write-Dbg 1 "Found via vswhere: $vsPath"
                        return @{
                            ToolsDir  = $toolsDir
                            VSInstall = "$vsPath\"
                            SemVer    = if ($semVer) { ($semVer -split '\+')[0] } else { $null }
                        }
                    }
                }
            }
        } catch { Write-Dbg 1 "vswhere failed: $_" }
    }

    # 3) Registry — OPT #1: use cached helper
    $vsDir = Get-RegValue 'HKLM:\SOFTWARE\Microsoft\VisualStudio\SxS\VS7' '18.0'
    if ($vsDir) {
        $toolsDir = "$vsDir\Common7\Tools\"
        if (Test-Path "$toolsDir\VsDevCmd.bat") {
            Write-Dbg 1 "Found via registry: $vsDir"
            return @{
                ToolsDir  = $toolsDir
                VSInstall = $vsDir.TrimEnd('\') + '\'
                SemVer    = $null
            }
        }
    }

    # 4) Known paths
    foreach ($known in @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\18\BuildTools\Common7\Tools",
        "${env:ProgramFiles}\Microsoft Visual Studio\18\Enterprise\Common7\Tools",
        "${env:ProgramFiles}\Microsoft Visual Studio\18\Professional\Common7\Tools",
        "${env:ProgramFiles}\Microsoft Visual Studio\18\Community\Common7\Tools"
    )) {
        if (Test-Path "$known\VsDevCmd.bat") {
            Write-Dbg 1 "Found via known path: $known"
            $vsDir = Split-Path (Split-Path $known -Parent) -Parent
            return @{
                ToolsDir  = "$known\"
                VSInstall = "$vsDir\"
                SemVer    = $null
            }
        }
    }
    return $null
}

Enter-Phase "Find-VSInstallation"
$vsInfo = Find-VSInstallation
Exit-Phase

if (-not $vsInfo) {
    Write-Host "[ERROR:VsDevCmd.ps1] Cannot locate Visual Studio installation."
    exit 1
}

$script:ToolsDir  = $vsInfo.ToolsDir
$script:VSInstall = $vsInfo.VSInstall.TrimEnd('\') + '\'
$script:DevEnv    = if (Test-Path "$($script:VSInstall)Common7\IDE") { "$($script:VSInstall)Common7\IDE\" } else { $null }

# Load persistent cache now that we know the VS path
$script:_RegCache = Load-RegCache $script:VSInstall

# ============================================================================
# Clean Environment Mode
# ============================================================================
if ($CleanEnv) {
    Write-Dbg 1 "Cleaning environment"
    $vars = @('DevEnvDir','VSINSTALLDIR','VSCMD_VER','VisualStudioVersion','VCINSTALLDIR',
        'VCToolsInstallDir','VCToolsRedistDir','VCIDEInstallDir','Platform',
        'CommandPromptType','PreferredToolArchitecture','VCTargetsUnderVCInstall',
        'ExtensionSdkDir','VCToolsVersion','IFCPATH','VSCMD_ARG_VCVARS_VER',
        'VSCMD_ARG_VCVARS_SPECTRE','WindowsSdkDir','WindowsSDKVersion',
        'WindowsSDKLibVersion','WindowsSdkBinPath','WindowsSdkVerBinPath',
        'WindowsLibPath','UCRTVersion','UniversalCRTSdkDir','NETFXSDKDir')
    foreach ($v in $vars) { [Environment]::SetEnvironmentVariable($v, $null, 'Process') }
    if ($script:_preInitPath)    { $env:PATH = $script:_preInitPath }    else { $env:PATH = $null }
    if ($script:_preInitInclude) { $env:INCLUDE = $script:_preInitInclude } else { $env:INCLUDE = $null }
    if ($script:_preInitLib)     { $env:LIB = $script:_preInitLib }       else { $env:LIB = $null }
    if ($script:_preInitLibPath) { $env:LIBPATH = $script:_preInitLibPath } else { $env:LIBPATH = $null }
    if ($script:_preInitExtInc)  { $env:EXTERNAL_INCLUDE = $script:_preInitExtInc } else { $env:EXTERNAL_INCLUDE = $null }
    if ($script:_preInitVS180Tools) { $env:VS180COMNTOOLS = $script:_preInitVS180Tools } else { $env:VS180COMNTOOLS = $null }
    return
}

# ============================================================================
# Test Mode
# ============================================================================
if ($Test) {
    Write-Dbg 1 "Test mode - environment not modified"
    $fail = 0
    foreach ($t in @('cl.exe','msbuild.exe','ilasm.exe')) {
        Write-Host "[TEST:VsDevCmd.ps1] Checking for $t..."
        if (-not (Get-Command $t -ErrorAction SilentlyContinue)) {
            Write-Host "[ERROR:VsDevCmd.ps1] '$t' not found in PATH"
            $fail++
        }
    }
    if ($fail -gt 0) { Write-Host "[ERROR:VsDevCmd.ps1] $fail test(s) failed"; exit 1 }
    Write-Host "[TEST:VsDevCmd.ps1] All tests passed"
    return
}

# ============================================================================
# Version & Banner — OPT #2: vswhere result reused from Find-VSInstallation
# ============================================================================
Enter-Phase "Version+Banner"

$env:VisualStudioVersion = '18.0'
$script:VSCMD_VER = if ($vsInfo.SemVer) { $vsInfo.SemVer } else { '18.0' }
$env:VSCMD_VER = $script:VSCMD_VER

if (-not $NoLogo) {
    Write-Host "**********************************************************************"
    Write-Host "** Visual Studio 2026 Developer PowerShell v$script:VSCMD_VER"
    Write-Host "** Copyright (c) 2026 Microsoft Corporation"
    Write-Host "**********************************************************************"
}
Exit-Phase

# ============================================================================
# Root environment variables
# ============================================================================
$env:VS180COMNTOOLS = $script:ToolsDir
$env:VSINSTALLDIR   = $script:VSInstall
AddTo-Path $script:ToolsDir
if ($script:DevEnv) {
    $env:DevEnvDir = $script:DevEnv
    AddTo-Path $script:DevEnv
}

# ============================================================================
# CORE: .NET Framework — OPT #3: batch registry reads
# ============================================================================
function Invoke-CoreDotNet {
    Write-Dbg 2 "Core: .NET Framework"

    $add32 = ($script:TgtArch -eq 'x86') -or ($script:HostArchE -eq 'x86')
    $add64 = ($script:TgtArch -eq 'x64') -or ($script:HostArchE -in @('x64', 'arm64'))
    $prefBitness = if ($script:HostArchE -eq 'x86') { '32' } else { '64' }

    # OPT #3: Check only the primary registry key. If missing (e.g. BuildTools
    # SKU), skip all fallback probing — each Test-Path on a non-existent key
    # costs 30-100ms. Defaults are already correct for BuildTools.
    $fwDir32 = 'C:\Windows\Microsoft.NET\Framework\'
    $fwDir64 = 'C:\Windows\Microsoft.NET\Framework64\'
    $fwVer32 = 'v4.0.30319'
    $fwVer64 = 'v4.0.30319'

    $primaryKey = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\SxS\VC7'
    # Get-RegValuesAll caches both hits AND misses — warm runs skip Test-Path entirely
    $bulk = Get-RegValuesAll $primaryKey
    if ($bulk.Count -gt 0) {
        if ($bulk['FrameworkDir32']) { $fwDir32 = $bulk['FrameworkDir32'] }
        if ($bulk['FrameworkDir64']) { $fwDir64 = $bulk['FrameworkDir64'] }
        if ($bulk['FrameworkVer32']) { $fwVer32 = $bulk['FrameworkVer32'] }
        if ($bulk['FrameworkVer64']) { $fwVer64 = $bulk['FrameworkVer64'] }
    }

    $fwDir = if ($prefBitness -eq '64') { $fwDir64 } else { $fwDir32 }
    $fwVer = if ($prefBitness -eq '64') { $fwVer64 } else { $fwVer32 }

    if ($fwDir) {
        if (-not $fwDir.EndsWith('\')) { $fwDir += '\' }
        foreach ($v in @($fwVer, 'v4.0' | Select-Object -Unique)) {
            AddTo-Path    "$fwDir$v"
            AddTo-LibPath "$fwDir$v"
        }
    }
}

# ============================================================================
# CORE: MSBuild
# ============================================================================
function Invoke-CoreMSBuild {
    Write-Dbg 2 "Core: MSBuild"
    $sub = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
    AddTo-Path "$script:VSInstall\MSBuild\Current\Bin\$sub"
}

# ============================================================================
# CORE: VS Bundled Build Tools (CMake, Ninja, vcpkg)
# Prepend so VS tools take priority over MinGW/system equivalents.
# ============================================================================
function Invoke-CoreBuildTools {
    Write-Dbg 2 "Core: VS Build Tools"

    # CMake
    $cmakeBin = "$script:VSInstall\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    if (Test-Path $cmakeBin) {
        AddTo-Path $cmakeBin
        Write-Dbg 1 "CMake: $cmakeBin"
    }

    # Ninja
    $ninjaDir = "$script:VSInstall\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja"
    if (Test-Path $ninjaDir) {
        AddTo-Path $ninjaDir
        Write-Dbg 1 "Ninja: $ninjaDir"
    }

    # vcpkg (bundled in VC)
    $vcpkgDir = "$script:VSInstall\VC\vcpkg"
    if (Test-Path "$vcpkgDir\vcpkg.exe") {
        AddTo-Path $vcpkgDir
        Write-Dbg 1 "vcpkg: $vcpkgDir"
    }
}

# ============================================================================
# CORE: Windows SDK
# ============================================================================
function Invoke-CoreWinSdk {
    Write-Dbg 2 "Core: Windows SDK"

    if ($WinSdk -eq 'none') { Write-Dbg 1 "WinSdk=none, skipping"; return }

    $script:WinSdkDir     = $null
    $script:WinSdkVersion = $null
    $script:WinSdkBinPath = $null
    $script:WinSdkVerBin  = $null
    $script:WinLibPath    = $null
    $script:WinSdkLibVer  = 'winv6.3\'
    $script:UCRTVer       = $null
    $script:UCRTSdkDir    = $null

    # ----- Windows 10 SDK -----
    function Find-Win10Sdk {
        $regBases = @(
            'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v10.0',
            'HKCU:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v10.0',
            'HKLM:\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v10.0',
            'HKCU:\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v10.0'
        )
        foreach ($base in $regBases) {
            $instDir = Get-RegValue $base 'InstallationFolder'
            if (-not $instDir) { continue }
            $instDir = $instDir.TrimEnd('\')

            $checkFile = if ($AppPlatform -eq 'UWP') { 'Windows.h' } else { 'winsdkver.h' }
            $incDir = "$instDir\include"
            if (-not (Test-Path $incDir)) { continue }

            # OPT #4: avoid version-cast sort — use natural string sort, faster
            $script:_FsEnums++
            $dirs = Get-ChildItem $incDir -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^10\.\d+\.\d+\.\d+$' }

            # Sort by splitting version parts as ints (faster than [version] cast)
            $sorted = $dirs | Sort-Object {
                $parts = $_.Name -split '\.'
                [int]$parts[0] * 1000000000 + [int]$parts[1] * 1000000 + [int]$parts[2] * 1000 + [int]$parts[3]
            } -Descending

            $found = $null
            foreach ($v in $sorted) {
                if (Test-Path "$incDir\$($v.Name)\um\$checkFile") {
                    $found = $v.Name
                    if ($WinSdk -and $v.Name -eq $WinSdk) { $found = $v.Name; break }
                    if (-not $WinSdk) { break }
                }
            }

            if ($WinSdk -and $found -ne $WinSdk) {
                Write-Dbg 1 "Specified WinSdk $WinSdk not found; using $WinSdk anyway"
                $found = $WinSdk
            }

            if ($found) {
                $script:WinSdkDir     = $instDir
                $script:WinSdkVersion = "$found\"
                $script:WinSdkLibVer  = "$found\"
                $script:WinSdkBinPath = "$instDir\bin\"
                if (Test-Path "$instDir\bin\$found\") {
                    $script:WinSdkVerBin = "$instDir\bin\$found"
                }
                if (Test-Path "$instDir\UnionMetadata\$found") {
                    $script:WinLibPath = "$instDir\UnionMetadata\$found;$instDir\References\$found"
                } else {
                    $script:WinLibPath = "$instDir\UnionMetadata;$instDir\References"
                }
                return $true
            }
        }
        return $false
    }

    # ----- Windows 8.1 SDK -----
    function Find-Win81Sdk {
        foreach ($base in @(
            'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1',
            'HKCU:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1',
            'HKLM:\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1',
            'HKCU:\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1'
        )) {
            $instDir = Get-RegValue $base 'InstallationFolder'
            if ($instDir) {
                $instDir = $instDir.TrimEnd('\')
                $script:WinSdkDir     = $instDir
                $script:WinSdkLibVer  = 'winv6.3\'
                $script:WinSdkBinPath = "$instDir\bin\"
                $script:WinLibPath    = "$instDir\References\CommonConfiguration\Neutral"
                return $true
            }
        }
        return $false
    }

    # ----- Universal CRT -----
    function Find-UCRT {
        foreach ($base in @(
            'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows Kits\Installed Roots',
            'HKCU:\SOFTWARE\Wow6432Node\Microsoft\Windows Kits\Installed Roots',
            'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots',
            'HKCU:\SOFTWARE\Microsoft\Windows Kits\Installed Roots'
        )) {
            $root = Get-RegValue $base 'KitsRoot10'
            if ($root) {
                $root = $root.TrimEnd('\')
                $script:UCRTSdkDir = $root
                $libDir = "$root\Lib"
                if (Test-Path $libDir) {
                    $script:_FsEnums++
                    $ucrtVers = Get-ChildItem $libDir -Directory -ErrorAction SilentlyContinue |
                        Where-Object { $_.Name -match '^10\.' }
                    # OPT #4: int comparison sort, same pattern
                    $sortedUCRT = $ucrtVers | Sort-Object {
                        $p = $_.Name -split '\.'
                        [int]$p[0] * 1000000000 + [int]$p[1] * 1000000 + [int]$p[2] * 1000 + [int]$p[3]
                    } -Descending
                    foreach ($uv in $sortedUCRT) {
                        if (Test-Path "$libDir\$($uv.Name)\ucrt\$script:TgtArch\ucrt.lib") {
                            $script:UCRTVer = $uv.Name
                            break
                        }
                    }
                }
                return
            }
        }
    }

    # ----- Export Phase -----
    $found = $false
    if ($WinSdk -eq '8.1') {
        if (-not (Find-Win81Sdk)) {
            Write-Host "[ERROR:VsDevCmd.ps1] Windows SDK 8.1 not found"
            $script:_errCount++; return
        }
        $found = $true
    } elseif ($WinSdk) {
        if (-not (Find-Win10Sdk)) {
            Write-Host "[ERROR:VsDevCmd.ps1] Windows SDK $WinSdk not found"
            $script:_errCount++; return
        }
        $found = $true
    } else {
        $found = Find-Win10Sdk
        if (-not $found) { $found = Find-Win81Sdk }
    }

    Find-UCRT | Out-Null

    if ($script:WinSdkBinPath) { AddTo-Path "$($script:WinSdkBinPath)$script:HostArchE" }
    if ($script:WinSdkVerBin)  { AddTo-Path "$($script:WinSdkVerBin)\$script:HostArchE" }
    if ($script:WinSdkDir -and $script:WinSdkLibVer) {
        AddTo-Lib "$($script:WinSdkDir)\lib\$($script:WinSdkLibVer)um\$script:TgtArch"
    }
    if ($script:WinSdkDir -and $script:WinSdkVersion) {
        $sd = $script:WinSdkDir; $sv = $script:WinSdkVersion
        AddTo-Var '_WINSDK_INC' "$sd\include\$sv\um"
        AddTo-Var '_WINSDK_INC' "$sd\include\$sv\shared"
        AddTo-Var '_WINSDK_INC' "$sd\include\$sv\winrt"
        AddTo-Var '_WINSDK_INC' "$sd\include\$sv\cppwinrt"
    }
    if ($script:WinLibPath) {
        foreach ($p in ($script:WinLibPath -split ';')) { if ($p) { AddTo-LibPath $p } }
    }
    if ($script:UCRTVer -and $script:UCRTSdkDir) {
        Write-Dbg 2 "UCRT: adding include and lib"
        AddTo-Var '_WINSDK_INC' "$($script:UCRTSdkDir)\include\$($script:UCRTVer)\ucrt"
        AddTo-Lib "$($script:UCRTSdkDir)\lib\$($script:UCRTVer)\ucrt\$script:TgtArch"
    }

    $env:WindowsSdkDir        = $script:WinSdkDir
    $env:WindowsSDKVersion    = $script:WinSdkVersion
    $env:WindowsSDKLibVersion = $script:WinSdkLibVer
    $env:WindowsSdkBinPath    = $script:WinSdkBinPath
    $env:WindowsSdkVerBinPath = $script:WinSdkVerBin
    $env:WindowsLibPath       = $script:WinLibPath
    $env:UCRTVersion          = $script:UCRTVer
    $env:UniversalCRTSdkDir   = $script:UCRTSdkDir
}

# ============================================================================
# Run Core — with profiling
# ============================================================================
Enter-Phase "Core: .NET Framework"
Invoke-CoreDotNet
Exit-Phase

Enter-Phase "Core: MSBuild"
Invoke-CoreMSBuild
Exit-Phase

Enter-Phase "Core: VS Build Tools"
Invoke-CoreBuildTools
Exit-Phase

Enter-Phase "Core: Windows SDK"
Invoke-CoreWinSdk
Exit-Phase

# ============================================================================
# EXT: VCVars (C++ Toolset)
# ============================================================================
function Invoke-ExtVCVars {
    if ($NoExt) { Write-Dbg 1 "Skipping ext (no_ext)"; return }
    Write-Dbg 2 "Ext: VCVars"

    $vcDir = "$script:VSInstall\VC\"
    if (-not (Test-Path $vcDir)) { Write-Dbg 1 "VC directory not found: $vcDir"; return }

    $env:VCINSTALLDIR    = $vcDir
    $env:VCIDEInstallDir = "$script:VSInstall\Common7\IDE\VC\"

    # ----- Resolve toolset version (unchanged from original — already efficient) -----
    $vcVer = $VcVarsVer
    if (-not $vcVer) { $vcVer = $env:VCToolsVersion }

    if (-not $vcVer) {
        $buildDir = "$vcDir\Auxiliary\Build"
        $propsPath = "$buildDir\Microsoft.VCToolsVersion.v145.default.props"
        $shortVer = $null
        if (Test-Path $propsPath) {
            try {
                [xml]$props = Get-Content $propsPath
                $ns = New-Object Xml.XmlNamespaceManager $props.NameTable
                $ns.AddNamespace('msb', 'http://schemas.microsoft.com/developer/msbuild/2003')
                $node = $props.SelectSingleNode('//msb:VCToolsVersionLatest', $ns)
                if ($node) { $shortVer = $node.InnerText.Trim() }
            } catch { Write-Dbg 1 "Failed to parse v145 props" }
        }

        if ($shortVer) {
            foreach ($f in @(
                "$buildDir\$shortVer\Microsoft.VCToolsVersion.$shortVer.txt",
                "$buildDir\v145\Microsoft.VCToolsVersion.VC.$shortVer.txt"
            )) {
                if (Test-Path $f) { $vcVer = (Get-Content $f).Trim(); break }
            }
        }

        if (-not $vcVer) {
            foreach ($f in @(
                "$buildDir\Microsoft.VCToolsVersion.v145.default.txt",
                "$buildDir\Microsoft.VCToolsVersion.default.txt"
            )) {
                if (Test-Path $f) { $vcVer = (Get-Content $f).Trim(); break }
            }
        }
    }

    if (-not $vcVer) { Write-Dbg 1 "Could not determine VC++ toolset version"; return }
    Write-Dbg 2 "VC++ Toolset: $vcVer"

    $vcToolsDir = "$vcDir\Tools\MSVC\$vcVer\"
    if (-not (Test-Path $vcToolsDir)) { Write-Dbg 1 "VC++ tools not found: $vcToolsDir"; return }

    $env:VCToolsInstallDir = $vcToolsDir
    $env:VCToolsVersion     = $vcVer

    $redistFile = "$vcDir\Auxiliary\Build\Microsoft.VCRedistVersion.default.txt"
    if (Test-Path $redistFile) {
        $rv = (Get-Content $redistFile).Trim()
        $rd = "$vcDir\Redist\MSVC\$rv\"
        if (Test-Path $rd) { $env:VCToolsRedistDir = $rd }
    }

    $hostMap = @{
        'x86'   = @{ Bin = '\HostX86';   Native = '\x86' }
        'x64'   = @{ Bin = '\HostX64';   Native = '\x64' }
        'arm'   = @{ Bin = '\HostARM';   Native = '\arm' }
        'arm64' = @{ Bin = '\HostARM64'; Native = '\arm64' }
    }
    $tgtMap  = @{ 'x86' = '\x86'; 'x64' = '\x64'; 'arm' = '\ARM'; 'arm64' = '\ARM64' }

    $hInfo   = $hostMap[$script:HostArchE]
    $tgtDir  = $tgtMap[$script:TgtArch]
    $specDir = if ($VcVarsSpectreLibs -eq 'spectre') { '\spectre' } else { '' }

    if (-not $hInfo -or -not $tgtDir) {
        Write-Host "[ERROR:VsDevCmd.ps1] Unsupported host=$script:HostArchE / target=$script:TgtArch"
        $script:_errCount++; return
    }

    $binDir    = "$($hInfo.Bin)$tgtDir"
    $nativeBin = "$($hInfo.Bin)$($hInfo.Native)"

    $env:Platform = $script:TgtArch
    if ($script:HostArchE -ne $script:TgtArch) {
        $env:CommandPromptType = 'Cross'
        $env:PreferredToolArchitecture = if ($script:HostArchE -eq 'x64') { 'x64' } else { $null }
    } else {
        $env:CommandPromptType = 'Native'
        $env:PreferredToolArchitecture = $null
    }

    $extSdk = "${env:ProgramFiles}\Microsoft SDKs\Windows Kits\10\ExtensionSDKs"
    if (-not (Test-Path $extSdk)) {
        $extSdk = "${env:ProgramFiles(x86)}\Microsoft SDKs\Windows Kits\10\ExtensionSDKs"
    }
    if (Test-Path $extSdk) { $env:ExtensionSdkDir = $extSdk }

    AddTo-Path "$script:VSInstall\Common7\IDE\VC\VCPackages"

    if ($env:CommandPromptType -eq 'Cross') {
        AddTo-Path "$vcToolsDir\bin$nativeBin"
    }
    AddTo-Path "$vcToolsDir\bin$binDir"

    AddTo-Var '_VCVARS_INC' "$script:VSInstall\VC\Auxiliary\VS\include"
    AddTo-Var '_VCVARS_INC' "$vcToolsDir\ATLMFC\include"
    AddTo-Var '_VCVARS_INC' "$vcToolsDir\include"

    AddTo-LibPath "$vcToolsDir\lib\x86\store\references"

    if ($AppPlatform -eq 'Desktop') {
        $vcLib  = "$vcToolsDir\lib$specDir$tgtDir"
        $atlLib = "$vcToolsDir\ATLMFC\lib$specDir$tgtDir"
        AddTo-Lib     $vcLib
        AddTo-Lib     $atlLib
        AddTo-LibPath $vcLib
        AddTo-LibPath $atlLib
    }

    if ($AppPlatform -eq 'UWP' -and $script:WinSdkDir -and ($script:WinSdkDir -notmatch '8\.1')) {
        AddTo-Lib "$vcToolsDir\lib$tgtDir\store\"
        if ($env:ExtensionSdkDir) {
            AddTo-LibPath "$($env:ExtensionSdkDir)\Microsoft.VCLibs\14.0\References\CommonConfiguration\neutral"
        }
    }

    $ifcPath = "$vcToolsDir\ifc$tgtDir"
    if ((-not $env:IFCPATH) -and (Test-Path $ifcPath)) { $env:IFCPATH = $ifcPath }
}

# ============================================================================
# EXT: .NET FX SDK — OPT #5: reduce version fallback chain, use cache
# ============================================================================
function Invoke-ExtNetFxSdk {
    if ($NoExt) { return }
    Write-Dbg 2 "Ext: .NET Framework SDK"

    $archKey = if ([Environment]::Is64BitProcess) { 'X64' } else { 'X86' }
    $script:NFX_SdkDir = $null
    $script:NFX_ExeX86 = $null
    $script:NFX_ExeX64 = $null

    # OPT #5: Aggressive early-exit. Each Test-Path on a missing registry key
    # costs ~78ms. Original probed 4 bases × 8 versions = 32 keys per run.
    # BuildTools has zero .NETFX SDK keys → 32 × 78ms = 2.5s wasted.
    # Strategy: probe only the 2 most recent versions on the primary base.
    # If the primary base has no keys, skip all others (not a full VS install).

    # Primary base only (HKLM Wow6432Node for x64, HKLM native for x86)
    $primaryBase = if ($archKey -eq 'X86') {
        'HKLM:\SOFTWARE\Microsoft\Microsoft SDKs\NETFXSDK'
    } else {
        'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\NETFXSDK'
    }

    # Only probe the 2 most common versions; if neither exists, this isn't a
    # full VS install and no NETFX SDK keys will exist anywhere.
    foreach ($v in @('4.8.1', '4.8')) {
        $all = Get-RegValuesAll "$primaryBase\$v"
        if ($all.Count -eq 0) { continue }
        if ($all['KitsInstallationFolder']) {
            $script:NFX_SdkDir = $all['KitsInstallationFolder']
        }
        $script:NFX_ExeX86 = Get-RegValue "$primaryBase\$v\WinSDK-NetFx40Tools-x86" 'InstallationFolder'
        $script:NFX_ExeX64 = Get-RegValue "$primaryBase\$v\WinSDK-NetFx40Tools-x64" 'InstallationFolder'
        if ($script:NFX_SdkDir) { break }
    }

    # BuildTools / non-full-VS: skip the exhaustive fallback chain.
    # If primary base had nothing, HKCU and other paths won't either.
    # Only probe fallback (Win 8.1A SDK) if x86/x64 tools still missing.
    if (-not $script:NFX_ExeX86 -and -not $script:NFX_ExeX64) {
        $fbKey = if ($archKey -eq 'X86') {
            'HKLM:\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1A'
        } else {
            'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1A'
        }
        $script:NFX_ExeX86 = Get-RegValue "$fbKey\WinSDK-NetFx40Tools-x86" 'InstallationFolder'
        $script:NFX_ExeX64 = Get-RegValue "$fbKey\WinSDK-NetFx40Tools-x64" 'InstallationFolder'
    }

    $env:NETFXSDKDir = $script:NFX_SdkDir

    $nfxTgt = switch ($script:TgtArch) {
        'x86' { '\x86' }; 'x64' { '\x64' }; 'arm' { '\arm' }; 'arm64' { '\arm64' }
    }

    if ($script:NFX_SdkDir) {
        if (Test-Path "$($script:NFX_SdkDir)include\um") {
            AddTo-Var '_NETFX_INC' "$($script:NFX_SdkDir)include\um"
        }
        if ($nfxTgt -and (Test-Path "$($script:NFX_SdkDir)lib\um$nfxTgt")) {
            AddTo-Lib "$($script:NFX_SdkDir)lib\um$nfxTgt"
        }
    }

    if ($script:HostArchE -eq 'x86' -and $script:NFX_ExeX86) {
        AddTo-Path $script:NFX_ExeX86
    } elseif ($script:HostArchE -in @('x64', 'arm64') -and $script:NFX_ExeX64) {
        AddTo-Path $script:NFX_ExeX64
    }
}

# ============================================================================
# EXT: Roslyn
# ============================================================================
function Invoke-ExtRoslyn {
    if ($NoExt) { return }
    Write-Dbg 2 "Ext: Roslyn"
    AddTo-Path "$script:VSInstall\MSBuild\Current\bin\Roslyn"
}

# ============================================================================
# Run Extensions — with profiling
# ============================================================================
Enter-Phase "Ext: .NET Framework SDK"
Invoke-ExtNetFxSdk
Exit-Phase

Enter-Phase "Ext: Roslyn"
Invoke-ExtRoslyn
Exit-Phase

Enter-Phase "Ext: VCVars"
Invoke-ExtVCVars
Exit-Phase

# ============================================================================
# Final Environment Assembly — OPT #6: direct variable read, no pipeline
# ============================================================================
Enter-Phase "Final assembly"

$vcInc    = Get-Variable -Name '_VCVARS_INC' -ValueOnly -Scope Script -ErrorAction SilentlyContinue
$wsInc    = Get-Variable -Name '_WINSDK_INC' -ValueOnly -Scope Script -ErrorAction SilentlyContinue
$nfxInc   = Get-Variable -Name '_NETFX_INC'  -ValueOnly -Scope Script -ErrorAction SilentlyContinue
$parts = @()
if ($vcInc)  { $parts += $vcInc }
if ($wsInc)  { $parts += $wsInc }
if ($nfxInc) { $parts += $nfxInc }
$incStr = $parts -join ';'
if ($incStr) {
    $env:INCLUDE          = "$incStr;$env:INCLUDE"
    $env:EXTERNAL_INCLUDE = "$incStr;$env:EXTERNAL_INCLUDE"
}

Remove-Variable -Name '_VCVARS_INC' -Scope Script -ErrorAction SilentlyContinue
Remove-Variable -Name '_WINSDK_INC' -Scope Script -ErrorAction SilentlyContinue
Remove-Variable -Name '_NETFX_INC'  -Scope Script -ErrorAction SilentlyContinue

# OPT #6: foreach instead of pipeline ForEach-Object
foreach ($v in @('PATH','INCLUDE','LIB','LIBPATH','EXTERNAL_INCLUDE')) {
    Normalize-PathVar $v
}

Exit-Phase

# ============================================================================
# Start Directory
# ============================================================================
if ($StartDir -eq 'none') {
    # stay put
} elseif ($StartDir -eq 'auto') {
    if ($env:VSCMD_START_DIR -and (Test-Path $env:VSCMD_START_DIR)) {
        Set-Location $env:VSCMD_START_DIR
    } elseif (Test-Path "$env:USERPROFILE\Source") {
        Set-Location "$env:USERPROFILE\Source"
    }
} elseif ($StartDir) {
    if (Test-Path $StartDir) { Set-Location $StartDir }
} elseif ($env:VSCMD_START_DIR) {
    Set-Location $env:VSCMD_START_DIR
}

# ============================================================================
# Result
# ============================================================================
if ($script:_errCount -gt 0) {
    Write-Host "[ERROR:VsDevCmd.ps1] *** $($script:_errCount) error(s). Environment may be incomplete. ***"
    Write-Host "[ERROR:VsDevCmd.ps1] Set `$env:VSCMD_DEBUG=1/2/3 and re-run for details."
    Show-Profile
    exit 1
} else {
    Write-Dbg 1 "VsDevCmd.ps1 completed successfully."
    Save-RegCache $script:VSInstall
    Show-Profile
}

```

Cmd 版

```cmd
@echo off
REM ============================================================================
REM VsDevCmd.cmd — MSVC development environment initialization
REM
REM Automatically detects Visual Studio installation, Windows SDK, VC++ toolset,
REM .NET Framework SDK, and Roslyn, then sets up PATH, INCLUDE, LIB, LIBPATH,
REM and all relevant environment variables for command-line C/C++ development.
REM
REM Inspired by VsDevCmd.ps1, optimized for batch speed.
REM
REM Usage: call VsDevCmd.cmd [arch] [hostarch] [winsdk] [/noext] [/nologo]
REM
REM   arch      Target architecture: x86 | x64 | arm | arm64   (default = native)
REM   hostarch  Host architecture                               (default = arch)
REM   winsdk    Windows SDK version, "8.1", or "none"           (default = latest)
REM   /noext    Skip optional extensions (VCVars, .NET SDK, Roslyn)
REM   /nologo   Suppress banner
REM   /cleanenv Start from clean environment
REM   /test     Validate configuration and exit
REM
REM Examples:
REM   call VsDevCmd.cmd                        (native development)
REM   call VsDevCmd.cmd x64                    (x64 target, x64 host)
REM   call VsDevCmd.cmd x64 x86                (x64 target, x86 host — cross)
REM   call VsDevCmd.cmd arm64                  (ARM64 native)
REM ============================================================================
REM NOTE: No SETLOCAL at top level — all variable changes persist in caller.
REM Subroutines use SETLOCAL/ENDLOCAL only when needed.
REM ============================================================================

set "__ERR=0"
set "__NOEXT=0"
set "__NOLOGO=0"
set "__CLEAN_ENV=0"
set "__TEST_MODE=0"
set "__HELP=0"
set "__WINSDK_VER="
set "__APP_PLATFORM=Desktop"
set "__VCVARS_VER="
set "__SPECTRE="

REM === Argument Parsing ===
set "__TGT_ARCH="
set "__HOST_ARCH="

:parse_args
if "%~1"=="" goto :parse_done

for %%a in (x86 amd64 x64 arm arm64) do if /i "%~1"=="%%a" (
    if not defined __TGT_ARCH (
        set "__TGT_ARCH=%%a" & shift & goto :parse_args
    )
    if not defined __HOST_ARCH (
        set "__HOST_ARCH=%%a" & shift & goto :parse_args
    )
    shift & goto :parse_args
)

if /i "%~1"=="/noext"       set "__NOEXT=1"      & shift & goto :parse_args
if /i "%~1"=="/nologo"      set "__NOLOGO=1"      & shift & goto :parse_args
if /i "%~1"=="/cleanenv"    set "__CLEAN_ENV=1"   & shift & goto :parse_args
if /i "%~1"=="/test"        set "__TEST_MODE=1"   & shift & goto :parse_args
if /i "%~1"=="/?"           set "__HELP=1"        & shift & goto :parse_args
if /i "%~1"=="/help"        set "__HELP=1"        & shift & goto :parse_args
if /i "%~1"=="-?"           set "__HELP=1"        & shift & goto :parse_args
if not defined __WINSDK_VER  set "__WINSDK_VER=%~1" & shift & goto :parse_args
shift & goto :parse_args
:parse_done

if "%__HELP%"=="1" (
    echo VsDevCmd.cmd - MSVC development environment initialization
    echo.
    echo Usage: call VsDevCmd.cmd [arch] [hostarch] [winsdk] [/noext] [/nologo]
    echo.
    echo   arch      Target architecture: x86 ^| x64 ^| arm ^| arm64   (default = native^)
    echo   hostarch  Host architecture                                 (default = arch^)
    echo   winsdk    Windows SDK version or "8.1" / "none"             (default = latest^)
    echo   /noext    Skip optional extensions
    echo   /nologo   Suppress banner
    echo   /cleanenv Start from clean environment
    echo   /test     Validate configuration and exit
    goto :eof
)

REM Normalize arch aliases
if /i "%__TGT_ARCH%"=="amd64" set "__TGT_ARCH=x64"
if /i "%__HOST_ARCH%"=="amd64" set "__HOST_ARCH=x64"

REM Detect current process architecture
set "__CURRENT_ARCH=x86"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64"  set "__CURRENT_ARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64"  set "__CURRENT_ARCH=arm64"
if defined PROCESSOR_ARCHITEW6432 if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" set "__CURRENT_ARCH=x64"

if not defined __TGT_ARCH set "__TGT_ARCH=%__CURRENT_ARCH%"
if not defined __HOST_ARCH (
    set "__HOST_ARCH=%__TGT_ARCH%"
    if /i "%__HOST_ARCH%"=="amd64" set "__HOST_ARCH=x64"
)

REM Validate architectures
set "__VALID=0"
for %%v in (x86 x64 arm arm64) do if /i "%__TGT_ARCH%"=="%%v" set "__VALID=1"
if "%__VALID%"=="0" (echo [ERROR] Unknown target arch: %__TGT_ARCH% & set "__ERR=1" & goto :finish)

set "__VALID=0"
for %%v in (x86 x64 arm arm64) do if /i "%__HOST_ARCH%"=="%%v" set "__VALID=1"
if "%__VALID%"=="0" (echo [ERROR] Unknown host arch: %__HOST_ARCH% & set "__ERR=1" & goto :finish)

if /i "%__HOST_ARCH%"=="arm64" if /i "%__TGT_ARCH%"=="x86" (
    echo [ERROR] arm64 host cannot target x86
    set "__ERR=1" & goto :finish
)

call :find_vs
if "%__ERR%"=="1" goto :finish

if "%__CLEAN_ENV%"=="1" call :clean_env
if "%__TEST_MODE%"=="1" call :run_test & goto :finish
if "%__NOLOGO%"=="0"   call :print_banner

call :set_root_vars
call :core_dotnet
call :core_msbuild
call :core_build_tools
call :core_winsdk
if "%__NOEXT%"=="0" (
    call :ext_netfxsdk
    call :ext_roslyn
    call :ext_vcvars
)
call :assemble_include
call :normalize_paths
goto :finish


REM ============================================================================
REM Subroutines
REM ============================================================================


:find_vs
set "__VS_TOOLSDIR="
set "__VS_INSTALL="
set "__VS_SEMVER="

REM 1) VS180COMNTOOLS env var
if defined VS180COMNTOOLS (
    set "__CAND=%VS180COMNTOOLS%"
    call set "_LAST=%%__CAND:~-1%%"
    if "%_LAST%"=="\" set "__CAND=%__CAND:~0,-1%"
    if exist "%__CAND%\VsDevCmd.bat" (
        for %%p in ("%__CAND%\..\..") do set "__VS_INSTALL=%%~fp\"
        set "__VS_TOOLSDIR=%__CAND%\"
        goto :vs_found
    )
)

REM 2) vswhere
set "__VSW=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%__VSW%" (
    for /f "usebackq tokens=*" %%a in (`"%__VSW%" -latest -products * -property installationPath 2^>nul`) do set "__VP=%%a"
    if defined __VP (
        for /f "usebackq tokens=*" %%a in (`"%__VSW%" -latest -products * -property catalog_productSemanticVersion 2^>nul`) do set "__VS_SEMVER=%%a"
        if exist "%__VP%\Common7\Tools\VsDevCmd.bat" (
            set "__VS_TOOLSDIR=%__VP%\Common7\Tools\"
            set "__VS_INSTALL=%__VP%\"
            goto :vs_found
        )
    )
)

REM 3) Registry — try both 32/64 bit views
set "__VP="
for %%r in (
    "HKLM\SOFTWARE\Microsoft\VisualStudio\SxS\VS7"
    "HKLM\SOFTWARE\Wow6432Node\Microsoft\VisualStudio\SxS\VS7"
) do if not defined __VP (
    for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r" /v "18.0" 2^>nul ^| findstr /i "REG_SZ"') do set "__VP=%%b"
)
if defined __VP (
    call set "_LAST=%%__VP:~-1%%"
    if "%_LAST%"=="\" set "__VP=%__VP:~0,-1%"
    if exist "%__VP%\Common7\Tools\VsDevCmd.bat" (
        set "__VS_TOOLSDIR=%__VP%\Common7\Tools\"
        set "__VS_INSTALL=%__VP%\"
        goto :vs_found
    )
)

REM 4) Known paths
for %%d in (
    "%ProgramFiles(x86)%\Microsoft Visual Studio\18\BuildTools\Common7\Tools"
    "%ProgramFiles%\Microsoft Visual Studio\18\Enterprise\Common7\Tools"
    "%ProgramFiles%\Microsoft Visual Studio\18\Professional\Common7\Tools"
    "%ProgramFiles%\Microsoft Visual Studio\18\Community\Common7\Tools"
) do if exist "%%~d\VsDevCmd.bat" for %%p in ("%%~d\..\..") do (
    set "__VS_INSTALL=%%~fp\"
    set "__VS_TOOLSDIR=%%~d\"
    goto :vs_found
)

REM 5) VS160COMNTOOLS (VS 2019 fallback)
if defined VS160COMNTOOLS (
    set "__CAND=%VS160COMNTOOLS%"
    call set "_LAST=%%__CAND:~-1%%"
    if "%_LAST%"=="\" set "__CAND=%__CAND:~0,-1%"
    if exist "%__CAND%\VsDevCmd.bat" (
        for %%p in ("%__CAND%\..\..") do set "__VS_INSTALL=%%~fp\"
        set "__VS_TOOLSDIR=%__CAND%\"
        goto :vs_found
    )
)

echo [ERROR] Cannot locate Visual Studio installation.
echo         Install Visual Studio 2022 (or 2019) with "Desktop development with C++" workload.
set "__ERR=1"
goto :eof

:vs_found
echo [OK] Visual Studio: %__VS_INSTALL%
goto :eof


:clean_env
set "PATH="
set "INCLUDE="
set "LIB="
set "LIBPATH="
set "EXTERNAL_INCLUDE="
goto :eof


:run_test
setlocal enabledelayedexpansion
echo VsDevCmd.cmd — Configuration Test
echo =================================
echo Target arch:  %__TGT_ARCH%
echo Host arch:    %__HOST_ARCH%
echo VS install:   %__VS_INSTALL%
echo VS tools:     %__VS_TOOLSDIR%
if defined __VS_SEMVER echo VS version:  %__VS_SEMVER%
echo.
echo Variables set by this script:
set VS 2>nul | findstr /b "VS"
set VSCMD 2>nul | findstr /b "VSCMD"
set WindowsSdk 2>nul | findstr /b "WindowsSdk"
set WindowsSDK 2>nul | findstr /b "WindowsSDK"
set UCRT 2>nul | findstr /b "UCRT"
echo.
echo PATH = %%PATH%%
endlocal
goto :eof


:print_banner
echo.
echo **********************************************************************
echo ** Visual Studio 2022 Developer Command Prompt
if defined __VS_SEMVER echo ** Version %__VS_SEMVER%
echo ** Target: %__TGT_ARCH%, Host: %__HOST_ARCH%
echo **********************************************************************
echo.
goto :eof


:set_root_vars
set "VS180COMNTOOLS=%__VS_TOOLSDIR%"
set "VSINSTALLDIR=%__VS_INSTALL%"
set "PATH=%__VS_TOOLSDIR%;%PATH%"

set "__DEVENV=%__VS_INSTALL%Common7\IDE\"
if exist "%__DEVENV%" (
    set "DevEnvDir=%__DEVENV%"
    set "PATH=%__DEVENV%;%PATH%"
)
set "VisualStudioVersion=18.0"
if defined __VS_SEMVER (
    set "VSCMD_VER=%__VS_SEMVER%"
) else (
    set "VSCMD_VER=18.0"
)
goto :eof


:core_dotnet
set "__FW_PREF=64"
if /i "%__HOST_ARCH%"=="x86" set "__FW_PREF=32"

set "__FW_DIR32=C:\Windows\Microsoft.NET\Framework"
set "__FW_DIR64=C:\Windows\Microsoft.NET\Framework64"
set "__FW_VER32=v4.0.30319"
set "__FW_VER64=v4.0.30319"

REM Try registry overrides from VS
for %%r in (
    "HKLM\SOFTWARE\Microsoft\VisualStudio\SxS\VC7"
    "HKLM\SOFTWARE\Wow6432Node\Microsoft\VisualStudio\SxS\VC7"
) do for %%a in (FrameworkDir32 FrameworkDir64 FrameworkVer32 FrameworkVer64) do (
    for /f "skip=2 tokens=2,*" %%x in ('reg query "%%~r" /v "%%a" 2^>nul ^| findstr /i "REG_SZ"') do (
        if "%%a"=="FrameworkDir32" set "__FW_DIR32=%%y"
        if "%%a"=="FrameworkDir64" set "__FW_DIR64=%%y"
        if "%%a"=="FrameworkVer32" set "__FW_VER32=%%y"
        if "%%a"=="FrameworkVer64" set "__FW_VER64=%%y"
    )
)

if "%__FW_PREF%"=="64" (set "__FD=%__FW_DIR64%" & set "__FV=%__FW_VER64%") else (set "__FD=%__FW_DIR32%" & set "__FV=%__FW_VER32%")

if not defined __FD goto :eof
call set "_LAST=%%__FD:~-1%%"
if "%_LAST%"=="\" set "__FD=%__FD:~0,-1%"
set "PATH=%__FD%\%__FV%;%PATH%"
set "LIBPATH=%__FD%\%__FV%;%LIBPATH%"
goto :eof


:core_msbuild
set "__MSB_SUB=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "__MSB_SUB=arm64"
if exist "%__VS_INSTALL%MSBuild\Current\Bin\%__MSB_SUB%\" (
    set "PATH=%__VS_INSTALL%MSBuild\Current\Bin\%__MSB_SUB%;%PATH%"
)
goto :eof


:core_build_tools
if exist "%__VS_INSTALL%Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\" (
    set "PATH=%__VS_INSTALL%Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"
)
if exist "%__VS_INSTALL%Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\" (
    set "PATH=%__VS_INSTALL%Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
)
if exist "%__VS_INSTALL%VC\vcpkg\vcpkg.exe" (
    set "PATH=%__VS_INSTALL%VC\vcpkg;%PATH%"
)
goto :eof


:core_winsdk
if /i "%__WINSDK_VER%"=="none" goto :eof

set "__WSDK_DIR="
set "__WSDK_VERSION="
set "__WSDK_BIN="
set "__WSDK_VERBIN="
set "__WSDK_LIBVER=winv6.3\"
set "__WSDK_LIBPATH="
set "__WINSDK_INC="
set "__UCRT_DIR="
set "__UCRT_VER="

REM Find Windows 10 SDK
set "__FOUND=0"
for %%b in (
    "HKLM\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v10.0"
    "HKCU\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v10.0"
    "HKLM\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v10.0"
    "HKCU\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v10.0"
) do if "%__FOUND%"=="0" (
    set "__SD="
    if defined __SD (
        call :_trim_trailing_backslash __SD
        if exist "%__SD%\include" (
            for /f "delims=" %%v in ('dir /b /ad "%__SD%\include" 2^>nul ^| findstr /r "^10\.[0-9]*\.[0-9]*\.[0-9]*$"') do (
                call :_check_winsdk "%__SD%" "%%v"
            )
        )
    )
)

if "%__FOUND%"=="0" call :find_win81sdk

REM Fallback: probe known SDK paths when registry has no record
if "%__FOUND%"=="0" call :find_winsdk_fallback

REM Find Universal CRT
for %%b in (
    "HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows Kits\Installed Roots"
    "HKCU\SOFTWARE\Wow6432Node\Microsoft\Windows Kits\Installed Roots"
    "HKLM\SOFTWARE\Microsoft\Windows Kits\Installed Roots"
    "HKCU\SOFTWARE\Microsoft\Windows Kits\Installed Roots"
) do if not defined __UCRT_DIR (
    set "__UK="
    for /f "skip=2 tokens=2,*" %%x in ('reg query "%%~b" /v "KitsRoot10" 2^>nul ^| findstr /i "REG_SZ"') do set "__UK=%%y"
    if defined __UK (
        call :_trim_trailing_backslash __UK
        if exist "%__UK%\Lib" (
            set "__UCRT_DIR=%__UK%"
            for /f "delims=" %%v in ('dir /b /ad "%__UK%\Lib" 2^>nul ^| findstr /r "^10\."') do (
                if exist "%__UK%\Lib\%%v\ucrt\%__TGT_ARCH%\ucrt.lib" set "__UCRT_VER=%%v"
            )
        )
    )
)

REM Fallback: probe known UCRT paths
if not defined __UCRT_DIR call :find_ucrt_fallback

REM Export Windows SDK
if defined __WSDK_BIN (
    set "PATH=%__WSDK_BIN%%__HOST_ARCH%;%PATH%"
)
if defined __WSDK_VERBIN (
    set "PATH=%__WSDK_VERBIN%\%__HOST_ARCH%;%PATH%"
)
if defined __WSDK_DIR if defined __WSDK_LIBVER (
    set "LIB=%__WSDK_DIR%\lib\%__WSDK_LIBVER%um\%__TGT_ARCH%;%LIB%"
)
call :_append_winsdk_inc
if defined __WSDK_LIBPATH (
    set "LIBPATH=%__WSDK_LIBPATH%;%LIBPATH%"
)
if defined __UCRT_VER if defined __UCRT_DIR (
    set "__WINSDK_INC=%__WINSDK_INC%;%__UCRT_DIR%\include\%__UCRT_VER%\ucrt"
    set "LIB=%__UCRT_DIR%\lib\%__UCRT_VER%\ucrt\%__TGT_ARCH%;%LIB%"
)

set "WindowsSdkDir=%__WSDK_DIR%"
set "WindowsSDKVersion=%__WSDK_VERSION%"
set "WindowsSDKLibVersion=%__WSDK_LIBVER%"
set "WindowsSdkBinPath=%__WSDK_BIN%"
if defined __WSDK_VERBIN set "WindowsSdkVerBinPath=%__WSDK_VERBIN%"
if defined __WSDK_LIBPATH set "WindowsLibPath=%__WSDK_LIBPATH%"
set "UCRTVersion=%__UCRT_VER%"
set "UniversalCRTSdkDir=%__UCRT_DIR%"
goto :eof


:_append_winsdk_inc
if not defined __WSDK_DIR goto :eof
if not defined __WSDK_VERSION goto :eof
set "__WINSDK_INC=%__WSDK_DIR%\include\%__WSDK_VERSION%um"
set "__WINSDK_INC=%__WINSDK_INC%;%__WSDK_DIR%\include\%__WSDK_VERSION%shared"
set "__WINSDK_INC=%__WINSDK_INC%;%__WSDK_DIR%\include\%__WSDK_VERSION%winrt"
set "__WINSDK_INC=%__WINSDK_INC%;%__WSDK_DIR%\include\%__WSDK_VERSION%cppwinrt"
goto :eof


:_check_winsdk
set "__SD=%~1"
set "__WV=%~2"
set "__CHECK=winsdkver.h"
if /i "%__APP_PLATFORM%"=="UWP" set "__CHECK=Windows.h"
if exist "%__SD%\include\%__WV%\um\%__CHECK%" (
    set "__WSDK_DIR=%__SD%"
    set "__WSDK_VERSION=%__WV%\"
    set "__WSDK_LIBVER=%__WV%\"
    set "__WSDK_BIN=%__SD%\bin\"
    if exist "%__SD%\bin\%__WV%\" set "__WSDK_VERBIN=%__SD%\bin\%__WV%"
    if exist "%__SD%\UnionMetadata\%__WV%" (
        set "__WSDK_LIBPATH=%__SD%\UnionMetadata\%__WV%;%__SD%\References\%__WV%"
    ) else (
        set "__WSDK_LIBPATH=%__SD%\UnionMetadata;%__SD%\References"
    )
    set "__FOUND=1"
)
goto :eof
:_trim_trailing_backslash
set "__VAR=%~1"
call set "__VAL=%%%__VAR%%%"
if not defined __VAL goto :eof
call set "_LAST=%%__VAL:~-1%%"
if "%_LAST%"=="\" call set "%__VAR%=%%__VAL:~0,-1%%"
goto :eof


:find_win81sdk
for %%b in (
    "HKLM\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1"
    "HKCU\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1"
    "HKLM\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1"
    "HKCU\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1"
) do if not defined __WSDK_DIR (
    set "__SD="
    for /f "skip=2 tokens=2,*" %%x in ('reg query "%%~b" /v "InstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__SD=%%y"
    if defined __SD (
        call :_trim_trailing_backslash __SD
        set "__WSDK_DIR=%__SD%"
        set "__WSDK_LIBVER=winv6.3\"
        set "__WSDK_BIN=%__SD%\bin\"
        set "__WSDK_LIBPATH=%__SD%\References\CommonConfiguration\Neutral"
    )
)
goto :eof


:find_winsdk_fallback
REM Check known SDK paths directly (when registry has no record)
if "%__FOUND%"=="1" goto :eof
for %%p in (
    "%ProgramFiles(x86)%\Windows Kits\10"
    "%ProgramFiles%\Windows Kits\10"
    "C:\Program Files (x86)\Windows Kits\10"
    "C:\Program Files\Windows Kits\10"
) do if "%__FOUND%"=="0" (
    if exist "%%~p\include" (
        for /f "delims=" %%v in ('dir /b /ad "%%~p\include" 2^>nul ^| findstr /r "^10\.[0-9]*\.[0-9]*\.[0-9]*$"') do (
            call :_check_winsdk "%%~p" "%%v"
        )
    )
)
goto :eof


:find_ucrt_fallback
for %%p in (
    "%ProgramFiles(x86)%\Windows Kits\10"
    "%ProgramFiles%\Windows Kits\10"
    "C:\Program Files (x86)\Windows Kits\10"
    "C:\Program Files\Windows Kits\10"
) do if not defined __UCRT_DIR (
    set "__UK=%%~p"
    if exist "%%~p\Lib" (
        set "__UCRT_DIR=%%~p"
        for /f "delims=" %%v in ('dir /b /ad "%%~p\Lib" 2^>nul ^| findstr /r "^10\."') do (
            if exist "%%~p\Lib\%%v\ucrt\%__TGT_ARCH%\ucrt.lib" set "__UCRT_VER=%%v"
        )
    )
)
goto :eof


:ext_netfxsdk
set "__NFX_DIR="
set "__NFX_X86="
set "__NFX_X64="

for %%v in (4.8.1 4.8) do if not defined __NFX_DIR (
    for %%r in (
        "HKLM\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\NETFXSDK\%%v"
        "HKLM\SOFTWARE\Microsoft\Microsoft SDKs\NETFXSDK\%%v"
    ) do if not defined __NFX_DIR (
        set "__NK="
        for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r" /v "KitsInstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__NK=%%b"
        if defined __NK (
            call set "_LAST=%%__NK:~-1%%"
            if "%_LAST%"=="\" set "__NK=%__NK:~0,-1%"
            set "__NFX_DIR=%__NK%"
        )
        for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r\WinSDK-NetFx40Tools-x86" /v "InstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__NFX_X86=%%b"
        for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r\WinSDK-NetFx40Tools-x64" /v "InstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__NFX_X64=%%b"
    )
)

REM Fallback: Windows 8.1A SDK tools
if not defined __NFX_X86 if not defined __NFX_X64 (
    for %%r in (
        "HKLM\SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v8.1A"
        "HKLM\SOFTWARE\Microsoft\Microsoft SDKs\Windows\v8.1A"
    ) do (
        for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r\WinSDK-NetFx40Tools-x86" /v "InstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__NFX_X86=%%b"
        for /f "skip=2 tokens=2,*" %%a in ('reg query "%%~r\WinSDK-NetFx40Tools-x64" /v "InstallationFolder" 2^>nul ^| findstr /i "REG_SZ"') do set "__NFX_X64=%%b"
    )
)

set "NETFXSDKDir=%__NFX_DIR%"

set "__NFX_TGT="
if /i "%__TGT_ARCH%"=="x86"   set "__NFX_TGT=\x86"
if /i "%__TGT_ARCH%"=="x64"   set "__NFX_TGT=\x64"
if /i "%__TGT_ARCH%"=="arm"   set "__NFX_TGT=\arm"
if /i "%__TGT_ARCH%"=="arm64" set "__NFX_TGT=\arm64"

if defined __NFX_DIR (
    if exist "%__NFX_DIR%include\um" (
        set "__NETFX_INC=%__NFX_DIR%include\um"
    )
    if defined __NFX_TGT if exist "%__NFX_DIR%lib\um%__NFX_TGT%" (
        set "LIB=%__NFX_DIR%lib\um%__NFX_TGT%;%LIB%"
    )
)

if /i "%__HOST_ARCH%"=="x86" (
    if defined __NFX_X86 set "PATH=%__NFX_X86%;%PATH%"
) else (
    if defined __NFX_X64 set "PATH=%__NFX_X64%;%PATH%"
)
goto :eof


:ext_roslyn
if exist "%__VS_INSTALL%MSBuild\Current\bin\Roslyn\" (
    set "PATH=%__VS_INSTALL%MSBuild\Current\bin\Roslyn;%PATH%"
)
goto :eof


:ext_vcvars
set "__VC_DIR=%__VS_INSTALL%VC\"
if not exist "%__VC_DIR%" goto :eof

set "VCINSTALLDIR=%__VC_DIR%"
set "VCIDEInstallDir=%__VS_INSTALL%Common7\IDE\VC\"

REM Resolve toolset version
set "__VC_VER=%__VCVARS_VER%"
if not defined __VC_VER if defined VCToolsVersion set "__VC_VER=%VCToolsVersion%"

if not defined __VC_VER set "__BUILD_DIR=%__VC_DIR%Auxiliary\Build"
if not defined __VC_VER if exist "%__BUILD_DIR%\Microsoft.VCToolsVersion.v145.default.txt" (
    for /f "usebackq delims=" %%a in ("%__BUILD_DIR%\Microsoft.VCToolsVersion.v145.default.txt") do set "__VC_VER=%%a"
)
if not defined __VC_VER if exist "%__BUILD_DIR%\Microsoft.VCToolsVersion.default.txt" (
    for /f "usebackq delims=" %%a in ("%__BUILD_DIR%\Microsoft.VCToolsVersion.default.txt") do set "__VC_VER=%%a"
)

if not defined __VC_VER goto :eof
set "__VC_TOOLS=%__VC_DIR%Tools\MSVC\%__VC_VER%\"
if not exist "%__VC_TOOLS%" goto :eof

set "VCToolsInstallDir=%__VC_TOOLS%"
set "VCToolsVersion=%__VC_VER%"

REM Redist version
if exist "%__VC_DIR%Auxiliary\Build\Microsoft.VCRedistVersion.default.txt" (
    for /f "usebackq delims=" %%a in ("%__VC_DIR%Auxiliary\Build\Microsoft.VCRedistVersion.default.txt") do set "__RV=%%a"
    if defined __RV if exist "%__VC_DIR%Redist\MSVC\%__RV%\" (
        set "VCToolsRedistDir=%__VC_DIR%Redist\MSVC\%__RV%\"
    )
)

REM Architecture maps
set "__HOST_BIN="
set "__HOST_NATIVE="
set "__TGT_DIR="
if /i "%__HOST_ARCH%"=="x86"   set "__HOST_BIN=\HostX86"   & set "__HOST_NATIVE=\x86"
if /i "%__HOST_ARCH%"=="x64"   set "__HOST_BIN=\HostX64"   & set "__HOST_NATIVE=\x64"
if /i "%__HOST_ARCH%"=="arm"   set "__HOST_BIN=\HostARM"   & set "__HOST_NATIVE=\arm"
if /i "%__HOST_ARCH%"=="arm64" set "__HOST_BIN=\HostARM64" & set "__HOST_NATIVE=\arm64"
if /i "%__TGT_ARCH%"=="x86"   set "__TGT_DIR=\x86"
if /i "%__TGT_ARCH%"=="x64"   set "__TGT_DIR=\x64"
if /i "%__TGT_ARCH%"=="arm"   set "__TGT_DIR=\ARM"
if /i "%__TGT_ARCH%"=="arm64" set "__TGT_DIR=\ARM64"

if not defined __HOST_BIN goto :eof
if not defined __TGT_DIR goto :eof

set "__SPECTRE_DIR="
if /i "%__SPECTRE%"=="spectre" set "__SPECTRE_DIR=\spectre"

REM Platform variables
set "Platform=%__TGT_ARCH%"
if /i not "%__HOST_ARCH%"=="%__TGT_ARCH%" (
    set "CommandPromptType=Cross"
    if /i "%__HOST_ARCH%"=="x64" (set "PreferredToolArchitecture=x64") else (set "PreferredToolArchitecture=")
) else (
    set "CommandPromptType=Native"
    set "PreferredToolArchitecture="
)

REM Extension SDK dir
set "__EXT_SDK=%ProgramFiles%\Microsoft SDKs\Windows Kits\10\ExtensionSDKs"
if not exist "%__EXT_SDK%\" (
    set "__EXT_SDK=%ProgramFiles(x86)%\Microsoft SDKs\Windows Kits\10\ExtensionSDKs"
)
if exist "%__EXT_SDK%\" set "ExtensionSdkDir=%__EXT_SDK%"

REM VCPackages
if exist "%__VS_INSTALL%Common7\IDE\VC\VCPackages\" (
    set "PATH=%__VS_INSTALL%Common7\IDE\VC\VCPackages;%PATH%"
)

REM Bin directories
if "%CommandPromptType%"=="Cross" (
    set "PATH=%__VC_TOOLS%bin%__HOST_NATIVE%;%PATH%"
)
set "PATH=%__VC_TOOLS%bin%__HOST_BIN%%__TGT_DIR%;%PATH%"

REM Includes
set "__VCVARS_INC=%__VS_INSTALL%VC\Auxiliary\VS\include"
set "__VCVARS_INC=%__VCVARS_INC%;%__VC_TOOLS%ATLMFC\include"
set "__VCVARS_INC=%__VCVARS_INC%;%__VC_TOOLS%include"

REM LIBPATH
set "LIBPATH=%__VC_TOOLS%lib\x86\store\references;%LIBPATH%"

REM LIB
if /i "%__APP_PLATFORM%"=="Desktop" (
    set "LIB=%__VC_TOOLS%lib%__SPECTRE_DIR%%__TGT_DIR%;%__VC_TOOLS%ATLMFC\lib%__SPECTRE_DIR%%__TGT_DIR%;%LIB%"
    set "LIBPATH=%__VC_TOOLS%lib%__SPECTRE_DIR%%__TGT_DIR%;%__VC_TOOLS%ATLMFC\lib%__SPECTRE_DIR%%__TGT_DIR%;%LIBPATH%"
)

REM IFC path
set "__IFC=%__VC_TOOLS%ifc%__TGT_DIR%"
if not defined IFCPATH if exist "%__IFC%" set "IFCPATH=%__IFC%"
goto :eof

:assemble_include
set "INCLUDE=%__VCVARS_INC%"
if defined __WINSDK_INC set "INCLUDE=%INCLUDE%;%__WINSDK_INC%"
if defined __NETFX_INC set "INCLUDE=%INCLUDE%;%__NETFX_INC%"
goto :eof


:normalize_paths
REM Skip PATH dedup (too long, duplicates harmless). Only dedup short vars.
for %%v in (INCLUDE LIB LIBPATH EXTERNAL_INCLUDE) do call :dedup_path %%v
goto :eof


:dedup_path
set "__V=%~1"
call set "__P=%%%__V%%%"
if not defined __P goto :eof

:dedup_loop
set "__O=%__P%"
set "__P=%__P:;;=;%"
if "%__P%"=="%__O%" goto :dedup_check_end
goto :dedup_loop

:dedup_check_end
REM Remove trailing ;
call set "_LAST_P=%%__P:~-1%%"
if "%_LAST_P%"==";" set "__P=%__P:~0,-1%"
REM Remove leading ;
call set "_FIRST_P=%%__P:~0,1%%"
if "%_FIRST_P%"==";" set "__P=%__P:~1%"
if not "%_LAST_P%"==";" if not "%_FIRST_P%"==";" goto :dedup_apply

:dedup_collapse
set "__O=%__P%"
set "__P=%__P:;;=;%"
if not "%__P%"=="%__O%" goto :dedup_collapse
call set "_LAST_P2=%%__P:~-1%%"
call set "_FIRST_P2=%%__P:~0,1%%"
if "%_LAST_P2%"==";" set "__P=%__P:~0,-1%"
if "%_FIRST_P2%"==";" set "__P=%__P:~1%"

:dedup_apply
call set "%__V%=%__P%"
goto :eof


:finish
set "__TMPF=%TEMP%\_vsdevcmd_export.bat"
if exist "%__TMPF%" del "%__TMPF%" 2>nul

REM Write each variable individually — avoids 8191-char block limit
> "%__TMPF%" echo @echo off
>> "%__TMPF%" echo set "PATH=%PATH%"
>> "%__TMPF%" echo set "INCLUDE=%INCLUDE%"
>> "%__TMPF%" echo set "LIB=%LIB%"
>> "%__TMPF%" echo set "LIBPATH=%LIBPATH%"
if defined EXTERNAL_INCLUDE >> "%__TMPF%" echo set "EXTERNAL_INCLUDE=%EXTERNAL_INCLUDE%"
if defined VS180COMNTOOLS >> "%__TMPF%" echo set "VS180COMNTOOLS=%VS180COMNTOOLS%"
if defined VSINSTALLDIR >> "%__TMPF%" echo set "VSINSTALLDIR=%VSINSTALLDIR%"
if defined DevEnvDir >> "%__TMPF%" echo set "DevEnvDir=%DevEnvDir%"
if defined VisualStudioVersion >> "%__TMPF%" echo set "VisualStudioVersion=%VisualStudioVersion%"
if defined VSCMD_VER >> "%__TMPF%" echo set "VSCMD_VER=%VSCMD_VER%"
if defined VCINSTALLDIR >> "%__TMPF%" echo set "VCINSTALLDIR=%VCINSTALLDIR%"
if defined VCIDEInstallDir >> "%__TMPF%" echo set "VCIDEInstallDir=%VCIDEInstallDir%"
if defined VCToolsInstallDir >> "%__TMPF%" echo set "VCToolsInstallDir=%VCToolsInstallDir%"
if defined VCToolsVersion >> "%__TMPF%" echo set "VCToolsVersion=%VCToolsVersion%"
if defined VCToolsRedistDir >> "%__TMPF%" echo set "VCToolsRedistDir=%VCToolsRedistDir%"
if defined Platform >> "%__TMPF%" echo set "Platform=%Platform%"
if defined CommandPromptType >> "%__TMPF%" echo set "CommandPromptType=%CommandPromptType%"
if defined PreferredToolArchitecture >> "%__TMPF%" echo set "PreferredToolArchitecture=%PreferredToolArchitecture%"
if defined WindowsSdkDir >> "%__TMPF%" echo set "WindowsSdkDir=%WindowsSdkDir%"
if defined WindowsSDKVersion >> "%__TMPF%" echo set "WindowsSDKVersion=%WindowsSDKVersion%"
if defined WindowsSDKLibVersion >> "%__TMPF%" echo set "WindowsSDKLibVersion=%WindowsSDKLibVersion%"
if defined WindowsSdkBinPath >> "%__TMPF%" echo set "WindowsSdkBinPath=%WindowsSdkBinPath%"
if defined WindowsSdkVerBinPath >> "%__TMPF%" echo set "WindowsSdkVerBinPath=%WindowsSdkVerBinPath%"
if defined WindowsLibPath >> "%__TMPF%" echo set "WindowsLibPath=%WindowsLibPath%"
if defined UCRTVersion >> "%__TMPF%" echo set "UCRTVersion=%UCRTVersion%"
if defined UniversalCRTSdkDir >> "%__TMPF%" echo set "UniversalCRTSdkDir=%UniversalCRTSdkDir%"
if defined ExtensionSdkDir >> "%__TMPF%" echo set "ExtensionSdkDir=%ExtensionSdkDir%"
if defined IFCPATH >> "%__TMPF%" echo set "IFCPATH=%IFCPATH%"
if defined NETFXSDKDir >> "%__TMPF%" echo set "NETFXSDKDir=%NETFXSDKDir%"

endlocal

call "%TEMP%\_vsdevcmd_export.bat" 2>nul
del "%TEMP%\_vsdevcmd_export.bat" 2>nul

REM Clean up internal vars (prefix __)
for /f "delims==" %%v in ('set __ 2^>nul') do set "%%v="
goto :eof

```

# windows powershell → pwsh

修改 `$USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`

```powershell
$pwshDir = "$env:USERPROFILE\Applications\PowerShell7"
$pwshExe = "$pwshDir\pwsh.exe"

if (Test-Path -LiteralPath $pwshExe) {
    # Inject into PATH so future pwsh calls work within the session
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Process")
    if ($currentPath -notlike "*$pwshDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$pwshDir;$currentPath", "Process")
    }

    $host.UI.RawUI.WindowTitle = "PowerShell 7 (pwsh)"
    # Capture launch directory: prefer -WorkingDirectory from right-click
    # since Get-Location doesn't respect it on some systems
    $cmdArgs = [Environment]::GetCommandLineArgs()
    $wdIdx = [array]::IndexOf($cmdArgs, '-WorkingDirectory')
    if ($wdIdx -ge 0 -and $wdIdx -lt $cmdArgs.Length - 1) {
        $currentDir = $cmdArgs[$wdIdx + 1]
    } else {
        $currentDir = (Get-Location).Path
    }
    & $pwshExe -NoLogo -NoExit -WorkingDirectory $currentDir
    exit
}

```