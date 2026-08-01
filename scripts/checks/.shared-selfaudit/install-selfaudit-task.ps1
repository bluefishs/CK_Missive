#Requires -Version 5.1
<#
.SYNOPSIS
    註冊每日自我檢核 Windows 排程 —— 共享版（canonical: shared-modules/selfaudit）

.DESCRIPTION
    工作名稱、入口腳本、執行時間全部讀 <repo>/selfaudit.config.json，
    不寫死任何 repo 專屬字串 —— 初版是 CK_Missive 專用檔，若各 repo 各複製一份
    就是「同一件事 N 份實作」（本專案一路在治的異質同工）。

    為何用 Windows 排程而非後端 cron：
      playwright 跑在 host（容器內無瀏覽器）。容器端只負責「監看產出新鮮度
      並走該 repo 既有告警管道」，不新建通知管道。

    為何用 schtasks.exe 而非 Register-ScheduledTask：
      後者建立 root 層排程需要系統管理員（實測 HRESULT 0x80070005 存取被拒），
      等於多一道人工提權步驟。schtasks 建「當前使用者」層級排程免提權，
      對本用途足夠（只讀公網頁面、寫專案內檔案）。

.NOTES
    UTF-8 BOM（L49.8：PS 5.1 於 cp950 host 解析中文）。
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'

# repo 根目錄：引擎位於 <repo>/scripts/checks/.shared-selfaudit/ → 上推三層。
# 不可假設安裝位置與原生 repo 相同（vendored 比原生多一層，2026-08-01 踩過）。
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$configPath = Join-Path $root 'selfaudit.config.json'
$wrapper = Join-Path $PSScriptRoot 'run-selfaudit.cmd'

if (-not (Test-Path $configPath)) {
    Write-Error "找不到設定檔: $configPath（跨專案導入需先建立 selfaudit.config.json）"
    exit 2
}
if (-not (Test-Path $wrapper)) {
    Write-Error "找不到執行包裝: $wrapper（引擎未同步？跑 sync-vendored.sh）"
    exit 2
}

$cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$project = $cfg.project
$entry = if ($cfg.entry_script) { $cfg.entry_script } else { 'scripts/checks/run_selfaudit.sh' }

# 排程時間可在 config 覆寫；預設避開常見高峰（02:00 fitness / 03:00 pipeline / 03:30 tender）
$flowTime = if ($cfg.schedule_flow_time) { $cfg.schedule_flow_time } else { '04:15' }
$sweepTime = if ($cfg.schedule_sweep_time) { $cfg.schedule_sweep_time } else { '04:30' }

$tasks = @(
    @{ Name = "$project-SelfAudit-Flow";  Time = $flowTime;  Args = '' }
    @{ Name = "$project-SelfAudit-Sweep"; Time = $sweepTime; Args = '--sweep' }
)

if ($Uninstall) {
    foreach ($t in $tasks) {
        schtasks /delete /TN $t.Name /F 2>$null | Out-Null
        Write-Host "已移除排程: $($t.Name)"
    }
    exit 0
}

foreach ($t in $tasks) {
    # 指向 wrapper 並把入口腳本當參數傳入，避開 schtasks 對
    #「含空白路徑＋引號參數」的解析陷阱
    $tr = "$wrapper $entry $($t.Args)".TrimEnd()
    schtasks /create /TN $t.Name /TR $tr /SC DAILY /ST $t.Time /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "註冊失敗: $($t.Name)"
        continue
    }

    # schtasks 建立的排程預設 StartWhenAvailable=false —— 機器在排定時間關機
    # 就**整個跳過、不補跑**，而且不會有任何訊號。這是沉默漏跑，
    # 檢核器本身消失了卻沒人知道（2026-08-01 實測發現）。
    # Set-ScheduledTask 對「當前使用者」層級的排程免提權。
    try {
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Hours 2)
        Set-ScheduledTask -TaskName $t.Name -Settings $settings -ErrorAction Stop | Out-Null
        Write-Host "已註冊排程: $($t.Name) 每日 $($t.Time)（錯過會補跑）"
    } catch {
        Write-Warning "已註冊但無法設定 StartWhenAvailable: $($t.Name) — $($_.Exception.Message)"
        Write-Warning "  → 機器在排定時間關機時會整個跳過，請手動於工作排程器勾選「僅要有可能就儘快啟動」"
    }
}

Write-Host ''
Write-Host "結果檔：$($cfg.output.flow_result) / $($cfg.output.sweep_result)"
Write-Host '停跑偵測：該 repo 的新鮮度檢核（producer watchdog / fitness / celery task）'
Write-Host '驗證：python scripts/checks/.shared-selfaudit/ui_smoke_freshness.py'
