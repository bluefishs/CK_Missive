<#
.SYNOPSIS
    CK_Missive Configuration Consistency Check

.DESCRIPTION
    Checks project configuration file consistency

.NOTES
    Version: 1.0.0
    Date: 2026-01-18
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================"
Write-Host "  CK_Missive Configuration Check"
Write-Host "========================================"
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$HasErrors = $false

# Check 1: Root .env
Write-Host "[1/4] Checking root .env..." -ForegroundColor Yellow
$RootEnvFile = Join-Path $ProjectRoot ".env"

if (Test-Path $RootEnvFile) {
    Write-Host "  OK: .env exists" -ForegroundColor Green
} else {
    Write-Host "  ERROR: .env not found" -ForegroundColor Red
    $HasErrors = $true
}

# Check 2: backend/.env should not exist
Write-Host ""
Write-Host "[2/4] Checking for duplicate backend/.env..." -ForegroundColor Yellow
$BackendEnvFile = Join-Path $ProjectRoot "backend\.env"

if (Test-Path $BackendEnvFile) {
    Write-Host "  WARNING: backend/.env exists (may cause conflicts)" -ForegroundColor Yellow
} else {
    Write-Host "  OK: No duplicate backend/.env" -ForegroundColor Green
}

# Check 3: Docker container
Write-Host ""
Write-Host "[3/4] Checking Docker PostgreSQL..." -ForegroundColor Yellow

$ContainerStatus = docker ps --filter "name=ck_missive_postgres_dev" --format "{{.Status}}" 2>$null
if ($ContainerStatus -like "Up*") {
    Write-Host "  OK: PostgreSQL container running" -ForegroundColor Green
} else {
    Write-Host "  WARNING: PostgreSQL container not running" -ForegroundColor Yellow
}

# Check 4: Python config
Write-Host ""
Write-Host "[4/4] Validating Python config..." -ForegroundColor Yellow

Push-Location (Join-Path $ProjectRoot "backend")
$ConfigResult = python -c "from app.core.config import settings; print('OK')" 2>&1
if ($ConfigResult -eq "OK") {
    Write-Host "  OK: Python config loaded" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Python config issue" -ForegroundColor Yellow
}
Pop-Location

# Summary
Write-Host ""
Write-Host "========================================"
if ($HasErrors) {
    Write-Host "  Check completed with errors" -ForegroundColor Red
} else {
    Write-Host "  All checks passed" -ForegroundColor Green
}
Write-Host "========================================"
Write-Host ""
