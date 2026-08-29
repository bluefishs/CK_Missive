# Remind Alembic Migration Hook (B-Plan v1.0)
# PostToolUse: remind alembic migration after ORM model edit
# Replaces type:"prompt" anti-pattern (unconditional inject caused stopped continuation)

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

# Path filter: only when editing ORM model files
if (-not $filePath -or $filePath -notmatch 'backend[\\/]app[\\/]extended[\\/]models') {
    exit 0
}

# Real match - output reminder
$msg = "[remind] ORM model changed ($filePath). Run: cd backend && alembic revision --autogenerate -m 'desc'"
# Correct shape: everything nests under hookSpecificOutput.
# The flat form (hookEventName/additionalContext at top level) does not match
# the documented contract, nor the working example in auto-approve.ps1.
# See docs/architecture/LESSONS_REGISTRY.md L114 (2026-08-30).
$context = @{
    hookSpecificOutput = @{
        hookEventName = "PostToolUse"
        additionalContext = $msg
    }
} | ConvertTo-Json -Compress -Depth 5

Write-Output $context
exit 0
