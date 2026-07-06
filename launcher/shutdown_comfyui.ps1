<#
.SYNOPSIS
    检测 ComfyUI 服务器是否正在运行，并询问用户是否关闭。
.DESCRIPTION
    通过检查默认端口 (8188) 和常见进程名来定位 ComfyUI 服务进程。
    如果有多个候选进程，只会定位到实际占用端口的那个。
#>

$ErrorActionPreference = "Stop"

# ============================================================
# 配置
# ============================================================
$DefaultPort = 8188
$ComfyUIRoot = $PSScriptRoot | Split-Path -Parent

# ============================================================
# 辅助函数
# ============================================================
function Write-Step { param($Text) Write-Host "`n>>> $Text" -ForegroundColor Cyan }
function Write-OK   { param($Text) Write-Host "    v $Text" -ForegroundColor Green }
function Write-Warn { param($Text) Write-Host "    ! $Text" -ForegroundColor Yellow }
function Write-Err  { param($Text) Write-Host "    x $Text" -ForegroundColor Red }

# ============================================================
# 1. 通过端口查找占用进程
# ============================================================
Write-Step "检查端口 $DefaultPort 占用情况..."

$portConnection = Get-NetTCPConnection -LocalPort $DefaultPort -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq 'Listen' } |
    Select-Object -First 1

if (-not $portConnection) {
    Write-OK "端口 $DefaultPort 未被占用 — ComfyUI 未运行。"
    exit 0
}

$portPid = $portConnection.OwningProcess
Write-Warn "端口 $DefaultPort 被进程 PID=$portPid 占用"

# ============================================================
# 2. 获取占用端口的进程详情
# ============================================================
$proc = Get-Process -Id $portPid -ErrorAction SilentlyContinue

if (-not $proc) {
    Write-Err "无法获取 PID=$portPid 的进程信息（可能已退出或权限不足）。"
    exit 1
}

$procName   = $proc.ProcessName
$procPath   = try { $proc.MainModule.FileName } catch { $null }
$cmdLine    = try { (Get-CimInstance Win32_Process -Filter "ProcessId=$portPid" | Select-Object -First 1).CommandLine } catch { $null }
$startTime  = $proc.StartTime.ToString("yyyy-MM-dd HH:mm:ss")
$cpuTime    = $proc.TotalProcessorTime

Write-Host ""
Write-Host "  PID       : $portPid"
Write-Host "  进程名    : $procName"
Write-Host "  可执行文件: $(if ($procPath) { $procPath } else { '(未知 — 可能需管理员权限)' })"
Write-Host "  启动时间  : $startTime"
Write-Host "  CPU 时间  : $([math]::Round($cpuTime.TotalMinutes, 1)) 分钟"
if ($cmdLine) { Write-Host "  命令行    : $cmdLine" }

# ============================================================
# 3. 验证是否为 ComfyUI 进程
# ============================================================
$isComfyUI = $false

# 方法 A：命令行中包含 ComfyUI 关键字
if ($cmdLine -match "ComfyUI|main\.py|server\.py") {
    $isComfyUI = $true
}

# 方法 B：可执行文件路径在 ComfyUI 目录下
if ($procPath -and $procPath.StartsWith($ComfyUIRoot, [StringComparison]::OrdinalIgnoreCase)) {
    $isComfyUI = $true
}

# 方法 C：进程名为 python 且监听 8188 端口（强信号）
if ($procName -eq "python" -or $procName -eq "python.exe" -or $procName -eq "pythonw.exe") {
    $isComfyUI = $true
}

if (-not $isComfyUI) {
    Write-Err "PID=$portPid 占用了 ComfyUI 默认端口，但无法确认它是 ComfyUI 进程。"
    Write-Host "  如需强制关闭，请手动运行: Stop-Process -Id $portPid -Force"
    exit 1
}

Write-OK "确认为 ComfyUI 服务进程"

# ============================================================
# 4. 询问用户
# ============================================================
Write-Host ""
$choice = Read-Host "是否关闭该 ComfyUI 进程？[Y/n]"

if ($choice -eq '' -or $choice -match '^[Yy]') {
    Write-Step "正在终止进程 PID=$portPid ..."
    try {
        Stop-Process -Id $portPid -Force
        Write-OK "进程已终止"

        # 确认端口已释放
        Start-Sleep -Milliseconds 500
        $still = Get-NetTCPConnection -LocalPort $DefaultPort -ErrorAction SilentlyContinue |
            Where-Object { $_.State -eq 'Listen' }
        if (-not $still) {
            Write-OK "端口 $DefaultPort 已释放"
        } else {
            Write-Warn "端口似乎仍被占用，请稍候再试"
        }
    } catch {
        Write-Err "无法终止进程: $_"
        Write-Host "  请尝试以管理员身份运行本脚本，或手动执行:"
        Write-Host "  Stop-Process -Id $portPid -Force"
        exit 1
    }
} else {
    Write-Host "已取消，ComfyUI 仍在运行。"
}
