# =============================================================================
# 乾坤測繪公文管理系統 - 統一配置管理腳本
# =============================================================================
# 功能：自動同步所有配置檔案，確保一致性
# 使用：./config-manager.ps1 [sync|clean|check]
# =============================================================================

param(
    [Parameter(Position=0)]
    [ValidateSet("sync", "clean", "check", "reset")]
    [string]$Action = "check"
)

# 顏色輸出函數
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# 主配置檔案路徑
$MASTER_CONFIG = ".env.master"
$TARGET_CONFIG = ".env"

# 需要清理的舊配置檔案列表
$OLD_CONFIGS = @(
    ".env.ports",
    "backend/.env",
    "backend/.env.example",
    "configs/.env",
    "configs/.env.docker",
    "configs/.env.production",
    "frontend/.env",
    "frontend/.env.backup.*",
    "frontend/.env.development*",
    "frontend/.env.local*",
    "frontend/.env.production*",
    "frontend/.env.example"
)

function Test-MasterConfig {
    if (-not (Test-Path $MASTER_CONFIG)) {
        Write-Error "❌ 主配置檔案 $MASTER_CONFIG 不存在！"
        return $false
    }
    return $true
}

function Sync-Config {
    Write-Info "🔄 開始同步配置..."

    if (-not (Test-MasterConfig)) { return }

    # 複製主配置為環境配置
    Copy-Item $MASTER_CONFIG $TARGET_CONFIG -Force
    Write-Success "✅ 已同步主配置到 $TARGET_CONFIG"

    # 確保日誌目錄存在
    $logDirs = @("logs", "backend/logs", "frontend/logs")
    foreach ($dir in $logDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Success "✅ 建立日誌目錄: $dir"
        }
    }

    Write-Success "🎉 配置同步完成！"
}

function Clean-OldConfigs {
    Write-Warning "Cleaning old config files..."

    $cleanedCount = 0
    foreach ($pattern in $OLD_CONFIGS) {
        $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            if ($file.Name -ne ".env.example") {  # 保留範例檔案
                Remove-Item $file.FullName -Force
                Write-Warning "🗑️  已刪除: $($file.FullName)"
                $cleanedCount++
            }
        }
    }

    if ($cleanedCount -eq 0) {
        Write-Info "✨ 沒有找到需要清理的舊配置檔案"
    } else {
        Write-Success "✅ 已清理 $cleanedCount 個舊配置檔案"
    }
}

function Check-Config {
    Write-Info "🔍 檢查配置狀態..."

    # 檢查主配置
    if (Test-Path $MASTER_CONFIG) {
        Write-Success "✅ 主配置檔案存在: $MASTER_CONFIG"
    } else {
        Write-Error "❌ 主配置檔案不存在: $MASTER_CONFIG"
    }

    # 檢查目標配置
    if (Test-Path $TARGET_CONFIG) {
        Write-Success "✅ 環境配置檔案存在: $TARGET_CONFIG"

        # 檢查同步狀態
        $masterHash = (Get-FileHash $MASTER_CONFIG).Hash
        $targetHash = (Get-FileHash $TARGET_CONFIG).Hash

        if ($masterHash -eq $targetHash) {
            Write-Success "✅ 配置檔案已同步"
        } else {
            Write-Warning "⚠️  配置檔案不同步，請執行 sync 命令"
        }
    } else {
        Write-Warning "⚠️  環境配置檔案不存在: $TARGET_CONFIG"
    }

    # 檢查舊配置檔案
    $oldConfigCount = 0
    foreach ($pattern in $OLD_CONFIGS) {
        $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
        $oldConfigCount += $files.Count
    }

    if ($oldConfigCount -gt 0) {
        Write-Warning "⚠️  發現 $oldConfigCount 個舊配置檔案，建議執行 clean 命令清理"
    } else {
        Write-Success "✅ 沒有發現舊配置檔案"
    }
}

function Reset-Config {
    Write-Warning "🔄 重置所有配置..."
    Clean-OldConfigs
    Sync-Config
    Write-Success "🎉 配置重置完成！"
}

# 主要執行邏輯
Write-Info "=== CK Missive Config Manager ==="

switch ($Action) {
    "sync" { Sync-Config }
    "clean" { Clean-OldConfigs }
    "check" { Check-Config }
    "reset" { Reset-Config }
}

Write-Info "=== Execution Complete ==="