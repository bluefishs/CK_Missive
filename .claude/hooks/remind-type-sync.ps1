# Remind Type Sync Hook (B-Plan v1.0)
# PostToolUse: remind type sync after backend schema edit
# Replaces type:"prompt" anti-pattern


# 2026-08-30：輸出編碼明示 UTF-8。Windows 主控台預設 cp950，
# PowerShell 會用它編碼 stdout/stderr ⇒ 中文訊息以亂碼抵達 Claude。
# 這不是顯示問題：同日 validate-file-location 擋下 Write 時，
# 「檔案位置違規」實際收到的是 `?????m?H?W` —— 擋對了但看不懂為什麼。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }
$ErrorActionPreference = "Stop"

$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

$filePath = ""
if ($rawInput) {
    try {
        $hookInput = $rawInput | ConvertFrom-Json
        $filePath = $hookInput.tool_input.file_path
    } catch { }
}

# Path filter: only when editing backend schema
if (-not $filePath -or $filePath -notmatch 'backend[\\/]app[\\/]schemas[\\/]') {
    exit 0
}

# Real match - output reminder
$msg = "[remind] backend Schema changed ($filePath). Run: cd frontend && npm run type:sync:full"
# ⚠️ 2026-08-30：原本是**扁平**的 `@{hookEventName; additionalContext}`，
# 而正確形狀是**巢狀在 hookSpecificOutput 底下**（同目錄的 `auto-approve.ps1`
# 就是對的那份）。實測扁平版的提醒**從來沒有到達過 Claude**：
# 建立一個 backend/app/schemas/ 底下的檔案，畫面上什麼都不會出現。
# ⇒ 這四支 remind-* 從寫好那天起就是啞的。
$context = @{
    hookSpecificOutput = @{
        hookEventName = "PostToolUse"
        additionalContext = $msg
    }
} | ConvertTo-Json -Compress -Depth 5

Write-Output $context
exit 0
