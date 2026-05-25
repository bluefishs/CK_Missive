# Remind Type Sync Hook (B-Plan v1.0)
# PostToolUse: remind type sync after backend schema edit
# Replaces type:"prompt" anti-pattern

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
$context = @{
    hookEventName = "PostToolUse"
    additionalContext = $msg
} | ConvertTo-Json -Compress

Write-Output $context
exit 0
