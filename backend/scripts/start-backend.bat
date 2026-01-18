@echo off
chcp 65001 >nul
echo ========================================
echo   CK_Missive 後端服務啟動腳本
echo ========================================
echo.

cd /d "%~dp0.."

echo [1/3] 檢查並終止佔用 8001 端口的進程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo   終止進程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/3] 等待端口釋放...
timeout /t 2 /nobreak >nul

echo [3/3] 啟動後端服務...
echo.
echo ========================================
echo   服務啟動中，按 Ctrl+C 停止
echo   API 文檔: http://localhost:8001/api/docs
echo ========================================
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
