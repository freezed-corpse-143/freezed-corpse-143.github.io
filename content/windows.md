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

# 默认