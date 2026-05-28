# =============================================================================
# CK_Missive NAS 部署腳本 (Windows PowerShell)
# =============================================================================
# 目標: QNAP NAS Container Station (192.168.50.41)
# 用法: .\scripts\deploy-nas.ps1
# =============================================================================

param(
    [string]$NasHost = "192.168.50.41",
    [string]$NasUser = "admin",
    [string]$NasPath = "/share/Container/ck-missive"
)

$ErrorActionPreference = "Stop"

# 顏色輸出函數
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red; exit 1 }
function Write-Step { Write-Host "📌 $args" -ForegroundColor Magenta }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   CK_Missive NAS Production 部署" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "目標: $NasHost" -ForegroundColor Cyan
Write-Host ""

# 步驟 1: 檢查本地檔案
Write-Step "步驟 1/7: 檢查本地檔案..."

$requiredFiles = @(
    "docker-compose.production.yml",
    ".env.production",
    "backend\Dockerfile",
    "frontend\Dockerfile"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Error "缺少必要檔案: $file"
    }
}
Write-Success "本地檔案檢查完成"

# 確認部署
Write-Host ""
Write-Warning "您即將部署到 Production 環境!"
Write-Host "  NAS: $NasHost"
Write-Host "  路徑: $NasPath"
Write-Host ""

$confirm = Read-Host "確定要繼續嗎？(yes/no)"
if ($confirm -ne "yes") {
    Write-Info "部署已取消"
    exit 0
}

# 步驟 2: 檢查安全配置
Write-Step "步驟 2/7: 檢查安全配置..."

$envContent = Get-Content ".env.production" -Raw
if ($envContent -match "CHANGE_THIS") {
    Write-Warning "偵測到預設 SECRET_KEY，正在生成新金鑰..."

    # 生成隨機金鑰
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $newSecret = [BitConverter]::ToString($bytes) -replace '-', ''

    $envContent = $envContent -replace "CHANGE_THIS_TO_RANDOM_64_CHAR_HEX_STRING_USE_OPENSSL", $newSecret.ToLower()
    Set-Content ".env.production" $envContent

    Write-Success "已生成新的 SECRET_KEY"
}

# 步驟 3: 打包部署檔案
Write-Step "步驟 3/7: 打包部署檔案..."

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$deployPackage = "ck-missive-deploy-$timestamp.tar.gz"

# 使用 tar 打包 (Windows 10+ 內建)
$excludePatterns = @(
    "--exclude=node_modules",
    "--exclude=__pycache__",
    "--exclude=.git",
    "--exclude=*.pyc",
    "--exclude=.env",
    "--exclude=logs/*",
    "--exclude=uploads/*"
)

$tarArgs = @("-czf", $deployPackage) + $excludePatterns + @(
    "backend/",
    "frontend/",
    "configs/",
    "docker-compose.production.yml",
    ".env.production"
)

& tar @tarArgs

if (-not (Test-Path $deployPackage)) {
    Write-Error "打包失敗"
}

$packageSize = [math]::Round((Get-Item $deployPackage).Length / 1MB, 2)
Write-Success "部署套件已建立: $deployPackage ($packageSize MB)"

# 步驟 4: 上傳到 NAS
Write-Step "步驟 4/7: 上傳到 NAS..."

Write-Info "正在連接 ${NasUser}@${NasHost}..."

# 建立遠端目錄
ssh "${NasUser}@${NasHost}" "mkdir -p $NasPath"

# 上傳檔案
scp $deployPackage "${NasUser}@${NasHost}:${NasPath}/"

Write-Success "檔案已上傳"

# 步驟 5: 在 NAS 上部署
Write-Step "步驟 5/7: 在 NAS 上部署..."

$remoteScript = @"
set -e
cd $NasPath

echo "📦 解壓部署套件..."
tar -xzf $deployPackage

echo "📝 設定環境變數..."
cp .env.production .env

echo "🐳 停止舊服務..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

echo "🔨 建構映像檔..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🚀 啟動服務..."
docker-compose -f docker-compose.production.yml up -d

echo "⏳ 等待服務啟動 (60秒)..."
sleep 60

echo "🏥 服務狀態..."
docker-compose -f docker-compose.production.yml ps

echo "🧹 清理部署套件..."
rm -f $deployPackage
"@

$remoteScript | ssh "${NasUser}@${NasHost}" "bash -s"

Write-Success "NAS 部署完成"

# 步驟 6: 健康檢查
Write-Step "步驟 6/7: 驗證服務..."
Start-Sleep -Seconds 10

Write-Info "檢查後端 API..."
try {
    $response = Invoke-WebRequest -Uri "http://${NasHost}:8001/health" -TimeoutSec 10 -UseBasicParsing
    Write-Success "後端 API 正常運行"
} catch {
    Write-Warning "後端 API 尚未就緒，請稍後手動檢查"
}

Write-Info "檢查前端..."
try {
    $response = Invoke-WebRequest -Uri "http://${NasHost}/" -TimeoutSec 10 -UseBasicParsing
    Write-Success "前端服務正常運行"
} catch {
    Write-Warning "前端服務尚未就緒，請稍後手動檢查"
}

# 步驟 7: 資料庫遷移
Write-Step "步驟 7/7: 執行資料庫遷移..."

$migrationScript = @"
cd $NasPath
docker-compose -f docker-compose.production.yml exec -T backend alembic upgrade head || echo "遷移可能已是最新"
"@

$migrationScript | ssh "${NasUser}@${NasHost}" "bash -s"

# 清理本地套件
Remove-Item $deployPackage -ErrorAction SilentlyContinue

# 完成
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   🎉 Production 部署完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "服務位址:" -ForegroundColor White
Write-Host "  📱 前端:     http://${NasHost}/" -ForegroundColor Cyan
Write-Host "  🔌 API:      http://${NasHost}:8001/api" -ForegroundColor Cyan
Write-Host "  📖 API 文件: http://${NasHost}:8001/docs" -ForegroundColor Cyan
Write-Host "  🗄️ Adminer:  http://${NasHost}:8080 (需手動啟用)" -ForegroundColor Cyan
Write-Host ""
Write-Host "管理指令 (SSH 到 NAS 後執行):" -ForegroundColor White
Write-Host "  cd $NasPath"
Write-Host "  docker-compose -f docker-compose.production.yml logs -f      # 查看日誌"
Write-Host "  docker-compose -f docker-compose.production.yml ps           # 服務狀態"
Write-Host "  docker-compose -f docker-compose.production.yml restart      # 重啟服務"
Write-Host ""
