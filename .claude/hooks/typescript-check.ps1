# TypeScript 編譯檢查 Hook
# PostToolUse: 在修改 .ts/.tsx 檔案後執行

param(
    [string]$EditedFile = ""
)

$ErrorActionPreference = "Stop"

Write-Host "TypeScript Check: 檢查前端編譯..." -ForegroundColor Cyan

# 切換到前端目錄
Push-Location "$PSScriptRoot/../../frontend"

try {
    # 執行 TypeScript 編譯檢查
    $result = & npx tsc --noEmit 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "TypeScript Check: 編譯通過" -ForegroundColor Green
    } else {
        Write-Host "TypeScript Check: 編譯失敗" -ForegroundColor Red
        Write-Host $result
    }

    exit $exitCode
}
finally {
    Pop-Location
}
