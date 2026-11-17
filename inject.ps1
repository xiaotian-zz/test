# 一键部署 + 注入
# 用法：进入游戏并站在挪威海后，右键“使用 PowerShell 运行”
$ErrorActionPreference = 'Stop'
$bundle = Join-Path $PSScriptRoot 'xmas_clone13'
$data = 'F:\RF4\Game\rf4_x64_Data\Data'

if (!(Test-Path $data)) {
    Write-Host "找不到游戏 Data 目录: $data" -ForegroundColor Red
    Write-Host "如果你的游戏不在 F 盘，请修改本脚本里的 `$data 变量"
    exit 1
}

Copy-Item $bundle $data -Force
Write-Host "已复制 xmas_clone13 到 $data" -ForegroundColor Green

$p = Get-Process rf4_x64 -ErrorAction SilentlyContinue |
     Where-Object { $_.Threads.Count -gt 3 } |
     Select-Object -First 1

if (!$p) {
    Write-Host "游戏进程未运行，请先启动游戏并进入挪威海" -ForegroundColor Red
    exit 1
}

Write-Host "检测到游戏进程 PID=$($p.Id)，开始注入..." -ForegroundColor Cyan
py -3.12 (Join-Path $PSScriptRoot 'scripts\frida_spawn_shop.py') $p.Id
