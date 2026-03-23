# Careful Guard Hook (v1.0.0)
# PreToolUse: 攔截危險命令並警告
# 協議: 從 stdin 讀取 JSON，檢查 Bash 命令是否包含危險操作

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
$toolInput = $hookInput.tool_input

# 只檢查 Bash 工具
if ($toolName -ne "Bash") { exit 0 }

$command = $toolInput.command
if (-not $command) { exit 0 }

# === 危險命令模式 ===

# Level 1: CRITICAL — 幾乎永遠不該自動執行
$criticalPatterns = @(
    @{ Pattern = 'rm\s+-rf\s+(/|~|\$HOME|\.\.)'; Desc = 'rm -rf 根目錄/家目錄/上層目錄' },
    @{ Pattern = 'DROP\s+(TABLE|DATABASE|SCHEMA)'; Desc = 'SQL DROP 操作' },
    @{ Pattern = 'TRUNCATE\s+TABLE'; Desc = 'SQL TRUNCATE 操作' },
    @{ Pattern = 'DELETE\s+FROM\s+\S+\s*(;|$)'; Desc = 'SQL DELETE 全表（無 WHERE）' },
    @{ Pattern = 'git\s+push\s+.*--force\s+.*main'; Desc = 'Force push 到 main' },
    @{ Pattern = 'git\s+push\s+.*--force\s+.*master'; Desc = 'Force push 到 master' },
    @{ Pattern = 'git\s+reset\s+--hard\s+origin'; Desc = 'Git hard reset 到 remote' },
    @{ Pattern = 'chmod\s+-R\s+777'; Desc = '遞迴設定 777 權限' },
    @{ Pattern = 'mkfs\.'; Desc = '格式化磁碟' },
    @{ Pattern = '>\s*/dev/sd[a-z]'; Desc = '直接寫入磁碟裝置' }
)

# Level 2: WARNING — 需確認但非致命
$warningPatterns = @(
    @{ Pattern = 'rm\s+-rf\s+'; Desc = 'rm -rf（非根目錄）' },
    @{ Pattern = 'git\s+push\s+.*--force'; Desc = 'Git force push' },
    @{ Pattern = 'git\s+reset\s+--hard'; Desc = 'Git hard reset' },
    @{ Pattern = 'git\s+branch\s+-D'; Desc = 'Git 強制刪除分支' },
    @{ Pattern = 'git\s+checkout\s+--\s+\.'; Desc = 'Git 放棄所有變更' },
    @{ Pattern = 'git\s+clean\s+-fd'; Desc = 'Git 清除未追蹤檔案' },
    @{ Pattern = 'git\s+stash\s+drop'; Desc = 'Git stash drop' },
    @{ Pattern = 'npm\s+cache\s+clean\s+--force'; Desc = 'npm cache 強制清除' },
    @{ Pattern = 'pip\s+uninstall\s+-y'; Desc = 'pip 無確認解除安裝' },
    @{ Pattern = 'docker\s+(rm|rmi)\s+-f'; Desc = 'Docker 強制刪除' },
    @{ Pattern = 'docker\s+system\s+prune'; Desc = 'Docker 系統清理' },
    @{ Pattern = 'ALTER\s+TABLE.*DROP'; Desc = 'SQL ALTER TABLE DROP' },
    @{ Pattern = 'kill\s+-9'; Desc = '強制殺進程' },
    @{ Pattern = 'alembic\s+downgrade'; Desc = 'Alembic 遷移降級' }
)

# 檢查 CRITICAL 模式
foreach ($p in $criticalPatterns) {
    if ($command -match $p.Pattern) {
        [Console]::Error.WriteLine("[CAREFUL] CRITICAL: $($p.Desc) -- 此命令可能造成不可逆的破壞。命令: $command")
        exit 2
    }
}

# 檢查 WARNING 模式
foreach ($p in $warningPatterns) {
    if ($command -match $p.Pattern) {
        [Console]::Error.WriteLine("[CAREFUL] WARNING: $($p.Desc) -- 請確認此操作的必要性。命令: $command")
        exit 2
    }
}

exit 0
