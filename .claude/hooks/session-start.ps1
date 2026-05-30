# SessionStart Hook: 自動載入專案上下文 (v1.0.0)
# 事件: SessionStart (matcher: startup)
# 輸出: stdout 內容自動加入 Claude 上下文

$ErrorActionPreference = "SilentlyContinue"

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

# 輸出上下文 (stdout → 自動加入 Claude 上下文)
$context -join "`n"
