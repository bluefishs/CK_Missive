# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    CK_Missive 後端服務啟動腳本

.DESCRIPTION
    此腳本用於安全啟動後端服務，會先終止佔用端口的舊進程，
    然後啟動新的 uvicorn 服務。

.PARAMETER Port
    指定後端服務端口 (預設: 8001)

.PARAMETER Reload
    是否啟用熱重載 (預設: true)

.EXAMPLE
    .\start-backend.ps1
    .\start-backend.ps1 -Port 8002
    .\start-backend.ps1 -Reload $false

.NOTES
    版本: 1.0.0
    日期: 2026-01-15
#>

param(
    [int]$Port = 8001,
    [bool]$Reload = $true
)

# 設置控制台編碼為 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CK_Missive 後端服務啟動腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 獲取腳本所在目錄的父目錄 (backend)
$BackendDir = Split-Path -Parent $PSScriptRoot
if (-not $BackendDir) {
    $BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

Write-Host "[1/4] 檢查端口 $Port 佔用情況..." -ForegroundColor Yellow

# 查找佔用端口的進程
$Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($Connections) {
    Write-Host "  發現 $($Connections.Count) 個進程佔用端口 $Port" -ForegroundColor Red

    foreach ($conn in $Connections) {
        $ProcessId = $conn.OwningProcess
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue

        if ($Process) {
            Write-Host "  終止進程: $($Process.Name) (PID: $ProcessId)" -ForegroundColor Red
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        }
    }

    # 等待端口釋放
    Write-Host "[2/4] 等待端口釋放..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
} else {
    Write-Host "  端口 $Port 未被佔用" -ForegroundColor Green
    Write-Host "[2/4] 跳過端口清理" -ForegroundColor Yellow
}

# 確認端口已釋放
$StillOccupied = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($StillOccupied) {
    Write-Host "  警告: 端口 $Port 仍被佔用，可能需要手動處理" -ForegroundColor Yellow
}

# 切換到 backend 目錄
Write-Host "[3/5] 切換到後端目錄: $BackendDir" -ForegroundColor Yellow
Set-Location $BackendDir

# 驗證設定檔
Write-Host "[4/5] 驗證設定檔..." -ForegroundColor Yellow
$ProjectRoot = Split-Path -Parent $BackendDir
$RootEnvFile = Join-Path $ProjectRoot ".env"
$BackendEnvFile = Join-Path $BackendDir ".env"

# 檢查根目錄 .env 是否存在
if (Test-Path $RootEnvFile) {
    Write-Host "  ✓ 專案根目錄 .env 存在" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 專案根目錄 .env 不存在，將使用預設值" -ForegroundColor Yellow
}

# 警告如果 backend/.env 存在
if (Test-Path $BackendEnvFile) {
    Write-Host "  ⚠ 警告: backend/.env 存在，可能導致設定衝突！" -ForegroundColor Yellow
    Write-Host "    建議刪除 backend/.env，統一使用專案根目錄的 .env" -ForegroundColor Yellow
}

# 驗證資料庫設定
$ConfigTest = python -c "from app.core.config import settings; print('OK' if settings.validate_database_config() else 'WARN')" 2>&1
if ($ConfigTest -eq "OK") {
    Write-Host "  ✓ 資料庫設定驗證通過" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 資料庫設定可能不完整，請檢查 .env 檔案" -ForegroundColor Yellow
}

# 構建啟動命令
$ReloadFlag = if ($Reload) { "--reload" } else { "" }
$Command = "python -m uvicorn main:app $ReloadFlag --host 0.0.0.0 --port $Port"

Write-Host "[5/5] 啟動後端服務..." -ForegroundColor Yellow
Write-Host "  命令: $Command" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  服務啟動中，按 Ctrl+C 停止" -ForegroundColor Green
Write-Host "  API 文檔: http://localhost:$Port/api/docs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 執行命令
Invoke-Expression $Command
