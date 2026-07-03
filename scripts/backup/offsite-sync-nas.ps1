<#
.SYNOPSIS
  異地備份：本機 DB dump → CKNAS UNC（Windows 原生，沿用 User1 NAS 存取，免容器 SMB 帳密）

.DESCRIPTION
  背景：05-27 廢 PM2 native backend 改純 Docker 後，Linux 容器無法存取 Windows Z:/NAS，
  容器內異地同步中斷。本腳本以 Windows 原生行程（Windows 排程 CK-Missive-Offsite-Backup，
  執行身分 User1）複製容器已寫好的 DB dump 到 NAS UNC，重用「5 月曾成功」的同一存取路徑，
  避免在容器/.env 存 SMB 帳密與 CIFS 掛載風險。

  來源 = 容器 db_backup 排程每日 02:00 寫到 backups/database/*.sql（host 已 mount /app/backups）。
  目的 = \\CKNAS\CK_Project\#Project_data\missive_databsae（= Z:\#Project_data\missive_databsae）。
  robocopy 只複製新增/變更（/XO），不用 /MIR（避免刪 NAS 既有較舊備份）；另在 dest 保留最近 N 份。

.NOTES
  觸發：Windows 排程 CK-Missive-Offsite-Backup 每日 03:00（02:00 產完 dump 後）。
  （PM2 跑 .ps1 不可靠已棄；排程 User1/Interactive/Limited，登入態即可存取 NAS）。手動測試：
    powershell -File scripts\backup\offsite-sync-nas.ps1 -DryRun   # 只列不複製
    powershell -File scripts\backup\offsite-sync-nas.ps1           # 實際同步
#>
param(
    [string]$Source = "D:\CKProject\CK_Missive\backups\database",
    [string]$Dest   = "\\CKNAS\CK_Project\#Project_data\missive_databsae",
    [int]$KeepCount = 30,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$logDir = "D:\CKProject\CK_Missive\logs\backup"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "offsite-sync-nas.log"

function Log($m) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Log "=== 異地同步開始 (DryRun=$DryRun) ==="

# 1. 前置檢查
if (-not (Test-Path $Source)) { Log "ERROR 來源不存在: $Source"; exit 1 }
if (-not (Test-Path $Dest)) {
    Log "目的地不存在，嘗試建立: $Dest"
    if (-not $DryRun) {
        try { New-Item -ItemType Directory -Path $Dest -Force -ErrorAction Stop | Out-Null }
        catch { Log "ERROR 無法建立/存取目的地（NAS 認證或連線問題）: $_"; exit 1 }
    }
}

# 2. robocopy 複製新增/變更的 .sql（/XO 只複製較新；不用 /MIR 保留 NAS 既有）
$rcArgs = @($Source, $Dest, "*.sql", "/XO", "/R:2", "/W:5", "/NP", "/NDL", "/NJH")
if ($DryRun) { $rcArgs += "/L" }
Log "robocopy $($rcArgs -join ' ')"
& robocopy @rcArgs | ForEach-Object { if ($_ -match '\S') { Log "  $_" } }
$code = $LASTEXITCODE
Log "robocopy exit=$code (0-7=成功, >=8=失敗)"
if ($code -ge 8) { Log "ERROR robocopy 失敗 exit=$code"; exit 1 }

# 3. 保留最近 N 份（僅刪 dest 超量的舊 .sql）
if (-not $DryRun) {
    try {
        $files = Get-ChildItem -Path $Dest -Filter "*.sql" -File -ErrorAction Stop | Sort-Object LastWriteTime -Descending
        if ($files.Count -gt $KeepCount) {
            $files | Select-Object -Skip $KeepCount | ForEach-Object {
                Log "prune 超量舊備份: $($_.Name)"
                Remove-Item $_.FullName -Force
            }
        }
        Log "NAS 現存 dump 份數: $([math]::Min($files.Count, $KeepCount))"
    } catch { Log "WARN 保留輪替失敗: $_" }
}

# 4. 更新 remote_backup.json last_sync（供 admin/backup UI 顯示 / 容器 mount 可見）
if (-not $DryRun) {
    $cfg = "D:\CKProject\CK_Missive\backend\config\remote_backup.json"
    try {
        $j = Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
        $j.remote_path = $Dest
        $j.last_sync_time = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.ffffff")
        $j.sync_status = "idle"
        ($j | ConvertTo-Json) | Set-Content -Path $cfg -Encoding UTF8
        Log "已更新 remote_backup.json last_sync"
    } catch { Log "WARN 更新 config 失敗: $_" }
}

Log "=== 異地同步完成 ==="
exit 0
