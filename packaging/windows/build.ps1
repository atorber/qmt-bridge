# QMT Bridge Windows 打包脚本
# 生成不依赖本机 Python 的便携目录，并在已安装 Inno Setup 6 时编译安装包。
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Arch x64
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Arch arm64
#
# 可选参数:
#   -Arch x64|arm64   默认随本机架构
#   -PythonVersion 3.12.10
#   -SkipInstaller
#   -SkipXtquant

param(
    [string]$Arch = "",
    [string]$PythonVersion = "3.12.10",
    [switch]$SkipInstaller,
    [switch]$SkipXtquant
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$PackagingDir = $PSScriptRoot
$Root = (Resolve-Path (Join-Path $PackagingDir "..\..")).Path
$Dist = Join-Path $PackagingDir "dist"
$Cache = Join-Path $Dist "cache"
$Portable = Join-Path $Dist "portable"
$Runtime = Join-Path $Portable "runtime"

function Get-RepoVersion {
    $versionFile = Join-Path $Root "src\qmt_bridge\_version.py"
    $text = Get-Content -Path $versionFile -Raw -Encoding UTF8
    if ($text -match '__version__\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    throw "无法从 src\qmt_bridge\_version.py 读取版本号"
}

function Get-DefaultArch {
    try {
        $osArch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        if ($osArch -match "Arm") {
            return "arm64"
        }
        return "x64"
    }
    catch {
        if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
            return "arm64"
        }
        return "x64"
    }
}

function Get-RemoteFile {
    param([string]$Url, [string]$Destination)
    if (Test-Path $Destination) {
        Write-Host "已缓存: $Destination"
        return
    }
    Write-Host "下载 $Url"
    $tmp = "$Destination.partial"
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing
    Move-Item -Force $tmp $Destination
}

function Write-PythonPth {
    param([string]$RuntimeDir, [string]$ShortVersion)
    $pthName = "python$($ShortVersion.Replace('.', ''))._pth"
    $pth = Join-Path $RuntimeDir $pthName
    if (-not (Test-Path $pth)) {
        $pth = Get-ChildItem $RuntimeDir -Filter "python*._pth" | Select-Object -First 1
        if (-not $pth) {
            throw "未找到 embeddable Python 的 ._pth 文件"
        }
        $pth = $pth.FullName
    }
    $zipName = [System.IO.Path]::GetFileNameWithoutExtension($pth) + ".zip"
    @"
$zipName
.
Lib\site-packages
import site
"@ | Set-Content -Path $pth -Encoding ASCII
}

function Find-Csc {
    $candidates = @(
        (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe")
    )
    foreach ($item in $candidates) {
        if ($item -and (Test-Path $item)) {
            return $item
        }
    }
    $cmd = Get-Command csc.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $null
}

function Find-ISCC {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    foreach ($item in $candidates) {
        if ($item -and (Test-Path $item)) {
            return $item
        }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $null
}

function Compile-Launcher {
    param(
        [string]$OutputExe,
        [string]$IconPath,
        [string]$SourceFile = "Launcher.cs",
        [ValidateSet("winexe", "exe")]
        [string]$Target = "winexe"
    )
    $source = Join-Path $PackagingDir $SourceFile
    if (-not (Test-Path $source)) {
        throw "启动器源码不存在: $source"
    }
    $csc = Find-Csc
    if ($csc) {
        # AnyCPU：x64 / ARM64 上都能拉起同目录的 python(w).exe
        $args = @(
            "/nologo",
            "/target:$Target",
            "/platform:anycpu",
            "/out:$OutputExe"
        )
        if ($Target -eq "winexe") {
            $args += "/r:System.Windows.Forms.dll"
            $args += "/r:System.Drawing.dll"
        }
        if ($IconPath -and (Test-Path $IconPath)) {
            $args += "/win32icon:$IconPath"
        }
        $args += $source
        & $csc @args
        if ($LASTEXITCODE -ne 0) {
            throw "csc 编译启动器失败: $SourceFile"
        }
        return
    }

    Write-Host "未找到 csc.exe，改用 Add-Type 编译启动器 ($SourceFile)"
    $code = Get-Content -Path $source -Raw -Encoding UTF8
    if ($Target -eq "winexe") {
        $refs = @("System.dll", "System.Windows.Forms.dll", "System.Drawing.dll")
        Add-Type -TypeDefinition $code -ReferencedAssemblies $refs -OutputAssembly $OutputExe -OutputType WindowsApplication
    }
    else {
        $refs = @("System.dll")
        Add-Type -TypeDefinition $code -ReferencedAssemblies $refs -OutputAssembly $OutputExe -OutputType ConsoleApplication
    }
}

if (-not $Arch) {
    $Arch = Get-DefaultArch
}
if ($Arch -notin @("x64", "arm64")) {
    throw "不支持的 -Arch: $Arch（仅 x64 / arm64）"
}
$ArchTag = if ($Arch -eq "arm64") { "arm-win" } else { "x86-win" }
$EmbedSuffix = if ($Arch -eq "arm64") { "arm64" } else { "amd64" }
if ($Arch -eq "arm64") {
    $SkipXtquant = $true
}

$Version = Get-RepoVersion
Write-Host "QMT Bridge $Version  Windows 打包 ($Arch / $ArchTag)"

New-Item -ItemType Directory -Force -Path $Cache | Out-Null
if (Test-Path $Portable) {
    Remove-Item -Recurse -Force $Portable
}
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

$pyParts = $PythonVersion.Split(".")
$shortVersion = "$($pyParts[0]).$($pyParts[1])"
$embedZipName = "python-$PythonVersion-embed-$EmbedSuffix.zip"
$embedZip = Join-Path $Cache $embedZipName
$embedUrl = "https://www.python.org/ftp/python/$PythonVersion/$embedZipName"
Get-RemoteFile -Url $embedUrl -Destination $embedZip

Write-Host "解压嵌入式 Python ($embedZipName)"
Expand-Archive -Path $embedZip -DestinationPath $Runtime -Force
Write-PythonPth -RuntimeDir $Runtime -ShortVersion $shortVersion

$getPip = Join-Path $Cache "get-pip.py"
Get-RemoteFile -Url "https://bootstrap.pypa.io/get-pip.py" -Destination $getPip
Copy-Item $getPip (Join-Path $Runtime "get-pip.py") -Force

$embedPython = Join-Path $Runtime "python.exe"
if (-not (Test-Path $embedPython)) {
    throw "嵌入式 Python 缺少 python.exe"
}

# 禁止写入/读取用户 site-packages，避免本机已装包导致便携运行时缺依赖
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = ""
$env:PIP_USER = "0"

Write-Host "安装 pip"
& $embedPython (Join-Path $Runtime "get-pip.py") --no-warn-script-location --disable-pip-version-check --no-user
if ($LASTEXITCODE -ne 0) {
    throw "get-pip 失败"
}

Write-Host "安装 setuptools / wheel（嵌入式环境默认无构建后端）"
& $embedPython -m pip install --no-warn-script-location --disable-pip-version-check --no-user setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "安装 setuptools/wheel 失败"
}

$req = Join-Path $PackagingDir "requirements.txt"
Write-Host "安装桌面运行时依赖"
& $embedPython -m pip install --no-warn-script-location --disable-pip-version-check --no-user --prefer-binary -r $req
if ($LASTEXITCODE -ne 0) {
    throw "安装 Python 依赖失败"
}

# 可选加速依赖：无对应平台 wheel 时跳过，不影响服务启动
Write-Host "尝试安装可选依赖 httptools / watchfiles"
& $embedPython -m pip install --no-warn-script-location --disable-pip-version-check --no-user --prefer-binary httptools watchfiles
if ($LASTEXITCODE -ne 0) {
    Write-Warning "httptools/watchfiles 未能安装（常见于 win_arm64），已跳过。"
}

if (-not $SkipXtquant) {
    Write-Host "尝试安装 xtquant（失败则跳过，运行时会探测 QMT 自带路径）"
    & $embedPython -m pip install --no-warn-script-location --disable-pip-version-check --no-user --prefer-binary xtquant
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "xtquant 未能通过 pip 安装，客户机仍可通过本机 QMT 探测使用。"
    }
}
else {
    Write-Host "已跳过 xtquant（$Arch 无官方 wheel，运行时探测 QMT 路径）"
}

$sitePackages = Join-Path $Runtime "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
$packageDest = Join-Path $sitePackages "qmt_bridge"
if (Test-Path $packageDest) {
    Remove-Item -Recurse -Force $packageDest
}
Write-Host "复制 qmt_bridge 源码到运行时"
Copy-Item -Recurse (Join-Path $Root "src\qmt_bridge") $packageDest

Write-Host "生成图标"
& $embedPython -c "from pathlib import Path; from qmt_bridge.desktop.icon import write_icon_files; write_icon_files(Path(r'$PackagingDir'))"
if ($LASTEXITCODE -ne 0) {
    throw "生成图标失败"
}

$iconIco = Join-Path $PackagingDir "qmt-bridge.ico"
$launcher = Join-Path $Portable "QMTBridge.exe"
Write-Host "编译 QMTBridge.exe"
Compile-Launcher -OutputExe $launcher -IconPath $iconIco -SourceFile "Launcher.cs" -Target winexe

$cliExe = Join-Path $Portable "qmt-server.exe"
Write-Host "编译 qmt-server.exe (CLI)"
Compile-Launcher -OutputExe $cliExe -IconPath $iconIco -SourceFile "ServerCli.cs" -Target exe

$licenseSrc = Join-Path $Root "LICENSE"
if (Test-Path $licenseSrc) {
    Copy-Item $licenseSrc (Join-Path $Portable "LICENSE.txt")
}

$archHint = if ($Arch -eq "arm64") {
    "当前包为 Windows ARM64。券商 miniQMT / xtquant 目前多为 x64，ARM 设备连交易请优先用 x86-win（x64）安装包（系统会模拟运行）。"
}
else {
    "当前包为 Windows x64（x86-win）。ARM 电脑也可安装本包（系统模拟运行），以便对接 miniQMT。"
}

$readme = @"
QMT Bridge $Version ($ArchTag)

客户机不需要安装 Python。$archHint

【桌面控制面板】
1. 先安装券商 miniQMT，勾选「独立交易」并保持登录
2. 双击 QMTBridge.exe
3. 在打开的窗口中确认端口 / 路径，点击「启动」
4. 浏览器打开文档地址（默认 http://127.0.0.1:8000/docs）

【命令行 CLI】
也可直接运行同目录的 qmt-server.exe（参数与 pip 版 qmt-server 相同），例如：
  qmt-server.exe --port 8000 --trading
  qmt-server.exe --help

配置与日志在: %APPDATA%\QMT Bridge\
关闭窗口后程序仍在托盘运行；退出请用托盘菜单「退出」。
"@
$readmePath = Join-Path $Portable "使用说明.txt"
$utf8Bom = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText($readmePath, $readme, $utf8Bom)

# ---- CLI 专用便携包（仅 runtime + qmt-server.exe，可单独拷贝使用）----
$CliPortable = Join-Path $Dist "cli-portable"
if (Test-Path $CliPortable) {
    Remove-Item -Recurse -Force $CliPortable
}
New-Item -ItemType Directory -Force -Path $CliPortable | Out-Null
Write-Host "组装 CLI 便携目录"
Copy-Item -Recurse $Runtime (Join-Path $CliPortable "runtime")
Copy-Item $cliExe (Join-Path $CliPortable "qmt-server.exe")
if (Test-Path $licenseSrc) {
    Copy-Item $licenseSrc (Join-Path $CliPortable "LICENSE.txt")
}
$cliReadme = @"
QMT Bridge CLI $Version ($ArchTag)

免安装 Python。解压后直接运行：

  qmt-server.exe
  qmt-server.exe --port 8000 --trading --api-key your-key
  qmt-server.exe --help

请先安装并登录券商 miniQMT（独立交易）。
配置以命令行参数为准，例如 --port / --trading / --api-key；
当前目录若有 .env 仅作缺省补充（不会覆盖已传参数）。
$archHint

勿只拷贝 qmt-server.exe：必须与 runtime\ 目录放在一起。
"@
[System.IO.File]::WriteAllText((Join-Path $CliPortable "使用说明.txt"), $cliReadme, $utf8Bom)

$innoAllowed = if ($Arch -eq "arm64") { "arm64" } else { "x64compatible" }
@"
#define MyAppVersion "$Version"
#define MyArchTag "$ArchTag"
#define MyArchitecturesAllowed "$innoAllowed"
#define MyArchitecturesInstallMode "$innoAllowed"
"@ | Set-Content -Path (Join-Path $PackagingDir "_version.iss") -Encoding ASCII

$zipPath = Join-Path $Dist "QMTBridge-$Version-$ArchTag.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath
}
Write-Host "压缩桌面便携包 $zipPath"
Compress-Archive -Path (Join-Path $Portable "*") -DestinationPath $zipPath

