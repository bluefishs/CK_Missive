# =============================================================================
# CK_Missive - 部署前置檢查腳本 (Windows PowerShell)
# =============================================================================
# 用途: 在部署前檢查環境配置、目錄權限、端口可用性
# 使用: .\pre-deploy.ps1
# =============================================================================

param(
    [switch]$BuildTest
)

$ErrorActionPreference = "Continue"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$EnvFile = "$ProjectRoot\.env.production"
$BackendDir = "$ProjectRoot\backend"

# Counters
$Script:Errors = 0
$Script:Warnings = 0

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "🔍 CK_Missive 部署前置檢查" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
function Write-Check {
    param([string]$Status, [string]$Message)
    switch ($Status) {
        "OK"      { Write-Host "  ✓ $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "  ✗ $Message" -ForegroundColor Red; $Script:Errors++ }
        "WARNING" { Write-Host "  ⚠ $Message" -ForegroundColor Yellow; $Script:Warnings++ }
        "INFO"    { Write-Host "  ! $Message" -ForegroundColor Yellow }
    }
}

# -----------------------------------------------------------------------------
# 1. 檢查必要檔案
# -----------------------------------------------------------------------------
Write-Host "📁 檢查必要檔案..." -ForegroundColor White

$RequiredFiles = @(
    @{ Path = "$ProjectRoot\docker-compose.production.yml"; Name = "docker-compose.production.yml" },
    @{ Path = "$BackendDir\Dockerfile"; Name = "backend/Dockerfile" },
    @{ Path = "$BackendDir\requirements.txt"; Name = "backend/requirements.txt" },
    @{ Path = "$BackendDir\alembic.ini"; Name = "backend/alembic.ini" },
    @{ Path = "$ProjectRoot\frontend\Dockerfile"; Name = "frontend/Dockerfile" }
)

foreach ($file in $RequiredFiles) {
    if (Test-Path $file.Path) {
        Write-Check "OK" $file.Name
    } else {
        Write-Check "ERROR" "$($file.Name) - 檔案不存在"
    }
}

Write-Host ""

# -----------------------------------------------------------------------------
# 2. 檢查環境變數檔案
# -----------------------------------------------------------------------------
Write-Host "🔧 檢查環境變數..." -ForegroundColor White

if (Test-Path $EnvFile) {
    Write-Check "OK" "環境變數檔案存在"

    $EnvContent = Get-Content $EnvFile -Raw

    $RequiredVars = @(
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "VITE_API_BASE_URL"
    )

    foreach ($var in $RequiredVars) {
        if ($EnvContent -match "^$var=.+$" -and $EnvContent -notmatch "^$var=$") {
            Write-Check "OK" "$var 已設定"
        } else {
            Write-Check "ERROR" "$var 未設定或為空"
        }
    }

    # Security checks
    if ($EnvContent -match "POSTGRES_PASSWORD=.*password|POSTGRES_PASSWORD=.*123456") {
        Write-Check "WARNING" "POSTGRES_PASSWORD 使用弱密碼"
    }

    $SecretKey = ($EnvContent | Select-String -Pattern "SECRET_KEY=(.*)$").Matches.Groups[1].Value
    if ($SecretKey.Length -lt 32) {
        Write-Check "WARNING" "SECRET_KEY 可能不夠安全 (建議 64 字元)"
    }
} else {
    Write-Check "ERROR" "環境變數檔案不存在: $EnvFile"
    Write-Host "     提示: 複製 .env.production.example 並修改" -ForegroundColor Yellow
}

Write-Host ""

# -----------------------------------------------------------------------------
# 3. 檢查目錄結構
# -----------------------------------------------------------------------------
Write-Host "📂 檢查目錄結構..." -ForegroundColor White

$RequiredDirs = @(
    @{ Path = "$BackendDir\logs"; Name = "backend/logs" },
    @{ Path = "$BackendDir\uploads"; Name = "backend/uploads" },
    @{ Path = "$BackendDir\backups"; Name = "backend/backups" },
    @{ Path = "$BackendDir\backup-logs"; Name = "backend/backup-logs" }
)

foreach ($dir in $RequiredDirs) {
    if (Test-Path $dir.Path) {
        Write-Check "OK" "$($dir.Name) 已存在"
    } else {
        Write-Check "INFO" "$($dir.Name) 不存在，正在建立..."
        New-Item -ItemType Directory -Path $dir.Path -Force | Out-Null
        Write-Check "OK" "$($dir.Name) 已建立"
    }
}

Write-Host ""

# -----------------------------------------------------------------------------
# 4. 檢查端口可用性
# -----------------------------------------------------------------------------
Write-Host "🔌 檢查端口可用性..." -ForegroundColor White

$Ports = @(
    @{ Port = 3000; Name = "Frontend" },
    @{ Port = 8001; Name = "Backend API" },
    @{ Port = 5434; Name = "PostgreSQL" },
    @{ Port = 6380; Name = "Redis" }
)

foreach ($p in $Ports) {
    $Connection = Get-NetTCPConnection -LocalPort $p.Port -ErrorAction SilentlyContinue
    if ($Connection) {
        Write-Check "ERROR" "Port $($p.Port) ($($p.Name)) 已被佔用"
    } else {
        Write-Check "OK" "Port $($p.Port) ($($p.Name)) 可用"
    }
}

Write-Host ""

# -----------------------------------------------------------------------------
# 5. 檢查 Docker
# -----------------------------------------------------------------------------
Write-Host "🐳 檢查 Docker..." -ForegroundColor White

$DockerVersion = docker --version 2>$null
if ($DockerVersion) {
    Write-Check "OK" "Docker 已安裝: $($DockerVersion -replace 'Docker version ', '')"

    $DockerInfo = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Check "OK" "Docker daemon 運行中"
    } else {
        Write-Check "ERROR" "Docker daemon 未運行"
    }
} else {
    Write-Check "ERROR" "Docker 未安裝"
}

$ComposeVersion = docker compose version 2>$null
if ($ComposeVersion) {
    Write-Check "OK" "Docker Compose 已安裝"
} else {
    Write-Check "ERROR" "Docker Compose 未安裝"
}

Write-Host ""

# -----------------------------------------------------------------------------
# 6. 驗證 Docker 建置 (可選)
# -----------------------------------------------------------------------------
if ($BuildTest) {
    Write-Host "🔨 測試 Docker 建置..." -ForegroundColor White

    Push-Location $ProjectRoot
    $BuildResult = docker compose -f docker-compose.production.yml config 2>&1
    Pop-Location

    if ($LASTEXITCODE -eq 0) {
        Write-Check "OK" "Docker Compose 配置有效"
    } else {
        Write-Check "WARNING" "Docker Compose 配置可能有問題"
    }

    Write-Host ""
}

# -----------------------------------------------------------------------------
# 結果摘要
# -----------------------------------------------------------------------------
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "📊 檢查結果摘要" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

if ($Script:Errors -eq 0 -and $Script:Warnings -eq 0) {
    Write-Host "✅ 所有檢查通過！可以開始部署。" -ForegroundColor Green
    exit 0
} elseif ($Script:Errors -eq 0) {
    Write-Host "⚠️  檢查完成，有 $($Script:Warnings) 個警告。" -ForegroundColor Yellow
    Write-Host "   建議處理警告後再部署。" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ 檢查失敗：$($Script:Errors) 個錯誤，$($Script:Warnings) 個警告。" -ForegroundColor Red
    Write-Host "   請修正錯誤後再執行部署。" -ForegroundColor Red
    exit 1
}
