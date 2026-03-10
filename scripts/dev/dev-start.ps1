# =============================================================================
# CK_Missive - 統一開發環境管理腳本
# =============================================================================
# 預設：混合模式（Docker 基礎設施 + PM2 應用服務）
#
# 使用方式：
#   .\dev-start.ps1              # 啟動混合模式（推薦）
#   .\dev-start.ps1 -FullDocker  # 全 Docker 模式
#   .\dev-start.ps1 -Stop        # 停止所有服務
#   .\dev-start.ps1 -Status      # 查看狀態
#   .\dev-start.ps1 -Restart     # 重啟 PM2 服務
#
# Version: 2.0.0
# Created: 2026-02-09
# =============================================================================

param(
    [switch]$FullDocker,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Restart
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Info { param([string]$msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-OK { param([string]$msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param([string]$msg) Write-Host "[ERR]  $msg" -ForegroundColor Red }

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$ServiceName,
        [int]$TimeoutSeconds = 30
    )
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("localhost", $Port)
            $tcp.Close()
            return $true
        } catch {
            Start-Sleep -Seconds 2
            $elapsed += 2
        }
    }
    return $false
}

function Wait-ForHealth {
    param(
        [string]$Url,
        [string]$ServiceName,
        [int]$TimeoutSeconds = 60
    )
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            # 繼續等待
        }
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
    return $false
}

function Stop-ConflictingContainers {
    Write-Info "Checking for conflicting Docker containers..."
    $containers = @("ck_missive_backend_dev", "ck_missive_frontend_dev")
    foreach ($name in $containers) {
        $running = docker ps --filter "name=$name" --format "{{.Names}}" 2>$null
        if ($running) {
            Write-Warn "Stopping conflicting container: $name"
            docker stop $name 2>$null | Out-Null
        }
    }
}

function Ensure-Directories {
    $dirs = @("logs", "backend\logs", "frontend\logs", "backend\uploads")
    foreach ($dir in $dirs) {
        $path = Join-Path $ProjectRoot $dir
        if (-not (Test-Path $path)) {
            New-Item -Path $path -ItemType Directory -Force | Out-Null
        }
    }
}

# ============================================================================
# Status Mode
# ============================================================================

function Show-Status {
    Write-Host ""
    Write-Host "=== CK_Missive Development Environment Status ===" -ForegroundColor Cyan
    Write-Host ""

    # Docker containers
    Write-Host "--- Docker Containers ---" -ForegroundColor Yellow
    try {
        docker ps --filter "name=ck_missive" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    } catch {
        Write-Warn "Docker CLI not available"
    }
    Write-Host ""

    # PM2 processes
    Write-Host "--- PM2 Processes ---" -ForegroundColor Yellow
    try {
        pm2 list 2>$null
    } catch {
        Write-Warn "PM2 not available"
    }
    Write-Host ""

    # Port status
    Write-Host "--- Port Status ---" -ForegroundColor Yellow
    $ports = @(
        @{ Port = 5434; Name = "PostgreSQL" },
        @{ Port = 6380; Name = "Redis" },
        @{ Port = 8001; Name = "Backend API" },
        @{ Port = 3000; Name = "Frontend" }
    )
    foreach ($p in $ports) {
        try {
            $conn = Get-NetTCPConnection -LocalPort $p.Port -State Listen -ErrorAction SilentlyContinue
            if ($conn) {
                $pid = $conn[0].OwningProcess
                $proc = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
                Write-OK "$($p.Name) (port $($p.Port)): LISTENING (PID: $pid, $proc)"
            } else {
                Write-Warn "$($p.Name) (port $($p.Port)): NOT LISTENING"
            }
        } catch {
            Write-Warn "$($p.Name) (port $($p.Port)): CHECK FAILED"
        }
    }
    Write-Host ""

    # Health endpoints
    Write-Host "--- Health Endpoints ---" -ForegroundColor Yellow
    try {
        $backendHealth = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-OK "Backend: $($backendHealth.StatusCode) OK"
    } catch {
        Write-Warn "Backend: NOT RESPONDING"
    }
    try {
        $frontendHealth = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-OK "Frontend: $($frontendHealth.StatusCode) OK"
    } catch {
        Write-Warn "Frontend: NOT RESPONDING"
    }
    Write-Host ""
}

# ============================================================================
# Stop Mode
# ============================================================================

function Stop-All {
    Write-Info "Stopping all services..."

    # Stop PM2
    try {
        pm2 stop all 2>$null | Out-Null
        Write-OK "PM2 services stopped"
    } catch {
        Write-Warn "PM2 not running or not available"
    }

    # Stop Docker infra
    Set-Location $ProjectRoot
    try {
        docker compose -f docker-compose.infra.yml down 2>$null | Out-Null
        Write-OK "Docker infrastructure stopped"
    } catch {
        Write-Warn "docker-compose.infra.yml down failed (may not be running)"
    }

    # Also stop any full-Docker containers
    try {
        docker compose -f docker-compose.dev.yml down --remove-orphans 2>$null | Out-Null
    } catch {
        # Ignore
    }

    Write-OK "All services stopped."
}

# ============================================================================
# Hybrid Mode (Default)
# ============================================================================

