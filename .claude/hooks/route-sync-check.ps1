<#
.SYNOPSIS
    路徑同步檢查 Hook

.DESCRIPTION
    檢查前端路由定義與後端導覽路徑白名單的一致性

.NOTES
    版本: 1.0.0
    日期: 2026-01-12

.EXAMPLE
    .\.claude\hooks\route-sync-check.ps1
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# 專案根目錄
$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

# 檔案路徑
$FrontendRoutesFile = Join-Path $ProjectRoot "frontend\src\router\types.ts"
$BackendValidatorFile = Join-Path $ProjectRoot "backend\app\core\navigation_validator.py"

Write-Host "=== 路徑同步檢查 ===" -ForegroundColor Cyan
Write-Host "專案目錄: $ProjectRoot"

# 檢查檔案是否存在
if (-not (Test-Path $FrontendRoutesFile)) {
    Write-Host "ERROR: 找不到前端路由檔案: $FrontendRoutesFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackendValidatorFile)) {
    Write-Host "ERROR: 找不到後端驗證器檔案: $BackendValidatorFile" -ForegroundColor Red
    exit 1
}

# 讀取前端路由定義
Write-Host "`n[1/3] 讀取前端路由定義..." -ForegroundColor Yellow
$FrontendContent = Get-Content $FrontendRoutesFile -Raw
$FrontendPaths = @()

# 使用正則表達式提取路由路徑
$matches = [regex]::Matches($FrontendContent, ":\s*'(/[^']*)'")
foreach ($match in $matches) {
    $path = $match.Groups[1].Value
    if ($path -and $path -ne "/404") {
        $FrontendPaths += $path
    }
}
$FrontendPaths = $FrontendPaths | Sort-Object -Unique

if ($Verbose) {
    Write-Host "  前端路由數量: $($FrontendPaths.Count)"
    $FrontendPaths | ForEach-Object { Write-Host "    $_" }
}

# 讀取後端驗證器路徑
Write-Host "[2/3] 讀取後端路徑白名單..." -ForegroundColor Yellow
$BackendContent = Get-Content $BackendValidatorFile -Raw
$BackendPaths = @()

# 提取 VALID_NAVIGATION_PATHS 中的路徑
$matches = [regex]::Matches($BackendContent, '"(/[^"]*)"')
foreach ($match in $matches) {
    $path = $match.Groups[1].Value
    if ($path) {
        $BackendPaths += $path
    }
}
$BackendPaths = $BackendPaths | Sort-Object -Unique

if ($Verbose) {
    Write-Host "  後端路徑數量: $($BackendPaths.Count)"
    $BackendPaths | ForEach-Object { Write-Host "    $_" }
}

# 比對差異
Write-Host "[3/3] 比對路徑差異..." -ForegroundColor Yellow

$MissingInBackend = $FrontendPaths | Where-Object { $_ -notin $BackendPaths }
$MissingInFrontend = $BackendPaths | Where-Object { $_ -notin $FrontendPaths }

$HasErrors = $false

if ($MissingInBackend.Count -gt 0) {
    Write-Host "`n[WARNING] 前端有定義但後端白名單缺少的路徑:" -ForegroundColor Yellow
    $MissingInBackend | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host "  建議: 在 backend/app/core/navigation_validator.py 中新增這些路徑" -ForegroundColor Gray
    $HasErrors = $true
}

if ($MissingInFrontend.Count -gt 0) {
    Write-Host "`n[INFO] 後端白名單有但前端未定義的路徑:" -ForegroundColor Cyan
    $MissingInFrontend | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
    Write-Host "  這可能是正常的（例如 /login, /register 等基礎頁面）" -ForegroundColor Gray
}

# 結果
Write-Host "`n=== 檢查結果 ===" -ForegroundColor Cyan
Write-Host "前端路由數量: $($FrontendPaths.Count)"
Write-Host "後端白名單數量: $($BackendPaths.Count)"

if (-not $HasErrors) {
    Write-Host "`n[OK] 路徑同步檢查通過！" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[WARN] 發現路徑不一致，請檢查上述警告。" -ForegroundColor Yellow
    exit 0  # 警告但不阻止
}
