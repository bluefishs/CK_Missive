# Remind Route Sync Hook (B-Plan v1.0)
# PostToolUse: remind 4-way sync after route file edit
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

# Path filter: route-related files
$routePatterns = @(
    'frontend[\\/]src[\\/]router[\\/]types\.ts$',
    'frontend[\\/]src[\\/]router[\\/]AppRouter\.tsx$'
)

$matched = $false
foreach ($pattern in $routePatterns) {
    if ($filePath -match $pattern) {
        $matched = $true
        break
    }
}

if (-not $matched) {
    exit 0
}

# Real match - output reminder
$msg = "[remind] route change detected ($filePath). 4-way sync: 1) router/types.ts 2) AppRouter.tsx 3) init_navigation_data.py 4) navigation_validator.py (auto). post-commit hook auto-syncs DB nav."
$context = @{
    hookEventName = "PostToolUse"
    additionalContext = $msg
} | ConvertTo-Json -Compress

Write-Output $context
exit 0
