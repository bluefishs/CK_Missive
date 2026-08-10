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
    # 2026-08-10：附件異地備份。原本這支只複製 *.sql（第 97 行寫死），
    # 於是「公文資料」有異地備份、「公文附件」一份都沒有 ——
    # backend/uploads 與其本機備份 backups/attachments 都在 D 槽同一顆實體磁碟，
    # 磁碟壞掉就等於：DB 還原得回來，但還原出一堆指向不存在檔案的紀錄。
    # 與 2026-08-09 在 DigitalTunnel 發現的「MinIO 是備份的目的地、資料與備份同一顆磁碟」同型。
    [string]$AttachSource = "D:\CKProject\CK_Missive\backend\uploads",
    [string]$AttachDest   = "\\CKNAS\CK_Project\#Project_data\missive_attachments",
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

$cfgPath = "D:\CKProject\CK_Missive\backend\config\remote_backup.json"

<#
  2026-07-29：把「NAS 實際狀態」寫進 config，讓 /admin/backup 能直接回答
  「異地備份到底正不正常」，而不是只看容器端那個刻意關閉的開關。
  失敗路徑也必須寫（原本 error 直接 exit → UI 仍顯示上次成功時間＝沉默失敗）。
#>
function Write-SyncStatus {
    param([string]$Result, [string]$Message = "")
    if ($DryRun) { return }
    try {
        $j = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $j.remote_path    = $Dest
        $j.last_sync_time = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.ffffff")
        $j.sync_status    = if ($Result -eq "success") { "idle" } else { "error" }
        # 新增狀態欄位（容器端 schema 已對應）
        $j | Add-Member -NotePropertyName last_sync_result  -NotePropertyValue $Result  -Force
        $j | Add-Member -NotePropertyName last_sync_source  -NotePropertyValue "windows_scheduled_task:CK-Missive-Offsite-Backup" -Force
        $j | Add-Member -NotePropertyName last_sync_message -NotePropertyValue $Message -Force
        # NAS 實際內容（ground truth）
        $cnt = 0; $latestName = $null; $latestMB = $null; $latestTime = $null
        try {
            $remote = Get-ChildItem -LiteralPath $Dest -Filter "*.sql" -File -ErrorAction Stop |
                      Sort-Object LastWriteTime -Descending
            $cnt = $remote.Count
            if ($cnt -gt 0) {
                $latestName = $remote[0].Name
                $latestMB   = [math]::Round($remote[0].Length / 1MB, 1)
                $latestTime = $remote[0].LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ss")
            }
        } catch { }
        $j | Add-Member -NotePropertyName remote_file_count    -NotePropertyValue $cnt        -Force
        $j | Add-Member -NotePropertyName latest_remote_file   -NotePropertyValue $latestName -Force
        $j | Add-Member -NotePropertyName latest_remote_size_mb -NotePropertyValue $latestMB  -Force
        $j | Add-Member -NotePropertyName latest_remote_time   -NotePropertyValue $latestTime -Force
        # 附件異地狀態（2026-08-10）。分開記，因為「DB 有備份」與「附件有備份」
        # 是兩件事，而先前正是把它們混為一談才漏了整整一類資料。
        $aCnt = 0; $aMB = 0
        try {
            $ra = Get-ChildItem -LiteralPath $AttachDest -Recurse -File -ErrorAction Stop
            $aCnt = $ra.Count
            $aMB  = [math]::Round((($ra | Measure-Object Length -Sum).Sum) / 1MB, 1)
        } catch { }
        $j | Add-Member -NotePropertyName attachment_remote_path     -NotePropertyValue $AttachDest -Force
        $j | Add-Member -NotePropertyName attachment_remote_count    -NotePropertyValue $aCnt -Force
        $j | Add-Member -NotePropertyName attachment_remote_size_mb  -NotePropertyValue $aMB -Force
        ($j | ConvertTo-Json) | Set-Content -Path $cfgPath -Encoding UTF8
        Log "已寫入同步狀態: result=$Result nas_files=$cnt latest=$latestName 附件=$aCnt 檔/$aMB MB"
    } catch { Log "WARN 更新 config 失敗: $_" }
}

Log "=== 異地同步開始 (DryRun=$DryRun) ==="

