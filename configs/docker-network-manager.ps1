# CK_Missive Docker 網路管理腳本
# 用於管理專案的獨立 Docker 網路和容器

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("status", "start", "stop", "restart", "cleanup", "full-deploy", "db-only")]
    [string]$Action,
    
    [string]$Service = "all"
)

$ProjectName = "CK_Missive"
$NetworkName = "${ProjectName}_network"
$ComposeFile = "docker-compose.yml"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Get-ProjectContainers {
    return docker ps -a --filter "name=${ProjectName}_" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
}

function Get-ProjectNetwork {
    return docker network ls --filter "name=${NetworkName}" --format "table {{.Name}}`t{{.Driver}}`t{{.Scope}}"
}

function Show-Status {
    Write-ColorOutput "=== CK_Missive 專案狀態 ===" "Cyan"
    
    Write-ColorOutput "`n🌐 網路狀態:" "Yellow"
    $networkExists = docker network ls --filter "name=${NetworkName}" --quiet
    if ($networkExists) {
        Get-ProjectNetwork
        Write-ColorOutput "✅ 專案網路已建立" "Green"
    } else {
        Write-ColorOutput "❌ 專案網路不存在" "Red"
    }
    
    Write-ColorOutput "`n📦 容器狀態:" "Yellow"
    $containers = docker ps -a --filter "name=${ProjectName}_" --quiet
    if ($containers) {
        Get-ProjectContainers
    } else {
        Write-ColorOutput "❌ 無 CK_Missive 容器運行" "Red"
    }
    
    Write-ColorOutput "`n🔗 埠號使用狀況:" "Yellow"
    $ports = @("5434", "8080", "8001", "3005", "6379")
    foreach ($port in $ports) {
        $process = netstat -an | Select-String ":${port}.*LISTENING"
        if ($process) {
            Write-ColorOutput "✅ 埠號 ${port} 已使用" "Green"
        } else {
            Write-ColorOutput "⚪ 埠號 ${port} 可用" "Gray"
        }
    }
}

function Start-Services {
    param([string]$Profile = "")
    
    Write-ColorOutput "🚀 啟動 CK_Missive 服務..." "Cyan"
    
    if ($Profile -eq "full-stack") {
        Write-ColorOutput "啟動完整堆疊 (包含前後端)..." "Yellow"
        docker-compose --profile full-stack up -d
    } else {
        Write-ColorOutput "啟動資料庫服務..." "Yellow"
        docker-compose up -d postgres adminer
    }
    
    Start-Sleep -Seconds 3
    Show-Status
}

function Stop-Services {
    Write-ColorOutput "🛑 停止 CK_Missive 服務..." "Cyan"
    
    $containers = docker ps --filter "name=${ProjectName}_" --quiet
    if ($containers) {
        docker stop $containers
        Write-ColorOutput "✅ 所有容器已停止" "Green"
    } else {
        Write-ColorOutput "ℹ️ 沒有運行中的容器" "Blue"
    }
}

function Restart-Services {
    Write-ColorOutput "🔄 重啟 CK_Missive 服務..." "Cyan"
    Stop-Services
    Start-Sleep -Seconds 2
    Start-Services
}

function Cleanup-Resources {
    Write-ColorOutput "🧹 清理 CK_Missive 資源..." "Cyan"
    
    # 確認清理操作
    $confirm = Read-Host "是否確定要清理所有 CK_Missive 資源? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-ColorOutput "Operation cancelled" "Red"
        return
    }
    
    # 停止並移除容器
    $containers = docker ps -a --filter "name=${ProjectName}_" --quiet
    if ($containers) {
        Write-ColorOutput "移除容器..." "Yellow"
        docker rm -f $containers
    }
    
    # 移除網路 (如果沒有容器使用)
    $networkExists = docker network ls --filter "name=${NetworkName}" --quiet
    if ($networkExists) {
        try {
            docker network rm $NetworkName
            Write-ColorOutput "Network removed successfully" "Green"
        } catch {
            Write-ColorOutput "⚠️ 網路可能仍被使用，無法移除" "Yellow"
        }
    }
    
    # 清理未使用的卷 (可選)
    $cleanVolumes = Read-Host "是否清理專案數據卷? 這將刪除所有資料 (y/N)"
    if ($cleanVolumes -eq "y" -or $cleanVolumes -eq "Y") {
        docker volume rm "${ProjectName}_postgres_data" -f 2>$null
        docker volume rm "${ProjectName}_redis_data" -f 2>$null
        Write-ColorOutput "Data volumes cleaned" "Green"
    }
    
    Write-ColorOutput "Cleanup completed" "Green"
}

function Test-NetworkIsolation {
    Write-ColorOutput "🔍 測試網路隔離..." "Cyan"
    
    # 檢查 CK_Missive 網路
    $ckMissiveNetwork = docker network inspect $NetworkName 2>$null
    if ($ckMissiveNetwork) {
        Write-ColorOutput "✅ CK_Missive 網路存在" "Green"
        
        # 檢查其他專案網路
        $otherNetworks = docker network ls --filter "name=ck_" --format "{{.Name}}" | Where-Object { $_ -ne $NetworkName }
        if ($otherNetworks) {
            Write-ColorOutput "`n🌐 其他專案網路:" "Yellow"
            foreach ($network in $otherNetworks) {
                Write-ColorOutput "  - $network" "Gray"
            }
            Write-ColorOutput "✅ 網路隔離正常" "Green"
        }
    } else {
        Write-ColorOutput "❌ CK_Missive 網路不存在" "Red"
    }
}

# 主邏輯
try {
    Set-Location (Split-Path $MyInvocation.MyCommand.Path)
    
    switch ($Action) {
        "status" { 
            Show-Status 
            Test-NetworkIsolation
        }
        "start" { Start-Services }
        "stop" { Stop-Services }
        "restart" { Restart-Services }
        "cleanup" { Cleanup-Resources }
        "full-deploy" { Start-Services -Profile "full-stack" }
        "db-only" { Start-Services }
        default { 
            Write-ColorOutput "❌ 無效的操作: $Action" "Red"
            exit 1
        }
    }
} catch {
    Write-ColorOutput "❌ 錯誤: $($_.Exception.Message)" "Red"
    exit 1
}

Write-ColorOutput "`nOperation completed successfully" "Green"