$cliZipPath = Join-Path $Dist "QMTBridge-CLI-$Version-$ArchTag.zip"
if (Test-Path $cliZipPath) {
    Remove-Item $cliZipPath
}
Write-Host "压缩 CLI 便携包 $cliZipPath"
Compress-Archive -Path (Join-Path $CliPortable "*") -DestinationPath $cliZipPath

$installer = Join-Path $Dist "QMTBridge-Setup-$Version-$ArchTag.exe"
if (-not $SkipInstaller) {
    $iscc = Find-ISCC
    if ($iscc) {
        Write-Host "编译 Inno Setup 安装包"
        & $iscc (Join-Path $PackagingDir "QMTBridge.iss")
        if ($LASTEXITCODE -ne 0) {
            throw "ISCC 编译失败"
        }
        if (-not (Test-Path $installer)) {
            throw "未生成安装包: $installer"
        }
    }
    else {
        Write-Warning "未检测到 Inno Setup 6，已跳过 Setup.exe。安装后重新运行本脚本即可生成安装包："
        Write-Warning "https://jrsoftware.org/isinfo.php"
        $installer = $null
    }
}

Write-Host ""
Write-Host "完成。"
Write-Host "架构:     $Arch ($ArchTag)"
Write-Host "便携目录: $Portable"
Write-Host "ZIP:      $zipPath"
Write-Host "CLI 目录: $CliPortable"
Write-Host "CLI ZIP:  $cliZipPath"
if ($installer -and (Test-Path $installer)) {
    Write-Host "安装包:   $installer"
}
Write-Host "请先在本机验证 QMTBridge.exe / qmt-server.exe。"
