# =============================================================================
# 讓高頻排程不再彈出 cmd 主控台視窗（LogonType: Interactive -> S4U）
#
# owner 2026-08-28 回報「一直彈跳 cmd 視窗」。量測結果：
#   啟用中非微軟排程 54，其中 45 個是 LogonType=Interactive -> 每天彈約 718 次
#     289 次/天  CK_AaaP_ContainerHealthAlerts    (每 5 分鐘)
#     288 次/天  CK-Hermes-Cron-Tick              (每 5 分鐘)
#     ------------------------------------------ 這兩個就佔 80%
#
# 根因：Principal.LogonType = Interactive => 工作在使用者的互動工作階段裡跑，
#       Windows 必然給它一個主控台視窗。
#
# ⚠️ -WindowStyle Hidden 擋不住這件事 —— CK-Hermes-Cron-Tick 的參數裡本來就有它，
#    照樣每 5 分鐘彈一次。那個旗標只在視窗建立「之後」才生效。
#
# 已先確認的風險（2026-08-28 實測）：
#   * S4U 拿不到對應網路磁碟機。這兩支腳本都沒有參照 Z: 或 UNC => 安全。
#   * 會碰 NAS 的排程（*-Offsite-Backup 等）刻意不動。
#   * S4U 需要「以批次工作登入」權限，系統管理員帳號通常已有。
#
# ⚠️ 這兩支排程分屬 CK_Hermes 與 CK_AaaP。改的是 Windows 排程的執行身分，
#    不動它們的程式碼；已於 2026-08-28 透過跨 session 訊息知會 CK_AaaP。
#
# 用法（不需先提權，本檔會自己要求）：
#     powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy/fix-task-logon-popups.ps1
#
# 還原：執行結束時會印出還原指令。
# =============================================================================

$ErrorActionPreference = 'Stop'
$names = @('CK-Hermes-Cron-Tick', 'CK_AaaP_ContainerHealthAlerts')

# --- 1. 自我提權（比照 scripts/deploy/install-task-scheduler.ps1 的作法）---
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host ''
    Write-Host '需要系統管理員權限 —— 開啟提權子視窗（請在 UAC 對話框按「是」）...' -ForegroundColor Yellow
    Write-Host ''
    $scriptPath = $MyInvocation.MyCommand.Definition
    $childArgs = '-NoProfile -ExecutionPolicy Bypass -NoExit -File "' + $scriptPath + '"'
    Start-Process powershell.exe -Verb RunAs -ArgumentList $childArgs
    Write-Host '已送出提權請求。結果會顯示在新開的視窗裡（該視窗不會自動關閉）。' -ForegroundColor Green
    exit 0
}

# --- 2. 改之前的狀態（還原用）---
Write-Host '=== 改之前（還原用，請留著）===' -ForegroundColor Cyan
$before = @{}
foreach ($n in $names) {
    $t = Get-ScheduledTask -TaskName $n
    $i = $t | Get-ScheduledTaskInfo
    $before[$n] = $t.Principal.LogonType
    '  {0,-32} LogonType={1,-12} RunLevel={2,-8} LastResult={3} LastRun={4}' -f $n, $t.Principal.LogonType, $t.Principal.RunLevel, $i.LastTaskResult, $i.LastRunTime
}

# --- 3. 套用 S4U ---
Write-Host ''
Write-Host '=== 套用 S4U ===' -ForegroundColor Cyan
foreach ($n in $names) {
    $t = Get-ScheduledTask -TaskName $n
    $pr = New-ScheduledTaskPrincipal -UserId $t.Principal.UserId -LogonType S4U -RunLevel $t.Principal.RunLevel
    Set-ScheduledTask -TaskName $n -Principal $pr | Out-Null
    '  {0,-32} -> {1}' -f $n, (Get-ScheduledTask -TaskName $n).Principal.LogonType
}

# --- 4. 驗證：改完必須確認它們「還會跑」---
# 一個安靜壞掉的 5 分鐘健康告警，比彈視窗糟糕得多。
Write-Host ''
Write-Host '=== 驗證：手動觸發並等待結果 ===' -ForegroundColor Cyan
foreach ($n in $names) { Start-ScheduledTask -TaskName $n }
Start-Sleep -Seconds 25

$fail = 0
foreach ($n in $names) {
    $i = Get-ScheduledTask -TaskName $n | Get-ScheduledTaskInfo
    $ok = ($i.LastTaskResult -eq 0)
    if (-not $ok) { $fail++ }
    $mark = 'OK'
    if (-not $ok) { $mark = '**失敗，見下方還原**' }
    '  {0,-32} LastResult={1}  LastRun={2}  {3}' -f $n, $i.LastTaskResult, $i.LastRunTime, $mark
}

Write-Host ''
if ($fail -eq 0) {
    Write-Host '完成：兩個工作都仍正常執行，且不再彈視窗（每天約少 577 次）。' -ForegroundColor Green
} else {
    Write-Host "有 $fail 個工作改完後失敗 —— 請用下方指令還原。" -ForegroundColor Red
}

# --- 5. 還原指令 ---
# 用單引號組字串：v1 在這裡用反引號逸出，整個檔 ParserError（而我交出去時沒有 parse 檢查過）
Write-Host ''
Write-Host '=== 還原指令（把 LogonType 改回原值）===' -ForegroundColor Yellow
foreach ($n in $names) {
    $orig = $before[$n]
    $line = '  $t = Get-ScheduledTask -TaskName ''' + $n + '''; ' +
            'Set-ScheduledTask -TaskName ''' + $n + ''' -Principal ' +
            '(New-ScheduledTaskPrincipal -UserId $t.Principal.UserId ' +
            '-LogonType ' + $orig + ' -RunLevel $t.Principal.RunLevel)'
    Write-Host $line
}
