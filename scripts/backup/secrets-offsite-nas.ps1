<#
.SYNOPSIS
  金鑰與憑證異地備份：.env + 服務帳號憑證 → 加密 → CKNAS

.DESCRIPTION
  2026-08-10 覆盤發現的最後一個「還原不出可運行系統」的缺口：

    公文資料  → NAS 有 30 份 dump（實測可還原）
    公文附件  → NAS 有 1486 檔（今日補上，先前一份都沒有）
    程式碼    → GitHub
    金鑰憑證  → **只有 D 槽一份**

  沒有 .env（95 個設定、其中 15 個金鑰/密碼）與 Google 服務帳號憑證，
  資料全部還原回來系統仍然起不來：Groq / NVIDIA / LINE / Google / Cloudflare
  的金鑰要一個一個重新申請，服務帳號憑證要重新產生並重新授權共享日曆。

  ## 為什麼要加密，以及加密防的是什麼

  NAS 是 SMB 共享。明文放 15 把金鑰上去，等於任何能連上該共享的人都拿得到。
  **加密防的是「NAS 上那份被隨意讀取」，不是防本機被入侵** —— 自動化要跑就得
  拿得到密碼，所以密碼一定在這台機器上。這個取捨是刻意的，不是疏漏。

  ## 密碼放哪裡（這是整份設計最重要的一句）

  密碼必須**同時**存在兩個地方：

    1. 本機 C:\Users\<user>\.ck\missive-secrets.key —— 給每日排程用
       （刻意放 C 槽：被保護的資料在 D 槽，兩者不該死在同一顆磁碟上）
    2. 你的密碼管理器 —— **D 槽壞掉之後唯一的解密途徑**

  只做 1 不做 2 的話，磁碟壞掉時 NAS 上會有一個永遠解不開的檔案，
  那比沒有備份更糟 —— 它看起來像有備份。

  ## 還原方式（寫在這裡，因為需要它的時候你不會有這台機器）

    openssl enc -d -aes-256-cbc -pbkdf2 -in secrets_YYYYMMDD.enc -out secrets.tar
    tar -xf secrets.tar

.NOTES
  觸發：Windows 排程 CK-Missive-Offsite-Backup（與 DB/附件同一支排程鏈，每日 03:00）
  手動：powershell -File scripts\backup\secrets-offsite-nas.ps1 -DryRun
        powershell -File scripts\backup\secrets-offsite-nas.ps1 -InitPassphrase   # 首次建立密碼
#>
param(
    [string]$Dest = "\\CKNAS\CK_Project\#Project_data\missive_secrets",
    [int]$KeepCount = 14,
    [switch]$DryRun,
    [switch]$InitPassphrase
)
$ErrorActionPreference = "Stop"
$repo = "D:\CKProject\CK_Missive"
$keyFile = Join-Path $env:USERPROFILE ".ck\missive-secrets.key"
$logDir = Join-Path $repo "logs\backup"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "secrets-offsite.log"

function Log($m) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# 要備份的東西。刻意逐一列舉而不是掃整個目錄 ——
# 「把整包 config 都帶走」會在某天悄悄夾帶不該離開本機的東西。
$targets = @(
    @{ Path = "$repo\.env";                              As = ".env" },
    @{ Path = "$repo\backend\GoogleCalendarAPIKEY.json"; As = "GoogleCalendarAPIKEY.json" },
    @{ Path = "$repo\backend\config\remote_backup.json"; As = "remote_backup.json" }
)

# ---------------------------------------------------------------------------
# 首次建立密碼
# ---------------------------------------------------------------------------
if ($InitPassphrase) {
    if (Test-Path $keyFile) {
        Write-Output "密碼檔已存在: $keyFile"
        Write-Output "若要重建，請先手動刪除（⚠️ 舊的 .enc 檔將無法用新密碼解開）"
        exit 1
    }
    $dir = Split-Path $keyFile -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $pass = [Convert]::ToBase64String($bytes)
    Set-Content -Path $keyFile -Value $pass -Encoding ascii -NoNewline
    # 只有本人可讀（移除繼承，僅保留目前使用者）
    $acl = Get-Acl $keyFile
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "$env:USERDOMAIN\$env:USERNAME", "FullControl", "Allow")
    $acl.SetAccessRule($rule)
    Set-Acl -Path $keyFile -AclObject $acl
    Write-Output ""
    Write-Output "=============================================================="
    Write-Output " 已建立密碼並寫入: $keyFile"
    Write-Output ""
    Write-Output "   $pass"
    Write-Output ""
    Write-Output " ⚠️ 現在就把上面這一行存進你的密碼管理器。"
    Write-Output "    D 槽壞掉之後，這是解開 NAS 上加密備份的唯一途徑；"
    Write-Output "    只存在這台機器上的話，備份看起來還在、實際打不開。"
    Write-Output "=============================================================="
    exit 0
}

Log "=== 金鑰異地備份開始 (DryRun=$DryRun) ==="

# ---------------------------------------------------------------------------
# 取得密碼。取不到就拒絕執行 —— 靜靜跳過會讓「沒有備份」長得跟「備份成功」一樣，
# 這正是本專案反覆抓到的形態（契約規則 4：外部依賴缺失一律出聲）。
# ---------------------------------------------------------------------------
$pass = $env:CK_SECRETS_PASSPHRASE
if (-not $pass -and (Test-Path $keyFile)) { $pass = (Get-Content $keyFile -Raw).Trim() }
if (-not $pass) {
    Log "ERROR 找不到密碼（env CK_SECRETS_PASSPHRASE 或 $keyFile）"
    Log "      請先執行： powershell -File scripts\backup\secrets-offsite-nas.ps1 -InitPassphrase"
    exit 2
}

