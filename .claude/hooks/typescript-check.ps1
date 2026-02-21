# TypeScript 編譯檢查 Hook (v2.0.0)
# PostToolUse: 在修改 .ts/.tsx 檔案後執行
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
        if (-not $filePath) {
            $filePath = $hookInput.tool_input.new_string  # Edit 工具
        }
    } catch { }
}

# 取得實際修改的檔案路徑
if (-not $filePath -and $hookInput.tool_input.file_path) {
    $filePath = $hookInput.tool_input.file_path
}

# 只檢查 .ts/.tsx 檔案
if ($filePath -and $filePath -notmatch '\.(ts|tsx)$') {
    exit 0
}

# 檢查前端目錄是否存在
$frontendDir = Join-Path $PSScriptRoot "../../frontend"
if (-not (Test-Path $frontendDir)) {
    exit 0
}

Push-Location $frontendDir

try {
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
