# schedule-memtest-extended.ps1 — 一鍵排入 Windows 記憶體診斷「延長模式、2 輪」並重開機
#
# 用途：A127 實驗②（主機層段錯誤家族，2026-08-15 起）。mdsched.exe 的 GUI 只能選 Standard，
#       Extended 要在測試畫面按 F1；改用 BCD 的 {memdiag} 元素可以事先設好、無人值守。
# 需要：系統管理員權限（bcdedit 與 shutdown 都要）。在一般 session 裡這樣叫：
#       Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\CKProject\CK_Missive\scripts\host\schedule-memtest-extended.ps1'
#       UAC 會跳一次「是否允許」，按「是」即可（ConsentPromptBehaviorAdmin=5，不用輸密碼）。
# 結果：測完自動重開回 Windows；看事件檢視器 System，來源 MemoryDiagnostics-Results：
#       1201＝沒有錯誤、1102＝偵測到硬體錯誤。開機恢復鏈（autostart.bat → Docker Desktop → 容器）照舊。
# 還原：不需要；bootsequence 是一次性的，測完 BCD 就回到正常開機順序。
#       若要取消已排的測試：bcdedit /deletevalue {bootmgr} bootsequence
param(
    [ValidateSet('basic','standard','extended')] [string] $TestMix = 'extended',
    [int] $PassCount = 2,
    [int] $DelaySeconds = 60,
    [switch] $NoReboot
)
$ErrorActionPreference = 'Stop'
$log = "D:\CKProject\CK_Missive\docs\health\kernel\memtest_schedule_$(Get-Date -Format yyyyMMdd_HHmmss).log"
function Log($m) { $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; $line; Add-Content -Path $log -Value $line -Encoding utf8 }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "需要系統管理員權限（bcdedit）。請用 -Verb RunAs 重跑。" }

Log "設定 {memdiag}: testmix=$TestMix passcount=$PassCount"
bcdedit /set '{memdiag}' testmix $TestMix | Out-Null
bcdedit /set '{memdiag}' passcount $PassCount | Out-Null
bcdedit /set '{bootmgr}' bootsequence '{memdiag}' | Out-Null
Log ("現況：`n" + (bcdedit /enum '{memdiag}' | Out-String))
Log ("bootsequence：`n" + ((bcdedit /enum '{bootmgr}' | Select-String 'bootsequence') -join ''))

if ($NoReboot) { Log "已排入，未重開（-NoReboot）。下次開機會先跑記憶體診斷。"; exit 0 }

Log "將於 $DelaySeconds 秒後重開機進入記憶體診斷（延長模式 $PassCount 輪，64 GB 預估 6–12 小時）。"
shutdown /r /t $DelaySeconds /c "A127 實驗②：Windows 記憶體診斷（Extended x$PassCount）。測完自動重開。" /d p:0:0
Log "shutdown 已下達。取消：shutdown /a"
