# -*- coding: utf-8 -*-
"""
CK_Missive Backend Startup Wrapper (Python)

PM2 啟動前自動執行：
Step 0:   端口衝突偵測 (port 8001)
Step 0.5: 基礎設施依賴檢查 (PostgreSQL + Redis)
Step 1:   安裝/更新 Python 依賴
Step 2:   套用資料庫遷移 (Alembic)
Step 3:   啟動 FastAPI 後端服務

使用 Python 替代 PowerShell 避免 Windows cp950 編碼問題。
PM2 ecosystem.config.js 可直接使用此腳本。

Version: 1.0.0
Created: 2026-02-11
"""

import os
import socket
import subprocess
import sys
import time

# 切換到 backend 目錄
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND_DIR)

# 載入 .env 環境變數（Feature Flags 如 PGVECTOR_ENABLED 需在模組匯入前可用）
try:
    from dotenv import load_dotenv
    # 優先載入專案根目錄的 .env（SSOT）
    root_env = os.path.join(os.path.dirname(BACKEND_DIR), ".env")
    if os.path.exists(root_env):
        load_dotenv(root_env, override=True)
    else:
        load_dotenv()  # fallback: 搜尋 .env
except ImportError:
    pass  # python-dotenv 不可用時跳過

# 強制 UTF-8（多層防護：PYTHONUTF8 為 Python 3.7+ 全域 UTF-8 模式）
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONUTF8"] = "1"


def log(step: str, msg: str, level: str = "INFO"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "\033[32m", "WARN": "\033[33m", "ERROR": "\033[31m"}.get(level, "")
    reset = "\033[0m" if prefix else ""
    print(f"{timestamp} [{step}] {prefix}{msg}{reset}", flush=True)


def check_port(port: int) -> bool:
    """檢查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result != 0  # 0 = 已被佔用, 非0 = 可用
    except Exception:
        return True  # 無法檢查，視為可用


def check_service(host: str, port: int, timeout: float = 2.0) -> bool:
    """檢查服務是否可連線"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except Exception:
        return False


def wait_for_service(host: str, port: int, name: str, max_wait: int = 30) -> bool:
    """等待服務就緒，最多等待 max_wait 秒"""
    for i in range(max_wait):
        if check_service(host, port):
            return True
        if i == 0:
            log("WAIT", f"等待 {name} ({host}:{port}) 就緒...")
        time.sleep(1)
    return False


def main():
    # ================================================================
    # Step 0: 端口衝突偵測
    # ================================================================
    log("Step 0", "Checking port 8001 availability...")

    if not check_port(8001):
        log("Step 0", "Port 8001 is occupied! Another process is using it.", "ERROR")
        log("Step 0", "Check: netstat -ano | findstr :8001", "WARN")
        sys.exit(1)

    log("Step 0", "Port 8001 is available.")

    # ================================================================
    # Step 0.5: 基礎設施依賴檢查
    # ================================================================
    log("Step 0.5", "Checking infrastructure dependencies...")

    # PostgreSQL (必要) — 等待最多 30 秒
    if not wait_for_service("localhost", 5434, "PostgreSQL", max_wait=30):
        log("Step 0.5", "PostgreSQL on port 5434 is not reachable!", "ERROR")
        log("Step 0.5", "Start: docker compose -f docker-compose.infra.yml up -d", "WARN")
        sys.exit(1)
    log("Step 0.5", "PostgreSQL on port 5434: OK")

    # Redis (選用) — 僅檢查一次
    if check_service("localhost", 6380):
        log("Step 0.5", "Redis on port 6380: OK")
    else:
        log("Step 0.5", "Redis on port 6380 not available. AI cache will use in-memory fallback.", "WARN")

    # ================================================================
    # Step 1: 安裝/更新 Python 依賴
    # ================================================================
    log("Step 1", "Checking Python dependencies...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            log("Step 1", "Dependencies check completed.")
        else:
            log("Step 1", f"pip install returned code {result.returncode}", "WARN")
    except subprocess.TimeoutExpired:
        log("Step 1", "pip install timed out (120s), continuing...", "WARN")
    except Exception as e:
        log("Step 1", f"pip install failed: {e}", "WARN")

    # ================================================================
    # Step 2: 套用資料庫遷移
    # ================================================================
    log("Step 2", "Checking database migrations...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            log("Step 2", "Database migrations applied.")
        else:
            log("Step 2", f"Alembic returned code {result.returncode}", "WARN")
            if result.stderr:
                # 只輸出最後幾行避免刷屏
                for line in result.stderr.strip().split("\n")[-3:]:
                    log("Step 2", f"  {line}", "WARN")
    except subprocess.TimeoutExpired:
        log("Step 2", "Alembic timed out (60s), continuing...", "WARN")
    except Exception as e:
        log("Step 2", f"Alembic failed: {e}", "WARN")

    # ================================================================
    # Step 3: 啟動 FastAPI 後端服務
    # ================================================================
    log("Step 3", "Starting backend service on port 8001...")

    if sys.platform == "win32":
        # Windows: os.execvp 會 spawn 新進程然後退出原進程，
        # 導致 PM2 看到進程退出而觸發重啟迴圈。
        # 改用 subprocess.run 保持阻塞，PM2 追蹤此 Python 進程。
        result = subprocess.run(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"],
        )
        sys.exit(result.returncode)
    else:
        # Linux/macOS: os.execvp 正確替換進程
        os.execvp(
            sys.executable,
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"],
        )


if __name__ == "__main__":
    main()
