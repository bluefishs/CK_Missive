# =============================================================================
# Ollama 服務健康檢查腳本
# =============================================================================
# 用途: 驗證本地 Ollama 服務狀態與模型可用性
# 執行: powershell -File scripts/check-ollama.ps1
# =============================================================================

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ollama 服務健康檢查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 讀取環境變數
$OLLAMA_BASE_URL = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { "http://localhost:11434" }
$OLLAMA_MODEL = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "llama3.1:8b" }

Write-Host "[INFO] Ollama URL: $OLLAMA_BASE_URL" -ForegroundColor Gray
Write-Host "[INFO] 預設模型: $OLLAMA_MODEL" -ForegroundColor Gray
Write-Host ""

# 1. 檢查服務連線
Write-Host "[1/4] 檢查服務連線..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$OLLAMA_BASE_URL/api/tags" -Method Get -TimeoutSec 5
    Write-Host "  ✅ Ollama 服務運行中" -ForegroundColor Green
    $serviceOk = $true
} catch {
    Write-Host "  ❌ 無法連線到 Ollama 服務" -ForegroundColor Red
    Write-Host "  建議: 執行 'ollama serve' 啟動服務" -ForegroundColor Gray
    $serviceOk = $false
}

# 2. 列出可用模型
Write-Host ""
Write-Host "[2/4] 檢查可用模型..." -ForegroundColor Yellow
if ($serviceOk) {
    $models = $response.models
    if ($models -and $models.Count -gt 0) {
        Write-Host "  ✅ 找到 $($models.Count) 個模型:" -ForegroundColor Green
        foreach ($model in $models) {
            $size = [math]::Round($model.size / 1GB, 2)
            Write-Host "     - $($model.name) (${size}GB)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠️ 未找到任何模型" -ForegroundColor Yellow
        Write-Host "  建議: 執行 'ollama pull llama3.1:8b' 下載模型" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⏭️ 跳過 (服務不可用)" -ForegroundColor Gray
}

# 3. 檢查預設模型
Write-Host ""
Write-Host "[3/4] 檢查預設模型 ($OLLAMA_MODEL)..." -ForegroundColor Yellow
if ($serviceOk -and $models) {
    $defaultModelFound = $models | Where-Object { $_.name -eq $OLLAMA_MODEL -or $_.name -like "$OLLAMA_MODEL*" }
    if ($defaultModelFound) {
        Write-Host "  ✅ 預設模型已安裝" -ForegroundColor Green
        $modelOk = $true
    } else {
        Write-Host "  ⚠️ 預設模型未安裝" -ForegroundColor Yellow
        Write-Host "  建議: 執行 'ollama pull $OLLAMA_MODEL'" -ForegroundColor Gray
        $modelOk = $false
    }
} else {
    Write-Host "  ⏭️ 跳過 (服務不可用)" -ForegroundColor Gray
    $modelOk = $false
}

# 4. 測試 AI 對話
Write-Host ""
Write-Host "[4/4] 測試 AI 對話..." -ForegroundColor Yellow
if ($serviceOk -and $modelOk) {
    try {
        $testBody = @{
            model = $OLLAMA_MODEL
            messages = @(
                @{
                    role = "user"
                    content = "回覆 OK 即可"
                }
            )
            stream = $false
        } | ConvertTo-Json -Depth 3

        $start = Get-Date
        $chatResponse = Invoke-RestMethod -Uri "$OLLAMA_BASE_URL/api/chat" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 60
        $elapsed = ((Get-Date) - $start).TotalSeconds

        if ($chatResponse.message.content) {
            Write-Host "  ✅ AI 對話測試成功 (耗時: $([math]::Round($elapsed, 2))s)" -ForegroundColor Green
            Write-Host "     回應: $($chatResponse.message.content.Substring(0, [Math]::Min(50, $chatResponse.message.content.Length)))..." -ForegroundColor Gray
        } else {
            Write-Host "  ⚠️ AI 回應為空" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ AI 對話測試失敗: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  ⏭️ 跳過 (前置條件不滿足)" -ForegroundColor Gray
}

# 總結
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  檢查結果總結" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($serviceOk -and $modelOk) {
    Write-Host ""
    Write-Host "  🎉 Ollama 備援服務已就緒!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  ⚠️ Ollama 備援服務未就緒" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  快速安裝指南:" -ForegroundColor Cyan
    Write-Host "  1. 下載: https://ollama.com/download" -ForegroundColor Gray
    Write-Host "  2. 啟動: ollama serve" -ForegroundColor Gray
    Write-Host "  3. 下載模型: ollama pull llama3.1:8b" -ForegroundColor Gray
    Write-Host "  4. 重新執行此腳本驗證" -ForegroundColor Gray
    Write-Host ""
}