# 1. 前置檢查
if (-not (Test-Path $Source)) {
    Log "ERROR 來源不存在: $Source"; Write-SyncStatus -Result "error" -Message "來源不存在: $Source"; exit 1
}
if (-not (Test-Path $Dest)) {
    Log "目的地不存在，嘗試建立: $Dest"
    if (-not $DryRun) {
        try { New-Item -ItemType Directory -Path $Dest -Force -ErrorAction Stop | Out-Null }
        catch {
            Log "ERROR 無法建立/存取目的地（NAS 認證或連線問題）: $_"
            Write-SyncStatus -Result "error" -Message "NAS 不可存取: $Dest"
            exit 1
        }
    }
}

# ---------------------------------------------------------------------------
# 2a. 里程碑快照 → 獨立目錄，不套用輪替（2026-08-10）
#
#   原本里程碑（PREUPGRADE / pre_pm2_deprecation）與日常備份混在同一個目錄、
#   共用「保留最近 30 份」規則。里程碑的日期永遠最舊 → **每天上傳、每天被刪**
#   （2026-08-10 實跑當場看到 242MB 的 pre_pm2 快照被 prune 掉）。
#   而 .dump / .sql.gz 格式的 PREUPGRADE 因為 filter 寫死 *.sql，從來沒有異地備份過。
#
#   里程碑是「回得去某個時間點」的錨點（L43 事故後刻意保留），不該被日常輪替擠掉。
# ---------------------------------------------------------------------------
$msDest = Join-Path $Dest "_milestones"
$milestones = Get-ChildItem -Path $Source -File -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -notlike "ck_missive_backup_*" -and $_.Extension -in @(".sql", ".dump", ".gz") }
if ($milestones) {
    if (-not (Test-Path $msDest) -and -not $DryRun) {
        try { New-Item -ItemType Directory -Path $msDest -Force -ErrorAction Stop | Out-Null } catch { Log "WARN 無法建立 $msDest : $_" }
    }
    foreach ($m in $milestones) {
        $t = Join-Path $msDest $m.Name
        if (Test-Path -LiteralPath $t) { continue }   # 里程碑不變，已在就跳過
        if ($DryRun) { Log "  [DryRun] 里程碑待上傳: $($m.Name)"; continue }
        try { Copy-Item -LiteralPath $m.FullName -Destination $t -ErrorAction Stop; Log "  里程碑上傳: $($m.Name)" }
        catch { Log "  ERROR 里程碑上傳失敗 $($m.Name): $_" }
    }
}

# 2b. robocopy 複製新增/變更的日常備份（/XO 只複製較新；不用 /MIR 保留 NAS 既有）
#     filter 由 *.sql 收窄為 ck_missive_backup_*.sql —— 否則里程碑會被 2a 與這裡各傳一次，
#     然後在步驟 3 被輪替刪掉。
$rcArgs = @($Source, $Dest, "ck_missive_backup_*.sql", "/XO", "/R:2", "/W:5", "/NP", "/NDL", "/NJH")
if ($DryRun) { $rcArgs += "/L" }
Log "robocopy $($rcArgs -join ' ')"
& robocopy @rcArgs | ForEach-Object { if ($_ -match '\S') { Log "  $_" } }
$code = $LASTEXITCODE
Log "robocopy exit=$code (0-7=成功, >=8=失敗)"
if ($code -ge 8) {
    Log "ERROR robocopy 失敗 exit=$code"
    Write-SyncStatus -Result "error" -Message "robocopy 失敗 exit=$code"
    exit 1
}

# 3. 保留最近 N 份（僅刪 dest 超量的舊 .sql）
if (-not $DryRun) {
    try {
        # 只輪替日常備份。里程碑在 _milestones/ 子目錄，Get-ChildItem 非遞迴故不會掃到，
        # 但仍明確收窄 filter —— 依賴「它剛好掃不到」是下一個人踩的坑。
        $files = Get-ChildItem -Path $Dest -Filter "ck_missive_backup_*.sql" -File -ErrorAction Stop | Sort-Object LastWriteTime -Descending
        if ($files.Count -gt $KeepCount) {
            $files | Select-Object -Skip $KeepCount | ForEach-Object {
                Log "prune 超量舊備份: $($_.Name)"
                Remove-Item $_.FullName -Force
            }
        }
        Log "NAS 現存 dump 份數: $([math]::Min($files.Count, $KeepCount))"
    } catch { Log "WARN 保留輪替失敗: $_" }
}

