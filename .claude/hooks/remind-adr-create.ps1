# Remind ADR Create Hook (B-Plan v1.0)
# PostToolUse: remind ADR creation after architectural change
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

# Path filter: architectural change patterns
$architecturalPatterns = @(
    'backend[\\/]app[\\/]extended[\\/]models',
    'backend[\\/]app[\\/]core[\\/]dependencies\.py',
    'frontend[\\/]src[\\/]router[\\/]',
    'docker-compose.*\.yml$',
    '\.env$'
)

$matched = $false
foreach ($pattern in $architecturalPatterns) {
    if ($filePath -match $pattern) {
        $matched = $true
        break
    }
}

if (-not $matched) {
    exit 0
}

# Real match - output reminder
$msg = "[remind] architectural change detected ($filePath). Consider /adr new 'description' to create ADR."
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
