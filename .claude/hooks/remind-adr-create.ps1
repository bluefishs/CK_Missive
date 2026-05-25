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
$context = @{
    hookEventName = "PostToolUse"
    additionalContext = $msg
} | ConvertTo-Json -Compress

Write-Output $context
exit 0