# ---------------------------------------------------------------------------
# 4. 附件異地同步（2026-08-10 新增）
#
#   /E 含空目錄、/XO 只複製較新；**刻意不用 /MIR** —— 本機刪檔不該傳播到異地，
#   異地備份的用途正是「刪錯了還救得回來」。
#
#   長檔名 fallback：NAS 是 Linux/Samba，單一檔名上限 255 **bytes**，
#   而中文在 UTF-8 是 3 bytes/字 → 約 85 個中文字就會撞到，robocopy 回 ERROR 123
#   （訊息寫「syntax is incorrect」，很容易被誤讀成路徑或權限問題）。
#   公文附件的原始檔名就是公文標題，超過 85 字並不罕見（實測 2 個檔）。
#   對這類檔案改為「整個目錄打包成 zip」上傳 —— 原始檔名完整保留在封裝內。
# ---------------------------------------------------------------------------
$attachFailed = 0
$attachArchived = 0
if (Test-Path $AttachSource) {
    if (-not (Test-Path $AttachDest) -and -not $DryRun) {
        try { New-Item -ItemType Directory -Path $AttachDest -Force -ErrorAction Stop | Out-Null }
        catch { Log "ERROR 無法建立附件目的地: $_" }
    }
    $acArgs = @($AttachSource, $AttachDest, "/E", "/XO", "/R:2", "/W:5", "/NP", "/NDL", "/NJH", "/NFL")
    if ($DryRun) { $acArgs += "/L" }
    Log "robocopy(附件) $($acArgs -join ' ')"
    $acOut = & robocopy @acArgs
    $acCode = $LASTEXITCODE
    $acOut | ForEach-Object { if ($_ -match 'Files :|Bytes :|FAILED') { Log "  $($_.Trim())" } }
    Log "robocopy(附件) exit=$acCode"

    if ($acCode -ge 8) {
        # 逐一撈出失敗檔，判斷是否為長檔名；是就打包該目錄
        $failLines = & robocopy $AttachSource $AttachDest /E /XO /R:0 /W:0 /NP /NDL /NJH 2>&1 |
                     Select-String -Pattern "ERROR \d+ .* Copying File (.+)$"
        $dirs = @{}
        foreach ($m in $failLines) {
            $attachFailed++
            $p = $m.Matches[0].Groups[1].Value.Trim()
            $d = Split-Path $p -Parent
            if ($d) { $dirs[$d] = $true }
        }
        if (-not $DryRun -and $dirs.Count -gt 0) {
            $arcRoot = Join-Path $AttachDest "_longname_archive"
            New-Item -ItemType Directory -Path $arcRoot -Force | Out-Null
            foreach ($d in $dirs.Keys) {
                try {
                    $leaf = Split-Path $d -Leaf
                    $zip = Join-Path $arcRoot "$leaf`_longname.zip"
                    Compress-Archive -Path (Join-Path $d "*") -DestinationPath $zip -Force -ErrorAction Stop
                    $attachArchived++
                    Log "  長檔名打包: $leaf → $(Split-Path $zip -Leaf)"
                } catch { Log "  ERROR 打包失敗 $d : $_" }
            }
        }
    }
} else {
    Log "WARN 附件來源不存在: $AttachSource"
}

# 5. 寫入同步狀態 + NAS 實際內容（供 admin/backup UI 顯示 / 容器 mount 可見）
#    附件若有失敗且未被打包救回 → 整體判 error。
#    「DB 同步成功但附件漏了」不得顯示成綠燈 —— 那正是這次要根治的形態。
if ($attachFailed -gt 0 -and $attachArchived -eq 0) {
    Write-SyncStatus -Result "error" -Message "附件同步失敗 $attachFailed 檔且未能打包"
    Log "=== 異地同步完成（附件有失敗）==="
    exit 1
}
Write-SyncStatus -Result "success" -Message $(
    if ($attachArchived -gt 0) { "附件 $attachFailed 檔為長檔名，已打包 $attachArchived 個目錄" } else { "" }
)

Log "=== 異地同步完成 ==="
exit 0
