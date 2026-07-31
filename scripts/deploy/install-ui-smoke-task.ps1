#Requires -Version 5.1
<#
.SYNOPSIS
    註冊每日 UI 自我檢核 Windows 排程（2026-07-31）

.DESCRIPTION
    owner：「強化前述程式、頁面與服務整合檢核自動化機制」。

    為何用 Windows 排程而非後端 cron：
      playwright 跑在 host（容器內無瀏覽器），與異地備份 CK-Missive-Offsite-Backup
      同一模式。結果寫入 wiki/memory/integration-health/ui-*.json，
      由既有 producer watchdog 以 file_fresh 監控 —— **停跑即由每日
      cron_outcome_freshness 走既有 LINE 告警**，不另建一套通知管道。

    排程時間刻意避開既有高峰（02:00 fitness / 03:00 pipeline / 03:30 tender）：
      04:15 流程檢核（深度，約 1 分鐘）
      04:30 全站掃描（廣度，約 3 分鐘）

.NOTES
    需系統管理員權限。UTF-8 BOM（L49.8：PS 5.1 於 cp950 host 解析中文）。
#>
param(
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$bash = 'C:\Program Files\Git\bin\bash.exe'

$tasks = @(
    @{ Name = 'CK-Missive-UI-Flow-Smoke';  Time = '04:15'; Args = '' }
    @{ Name = 'CK-Missive-UI-Page-Sweep';  Time = '04:30'; Args = '--sweep' }
)

if ($Uninstall) {
    foreach ($t in $tasks) {
        try {
            Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
            Write-Host "已移除排程: $($t.Name)"
        } catch { Write-Host "排程不存在: $($t.Name)" }
    }
    exit 0
}

if (-not (Test-Path $bash)) {
    Write-Error "找不到 Git Bash: $bash（檢核腳本為 .sh，需要它執行）"
    exit 1
}

foreach ($t in $tasks) {
    $cmd = "cd '$root' && bash scripts/checks/run_ui_smoke.sh $($t.Args) >> logs/ui_smoke.log 2>&1"
    $action = New-ScheduledTaskAction -Execute $bash -Argument "-lc `"$cmd`""
    $trigger = New-ScheduledTaskTrigger -Daily -At $t.Time
    # StartWhenAvailable：機器當時關機也會在下次開機補跑（比照既有備份排程）
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew

    try { Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false } catch { }
    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger `
        -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "已註冊排程: $($t.Name) 每日 $($t.Time)"
}

Write-Host ''
Write-Host '結果檔：wiki/memory/integration-health/ui-flow.json / ui-sweep.json'
Write-Host '停跑偵測：producer watchdog（file_fresh，門檻 30h）→ 既有每日 LINE 告警'
