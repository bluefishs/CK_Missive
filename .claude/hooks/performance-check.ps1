# 效能檢查 Hook (v2.0.0)
# PostToolUse: 在修改後端 .py 檔案後執行
# 協議: 從 stdin 讀取 JSON，根據 file_path 副檔名決定是否執行

$ErrorActionPreference = "Stop"

# 從 stdin 讀取 hook 輸入 JSON
$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

# 解析 JSON 取得檔案路徑
$filePath = ""
if ($rawInput) {
    try {
        $hookInput = $rawInput | ConvertFrom-Json
        $filePath = $hookInput.tool_input.file_path
    } catch { }
}

# 只檢查 .py 檔案
if ($filePath -and $filePath -notmatch '\.py$') {
    exit 0
}

# 只檢查後端服務或 API 檔案
if ($filePath -and $filePath -notmatch 'backend[\\/]app[\\/](services|api[\\/]endpoints|repositories)[\\/]') {
    exit 0
}

# 檢查後端目錄是否存在
$backendDir = Join-Path $PSScriptRoot "../../backend"
if (-not (Test-Path $backendDir)) {
    exit 0
}

Push-Location $backendDir

try {
    # 調整路徑：去掉 backend/ 前綴
    $targetFile = $filePath
    if ($targetFile) {
        $targetFile = $targetFile -replace '^(\.[\\/])?backend[\\/]', ''
        $targetFile = $targetFile -replace '\\', '/'
    }

    if (-not $targetFile -or -not (Test-Path $targetFile)) {
        exit 0
    }

    $content = Get-Content $targetFile -Raw -ErrorAction SilentlyContinue
    if (-not $content) { exit 0 }

    $issues = @()
    $lineNumber = 0

    foreach ($line in ($content -split "`n")) {
        $lineNumber++

        # 模式 1: for 迴圈中的 db 操作（N+1 查詢）
        if ($line -match "^\s*for\s+.*\s+in\s+.*:") {
            $allLines = $content -split "`n"
            $endIdx = [Math]::Min($lineNumber + 10, $allLines.Count - 1)
            $nextLines = $allLines[$lineNumber..$endIdx] -join "`n"
            if ($nextLines -match "await\s+db\.(execute|query|get)" -or $nextLines -match "\.scalars\(\)") {
                $issues += @{
                    Line = $lineNumber
                    Pattern = "N+1 查詢: 迴圈中有 DB 操作"
                    Suggestion = "使用 selectinload() 或批次查詢"
                }
            }
        }

        # 模式 2: SELECT 查詢沒有 limit（可能載入整張表）
        if ($line -match "await\s+db\.execute\(.*select\(" -and
            $line -notmatch "\.limit\(" -and
            $line -notmatch "scalar_one" -and
            $line -notmatch "func\.count") {
            $allLines = $content -split "`n"
            $startIdx = [Math]::Max(0, $lineNumber - 5)
            $endIdx = [Math]::Min($allLines.Count - 1, $lineNumber + 5)
            $context = $allLines[$startIdx..$endIdx] -join "`n"
            if ($context -notmatch "\.limit\(" -and $context -notmatch "\.first\(") {
                $issues += @{
                    Line = $lineNumber
                    Pattern = "查詢缺少分頁: 沒有 .limit()"
                    Suggestion = "加入 .limit() 防止載入整張表"
                }
            }
        }
    }

    if ($issues.Count -eq 0) {
        Write-Host "Performance Check: 檢查通過" -ForegroundColor Green
    } else {
        Write-Host "Performance Check: 發現 $($issues.Count) 個潛在問題" -ForegroundColor Yellow
        foreach ($issue in $issues) {
            Write-Host "  Line $($issue.Line): $($issue.Pattern)" -ForegroundColor Yellow
            Write-Host "    -> $($issue.Suggestion)" -ForegroundColor Gray
        }
        Write-Host "  參考: .claude/skills/database-performance.md" -ForegroundColor Gray
    }

    # 僅警告，不阻擋
    exit 0
}
finally {
    Pop-Location
}
