#Requires -Version 5.1
<#
.SYNOPSIS
    註冊每日 UI 自我檢核 Windows 排程（2026-07-31）

.DESCRIPTION
    owner：「強化程式、頁面與服務整合檢核自動化機制」。

    為何用 Windows 排程而非後端 cron：
      playwright 跑在 host（容器內無瀏覽器），與異地備份 CK-Missive-Offsite-Backup
      同一模式。結果寫入 wiki/memory/integration-health/ui-*.json，
      由既有 producer watchdog 以 file_fresh 監控 —— 停跑即由每日
      cron_outcome_freshness 走既有 LINE 告警，不另建通知管道。

    為何用 schtasks.exe 而非 Register-ScheduledTask：
      後者建立 root 層排程需要系統管理員（實測 HRESULT 0x80070005 存取被拒），
      owner 得另開提權視窗＝多一道人工步驟、也是 L49.9 那次踩過的坑。
      schtasks 建立「當前使用者」層級排程免提權，對本用途足夠
      （檢核只讀公網頁面、寫專案內檔案，不需要提升權限）。

    排程時間避開既有高峰（02:00 fitness / 03:00 pipeline / 03:30 tender）。

.NOTES
    UTF-8 BOM（L49.8：PS 5.1 於 cp950 host 解析中文）。
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$wrapper = Join-Path $PSScriptRoot 'run-ui-smoke.cmd'

$tasks = @(
    @{ Name = 'CK-Missive-UI-Flow-Smoke'; Time = '04:15'; Args = '' }
    @{ Name = 'CK-Missive-UI-Page-Sweep'; Time = '04:30'; Args = '--sweep' }
)

if ($Uninstall) {
    foreach ($t in $tasks) {
        schtasks /delete /TN $t.Name /F 2>$null | Out-Null
        Write-Host "已移除排程: $($t.Name)"
    }
    exit 0
}

if (-not (Test-Path $wrapper)) {
    Write-Error "找不到執行包裝: $wrapper"
    exit 1
}

foreach ($t in $tasks) {
    # cd 到專案根目錄再執行 —— 排程的工作目錄預設是 system32
    # 指向 wrapper，避開 schtasks 對「含空白路徑＋引號參數」的解析陷阱
    $tr = if ($t.Args) { "$wrapper $($t.Args)" } else { $wrapper }
    schtasks /create /TN $t.Name /TR $tr /SC DAILY /ST $t.Time /F | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "已註冊排程: $($t.Name) 每日 $($t.Time)"
    } else {
        Write-Warning "註冊失敗: $($t.Name)"
    }
}

Write-Host ''
Write-Host '結果檔：wiki/memory/integration-health/ui-flow.json / ui-sweep.json'
Write-Host '停跑偵測：producer watchdog（file_fresh 30h）→ 既有每日 LINE 告警'
Write-Host '驗證：python scripts/checks/ui_smoke_freshness.py'
