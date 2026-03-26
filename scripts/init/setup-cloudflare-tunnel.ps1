<#
.SYNOPSIS
    Cloudflare Tunnel 安裝與配置腳本

.DESCRIPTION
    1. 下載安裝 cloudflared
    2. 使用 token 安裝為 Windows 服務
    3. 驗證連線

.EXAMPLE
    .\scripts\init\setup-cloudflare-tunnel.ps1

.NOTES
    Tunnel ID: e66a0acc-7940-4b54-ac75-ca3923e652d0
    Domain: cksurvey.cloudflareaccess.com
    需以系統管理員身份執行 (安裝服務)

Version: 1.0.0
Created: 2026-03-26
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

Write-Host "=== Cloudflare Tunnel 安裝 ===" -ForegroundColor Cyan

# 1. 檢查 cloudflared
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Write-Host "cloudflared 未安裝，開始下載..." -ForegroundColor Yellow
    $msiUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi"
    $msiPath = Join-Path $env:TEMP "cloudflared-windows-amd64.msi"

    Write-Host "下載: $msiUrl" -ForegroundColor Gray
    Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing

    Write-Host "安裝 MSI..." -ForegroundColor Green
    Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /quiet" -Wait -NoNewWindow
    Write-Host "安裝完成" -ForegroundColor Green

    # 重新檢查
    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cloudflared) {
        Write-Host "ERROR: 安裝後仍找不到 cloudflared，請手動安裝" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "cloudflared 已安裝: $(cloudflared version)" -ForegroundColor Green
}

# 2. 讀取 token
$envPath = Join-Path $ProjectRoot ".env"
$token = ""
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath
    foreach ($line in $envContent) {
        if ($line -match "^CLOUDFLARE_TUNNEL_TOKEN=(.+)$") {
            $token = $Matches[1].Trim()
        }
    }
}

if (-not $token) {
    Write-Host "ERROR: .env 中未找到 CLOUDFLARE_TUNNEL_TOKEN" -ForegroundColor Red
    exit 1
}

# 3. 安裝為 Windows 服務
Write-Host ""
Write-Host "安裝 Cloudflare Tunnel 為 Windows 服務..." -ForegroundColor Yellow
Write-Host "  (需要系統管理員權限)" -ForegroundColor Gray

try {
    cloudflared service install $token
    Write-Host "服務安裝成功!" -ForegroundColor Green
} catch {
    Write-Host "服務安裝失敗: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "替代方案 — 手動啟動:" -ForegroundColor Yellow
    Write-Host "  cloudflared tunnel run --token <token>" -ForegroundColor White
    Write-Host "  或使用: .\scripts\dev\start-tunnel.ps1" -ForegroundColor White
}

# 4. 顯示配置資訊
Write-Host ""
Write-Host "=== 配置摘要 ===" -ForegroundColor Cyan
Write-Host "  Tunnel ID:  e66a0acc-7940-4b54-ac75-ca3923e652d0" -ForegroundColor White
Write-Host "  Domain:     cksurvey.cloudflareaccess.com" -ForegroundColor White
Write-Host ""
Write-Host "  Webhook URLs:" -ForegroundColor Green
Write-Host "    LINE:    https://cksurvey.cloudflareaccess.com/api/line/webhook" -ForegroundColor Cyan
Write-Host "    Discord: https://cksurvey.cloudflareaccess.com/api/discord/webhook" -ForegroundColor Cyan
Write-Host "    Health:  https://cksurvey.cloudflareaccess.com/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "  下一步:" -ForegroundColor Yellow
Write-Host "    1. 在 Cloudflare Dashboard 設定 Public Hostname → http://localhost:8001" -ForegroundColor White
Write-Host "    2. 在 LINE Developers Console 設定 Webhook URL" -ForegroundColor White
Write-Host "    3. 在 Discord Developer Portal 設定 Interactions Endpoint URL" -ForegroundColor White
