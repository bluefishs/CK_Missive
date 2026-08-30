# PermissionRequest Hook: 自動核准唯讀操作 (v1.0.0)
# 事件: PermissionRequest
# 自動 allow: Read, Glob, Grep, WebFetch, WebSearch, Task (Explore)
# 不介入: Edit, Write, Bash (交由使用者決定)


# 2026-08-30：輸出編碼明示 UTF-8。Windows 主控台預設 cp950，
# PowerShell 會用它編碼 stdout/stderr ⇒ 中文訊息以亂碼抵達 Claude。
# 這不是顯示問題：同日 validate-file-location 擋下 Write 時，
# 「檔案位置違規」實際收到的是 `?????m?H?W` —— 擋對了但看不懂為什麼。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }
$ErrorActionPreference = "SilentlyContinue"

# 從 stdin 讀取 hook 輸入 JSON
$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

if (-not $rawInput) {
    exit 0
}

try {
    $hookInput = $rawInput | ConvertFrom-Json
} catch {
    exit 0
}

$toolName = $hookInput.tool_name

# 定義自動核准的唯讀工具
$autoApproveTools = @(
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "ListMcpResourcesTool",
    "ReadMcpResourceTool",
    "ToolSearch"
)

# 定義自動核准的安全 Bash 命令模式
$safeBashPatterns = @(
    "^git (status|log|diff|branch|show|remote)",
    "^npm (test|run test|run lint)",
    "^npx (tsc|eslint)",
    "^python -m (pytest|py_compile|mypy)",
    "^docker (ps|images|logs)",
    "^pm2 (list|jlist|status|logs)"
)

$shouldAllow = $false

if ($autoApproveTools -contains $toolName) {
    $shouldAllow = $true
}

# 檢查 Bash 命令是否安全
if ($toolName -eq "Bash" -and $hookInput.tool_input.command) {
    $cmd = $hookInput.tool_input.command
    foreach ($pattern in $safeBashPatterns) {
        if ($cmd -match $pattern) {
            $shouldAllow = $true
            break
        }
    }
}

if ($shouldAllow) {
    # 輸出 JSON 允許決策
    $response = @{
        hookSpecificOutput = @{
            hookEventName = "PermissionRequest"
            decision = @{
                behavior = "allow"
            }
        }
    } | ConvertTo-Json -Depth 5 -Compress
    Write-Output $response
}

exit 0
