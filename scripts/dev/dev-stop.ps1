# =============================================================================
# CK_Missive - 開發環境停止腳本
# =============================================================================
# 使用方式：
#   .\dev-stop.ps1              # 停止 PM2 + Docker 基礎設施
#   .\dev-stop.ps1 -KeepInfra   # 僅停止 PM2，保留 PostgreSQL/Redis
#   .\dev-stop.ps1 -All         # 停止所有（含 Docker 完整環境）
#
# Version: 1.0.0
# Created: 2026-02-09
# =============================================================================

param(
    [switch]$KeepInfra,
    [switch]$All
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Write-Info { param([string]$msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-OK { param([string]$msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== CK_Missive Development Environment Shutdown ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop PM2 services
Write-Info "Stopping PM2 services..."
try {
    pm2 stop all 2>$null | Out-Null
    Write-OK "PM2 services stopped"
} catch {
    Write-Warn "PM2 not running or not available"
}

# Step 2: Stop Docker infrastructure (unless -KeepInfra)
if (-not $KeepInfra) {
    Set-Location $ProjectRoot
    Write-Info "Stopping Docker infrastructure..."
    try {
        docker compose -f docker-compose.infra.yml down 2>$null | Out-Null
        Write-OK "Docker infrastructure (PostgreSQL + Redis) stopped"
    } catch {
        Write-Warn "Docker infrastructure was not running"
    }
} else {
    Write-Info "Keeping Docker infrastructure running (-KeepInfra)"
}

# Step 3: If -All, also stop full Docker containers
if ($All) {
    Set-Location $ProjectRoot
    Write-Info "Stopping all Docker containers..."
    try {
        docker compose -f docker-compose.dev.yml down --remove-orphans 2>$null | Out-Null
        Write-OK "All Docker containers stopped"
    } catch {
        Write-Warn "No full Docker containers to stop"
    }
}

Write-Host ""
Write-OK "Shutdown complete."
Write-Host ""
