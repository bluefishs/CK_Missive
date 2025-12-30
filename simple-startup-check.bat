@echo off
REM ===================================================================
REM 簡單的系統重啟後檢查腳本 - 避免複雜化
REM ===================================================================

echo === 系統重啟後基本檢查 ===
cd /d "%~dp0"

echo.
echo 1. 檢查必要檔案是否存在...
if not exist .env (
    echo [ERROR] .env 檔案不存在
    copy .env.master .env > nul 2>&1
    echo [FIX] 已從 .env.master 復原
)

if not exist docker-compose.unified.yml (
    echo [ERROR] docker-compose.unified.yml 不存在
    goto :error
)

echo [OK] 基本檔案檢查完成

echo.
echo 2. 啟動服務...
docker-compose -f docker-compose.unified.yml up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker 服務啟動失敗
    goto :error
)

echo.
echo 3. 等待服務就緒 (30秒)...
timeout /t 30 /nobreak > nul

echo.
echo 4. 檢查服務狀態...
docker-compose -f docker-compose.unified.yml ps

echo.
echo 5. 簡單連通性測試...
curl -s http://localhost:8001/health > nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] 後端 API 可連接
) else (
    echo [WARN] 後端 API 無法連接，可能需要更多時間啟動
)

curl -s http://localhost:3000 > nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] 前端服務可連接
) else (
    echo [WARN] 前端服務無法連接，可能需要更多時間啟動
)

echo.
echo === 基本檢查完成 ===
echo 如果服務無法正常訪問，請等待 1-2 分鐘後再試
echo.
echo 服務地址：
echo   前端: http://localhost:3000
echo   後端: http://localhost:8001
echo   管理: http://localhost:8080
echo.
pause
goto :end

:error
echo.
echo [ERROR] 啟動過程中發生錯誤
echo 請檢查 Docker 是否正常運行
pause

:end