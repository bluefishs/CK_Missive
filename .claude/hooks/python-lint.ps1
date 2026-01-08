# Python 語法檢查 Hook
# PostToolUse: 在修改 .py 檔案後執行

param(
    [string]$EditedFile = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Python Lint: 檢查後端語法..." -ForegroundColor Cyan

# 切換到後端目錄
Push-Location "$PSScriptRoot/../../backend"

try {
    if ($EditedFile -and (Test-Path $EditedFile)) {
        # 檢查特定檔案
        $result = & python -m py_compile $EditedFile 2>&1
    } else {
        # 檢查主程式
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
