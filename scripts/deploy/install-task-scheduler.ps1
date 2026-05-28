# =============================================================================
# CK_Missive Layer 4 開機自啟 Task Scheduler 安裝腳本
# =============================================================================
# 用途：自動 import \CK_Missive\AutoStart 任務（PM2 廢除後的 Layer 4 safety net）
# 觸發：5/27 owner 以為 import 成功但實際失敗（schtasks 沒 task）→ L49 family 跡證
# 用法：右鍵「以系統管理員身分執行」 OR PowerShell elevated 跑 `./install-task-scheduler.ps1`
#
# Self-elevating：如非 Admin 自動 spawn elevated child + 等候完成
# =============================================================================

param(
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# 1. Self-elevation check
$currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Host "⚠️  需要 Administrator 權限 — 自動 spawn elevated child window..." -ForegroundColor Yellow
    Write-Host ""
    $scriptPath = $MyInvocation.MyCommand.Definition
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
    if ($Force) { $args += " -Force" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args -Wait
    Write-Host "✓ Elevated child window completed" -ForegroundColor Green
    exit 0
}

# 2. 找 XML
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$xmlPath = Join-Path $repoRoot "scripts/deploy/task-scheduler-autostart.xml"

Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " CK_Missive Layer 4 Task Scheduler Installer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repo root: $repoRoot" -ForegroundColor Gray
Write-Host "XML path:  $xmlPath" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $xmlPath)) {
    Write-Host "✗ XML not found: $xmlPath" -ForegroundColor Red
    exit 1
}

# 3. 查既有 task 防重複
$existing = schtasks /Query /TN "\CK_Missive\AutoStart" 2>$null
if ($existing -and -not $Force) {
    Write-Host "⚠️  Task \CK_Missive\AutoStart 已存在 — 使用 -Force 強制覆蓋" -ForegroundColor Yellow
    schtasks /Query /TN "\CK_Missive\AutoStart" /V /FO LIST 2>$null | Select-String "TaskName|Status|Next Run|Last Run" | Select-Object -First 5
    Read-Host "Press Enter to exit"
    exit 0
}

# 4. Import — 先驗 XML BOM 編碼（L49 family 第 11 案：encoding="UTF-16" 但實際 ASCII）
Write-Host "→ Verifying XML encoding..." -ForegroundColor White
$xmlBytes = [System.IO.File]::ReadAllBytes($xmlPath)
if (-not ($xmlBytes[0] -eq 0xFF -and $xmlBytes[1] -eq 0xFE)) {
    Write-Host "⚠ XML 不是 UTF-16 LE BOM (Task Scheduler 會拒收) — 自動修正..." -ForegroundColor Yellow
    $content = Get-Content $xmlPath -Raw -Encoding UTF8
    $utf16 = New-Object System.Text.UnicodeEncoding($false, $true)
    [System.IO.File]::WriteAllText($xmlPath, $content, $utf16)
    Write-Host "✓ XML 已重存為 UTF-16 LE with BOM" -ForegroundColor Green
}

Write-Host "→ Importing Task Scheduler XML..." -ForegroundColor White
$result = schtasks /Create /TN "\CK_Missive\AutoStart" /XML "$xmlPath" /F 2>&1
$exitCode = $LASTEXITCODE

Write-Host ($result | Out-String).Trim()

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "✗ schtasks /XML import FAILED (exit $exitCode) — fallback to Register-ScheduledTask" -ForegroundColor Yellow

    # Fallback: 用 PowerShell cmdlet 程序化建 task（不依賴 XML 編碼）
    try {
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $trigger.Delay = "PT30S"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-ExecutionPolicy Bypass -NoProfile -Command `"Start-Sleep 60; Set-Location 'D:\CKProject\CK_Missive'; docker compose -f docker-compose.production.yml up -d 2>&1 | Tee-Object 'D:\CKProject\CK_Missive\backups\autostart.log'`"" `
            -WorkingDirectory "D:\CKProject\CK_Missive"
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -StartWhenAvailable -RunOnlyIfNetworkAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
        Register-ScheduledTask `
            -TaskPath "\CK_Missive\" `
            -TaskName "AutoStart" `
            -Trigger $trigger `
            -Action $action `
            -Principal $principal `
            -Settings $settings `
            -Description "CK_Missive auto-start on boot (v6.11 PM2 deprecation Layer 3 backup)" `
            -Force | Out-Null
        Write-Host "✓ Register-ScheduledTask fallback 成功" -ForegroundColor Green
        $exitCode = 0
    } catch {
        Write-Host "✗ Register-ScheduledTask fallback 也失敗: $_" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 5. 驗證
Write-Host ""
Write-Host "✓ Import succeeded — verifying..." -ForegroundColor Green
Write-Host ""
schtasks /Query /TN "\CK_Missive\AutoStart" /V /FO LIST 2>$null | Select-String "TaskName|Status|Author|Description|Trigger|Run As User" | Select-Object -First 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Layer 4 ready ✓ — 開機時 BootTrigger +30s 自動執行" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "下次驗收：完整關機重啟 → 等 2 分鐘 → curl http://localhost:8001/health"
Write-Host ""
Read-Host "Press Enter to close"