# 前置檢查：來源缺一不可。少一個就是還原時少一塊，不該當成小事帶過。
$missing = @()
foreach ($t in $targets) { if (-not (Test-Path $t.Path)) { $missing += $t.As } }
if ($missing.Count -gt 0) {
    Log "ERROR 來源檔案缺少: $($missing -join ', ')"
    exit 2
}

if (-not (Test-Path $Dest) -and -not $DryRun) {
    try { New-Item -ItemType Directory -Path $Dest -Force -ErrorAction Stop | Out-Null }
    catch { Log "ERROR 無法建立/存取 NAS 目的地: $_"; exit 1 }
}

$stamp = Get-Date -Format "yyyyMMdd"
$work = Join-Path $env:TEMP "ck_secrets_$stamp"
$tar  = "$work.tar"
$enc  = Join-Path $Dest "secrets_$stamp.enc"

if ($DryRun) {
    Log "[DryRun] 將打包 $($targets.Count) 個檔案 → 加密 → $enc"
    foreach ($t in $targets) { Log "  [DryRun] $($t.As) ($([math]::Round((Get-Item $t.Path).Length/1KB,1)) KB)" }
    Log "=== 金鑰異地備份完成 (DryRun) ==="
    exit 0
}

try {
    if (Test-Path $work) { Remove-Item $work -Recurse -Force }
    New-Item -ItemType Directory -Path $work -Force | Out-Null
    foreach ($t in $targets) { Copy-Item -LiteralPath $t.Path -Destination (Join-Path $work $t.As) -Force }

    # ⚠️ 2026-08-22：tar **必須用 Windows 內建那個**（System32\tar.exe）。
    #    系統 PATH 上 Git for Windows 的 tar.exe 排在前面，而它會把
    #    `C:\...` 當成遠端主機 ⇒ `Cannot connect to C: resolve failed`、exit=128。
    #    這不是環境問題而是腳本缺陷：呼叫 `tar` 卻沒指定是哪一個 ——
    #    碰巧走到對的那支就成功、走到另一支就失敗，而兩者長得一模一樣。
    #    openssl 仍用 Git 附的（3.5.x，本來就正常）；
    #    -pbkdf2 是必要的：預設 KDF 已不安全，且新版 openssl 解密時會抱怨。
    $tarExe = Join-Path $env:SystemRoot 'System32\tar.exe'
    if (-not (Test-Path $tarExe)) { throw "找不到 Windows 內建 tar：$tarExe" }
    & $tarExe -cf $tar -C $work .
    if ($LASTEXITCODE -ne 0) { throw "tar 失敗 exit=$LASTEXITCODE" }

    $env:CK_ENC_PASS = $pass
    & openssl enc -aes-256-cbc -pbkdf2 -salt -in $tar -out $enc -pass env:CK_ENC_PASS
    $encCode = $LASTEXITCODE
    Remove-Item Env:\CK_ENC_PASS -ErrorAction SilentlyContinue
    if ($encCode -ne 0) { throw "openssl 加密失敗 exit=$encCode" }

    # ⚠️ 立刻驗證解得開。只驗「檔案產生了」等於沒驗 ——
    # 一個解不開的加密備份比沒有備份更糟，它看起來像有備份。
    $verifyOut = Join-Path $env:TEMP "ck_secrets_verify.tar"
    $env:CK_ENC_PASS = $pass
    & openssl enc -d -aes-256-cbc -pbkdf2 -in $enc -out $verifyOut -pass env:CK_ENC_PASS
    $decCode = $LASTEXITCODE
    Remove-Item Env:\CK_ENC_PASS -ErrorAction SilentlyContinue
    if ($decCode -ne 0) { throw "解密驗證失敗 exit=$decCode（備份不可用）" }

    $srcHash = (Get-FileHash $tar -Algorithm SHA256).Hash
    $dstHash = (Get-FileHash $verifyOut -Algorithm SHA256).Hash
    Remove-Item $verifyOut -Force -ErrorAction SilentlyContinue
    if ($srcHash -ne $dstHash) { throw "解密內容與原始不符（SHA256 不同）" }

    Log "已加密並驗證可解開: $(Split-Path $enc -Leaf) ($([math]::Round((Get-Item $enc).Length/1KB,1)) KB)"
}
catch {
    Log "ERROR $_"
    exit 1
}
finally {
    if (Test-Path $tar)  { Remove-Item $tar -Force -ErrorAction SilentlyContinue }
    if (Test-Path $work) { Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue }
}

# 輪替：金鑰不常變，14 份已足夠回溯
try {
    $files = Get-ChildItem -Path $Dest -Filter "secrets_*.enc" -File | Sort-Object LastWriteTime -Descending
    if ($files.Count -gt $KeepCount) {
        $files | Select-Object -Skip $KeepCount | ForEach-Object {
            Log "prune 超量: $($_.Name)"; Remove-Item $_.FullName -Force
        }
    }
    Log "NAS 現存金鑰備份份數: $([math]::Min($files.Count, $KeepCount))"
} catch { Log "WARN 輪替失敗: $_" }

Log "=== 金鑰異地備份完成 ==="
exit 0
