# Safe Restart Script — pm2 restart ck-backend with LINE pre-notify
#
# 使用：
#   .\scripts\dev\safe-restart.ps1                  # 預設提前 5 秒
#   .\scripts\dev\safe-restart.ps1 -GraceSeconds 10 # 延長提前通知
#   .\scripts\dev\safe-restart.ps1 -SkipNotify      # 不發 LINE（緊急用）
#
# 流程：
#   1. 發 LINE 通知「將於 N 秒後重啟，預計 downtime 12-15 秒」
#   2. 等候 GraceSeconds 秒（讓 admin 完成手上動作）
#   3. pm2 restart ck-backend
#   4. 輪詢 /api/health 直到 200（最多 30s）
#   5. 發 LINE 通知「已恢復」
#
# 對應問題：
#   pm2 restart 期間（10-15s）用戶看到 ERR_CONNECTION_REFUSED
#   前端 retry 退避 13s 涵蓋大部分情況，但用戶體感仍有「卡頓」
#   本腳本：用 LINE 預警 + 健康輪詢回報，把「卡頓」變「預期」

param(
    [int]$GraceSeconds = 5,
    [switch]$SkipNotify,
    [string]$Reason = "手動 restart"
)

$BACKEND_URL = "http://127.0.0.1:8001/api/health"
$MAX_HEALTH_WAIT = 30  # 秒

# 強制 UTF-8（避免 cp950 中文亂碼）
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Send-LineNotify {
    param([string]$Message)
    if ($SkipNotify) { return }
    try {
        $body = @{ event_type = "system_restart"; message = $Message } | ConvertTo-Json
        Invoke-WebRequest -Uri "http://localhost:8001/api/admin/system/notify" `
            -Method POST -Body $body -ContentType "application/json" `
            -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # LINE notify 失敗不阻擋重啟（best-effort）
        Write-Warning "LINE notify 失敗: $_"
    }
}

Write-Host "=== Safe Restart ck-backend ===" -ForegroundColor Cyan
Write-Host "Reason: $Reason"
Write-Host "Grace period: $GraceSeconds 秒"
Write-Host ""

# Step 1: Pre-notify
Send-LineNotify "🔄 ck-backend 將於 ${GraceSeconds} 秒後重啟（${Reason}），預計 downtime ~12 秒。前端 retry 已涵蓋。"
Write-Host "[1/4] Pre-notify sent (or skipped)" -ForegroundColor Green

# Step 2: Grace period
Write-Host "[2/4] Grace period: 等候 $GraceSeconds 秒..." -ForegroundColor Yellow
for ($i = $GraceSeconds; $i -gt 0; $i--) {
    Write-Host "  ${i}..." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

# Step 3: Restart
Write-Host "[3/4] pm2 restart ck-backend --update-env" -ForegroundColor Yellow
$startTime = Get-Date
pm2 restart ck-backend --update-env | Out-Null

# Step 4: Health poll
Write-Host "[4/4] 輪詢 /api/health（最多 $MAX_HEALTH_WAIT 秒）..." -ForegroundColor Yellow
$elapsed = 0
$healthy = $false
while ($elapsed -lt $MAX_HEALTH_WAIT) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    # 改用 curl（更可靠，避免 PowerShell Invoke-WebRequest 在連線拒絕時的奇怪行為）
    $statusCode = & curl.exe -s -o NUL -w "%{http_code}" --max-time 2 $BACKEND_URL 2>$null
    if ($statusCode -eq "200") {
        $healthy = $true
        break
    }
    Write-Host "  ${elapsed}s: 仍未 ready (status=$statusCode)..."
}

$totalDuration = ((Get-Date) - $startTime).TotalSeconds
if ($healthy) {
    Write-Host ""
    Write-Host "✅ Backend ready (took ${elapsed}s, total ${totalDuration}s)" -ForegroundColor Green
    Send-LineNotify "✅ ck-backend 已恢復（用時 ${elapsed} 秒）"
} else {
    Write-Host ""
    Write-Host "❌ Backend 未在 ${MAX_HEALTH_WAIT}s 內 ready，請檢查 pm2 logs" -ForegroundColor Red
    Send-LineNotify "⚠️ ck-backend 重啟後 ${MAX_HEALTH_WAIT}s 未 ready，需人工檢查"
    exit 1
}
