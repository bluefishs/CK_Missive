# ============================================================
# ADR-0010 Tier 5 - pre-commit hook PowerShell installer
# ============================================================
#
# PowerShell version (no bash / WSL required).
# Usage in PowerShell:
#   .\scripts\install-pre-commit-hook.ps1
#   .\scripts\install-pre-commit-hook.ps1 -Check   # dry-run preview
#
# Equivalent to install-pre-commit-hook.sh (bash version).
#
# Why this exists: 2026-05-27 owner ran `bash` in PowerShell triggering
# WSL relay failure (execvpe(/bin/bash) failed). Pure PowerShell removes
# bash/WSL dependency for cross-environment portability.
#
# Exit codes:
#   0  installed (or -Check mode)
#   1  source not found
#   2  existing non-matching hook (manual merge required)

param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"

# Get repo root
$RepoRoot = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Not inside a git repo" -ForegroundColor Red
    exit 1
}
$RepoRoot = $RepoRoot.Trim()

$HookSrc = Join-Path $RepoRoot "scripts\pre-commit-block-destructive.sh"
$HookDst = Join-Path $RepoRoot ".git\hooks\pre-commit"

if (-not (Test-Path $HookSrc)) {
    Write-Host "[ERROR] Source hook not found: $HookSrc" -ForegroundColor Red
    Write-Host "        First distribute pre-commit-block-destructive.sh to target repo scripts/" -ForegroundColor Yellow
    exit 1
}

# Warn if existing hook is not ours
if ((Test-Path $HookDst) -and -not (Select-String -Path $HookDst -Pattern "pre-commit-block-destructive" -Quiet -ErrorAction SilentlyContinue)) {
    Write-Host "[WARN] $HookDst exists but is not the ADR-0010 hook" -ForegroundColor Yellow
    Write-Host "       First 5 lines of existing hook:" -ForegroundColor Yellow
    Get-Content $HookDst -TotalCount 5 | ForEach-Object { Write-Host "         $_" }
    Write-Host ""
    Write-Host "       Manual merge required. Add this chain to your existing hook:" -ForegroundColor Yellow
    Write-Host '         DESTRUCTIVE_HOOK="$(git rev-parse --show-toplevel)/scripts/pre-commit-block-destructive.sh"'
    Write-Host '         if [ -x "$DESTRUCTIVE_HOOK" ]; then'
    Write-Host '             bash "$DESTRUCTIVE_HOOK" || exit $?'
    Write-Host '         fi'
    exit 2
}

if ($Check) {
    Write-Host "[dry-run] Would copy hook:" -ForegroundColor Cyan
    Write-Host "  $HookDst <- $HookSrc"
    exit 0
}

# Ensure .git/hooks directory exists
$HooksDir = Split-Path $HookDst -Parent
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Force -Path $HooksDir | Out-Null
}

# Copy (Windows git hooks dont support symlinks reliably; cp is the standard)
Copy-Item -Path $HookSrc -Destination $HookDst -Force

Write-Host "[OK] pre-commit hook installed:" -ForegroundColor Green
Write-Host "     $HookDst"
Write-Host "     (copy of $HookSrc - rerun installer to sync source updates)"
Write-Host ""
Write-Host "Verify:" -ForegroundColor Cyan
Write-Host "  'DROP TABLE foo;' | Out-File -Encoding utf8 test-DELETEME.sql"
Write-Host "  git add test-DELETEME.sql"
Write-Host "  git commit -m test"
Write-Host "  # Should see: [pre-commit] X Rule D1-DropTable blocked"
Write-Host "  git restore --staged test-DELETEME.sql"
Write-Host "  Remove-Item test-DELETEME.sql"
Write-Host ""
Write-Host "Emergency bypass (not recommended):" -ForegroundColor Yellow
Write-Host '  $env:ALLOW_DESTRUCTIVE = "1"; git commit ...; $env:ALLOW_DESTRUCTIVE = $null'
