# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    [DEPRECATED] CK_Missive 開發環境一鍵啟動腳本

.DESCRIPTION
    ⚠️ 此腳本已棄用，請改用：
        .\scripts\dev-start.ps1          # 混合模式（推薦）
        .\scripts\dev-start.ps1 -Status  # 查看狀態
        .\scripts\dev-stop.ps1           # 停止所有

    此腳本保留供向後相容，功能不再更新。

.EXAMPLE
    .\start-dev.ps1

.NOTES
    版本: 1.0.0 (DEPRECATED - use dev-start.ps1 instead)
    日期: 2026-01-15
#>

Write-Host "⚠️  WARNING: start-dev.ps1 is deprecated. Use dev-start.ps1 instead." -ForegroundColor Yellow
Write-Host "   Recommended: .\scripts\dev-start.ps1" -ForegroundColor Yellow
Write-Host ""

# 設置控制台編碼為 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CK_Missive 開發環境啟動腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Step 1: 檢查並啟動 Docker
Write-Host "[1/4] 檢查 Docker 狀態..." -ForegroundColor Yellow

$DockerRunning = docker info 2>$null
if (-not $DockerRunning) {
    Write-Host "  Docker 未運行，請先啟動 Docker Desktop" -ForegroundColor Red
    Write-Host "  啟動後請重新執行此腳本" -ForegroundColor Red
    exit 1
}
Write-Host "  Docker 正在運行" -ForegroundColor Green

# Step 2: 啟動 PostgreSQL 容器
Write-Host "[2/4] 啟動 PostgreSQL 容器..." -ForegroundColor Yellow

$ContainerStatus = docker ps -a --filter "name=ck_missive_postgres_dev" --format "{{.Status}}" 2>$null
if ($ContainerStatus -like "Up*") {
    Write-Host "  PostgreSQL 容器已在運行" -ForegroundColor Green
} else {
    docker start ck_missive_postgres_dev 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PostgreSQL 容器已啟動" -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  PostgreSQL 容器啟動失敗" -ForegroundColor Red
    }
}

# Step 3: 驗證設定檔
Write-Host "[3/5] 驗證設定檔..." -ForegroundColor Yellow

$RootEnvFile = Join-Path $ProjectRoot ".env"
$BackendEnvFile = Join-Path $ProjectRoot "backend\.env"

if (Test-Path $RootEnvFile) {
    Write-Host "  ✓ 專案根目錄 .env 存在" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 專案根目錄 .env 不存在" -ForegroundColor Yellow
    Write-Host "    請複製 .env.example 並設定必要參數" -ForegroundColor Yellow
}

if (Test-Path $BackendEnvFile) {
    Write-Host "  ⚠ 警告: backend/.env 存在，可能導致設定衝突！" -ForegroundColor Yellow
    Write-Host "    建議刪除此檔案，統一使用專案根目錄的 .env" -ForegroundColor Yellow
}

# Step 4: 清理並啟動後端
Write-Host "[4/5] 啟動後端服務..." -ForegroundColor Yellow

# 終止佔用 8001 端口的進程
$Connections = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $Connections) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# 在新窗口啟動後端
$BackendCmd = "cd '$ProjectRoot\backend'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd
Write-Host "  後端服務已在新窗口啟動" -ForegroundColor Green

# Step 5: 啟動前端
Write-Host "[5/5] 啟動前端服務..." -ForegroundColor Yellow

# 在新窗口啟動前端
$FrontendCmd = "cd '$ProjectRoot\frontend'; npm run dev -- --host"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd
Write-Host "  前端服務已在新窗口啟動" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  開發環境啟動完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  後端: http://localhost:8001" -ForegroundColor Cyan
Write-Host "  API 文檔: http://localhost:8001/api/docs" -ForegroundColor Cyan
Write-Host ""
