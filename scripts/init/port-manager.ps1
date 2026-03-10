# CK_Missive 端口管理腳本
# 統一管理所有服務端口，避免衝突

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("check", "kill", "start", "status")]
    [string]$Action,

    [string]$Service = "all"
)

# 從 port-config.json 讀取配置
$ConfigPath = Join-Path $PSScriptRoot "..\port-config.json"
$Config = Get-Content $ConfigPath | ConvertFrom-Json

function Show-Usage {
    Write-Host "CK_Missive 端口管理工具" -ForegroundColor Green
    Write-Host "用法: .\port-manager.ps1 -Action <action> [-Service <service>]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Actions:" -ForegroundColor Cyan
    Write-Host "  check   - 檢查端口使用狀況"
    Write-Host "  kill    - 終止佔用端口的進程"
    Write-Host "  start   - 啟動服務"
    Write-Host "  status  - 顯示所有服務狀態"
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  frontend - 前端服務 (端口 $($Config.services.frontend.port))"
    Write-Host "  backend  - 後端服務 (端口 $($Config.services.backend.port))"
    Write-Host "  all      - 所有服務 (預設)"
}

function Check-Port {
    param([int]$Port, [string]$ServiceName)

    $Process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($Process) {
        Write-Host "✗ 端口 $Port ($ServiceName) 被佔用" -ForegroundColor Red
        return $false
    } else {
        Write-Host "✓ 端口 $Port ($ServiceName) 可用" -ForegroundColor Green
        return $true
    }
}

function Kill-ProcessOnPort {
    param([int]$Port, [string]$ServiceName)

    $Connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($Connections) {
        foreach ($Connection in $Connections) {
            $ProcessId = $Connection.OwningProcess
            Write-Host "終止佔用端口 $Port 的進程 $ProcessId..." -ForegroundColor Yellow
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "✓ 端口 $Port ($ServiceName) 已清理" -ForegroundColor Green
    } else {
        Write-Host "✓ 端口 $Port ($ServiceName) 沒有被佔用" -ForegroundColor Green
    }
}

# 主要邏輯
switch ($Action) {
    "check" {
        Write-Host "=== 端口檢查 ===" -ForegroundColor Blue
        Check-Port $Config.services.frontend.port "Frontend"
        Check-Port $Config.services.backend.port "Backend"
        Check-Port $Config.services.database.port "Database"
        Check-Port $Config.services.adminer.port "Adminer"
    }

    "kill" {
        Write-Host "=== 端口清理 ===" -ForegroundColor Blue
        if ($Service -eq "frontend" -or $Service -eq "all") {
            Kill-ProcessOnPort $Config.services.frontend.port "Frontend"
        }
        if ($Service -eq "backend" -or $Service -eq "all") {
            Kill-ProcessOnPort $Config.services.backend.port "Backend"
        }
    }

    "status" {
        Write-Host "=== 服務狀態 ===" -ForegroundColor Blue
        Write-Host "配置檔案: $ConfigPath" -ForegroundColor Gray
        Write-Host "前端: $($Config.services.frontend.url)" -ForegroundColor Cyan
        Write-Host "後端: $($Config.services.backend.url)" -ForegroundColor Cyan
        Write-Host "API文檔: $($Config.services.backend.api_docs)" -ForegroundColor Cyan
        Write-Host "資料庫管理: $($Config.services.adminer.url)" -ForegroundColor Cyan
        Write-Host ""

        # 檢查服務狀態
        try {
            $FrontendResponse = Invoke-WebRequest -Uri $Config.services.frontend.url -UseBasicParsing -TimeoutSec 2
            Write-Host "✓ 前端服務正常" -ForegroundColor Green
        } catch {
            Write-Host "✗ 前端服務未運行" -ForegroundColor Red
        }

        try {
            $BackendResponse = Invoke-WebRequest -Uri "$($Config.services.backend.url)/health" -UseBasicParsing -TimeoutSec 2
            Write-Host "✓ 後端服務正常" -ForegroundColor Green
        } catch {
            Write-Host "✗ 後端服務未運行" -ForegroundColor Red
        }
    }

    default {
        Show-Usage
    }
}