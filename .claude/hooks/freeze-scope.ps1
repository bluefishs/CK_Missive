# Freeze Scope Hook (v1.0.0)
# PreToolUse: 限制編輯範圍到指定目錄，防止偵錯/重構時意外修改無關程式碼
# 協議: 從 stdin 讀取 JSON，檢查 Edit/Write 的目標路徑是否在允許範圍內
#
# 啟用方式: 建立 .claude/freeze-scope.json
# {
#   "allowed_paths": ["backend/app/services/erp/", "backend/app/schemas/erp/"],
#   "reason": "ERP 費用報銷重構中，僅允許修改 ERP 相關檔案"
# }
#
# 停用方式: 刪除 .claude/freeze-scope.json 或使用 /unfreeze 指令

$ErrorActionPreference = "Stop"

# 從 stdin 讀取 hook 輸入 JSON
$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

if (-not $rawInput) { exit 0 }

try {
    $hookInput = $rawInput | ConvertFrom-Json
} catch { exit 0 }

$toolName = $hookInput.tool_name

# 只檢查 Edit 和 Write 工具
if ($toolName -ne "Edit" -and $toolName -ne "Write") { exit 0 }

$filePath = $hookInput.tool_input.file_path
if (-not $filePath) { exit 0 }

# 檢查 freeze-scope.json 是否存在
$freezeFile = Join-Path $PSScriptRoot "..\freeze-scope.json"
if (-not (Test-Path $freezeFile)) { exit 0 }

try {
    $freezeConfig = Get-Content $freezeFile -Raw | ConvertFrom-Json
} catch { exit 0 }

$allowedPaths = $freezeConfig.allowed_paths
$reason = $freezeConfig.reason

if (-not $allowedPaths -or $allowedPaths.Count -eq 0) { exit 0 }

# 正規化檔案路徑
$normalizedPath = $filePath -replace '\\', '/'

# 檢查是否在允許範圍內
$isAllowed = $false
foreach ($allowed in $allowedPaths) {
    $normalizedAllowed = $allowed -replace '\\', '/'
    if ($normalizedPath -match [regex]::Escape($normalizedAllowed)) {
        $isAllowed = $true
        break
    }
}

# 永遠允許 .claude/ 目錄的修改（用於管理 freeze 本身）
if ($normalizedPath -match '\.claude/') {
    $isAllowed = $true
}

if ($isAllowed) {
    exit 0
} else {
    $allowedList = $allowedPaths -join ", "
    $msg = "[FREEZE] 編輯範圍已鎖定。"
    if ($reason) { $msg += " 原因: $reason。" }
    $msg += " 允許範圍: $allowedList。目標檔案: $filePath 不在允許範圍內。使用 /unfreeze 解除鎖定。"
    [Console]::Error.WriteLine($msg)
    exit 2
}
