# SessionStart Hook: 自動載入專案上下文 (v1.0.0)
# 事件: SessionStart (matcher: startup)
# 輸出: stdout 內容自動加入 Claude 上下文

$ErrorActionPreference = "SilentlyContinue"

# 2026-08-30：**輸出編碼必須明示 UTF-8**。
# Windows 主控台預設 cp950，PowerShell 會用它編碼 stdout ⇒ 中文送出去是亂碼。
# 這不是顯示問題：同日 PreToolUse 擋下 Write 時，我收到的錯誤訊息就是
# 「檔案位置違規」變成 `�ɮצ�m�H�W` —— **hook 的訊息真的以亂碼抵達**。
# 一個滿是亂碼的 session 起點等於沒有起點。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

$projectDir = $env:CLAUDE_PROJECT_DIR
if (-not $projectDir) { $projectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }

$context = @()
$context += "=== CK_Missive 專案狀態 ==="

# Git 狀態
$branch = git -C $projectDir branch --show-current 2>$null
if ($branch) {
    $context += "分支: $branch"

    $recentCommits = git -C $projectDir log --oneline -3 2>$null
    if ($recentCommits) {
        $context += "最近提交:"
        foreach ($commit in $recentCommits) {
            $context += "  $commit"
        }
    }

    $uncommitted = (git -C $projectDir status --porcelain 2>$null | Measure-Object).Count
    if ($uncommitted -gt 0) {
        $context += "未提交變更: $uncommitted 個檔案"
    }
}

# Docker 服務狀態
$dockerRunning = docker ps --filter "name=ck_missive" --format "{{.Names}}: {{.Status}}" 2>$null
if ($dockerRunning) {
    $context += "Docker 服務:"
    foreach ($svc in $dockerRunning) {
        $context += "  $svc"
    }
} else {
    $context += "Docker 服務: 未執行"
}

# PM2 狀態
$pm2List = pm2 jlist 2>$null
if ($pm2List -and $pm2List -ne "[]") {
    try {
        $pm2Data = $pm2List | ConvertFrom-Json
        $running = ($pm2Data | Where-Object { $_.pm2_env.status -eq "online" }).Count
        $total = $pm2Data.Count
        $context += "PM2: $running/$total 個服務運行中"
    } catch {
        $context += "PM2: 已安裝 (狀態解析失敗)"
    }
} else {
    $context += "PM2: 未執行"
}

# v6.12 (2026-05-30) 整合 SSOT Dashboard 入口
# 解 owner「每次詢問都有缺漏」meta 問題 — 把 dashboard 提示放 session 啟動
$dashboardPath = Join-Path $projectDir "docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md"
if (Test-Path $dashboardPath) {
    $dashFile = Get-Item $dashboardPath
    $ageHours = [math]::Round(((Get-Date) - $dashFile.LastWriteTime).TotalHours, 1)
    $freshness = if ($ageHours -lt 24) { "GREEN" } elseif ($ageHours -lt 48) { "YELLOW" } else { "RED" }
    $context += ""
    $context += "=== 整合 SSOT Dashboard ==="
    $context += "⭐ 首選入口: docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md"
    $context += "  freshness: $freshness ($ageHours h 前更新)"
    $context += "  內容: 4 類規範 + 15+ 真活 metric + 8 commits 軌跡 + 5 session 覆盤 + B 方案 trial + L4x family + v6.12 4 原則 + 漂移看板"
    $context += "  說明: cron 每日 06:00 自動 regenerate；直接讀此檔取 single SSOT 快照避免散處 grep"
}

# 2026-08-30（owner 目標：不要再發生每個 session 各自創、無整合運用）
#
# 這一段是「讓下一個 session 有共同起點」的唯一入口 —— 若它自己沒送達，
# 每個 session 就只能從零開始各自摸索，而那正是要防的事。
$context += ""
$context += "=== 建構標準（新增任何能力前先讀）==="
$context += "⭐ docs/architecture/SERVICE_CONSTRUCTION_STANDARD.md"
$context += "  四類能力的**完整部件集**：檢核／排程／API 契約／hook。"
$context += "  只做部件 A 等於沒做 —— 每一條都對應一次真實失效。"
$context += "  常見漏掉的部件：腳本沒接進 runner／metric 沒有消費端／"
$context += "  schema 欄位沒到前端型別／commit 了但沒 rebuild。"
$context += ""
$context += "=== 不要自己造一份（weekly 93/94 會擋）==="
$context += "  路徑一律 `from lib.paths import repo_root` —— 不要寫 parents[N]"
$context += "  容器一律 `from lib.docker_exec import exec_in` —— 不要自己拼 docker exec"
$context += "  實測 182 支檢核裡 110 支自算路徑、40 支自開 docker exec，"
$context += "  而共用層早就存在、採用率只有 3.3%。新增自造 ⇒ weekly 93 判紅。"
$context += "  長期紅燈必須登記 .chronic_red_registry.json ⇒ weekly 94 判紅。"

# 輸出上下文
#
# ⚠️ 2026-08-30 改為協議記載的巢狀形狀。原本是 `$context -join "`n"` ——
# 純文字直接吐到 stdout，而檔內註解寫著「stdout → 自動加入 Claude 上下文」。
# 同日實測：PostToolUse 的純文字（Write-Host）**送不到**，
# 而同目錄 auto-approve.ps1（實際運作中）用的是巢狀 hookSpecificOutput，
# CK_DigitalTunnel 的 hooks-reference.md 也記載 SessionStart 用同一形狀。
# ⚠️ 我無法在本 session 內驗證它是否送達（要等下一個 session 啟動）——
#    但「與協議一致」比「與註解一致」可靠。
$payload = @{
    hookSpecificOutput = @{
        hookEventName     = "SessionStart"
        additionalContext = ($context -join "`n")
    }
} | ConvertTo-Json -Compress -Depth 5
Write-Output $payload
