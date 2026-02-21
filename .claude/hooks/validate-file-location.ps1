# 檔案位置驗證 Hook (v2.0.0)
# PreToolUse: 在建立/編輯檔案前驗證位置是否符合架構規範
# 協議: 從 stdin 讀取 JSON，從 tool_input.file_path 取得路徑

$ErrorActionPreference = "Stop"

# 從 stdin 讀取 hook 輸入 JSON
$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

# 解析 JSON 取得檔案路徑
$FilePath = ""
if ($rawInput) {
    try {
        $hookInput = $rawInput | ConvertFrom-Json
        $FilePath = $hookInput.tool_input.file_path
    } catch { }
}

if (-not $FilePath) {
    exit 0
}

# 定義禁止放置檔案的位置
$ForbiddenPatterns = @(
    "backend/test_.*\.py$",           # 測試檔案不應在 backend 根目錄
    "backend/.*\.sql$",               # SQL 檔案應在指定位置
    "frontend/.*\.py$",               # Python 檔案不應在前端
    "^[^/]+\.md$",                     # 根目錄不應隨意新增 md 檔案
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

if (Test-FilePath -Path $FilePath) {
    exit 0
} else {
    # exit 2 = 阻擋操作，stderr 傳給 Claude
    [Console]::Error.WriteLine("檔案位置違規: $FilePath - 請參考 .claude/rules/architecture.md 確認正確的檔案放置位置")
    exit 2
}
