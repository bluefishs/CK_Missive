# =============================================================================
# 清理 Python bytecode 後熱重載 backend
# =============================================================================
# 用途: 解決重構後 sys.modules 殘留舊模組路徑的 ModuleNotFoundError 問題
# 背景: 2026-04-10 AI 子包重構 (131→0 stubs) 後 ck-backend 仍以舊路徑載入
#       federation-health 端點，reload 後仍失敗，清 pyc 才解。
# 用法: .\scripts\dev\clear-pyc-reload.ps1
# =============================================================================

param(
    [switch]$NoReload  # 只清快取，不 reload PM2
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

Write-Host "[1/3] 清理 backend Python bytecode..." -ForegroundColor Cyan
$pycDirs = Get-ChildItem -Path "backend/app" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
if ($pycDirs) {
    $count = $pycDirs.Count
    $pycDirs | Remove-Item -Recurse -Force
    Write-Host "    已清除 $count 個 __pycache__ 目錄" -ForegroundColor Green
} else {
    Write-Host "    無 __pycache__ 可清" -ForegroundColor DarkGray
}

Write-Host "[2/3] 清理 scripts Python bytecode..." -ForegroundColor Cyan
$scriptPycDirs = Get-ChildItem -Path "scripts" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
if ($scriptPycDirs) {
    $count = $scriptPycDirs.Count
    $scriptPycDirs | Remove-Item -Recurse -Force
    Write-Host "    已清除 $count 個 __pycache__ 目錄" -ForegroundColor Green
}

if ($NoReload) {
    Write-Host "`n已完成清理 (未 reload)。" -ForegroundColor Yellow
    exit 0
}

Write-Host "[3/3] PM2 reload ck-backend..." -ForegroundColor Cyan
$pm2 = Get-Command pm2 -ErrorAction SilentlyContinue
if (-not $pm2) {
    Write-Warning "未找到 pm2。請手動執行: pm2 reload ck-backend"
    exit 1
}

pm2 reload ck-backend
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 完成。後端已以乾淨 Python 狀態重新啟動。" -ForegroundColor Green
    Write-Host "   驗證: curl http://127.0.0.1:8001/health" -ForegroundColor DarkGray
} else {
    Write-Warning "pm2 reload 失敗，請檢查 pm2 logs ck-backend"
    exit $LASTEXITCODE
}
