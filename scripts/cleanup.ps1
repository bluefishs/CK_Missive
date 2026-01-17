<#
.SYNOPSIS
    CK_Missive 專案清理腳本

.DESCRIPTION
    清理專案中的臨時檔案、快取目錄和其他不需要的檔案。
    建議在每次開發工作結束後執行。

.PARAMETER DryRun
    預覽模式，只顯示會被刪除的檔案，不實際刪除

.PARAMETER Verbose
    顯示詳細輸出

.EXAMPLE
    .\cleanup.ps1
    執行完整清理

.EXAMPLE
    .\cleanup.ps1 -DryRun
    預覽會被清理的檔案

.NOTES
    Version: 1.0.0
    Date: 2026-01-16
#>

param(
    [switch]$DryRun,
    [switch]$Verbose
)

$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CK_Missive 專案清理工具" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[預覽模式] 不會實際刪除任何檔案" -ForegroundColor Yellow
    Write-Host ""
}

$totalCleaned = 0

# 1. 清理 Claude 臨時目錄
Write-Host "[1/6] 清理 Claude 臨時目錄..." -ForegroundColor White
$claudeTemp = Get-ChildItem -Path $ProjectRoot -Filter "tmpclaude-*" -Recurse -ErrorAction SilentlyContinue
if ($claudeTemp) {
    $count = $claudeTemp.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個 Claude 臨時項目" -ForegroundColor Gray
    } else {
        $claudeTemp | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個 Claude 臨時項目" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

# 2. 清理 Python 快取
Write-Host "[2/6] 清理 Python __pycache__..." -ForegroundColor White
$pycache = Get-ChildItem -Path $ProjectRoot -Filter "__pycache__" -Directory -Recurse -ErrorAction SilentlyContinue
if ($pycache) {
    $count = $pycache.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個 __pycache__ 目錄" -ForegroundColor Gray
    } else {
        $pycache | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個 __pycache__ 目錄" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

# 3. 清理 .pyc 檔案
Write-Host "[3/6] 清理 .pyc 編譯檔案..." -ForegroundColor White
$pyc = Get-ChildItem -Path $ProjectRoot -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue
if ($pyc) {
    $count = $pyc.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個 .pyc 檔案" -ForegroundColor Gray
    } else {
        $pyc | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個 .pyc 檔案" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

# 4. 清理編輯器交換檔
Write-Host "[4/6] 清理編輯器交換檔 (.swp, .swo)..." -ForegroundColor White
$swapFiles = Get-ChildItem -Path $ProjectRoot -Include "*.swp", "*.swo", "*~" -Recurse -ErrorAction SilentlyContinue
if ($swapFiles) {
    $count = $swapFiles.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個交換檔" -ForegroundColor Gray
    } else {
        $swapFiles | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個交換檔" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

# 5. 清理 pytest 快取
Write-Host "[5/6] 清理 pytest 快取..." -ForegroundColor White
$pytestCache = Get-ChildItem -Path $ProjectRoot -Filter ".pytest_cache" -Directory -Recurse -ErrorAction SilentlyContinue
if ($pytestCache) {
    $count = $pytestCache.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個 .pytest_cache 目錄" -ForegroundColor Gray
    } else {
        $pytestCache | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個 .pytest_cache 目錄" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

# 6. 清理 Vite 快取
Write-Host "[6/6] 清理 Vite 快取..." -ForegroundColor White
$viteCache = Get-ChildItem -Path $ProjectRoot -Filter ".vite" -Directory -Recurse -ErrorAction SilentlyContinue
if ($viteCache) {
    $count = $viteCache.Count
    if ($DryRun) {
        Write-Host "  會刪除 $count 個 .vite 目錄" -ForegroundColor Gray
    } else {
        $viteCache | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  已刪除 $count 個 .vite 目錄" -ForegroundColor Green
    }
    $totalCleaned += $count
} else {
    Write-Host "  無需清理" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  預覽完成：共 $totalCleaned 個項目待清理" -ForegroundColor Yellow
} else {
    Write-Host "  清理完成：共清理 $totalCleaned 個項目" -ForegroundColor Green
}
Write-Host "============================================" -ForegroundColor Cyan
