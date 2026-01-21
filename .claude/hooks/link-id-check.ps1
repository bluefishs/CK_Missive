#!/usr/bin/env pwsh
<#
.SYNOPSIS
    link_id usage pattern check script

.DESCRIPTION
    Check frontend code for dangerous link_id usage patterns:
    1. link_id ?? id fallback logic
    2. link_id || id fallback logic
    3. any type that may bypass type checking

.NOTES
    Version: 1.0.0
    Date: 2026-01-21
    Reference: docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md
#>

param(
    [switch]$Verbose,
    [switch]$FailOnWarning
)

$ErrorActionPreference = "Continue"
$script:hasErrors = $false
$script:hasWarnings = $false

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "link_id Usage Pattern Check" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$frontendPath = Join-Path $PSScriptRoot "..\..\frontend\src"

# Check 1: Dangerous fallback logic link_id ??
Write-Host "[Check 1] Search dangerous pattern: link_id ??" -ForegroundColor Yellow
$pattern1 = Select-String -Path "$frontendPath\**\*.tsx","$frontendPath\**\*.ts" -Pattern "link_id\s*\?\?" -ErrorAction SilentlyContinue
if ($pattern1) {
    Write-Host "  [ERROR] Found dangerous fallback logic:" -ForegroundColor Red
    foreach ($match in $pattern1) {
        Write-Host "    $($match.Path):$($match.LineNumber)" -ForegroundColor Red
        Write-Host "      $($match.Line.Trim())" -ForegroundColor DarkRed
    }
    $script:hasErrors = $true
} else {
    Write-Host "  [PASS] No link_id ?? pattern found" -ForegroundColor Green
}

# Check 2: Dangerous fallback logic link_id ||
Write-Host ""
Write-Host "[Check 2] Search dangerous pattern: link_id ||" -ForegroundColor Yellow
$pattern2 = Select-String -Path "$frontendPath\**\*.tsx","$frontendPath\**\*.ts" -Pattern "link_id\s*\|\|" -ErrorAction SilentlyContinue
if ($pattern2) {
    Write-Host "  [ERROR] Found dangerous fallback logic:" -ForegroundColor Red
    foreach ($match in $pattern2) {
        Write-Host "    $($match.Path):$($match.LineNumber)" -ForegroundColor Red
        Write-Host "      $($match.Line.Trim())" -ForegroundColor DarkRed
    }
    $script:hasErrors = $true
} else {
    Write-Host "  [PASS] No link_id || pattern found" -ForegroundColor Green
}

# Check 3: any type usage in pages (may bypass type checking)
Write-Host ""
Write-Host "[Check 3] Search any type in pages (potential risk)" -ForegroundColor Yellow
$pagesPath = Join-Path $frontendPath "pages"
$anyPatterns = Select-String -Path "$pagesPath\*.tsx" -Pattern ":\s*any\b|as\s+any\b" -ErrorAction SilentlyContinue

# Filter link-related any usage
$linkRelatedAny = $anyPatterns | Where-Object {
    $_.Line -match "link|dispatch|project|unlink" -and $_.Line -notmatch "error:\s*any"
}

if ($linkRelatedAny) {
    Write-Host "  [WARN] Found link-related any type usage:" -ForegroundColor Yellow
    foreach ($match in $linkRelatedAny) {
        $fileName = Split-Path $match.Path -Leaf
        Write-Host "    ${fileName}:$($match.LineNumber)" -ForegroundColor Yellow
        if ($Verbose) {
            Write-Host "      $($match.Line.Trim())" -ForegroundColor DarkYellow
        }
    }
    $script:hasWarnings = $true
} else {
    Write-Host "  [PASS] No link-related any usage found" -ForegroundColor Green
}

# Check 4: Confirm BaseLink interface exists
Write-Host ""
Write-Host "[Check 4] Confirm BaseLink interface definition" -ForegroundColor Yellow
$typesPath = Join-Path $frontendPath "types\api.ts"
if (Test-Path $typesPath) {
    $baseLink = Select-String -Path $typesPath -Pattern "interface BaseLink" -ErrorAction SilentlyContinue
    if ($baseLink) {
        Write-Host "  [PASS] BaseLink interface defined in types/api.ts" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] BaseLink interface not found in types/api.ts" -ForegroundColor Red
        $script:hasErrors = $true
    }
} else {
    Write-Host "  [ERROR] types/api.ts file not found" -ForegroundColor Red
    $script:hasErrors = $true
}

# Check 5: Confirm defensive check pattern exists
Write-Host ""
Write-Host "[Check 5] Confirm defensive check patterns" -ForegroundColor Yellow
$defensiveCheck = Select-String -Path "$pagesPath\*.tsx" -Pattern "link_id\s*===\s*undefined|link_id\s*!==\s*undefined" -ErrorAction SilentlyContinue
$checkCount = 0
if ($defensiveCheck) {
    $checkCount = ($defensiveCheck | Measure-Object).Count
}
Write-Host "  [INFO] Found $checkCount defensive checks" -ForegroundColor Cyan

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($script:hasErrors) {
    Write-Host "[FAIL] Check failed, please fix errors above" -ForegroundColor Red
    exit 1
} elseif ($script:hasWarnings -and $FailOnWarning) {
    Write-Host "[WARN] Potential risks exist, please review warnings above" -ForegroundColor Yellow
    exit 1
} elseif ($script:hasWarnings) {
    Write-Host "[PASS] Check passed with warnings" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "[SUCCESS] All checks passed" -ForegroundColor Green
    exit 0
}
