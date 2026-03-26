<#
.SYNOPSIS
    Cloudflare Tunnel / ngrok 啟動腳本

.DESCRIPTION
    優先使用 Cloudflare Tunnel，回退到 ngrok。
    Quick Tunnel 模式自動取得 URL 並寫入 .env。

.PARAMETER Mode
    tunnel 模式: "cloudflare" (預設) 或 "ngrok"

.PARAMETER Port
    後端 port (預設 8001)

.EXAMPLE
    .\scripts\dev\start-tunnel.ps1
    .\scripts\dev\start-tunnel.ps1 -Mode ngrok
    .\scripts\dev\start-tunnel.ps1 -Port 8001

Version: 1.1.0
Created: 2026-03-25
#>

param(
    [ValidateSet("cloudflare", "ngrok")]
    [string]$Mode = "cloudflare",
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$EnvPath = Join-Path $ProjectRoot ".env"

function Update-EnvVar {
    param([string]$Key, [string]$Value)
    if (-not (Test-Path $EnvPath)) { return }
    $content = Get-Content $EnvPath -Raw
    if ($content -match "(?m)^$Key=.*$") {
        $content = $content -replace "(?m)^$Key=.*$", "$Key=$Value"
    } else {
        $content += "`n$Key=$Value"
    }
    Set-Content $EnvPath -Value $content -NoNewline
    Write-Host "  .env 已更新: $Key=$Value" -ForegroundColor Gray
}

function Show-WebhookUrls {
    param([string]$BaseUrl)
    Write-Host ""
    Write-Host "=== Webhook URLs ===" -ForegroundColor Green
    Write-Host "  LINE:    $BaseUrl/api/line/webhook" -ForegroundColor Cyan
    Write-Host "  Discord: $BaseUrl/api/discord/webhook" -ForegroundColor Cyan
    Write-Host "  Health:  $BaseUrl/api/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "請將 URL 設定到 LINE Developers Console / Discord Developer Portal" -ForegroundColor Yellow

    Update-EnvVar "WEBHOOK_BASE_URL" $BaseUrl
}

Write-Host "=== CK_Missive Tunnel ===" -ForegroundColor Cyan
Write-Host "模式: $Mode | Port: $Port" -ForegroundColor Yellow

# ── Cloudflare ──

if ($Mode -eq "cloudflare") {
    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cloudflared) {
        Write-Host "cloudflared 未安裝。安裝: winget install Cloudflare.cloudflared" -ForegroundColor Red
        Write-Host "回退到 ngrok..." -ForegroundColor Yellow
        $Mode = "ngrok"
    } else {
        # 讀取 .env 中的 token
        $tunnelToken = ""
        if (Test-Path $EnvPath) {
            $envContent = Get-Content $EnvPath
            foreach ($line in $envContent) {
                if ($line -match "^CLOUDFLARE_TUNNEL_TOKEN=(.+)$") {
                    $tunnelToken = $Matches[1].Trim()
                }
            }
        }

        if ($tunnelToken) {
            # Token-based Tunnel (推薦，Cloudflare Dashboard 設定路由)
            Write-Host "啟動 Token-based Tunnel..." -ForegroundColor Green
            Show-WebhookUrls "https://cksurvey.cloudflareaccess.com"
            cloudflared tunnel run --token $tunnelToken
        } elseif (Test-Path (Join-Path $ProjectRoot "configs\cloudflare-tunnel.yml")) {
            # Named Tunnel (有 config)
            $configPath = Join-Path $ProjectRoot "configs\cloudflare-tunnel.yml"
            Write-Host "啟動 Named Tunnel (配置: $configPath)" -ForegroundColor Green
            Show-WebhookUrls "https://cksurvey.cloudflareaccess.com"
            cloudflared tunnel --config $configPath run
        } else {
            # Quick Tunnel (背景啟動 + 解析 URL)
            Write-Host "啟動 Quick Tunnel..." -ForegroundColor Green
            $logFile = Join-Path $env:TEMP "cloudflared-quicktunnel.log"

            # 背景啟動，log 到暫存檔
            $proc = Start-Process cloudflared `
                -ArgumentList "tunnel --url http://localhost:$Port --metrics localhost:33939" `
                -RedirectStandardError $logFile `
                -PassThru -NoNewWindow

            # 等待 URL 出現在 metrics
            $attempts = 0
            $tunnelUrl = ""
            while ($attempts -lt 15 -and -not $tunnelUrl) {
                Start-Sleep -Seconds 2
                $attempts++
                try {
                    # cloudflared metrics 提供 tunnel info
                    $logContent = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
                    if ($logContent -match "(https://[a-z0-9\-]+\.trycloudflare\.com)") {
                        $tunnelUrl = $Matches[1]
                    }
                } catch {}
            }

            if ($tunnelUrl) {
                Show-WebhookUrls $tunnelUrl
                Write-Host "Tunnel PID: $($proc.Id) | Ctrl+C 停止" -ForegroundColor Gray
                Write-Host ""
                # 前景等待
                $proc.WaitForExit()
            } else {
                Write-Host "無法取得 Quick Tunnel URL (${attempts}s timeout)" -ForegroundColor Red
                Write-Host "請查看 log: $logFile" -ForegroundColor Gray
                if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id }
            }
        }
        return
    }
}

# ── ngrok fallback ──

if ($Mode -eq "ngrok") {
    $ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
    if (-not $ngrok) {
        Write-Host "ngrok 未安裝。" -ForegroundColor Red
        exit 1
    }

    Write-Host "啟動 ngrok tunnel..." -ForegroundColor Green

    Start-Process ngrok -ArgumentList "http $Port" -NoNewWindow -PassThru | Out-Null
    Start-Sleep -Seconds 3

    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 5
        $publicUrl = $tunnels.tunnels[0].public_url
        Show-WebhookUrls $publicUrl
    } catch {
        Write-Host "無法取得 ngrok URL，請檢查 http://localhost:4040" -ForegroundColor Red
    }
}
