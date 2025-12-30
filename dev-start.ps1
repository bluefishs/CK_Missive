# =============================================================================
# 乾坤測繪公文管理系統 - Windows 開發環境啟動腳本
# =============================================================================
# 🎯 目標：Windows PowerShell 版本的開發環境管理
# 🔧 功能：一鍵啟動開發環境，支援熱重載
# =============================================================================

param(
    [switch]$Clean,
    [switch]$Rebuild,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Logs
)

function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Log-Info { param([string]$msg) Write-ColoredOutput "ℹ️  $msg" "Cyan" }
function Log-Success { param([string]$msg) Write-ColoredOutput "✅ $msg" "Green" }
function Log-Warning { param([string]$msg) Write-ColoredOutput "⚠️  $msg" "Yellow" }
function Log-Error { param([string]$msg) Write-ColoredOutput "❌ $msg" "Red" }
function Log-Dev { param([string]$msg) Write-ColoredOutput "🔧 $msg" "Magenta" }

function Show-Usage {
    Write-ColoredOutput "=== 乾坤測繪開發環境管理工具 ===" "Green"
    Write-Host ""
    Write-ColoredOutput "用法：" "Yellow"
    Write-Host "  .\dev-start.ps1              # 啟動開發環境"
    Write-Host "  .\dev-start.ps1 -Clean       # 清理後啟動"
    Write-Host "  .\dev-start.ps1 -Rebuild     # 重建後啟動"
    Write-Host "  .\dev-start.ps1 -Stop        # 停止開發環境"
    Write-Host "  .\dev-start.ps1 -Status      # 查看狀態"
    Write-Host "  .\dev-start.ps1 -Logs        # 查看日誌"
    Write-Host ""
}

function Test-DevEnvironment {
    Log-Info "檢查開發環境..."

    # 檢查 Docker
    try {
        $dockerVersion = docker --version
        Log-Success "Docker 已安裝: $($dockerVersion.Split(' ')[2])"
    }
    catch {
        Log-Error "Docker 未安裝或未啟動！請先安裝並啟動 Docker Desktop"
        exit 1
    }

    # 檢查 Docker Compose
    try {
        $composeVersion = docker-compose --version
        Log-Success "Docker Compose 已安裝"
    }
    catch {
        Log-Error "Docker Compose 未安裝！"
        exit 1
    }

    # 檢查開發配置文件
    if (-not (Test-Path "docker-compose.dev.yml")) {
        Log-Error "開發配置文件 docker-compose.dev.yml 不存在！"
        exit 1
    }

    Log-Success "開發環境檢查通過"
}

function Sync-DevConfig {
    Log-Info "同步開發配置..."

    # 確保主配置存在
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.master") {
            Copy-Item ".env.master" ".env"
            Log-Success "已從 .env.master 創建 .env"
        } else {
            Log-Error "配置文件不存在！"
            exit 1
        }
    }

    # 建立開發目錄
    $dirs = @("logs", "backend\logs", "frontend\logs", "backend\uploads")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -Path $dir -ItemType Directory -Force | Out-Null
        }
    }
    Log-Success "開發目錄結構已建立"
}

function Stop-DevServices {
    Log-Info "停止開發服務..."

    try {
        docker-compose -f docker-compose.dev.yml down --remove-orphans
        Log-Success "開發服務已停止"
    }
    catch {
        Log-Warning "停止服務時出現問題: $($_.Exception.Message)"
    }
}

function Start-DevServices {
    param([switch]$Rebuild)

    Log-Info "啟動開發服務（支援熱重載）..."

    $buildArg = if ($Rebuild) { "--build" } else { "" }

    try {
        if ($Rebuild) {
            docker-compose -f docker-compose.dev.yml up --build -d
        } else {
            docker-compose -f docker-compose.dev.yml up -d
        }

        Log-Success "開發服務啟動完成"
        Log-Dev "開發模式特色："
        Log-Dev "  • 後端：支援 uvicorn --reload 熱重載"
        Log-Dev "  • 前端：支援 Vite HMR 熱更新"
        Log-Dev "  • 資料庫：獨立開發資料"
        Log-Dev "  • 程式碼：即時同步不需重建"
    }
    catch {
        Log-Error "啟動開發服務失敗: $($_.Exception.Message)"
        exit 1
    }
}

