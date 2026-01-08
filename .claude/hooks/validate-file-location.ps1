# 檔案位置驗證 Hook
# PreToolUse: 在建立/編輯檔案前驗證位置是否符合架構規範

param(
    [string]$FilePath = ""
)

$ErrorActionPreference = "Stop"

# 定義禁止放置檔案的位置
$ForbiddenPatterns = @(
    "backend/test_.*\.py$",           # 測試檔案不應在 backend 根目錄
    "backend/.*\.sql$",               # SQL 檔案應在指定位置
    "frontend/.*\.py$",               # Python 檔案不應在前端
    "^[^/]+\.md$",                     # 根目錄不應隨意新增 md 檔案 (除特定允許的)
    "^temp_",                          # 暫存檔案
    "^test_"                           # 測試檔案不應在根目錄
)

# 允許的根目錄 md 檔案
$AllowedRootMd = @(
    "README.md",
    "CLAUDE.md",
    "STRUCTURE.md",
    "@AGENT.md",
    "@fix_plan.md"
)

function Test-FilePath {
    param([string]$Path)

    # 正規化路徑
    $normalizedPath = $Path -replace '\\', '/'
    $fileName = Split-Path $Path -Leaf

    # 檢查是否為允許的根目錄 md 檔案
    if ($normalizedPath -notmatch '/' -and $fileName -match '\.md$') {
        if ($AllowedRootMd -contains $fileName) {
            return $true
        }
    }

    # 檢查禁止的模式
    foreach ($pattern in $ForbiddenPatterns) {
        if ($normalizedPath -match $pattern) {
            return $false
        }
    }

    return $true
}

if ($FilePath) {
    Write-Host "File Location Check: 驗證檔案位置..." -ForegroundColor Cyan

    if (Test-FilePath -Path $FilePath) {
        Write-Host "File Location Check: 位置合規 - $FilePath" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "File Location Check: 位置違規 - $FilePath" -ForegroundColor Red
        Write-Host "請參考 STRUCTURE.md 確認正確的檔案放置位置"
        exit 1
    }
} else {
    Write-Host "File Location Check: 未提供檔案路徑" -ForegroundColor Yellow
    exit 0
}
