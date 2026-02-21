# API 序列化檢查 Hook (v2.0.0)
# PostToolUse: 在修改 API 端點 .py 檔案後執行
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

# 只檢查 API 端點檔案
if ($filePath -and $filePath -notmatch 'backend[\\/]app[\\/]api[\\/]endpoints[\\/]') {
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

    $lines = Get-Content $targetFile
    $issues = @()

    # 模式 1: .scalars().all() 後直接返回（未經 Schema 序列化）
    $lineNumber = 0
    foreach ($line in $lines) {
        $lineNumber++
        if ($line -match '\.scalars\(\)\.all\(\)') {
            $varMatch = [regex]::Match($line, '(\w+)\s*=\s*.*\.scalars\(\)\.all\(\)')
            if ($varMatch.Success) {
                $varName = $varMatch.Groups[1].Value
                $endIdx = [Math]::Min($lineNumber + 9, $lines.Count - 1)
                $nextLines = $lines[$lineNumber..$endIdx] -join "`n"
                if ($nextLines -match "return\s+\{[^}]*[`"']items[`"']\s*:\s*$varName\s*[,\}]") {
                    $issues += @{
                        Line = $lineNumber
                        Message = "可能直接返回 ORM 模型列表: $varName"
                        Severity = "Warning"
                    }
                }
            }
        }
    }

    # 模式 2: datetime 欄位未使用 .isoformat()
    $lineNumber = 0
    foreach ($line in $lines) {
        $lineNumber++
        if ($line -match '["''](created_at|updated_at|deadline|start_date|end_date)["\'']\s*:\s*\w+\.(?:created_at|updated_at|deadline|start_date|end_date)(?!\.isoformat)') {
            $issues += @{
                Line = $lineNumber
                Message = "datetime 欄位可能未使用 .isoformat()"
                Severity = "Info"
            }
        }
    }

    if ($issues.Count -eq 0) {
        Write-Host "API Serialization: 檢查通過" -ForegroundColor Green
    } else {
        Write-Host "API Serialization: 發現 $($issues.Count) 個潛在問題" -ForegroundColor Yellow
        foreach ($issue in $issues) {
            $color = if ($issue.Severity -eq "Warning") { "Yellow" } else { "Gray" }
            Write-Host "  Line $($issue.Line): $($issue.Message)" -ForegroundColor $color
        }
        Write-Host "  參考: .claude/skills/api-serialization.md" -ForegroundColor Gray
    }

    # 僅警告，不阻擋
    exit 0
}
finally {
    Pop-Location
}