function Test-DevServices {
    Log-Info "驗證開發服務狀態..."

    # 等待服務啟動
    Log-Info "等待服務啟動完成..."
    Start-Sleep -Seconds 20

    # 檢查容器狀態
    try {
        $containerStatus = docker-compose -f docker-compose.dev.yml ps
        if ($containerStatus -match "Up") {
            Log-Success "開發容器運行正常"
        } else {
            Log-Warning "部分開發容器可能未正常啟動"
            Write-Host $containerStatus
        }
    }
    catch {
        Log-Warning "無法獲取容器狀態"
    }

    # 檢查後端健康
    Log-Info "檢查後端服務..."
    for ($i = 1; $i -le 6; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Log-Success "後端開發服務健康檢查通過"
                break
            }
        }
        catch {
            if ($i -eq 6) {
                Log-Warning "後端服務可能還在啟動中，請稍後手動檢查"
            } else {
                Log-Info "等待後端服務啟動... ($i/6)"
                Start-Sleep -Seconds 10
            }
        }
    }

    # 檢查前端健康
    Log-Info "檢查前端服務..."
    for ($i = 1; $i -le 6; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Log-Success "前端開發服務健康檢查通過"
                break
            }
        }
        catch {
            if ($i -eq 6) {
                Log-Warning "前端服務可能還在啟動中，請稍後手動檢查"
            } else {
                Log-Info "等待前端服務啟動... ($i/6)"
                Start-Sleep -Seconds 10
            }
        }
    }
}

function Show-DevInfo {
    Write-Host ""
    Log-Dev "=== 🔧 開發環境資訊 ==="
    Write-Host ""
    Write-Host "🌐 前端開發伺服器: http://localhost:3000" -ForegroundColor White
    Write-Host "   • 支援 Vite HMR 熱更新" -ForegroundColor Gray
    Write-Host "   • 程式碼變更即時反映" -ForegroundColor Gray
    Write-Host ""
    Write-Host "⚡ 後端開發 API: http://localhost:8001" -ForegroundColor White
    Write-Host "   • 支援 uvicorn --reload 熱重載" -ForegroundColor Gray
    Write-Host "   • 程式碼變更自動重啟" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📖 API 開發文檔: http://localhost:8001/api/docs" -ForegroundColor White
    Write-Host "   • Swagger UI 介面" -ForegroundColor Gray
    Write-Host "   • 即時 API 測試" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🗄️  開發資料庫管理: http://localhost:8080" -ForegroundColor White
    Write-Host "   • 獨立開發資料庫" -ForegroundColor Gray
    Write-Host "   • 不影響生產資料" -ForegroundColor Gray
    Write-Host ""
    Log-Dev "=== 🛠️  開發管理命令 ==="
    Write-Host ""
    Write-Host "📊 查看開發狀態: docker-compose -f docker-compose.dev.yml ps"
    Write-Host "📝 查看開發日誌: docker-compose -f docker-compose.dev.yml logs -f"
    Write-Host "🔄 重啟某服務: docker-compose -f docker-compose.dev.yml restart [service]"
    Write-Host "🛑 停止開發環境: .\dev-start.ps1 -Stop"
    Write-Host ""
    Write-Host "📂 程式碼同步資訊:" -ForegroundColor Yellow
    Write-Host "   • 後端：.\backend → /app (即時同步)"
    Write-Host "   • 前端：.\frontend → /app (即時同步)"
    Write-Host "   • 修改程式碼後無需重建容器"
    Write-Host ""
    Log-Success "🎉 開發環境啟動完成！開始愉快的開發吧！"
}

function Show-Status {
    Log-Info "開發環境狀態："
    try {
        docker-compose -f docker-compose.dev.yml ps
    }
    catch {
        Log-Error "無法獲取狀態信息"
    }
}

function Show-Logs {
    Log-Info "顯示開發環境日誌..."
    try {
        docker-compose -f docker-compose.dev.yml logs -f
    }
    catch {
        Log-Error "無法獲取日誌信息"
    }
}

# 主邏輯
switch ($true) {
    $Stop {
        Stop-DevServices
        break
    }
    $Status {
        Show-Status
        break
    }
    $Logs {
        Show-Logs
        break
    }
    default {
        Log-Dev "=== 乾坤測繪開發環境啟動 ==="

        Test-DevEnvironment
        Sync-DevConfig

        if ($Clean) {
            Log-Info "執行清理模式..."
            Stop-DevServices
            docker system prune -f
        }

        Start-DevServices -Rebuild:$Rebuild
        Test-DevServices
        Show-DevInfo
    }
}