# 乾坤測繪公文系統架構快速檢視
Write-Host "=== 乾坤測繪公文管理系統架構檢視 ===" -ForegroundColor Cyan

# 檢查服務狀態
Write-Host "`n📡 檢查服務狀態..." -ForegroundColor Yellow

try {
    $healthCheck = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get
    Write-Host "✅ 後端服務: 正常運行" -ForegroundColor Green
} catch {
    Write-Host "❌ 後端服務: 無法連接" -ForegroundColor Red
}

# 檢查前端服務
$frontendPorts = @(3005, 3006)
$frontendRunning = $false

foreach ($port in $frontendPorts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port" -Method Get -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 前端服務: 運行在端口 $port" -ForegroundColor Green
            $frontendRunning = $true
            break
        }
    } catch {
        # 繼續檢查下一個端口
    }
}

if (-not $frontendRunning) {
    Write-Host "❌ 前端服務: 未檢測到" -ForegroundColor Red
}

# 顯示檔案對應關係
Write-Host "`n🗂️ 前端-後端檔案對應關係:" -ForegroundColor Yellow
Write-Host "-" * 60

$mappings = @(
    @("API服務層", "frontend/src/services/documentAPI.js", "API端點", "backend/app/api/endpoints/documents.py"),
    @("CSV匯入介面", "frontend/src/components/Documents/DocumentImport.jsx", "CSV處理器", "backend/csv_processor.py"),
    @("API配置", "frontend/src/api/config.ts", "主程式", "backend/main.py"),
    @("TypeScript API", "frontend/src/api/documents.ts", "資料模型", "backend/app/db/models.py")
)

foreach ($mapping in $mappings) {
    Write-Host "📁 $($mapping[0])" -ForegroundColor Cyan -NoNewline
    Write-Host " | $($mapping[1])" -ForegroundColor White
    Write-Host "   $($mapping[2])" -ForegroundColor Cyan -NoNewline
    Write-Host " | $($mapping[3])" -ForegroundColor White
    Write-Host ""
}

# 測試主要API端點
Write-Host "📋 測試主要API端點..." -ForegroundColor Yellow

try {
    $docs = Invoke-RestMethod -Uri "http://localhost:8001/api/documents/?limit=3" -Method Get
    Write-Host "✅ 文件API: 正常" -ForegroundColor Green
    Write-Host "   資料庫記錄數: $($docs.total)" -ForegroundColor Gray
    
    if ($docs.documents.Count -gt 0) {
        Write-Host "   最新文件: $($docs.documents[0].doc_number)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ 文件API: 異常" -ForegroundColor Red
}

Write-Host "`n💡 VB.NET整合建議:" -ForegroundColor Yellow
Write-Host "1. 使用HttpClient直接調用現有API" -ForegroundColor White
Write-Host "2. 參考ArchitectureViewer.vb範例程式" -ForegroundColor White
Write-Host "3. 瀏覽器開啟architecture_viewer.html檢視詳細資訊" -ForegroundColor White