function Start-Hybrid {
    Write-Host ""
    Write-Host "=== CK_Missive Hybrid Development Environment ===" -ForegroundColor Cyan
    Write-Host "    Docker: PostgreSQL + Redis" -ForegroundColor Gray
    Write-Host "    PM2:    Backend (FastAPI) + Frontend (Vite)" -ForegroundColor Gray
    Write-Host ""

    Set-Location $ProjectRoot

    # Step 1: Prerequisites
    Write-Info "Step 1: Checking prerequisites..."

    # Check Docker
    try {
        docker info 2>$null | Out-Null
        Write-OK "Docker is running"
    } catch {
        Write-Err "Docker is not running. Please start Docker Desktop first."
        exit 1
    }

    # Check .env
    if (-not (Test-Path ".env")) {
        Write-Err ".env file not found. Please copy .env.example to .env"
        exit 1
    }
    Write-OK ".env file found"

    # Ensure directories
    Ensure-Directories

    # Step 2: Stop conflicting Docker app containers
    Write-Info "Step 2: Stopping conflicting Docker app containers..."
    Stop-ConflictingContainers
    Write-OK "No conflicting containers"

    # Step 3: Start Docker infrastructure
    Write-Info "Step 3: Starting Docker infrastructure (PostgreSQL + Redis)..."
    docker compose -f docker-compose.infra.yml up -d 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to start Docker infrastructure"
        exit 1
    }
    Write-OK "Docker infrastructure started"

    # Step 4: Wait for PostgreSQL
    Write-Info "Step 4: Waiting for PostgreSQL (port 5434, max 30s)..."
    if (Wait-ForPort -Port 5434 -ServiceName "PostgreSQL" -TimeoutSeconds 30) {
        Write-OK "PostgreSQL is ready"
    } else {
        Write-Err "PostgreSQL did not start within 30s"
        exit 1
    }

    # Step 5: Wait for Redis
    Write-Info "Step 5: Waiting for Redis (port 6380, max 15s)..."
    if (Wait-ForPort -Port 6380 -ServiceName "Redis" -TimeoutSeconds 15) {
        Write-OK "Redis is ready"
    } else {
        Write-Warn "Redis not available. AI cache will use in-memory fallback."
    }

    # Step 6: Start PM2
    Write-Info "Step 6: Starting PM2 services..."
    pm2 start ecosystem.config.js 2>&1 | Out-Null
    Write-OK "PM2 services starting"

    # Step 7: Wait for backend health
    Write-Info "Step 7: Waiting for backend health (max 90s)..."
    if (Wait-ForHealth -Url "http://localhost:8001/health" -ServiceName "Backend" -TimeoutSeconds 90) {
        Write-OK "Backend is healthy"
    } else {
        Write-Warn "Backend health check timed out. Check: pm2 logs ck-backend"
    }

    # Step 8: Display URLs
    Write-Host ""
    Write-Host "=== Development Environment Ready ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
    Write-Host "  Backend:   http://localhost:8001" -ForegroundColor White
    Write-Host "  API Docs:  http://localhost:8001/api/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "  Commands:" -ForegroundColor Yellow
    Write-Host "    .\scripts\dev-start.ps1 -Status    # Check status" -ForegroundColor Gray
    Write-Host "    .\scripts\dev-start.ps1 -Restart   # Restart PM2" -ForegroundColor Gray
    Write-Host "    .\scripts\dev-stop.ps1             # Stop all" -ForegroundColor Gray
    Write-Host "    pm2 logs                           # View logs" -ForegroundColor Gray
    Write-Host ""
}

# ============================================================================
# Full Docker Mode
# ============================================================================

function Start-FullDocker {
    Write-Host ""
    Write-Host "=== CK_Missive Full Docker Development ===" -ForegroundColor Cyan
    Write-Host ""

    Set-Location $ProjectRoot

    # Stop PM2 if running
    try {
        pm2 stop all 2>$null | Out-Null
        Write-OK "PM2 services stopped"
    } catch {
        # Ignore
    }

    # Start full Docker
    Write-Info "Starting docker-compose.dev.yml (all services in Docker)..."
    docker compose -f docker-compose.dev.yml up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to start Docker services"
        exit 1
    }

    Write-OK "Full Docker environment started"
    Write-Host ""
    Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
    Write-Host "  Backend:   http://localhost:8001" -ForegroundColor White
    Write-Host "  Adminer:   http://localhost:8080" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# Restart Mode
# ============================================================================

function Restart-PM2 {
    Write-Info "Restarting PM2 services..."
    pm2 restart all 2>&1 | Out-Null
    Write-OK "PM2 services restarted"

    Write-Info "Waiting for backend health..."
    if (Wait-ForHealth -Url "http://localhost:8001/health" -ServiceName "Backend" -TimeoutSeconds 90) {
        Write-OK "Backend is healthy"
    } else {
        Write-Warn "Backend health check timed out. Check: pm2 logs ck-backend"
    }
}

# ============================================================================
# Main
# ============================================================================

switch ($true) {
    $Stop {
        Stop-All
        break
    }
    $Status {
        Show-Status
        break
    }
    $Restart {
        Restart-PM2
        break
    }
    $FullDocker {
        Start-FullDocker
        break
    }
    default {
        Start-Hybrid
    }
}
