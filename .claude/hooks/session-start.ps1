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

# 輸出上下文 (stdout → 自動加入 Claude 上下文)
$context -join "`n"
