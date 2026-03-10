# ============================================================================
# CK_Missive Backend Startup Wrapper
#
# PM2 啟動前自動執行：
# Step 0:   端口衝突偵測（port 8001）
# Step 0.5: 基礎設施依賴檢查（PostgreSQL + Redis）
# Step 1:   安裝/更新 Python 依賴
# Step 2:   套用資料庫遷移 (Alembic)
# Step 3:   啟動 FastAPI 後端服務
#
# Version: 2.0.0
# Created: 2026-02-09
# Updated: 2026-02-09 - 新增端口衝突偵測與基礎設施檢查
# ============================================================================

$ErrorActionPreference = "Continue"

# Force UTF-8 encoding to prevent cp950 decode errors on Windows
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$BackendDir = Join-Path $PSScriptRoot "..\backend"
$ProjectRoot = Join-Path $PSScriptRoot ".."

# ============================================================================
# Step 0: 端口衝突偵測
# ============================================================================
Write-Host "[Step 0] Checking port 8001 availability..."

$portInUse = $false
try {
    $connections = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        $portInUse = $true
        $pid = $connections[0].OwningProcess
        $processName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName

        # 檢查是否為 Docker 容器佔用
        $dockerContainer = $null
        try {
            $dockerContainer = docker ps --filter "publish=8001" --format "{{.Names}}" 2>$null
        } catch {
            # Docker CLI 不可用，忽略
        }

        if ($dockerContainer) {
            Write-Host "[Step 0] ERROR: Port 8001 is occupied by Docker container: $dockerContainer" -ForegroundColor Red
            Write-Host "[Step 0] Fix: docker stop $dockerContainer" -ForegroundColor Yellow
            Write-Host "[Step 0] Or use infra-only mode: docker compose -f docker-compose.infra.yml up -d" -ForegroundColor Yellow
        } else {
            Write-Host "[Step 0] ERROR: Port 8001 is occupied by process: $processName (PID: $pid)" -ForegroundColor Red
            Write-Host "[Step 0] Please stop the process and retry." -ForegroundColor Yellow
        }
        exit 1
    }
    Write-Host "[Step 0] Port 8001 is available." -ForegroundColor Green
} catch {
    # Get-NetTCPConnection 可能在某些環境中失敗，繼續執行
    Write-Host "[Step 0] Port check skipped (Get-NetTCPConnection unavailable)."
}

# ============================================================================
# Step 0.5: 基礎設施依賴檢查
# ============================================================================
Write-Host "[Step 0.5] Checking infrastructure dependencies..."

# PostgreSQL 連線檢查（必要）
$pgReady = $false
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", 5434)
    $pgReady = $true
    $tcpClient.Close()
} catch {
    $pgReady = $false
}

if (-not $pgReady) {
    Write-Host "[Step 0.5] ERROR: PostgreSQL on port 5434 is not reachable." -ForegroundColor Red
    Write-Host "[Step 0.5] Start infrastructure:" -ForegroundColor Yellow
    Write-Host "[Step 0.5]   docker compose -f docker-compose.infra.yml up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "[Step 0.5] PostgreSQL on port 5434: OK" -ForegroundColor Green

# Redis 連線檢查（選用，失敗僅警告）
$redisReady = $false
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", 6380)
    $redisReady = $true
    $tcpClient.Close()
} catch {
    $redisReady = $false
}

if ($redisReady) {
    Write-Host "[Step 0.5] Redis on port 6380: OK" -ForegroundColor Green
} else {
    Write-Host "[Step 0.5] WARNING: Redis on port 6380 is not reachable. AI cache will use in-memory fallback." -ForegroundColor Yellow
}

# ============================================================================
# Step 1: 安裝/更新 Python 依賴
# ============================================================================
Set-Location $BackendDir

Write-Host "[Step 1] Checking Python dependencies..."
try {
    # Avoid capturing output with 2>&1 to prevent cp950 encoding errors on Windows
    pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[Step 1] Dependencies check completed."
    } else {
        Write-Host "[Step 1] WARNING: pip install returned exit code $LASTEXITCODE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[Step 1] WARNING: pip install failed: $_" -ForegroundColor Yellow
    Write-Host "[Step 1] Continuing with existing dependencies..."
}

# ============================================================================
# Step 2: 套用資料庫遷移
# ============================================================================
Write-Host "[Step 2] Checking database migrations..."
try {
    # Avoid capturing output with 2>&1 to prevent cp950 encoding errors on Windows
    python -m alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[Step 2] Database migrations applied."
    } else {
        Write-Host "[Step 2] WARNING: Alembic returned exit code $LASTEXITCODE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[Step 2] WARNING: Alembic migration failed: $_" -ForegroundColor Yellow
    Write-Host "[Step 2] Continuing with current schema..."
}

# ============================================================================
# Step 3: 啟動後端服務
# ============================================================================
Write-Host "[Step 3] Starting backend service on port 8001..."
python -m uvicorn main:app --host 0.0.0.0 --port 8001
