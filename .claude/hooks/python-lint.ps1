# Python 語法檢查 Hook (v2.0.0)
# PostToolUse: 在修改 .py 檔案後執行
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

# 檢查後端目錄是否存在
$backendDir = Join-Path $PSScriptRoot "../../backend"
if (-not (Test-Path $backendDir)) {
    exit 0
}

Push-Location $backendDir

try {
    if ($filePath -and (Test-Path $filePath)) {
        $result = & python -m py_compile $filePath 2>&1
    } else {
        $result = & python -m py_compile app/main.py 2>&1
    }

    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "Python Lint: 語法檢查通過" -ForegroundColor Green
    } else {
        Write-Host "Python Lint: 語法錯誤" -ForegroundColor Red
        Write-Host $result
    }

    exit $exitCode
}
finally {
    Pop-Location
}
