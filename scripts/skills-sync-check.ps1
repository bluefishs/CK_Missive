# Skills Sync Check Script
# Version: 1.0.0
# Date: 2026-01-28

param([switch]$Verbose)

$ErrorActionPreference = "Continue"
$errors = [System.Collections.ArrayList]::new()
$warnings = [System.Collections.ArrayList]::new()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Skills Sync Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Skills files
Write-Host "1. Checking Skills files..." -ForegroundColor White

$expectedSkills = @(
    "document-management.md",
    "calendar-integration.md",
    "api-development.md",
    "database-schema.md",
    "testing-guide.md",
    "frontend-architecture.md",
    "error-handling.md",
    "security-hardening.md",
    "type-management.md",
    "api-serialization.md",
    "python-common-pitfalls.md",
    "unicode-handling.md",
    "database-performance.md",
    "development-environment.md"
)

$skillsPath = ".claude/skills"
$missingSkills = 0

foreach ($skill in $expectedSkills) {
    $fullPath = Join-Path $skillsPath $skill
    if (-not (Test-Path $fullPath)) {
        Write-Host "   [FAIL] Missing: $skill" -ForegroundColor Red
        [void]$errors.Add("Missing Skill: $skill")
        $missingSkills++
    } elseif ($Verbose) {
        Write-Host "   [PASS] $skill" -ForegroundColor Green
    }
}

if ($missingSkills -eq 0) {
    Write-Host "   [PASS] All $($expectedSkills.Count) Skills files exist" -ForegroundColor Green
}

# 2. Check Commands files
Write-Host ""
Write-Host "2. Checking Commands files..." -ForegroundColor White

$expectedCommands = @(
    "pre-dev-check.md",
    "route-sync-check.md",
    "api-check.md",
    "type-sync.md",
    "dev-check.md",
    "data-quality-check.md",
    "db-backup.md",
    "csv-import-validate.md",
    "security-audit.md",
    "performance-check.md",
    "superpowers/brainstorm.md",
    "superpowers/write-plan.md",
    "superpowers/execute-plan.md"
)

$commandsPath = ".claude/commands"
$missingCommands = 0

foreach ($cmd in $expectedCommands) {
    $fullPath = Join-Path $commandsPath $cmd
    if (-not (Test-Path $fullPath)) {
        Write-Host "   [FAIL] Missing: $cmd" -ForegroundColor Red
        [void]$errors.Add("Missing Command: $cmd")
        $missingCommands++
    } elseif ($Verbose) {
        Write-Host "   [PASS] $cmd" -ForegroundColor Green
    }
}

if ($missingCommands -eq 0) {
    Write-Host "   [PASS] All $($expectedCommands.Count) Commands files exist" -ForegroundColor Green
}

# 3. Check Hooks files
Write-Host ""
Write-Host "3. Checking Hooks files..." -ForegroundColor White

$expectedHooks = @(
    "typescript-check.ps1",
    "python-lint.ps1",
    "validate-file-location.ps1",
    "route-sync-check.ps1",
    "api-serialization-check.ps1",
    "link-id-check.ps1",
    "link-id-validation.ps1",
    "performance-check.ps1"
)

$hooksPath = ".claude/hooks"
$missingHooks = 0

foreach ($hook in $expectedHooks) {
    $fullPath = Join-Path $hooksPath $hook
    if (-not (Test-Path $fullPath)) {
        Write-Host "   [FAIL] Missing: $hook" -ForegroundColor Red
        [void]$errors.Add("Missing Hook: $hook")
        $missingHooks++
    } elseif ($Verbose) {
        Write-Host "   [PASS] $hook" -ForegroundColor Green
    }
}

if ($missingHooks -eq 0) {
    Write-Host "   [PASS] All $($expectedHooks.Count) Hooks files exist" -ForegroundColor Green
}

# 4. Check Agents files
Write-Host ""
Write-Host "4. Checking Agents files..." -ForegroundColor White

$expectedAgents = @(
    "code-review.md",
    "api-design.md",
    "bug-investigator.md"
)

$agentsPath = ".claude/agents"
$missingAgents = 0

foreach ($agent in $expectedAgents) {
    $fullPath = Join-Path $agentsPath $agent
    if (-not (Test-Path $fullPath)) {
        Write-Host "   [FAIL] Missing: $agent" -ForegroundColor Red
        [void]$errors.Add("Missing Agent: $agent")
        $missingAgents++
    } elseif ($Verbose) {
        Write-Host "   [PASS] $agent" -ForegroundColor Green
    }
}

if ($missingAgents -eq 0) {
    Write-Host "   [PASS] All $($expectedAgents.Count) Agents files exist" -ForegroundColor Green
}

# 5. Check settings.json
Write-Host ""
Write-Host "5. Checking settings.json..." -ForegroundColor White

$settingsPath = ".claude/settings.json"
if (Test-Path $settingsPath) {
    try {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
        $inheritPaths = $settings.skills.inherit

        $inherit1 = ".claude/skills/_shared/shared"
        $inherit2 = ".claude/skills/_shared/backend"

        if ($inheritPaths -contains $inherit1) {
            Write-Host "   [PASS] inherit: _shared/shared" -ForegroundColor Green
        } else {
            Write-Host "   [FAIL] Missing inherit: _shared/shared" -ForegroundColor Red
            [void]$errors.Add("settings.json missing inherit config")
        }

        if ($inheritPaths -contains $inherit2) {
            Write-Host "   [PASS] inherit: _shared/backend" -ForegroundColor Green
        } else {
            Write-Host "   [FAIL] Missing inherit: _shared/backend" -ForegroundColor Red
            [void]$errors.Add("settings.json missing inherit config")
        }
    } catch {
        Write-Host "   [FAIL] settings.json parse error" -ForegroundColor Red
        [void]$errors.Add("settings.json parse error")
    }
} else {
    Write-Host "   [FAIL] settings.json not found" -ForegroundColor Red
    [void]$errors.Add("settings.json not found")
}

# 6. Check README files
Write-Host ""
Write-Host "6. Checking README files..." -ForegroundColor White

$readmeFiles = @(
    ".claude/skills/README.md",
    ".claude/hooks/README.md"
)

foreach ($readme in $readmeFiles) {
    if (Test-Path $readme) {
        Write-Host "   [PASS] $readme" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] $readme not found" -ForegroundColor Yellow
        [void]$warnings.Add("README not found: $readme")
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalChecks = $expectedSkills.Count + $expectedCommands.Count + $expectedHooks.Count + $expectedAgents.Count
$failedChecks = $missingSkills + $missingCommands + $missingHooks + $missingAgents
$passedChecks = $totalChecks - $failedChecks

Write-Host "Total checks: $totalChecks"
Write-Host "Passed: $passedChecks" -ForegroundColor Green

if ($errors.Count -gt 0) {
    Write-Host "Errors: $($errors.Count)" -ForegroundColor Red
} else {
    Write-Host "Errors: 0" -ForegroundColor Green
}

if ($warnings.Count -gt 0) {
    Write-Host "Warnings: $($warnings.Count)" -ForegroundColor Yellow
} else {
    Write-Host "Warnings: 0" -ForegroundColor Green
}

Write-Host ""
if ($errors.Count -eq 0) {
    Write-Host "[SUCCESS] Skills sync check passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAILED] Skills sync check failed!" -ForegroundColor Red
    Write-Host "Error list:" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "  - $err" -ForegroundColor Red
    }
    exit 1
}
