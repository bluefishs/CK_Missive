# 檔案位置驗證 Hook (v2.0.0)
# PreToolUse: 在建立/編輯檔案前驗證位置是否符合架構規範
# 協議: 從 stdin 讀取 JSON，從 tool_input.file_path 取得路徑


# 2026-08-30：輸出編碼明示 UTF-8。Windows 主控台預設 cp950，
# PowerShell 會用它編碼 stdout/stderr ⇒ 中文訊息以亂碼抵達 Claude。
# 這不是顯示問題：同日 validate-file-location 擋下 Write 時，
# 「檔案位置違規」實際收到的是 `?????m?H?W` —— 擋對了但看不懂為什麼。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }
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

# 定義禁止放置檔案的位置（比對「正規化後的完整路徑」，故不得用 ^ 錨點）
#
# ⚠️ 2026-08-30：原本這裡有三條帶 `^` 的規則（`^[^/]+\.md$`／`^temp_`／`^test_`）。
#    它們比對的是 `$normalizedPath`，而 Claude Code 的 Write/Edit **要求絕對路徑**
#    ⇒ 字串一律以 `D:/...` 開頭 ⇒ **那三條在真實運作中從來沒有命中過**。
#    實測：同一支 hook 餵絕對路徑 exit 0、餵相對路徑 exit 2。
#    而另外三條會命中，所以這支 hook 一直看起來是正常的。
#    ⇒ 需要「檔名」語意的規則改用 $ForbiddenFileNames（比對 Split-Path -Leaf），
#      需要「就在 repo 根」語意的改用 $RootOnlyMdCheck。
$ForbiddenPatterns = @(
    "backend/test_.*\.py$",           # 測試檔案不應在 backend 根目錄
    "backend/.*\.sql$",               # SQL 檔案應在指定位置
    "frontend/.*\.py$",               # Python 檔案不應在前端
    "backend/\.env$"                  # development-rules §2：.env 唯一來源在專案根，
                                      # backend/.env **禁止存在**。原本沒有任何機制在擋 ——
                                      # CI 的 config-consistency job 自 2026-03-09 起全面停用
                                      # （收費），而這支不查它 ⇒ 零強制（2026-08-30 補）。
)

# 「只在 repo 根目錄才禁止」的檔名規則
#
# ⚠️ 這裡的語意是**根目錄**，不是全庫。改寫時我第一版把它們套到所有檔名，
#    那會把 `backend/tests/test_foo.py` 這種合法的 pytest 檔全部擋掉 ——
#    **修一條沒生效的規則時，很容易順手把它放寬成另一個 bug。**
$RootOnlyForbiddenNames = @(
    "^temp_",                          # 暫存檔案（應放 session scratchpad）
    "^test_"                           # 測試檔案應在 tests/ 底下，不散在根目錄
)

# repo 根 = 本 hook 的 .claude/hooks 往上兩層（同 route-sync-check 2026-08-30 的修法：
# 那支用了三層 Split-Path，算到 monorepo 根，於是每次都找不到檔）
$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) -replace '\\', '/'

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

    # 「就在 repo 根目錄」才適用的規則 —— 用目錄比對，不用 ^ 錨點
    # （原本三條 ^ 規則在絕對路徑下從未命中；見上方註解）
    $parentDir = (Split-Path -Parent $normalizedPath) -replace '\\', '/'
    $isAtRepoRoot = ($parentDir.TrimEnd('/') -ieq $RepoRoot.TrimEnd('/'))
    if ($isAtRepoRoot) {
        foreach ($namePattern in $RootOnlyForbiddenNames) {
            if ($fileName -match $namePattern) { return $false }
        }
        # 根目錄的 md 需在白名單內
        if ($fileName -match '\.md$' -and ($AllowedRootMd -notcontains $fileName)) {
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
