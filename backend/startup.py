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
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # 禁止 .pyc 快取，確保代碼更新即時生效


def _clear_pycache():
    """清除 __pycache__ 確保代碼更新生效"""
    import shutil
    count = 0
    for root, dirs, _ in os.walk(BACKEND_DIR):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                count += 1
    if count > 0:
        print(f"[Step 0] Cleared {count} __pycache__ directories", flush=True)

_clear_pycache()


def log(step: str, msg: str, level: str = "INFO"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "\033[32m", "WARN": "\033[33m", "ERROR": "\033[31m"}.get(level, "")
    reset = "\033[0m" if prefix else ""
    print(f"{timestamp} [{step}] {prefix}{msg}{reset}", flush=True)


def check_port(port: int) -> bool:
    """檢查端口是否可用（使用 connect 測試，確保與 uvicorn bind 地址一致）"""
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect((host, port))
            return False  # 連得上 = 被佔用
    except (ConnectionRefusedError, OSError):
        return True  # 連不上 = 可用


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


def _acquire_lock() -> bool:
    """PID 鎖檔防護：防止 PM2 競態啟動多個進程"""
    lock_file = os.path.join(BACKEND_DIR, ".startup.lock")
    my_pid = os.getpid()

    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                old_pid = int(f.read().strip())
            # 檢查舊進程是否還活著
            if old_pid != my_pid:
                try:
                    os.kill(old_pid, 0)  # signal 0 = 探測存活
                    log("Step 0", f"Another startup (PID={old_pid}) is running, aborting.", "ERROR")
                    return False
                except OSError:
                    pass  # 舊進程已死，可以繼續
        except (ValueError, IOError):
            pass  # 鎖檔損壞，覆蓋

    with open(lock_file, "w") as f:
        f.write(str(my_pid))

    import atexit
    atexit.register(lambda: os.path.exists(lock_file) and os.remove(lock_file))
    return True


def main():
    # ================================================================
    # Step 0: PID 鎖檔 + 端口衝突偵測
    # ================================================================
    if not _acquire_lock():
        sys.exit(1)

    port = int(os.environ.get("BACKEND_PORT", "8001"))
    log("Step 0", f"Checking port {port} availability...")

    if not check_port(port):
        log("Step 0", f"Port {port} is occupied, attempting auto-cleanup...", "WARN")
        # 自動清理佔用端口的殭屍進程
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            for line in (result.stdout or "").splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != os.getpid():
                        log("Step 0", f"Killing orphan process PID={pid} on port {port}", "WARN")
                        subprocess.run(["taskkill", "/PID", pid, "/F"], timeout=5,
                                       capture_output=True, encoding="utf-8", errors="replace")
                        time.sleep(2)
        except Exception as e:
            log("Step 0", f"Auto-cleanup failed: {e}", "WARN")

        # 重新檢查
        if not check_port(port):
            log("Step 0", f"Port {port} still occupied after cleanup!", "ERROR")
            sys.exit(1)

    log("Step 0", f"Port {port} is available.")

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
    # Step 1: 安裝/更新 Python 依賴（條件式 — hash 不變則跳過，省 ~20s）
    # ================================================================
    import hashlib
    req_file = os.path.join(BACKEND_DIR, "requirements.txt")
    hash_file = os.path.join(BACKEND_DIR, ".pip_hash")
    req_hash = hashlib.md5(open(req_file, "rb").read()).hexdigest() if os.path.exists(req_file) else ""
    cached_hash = open(hash_file).read().strip() if os.path.exists(hash_file) else ""

    if req_hash and req_hash == cached_hash:
        log("Step 1", "Dependencies unchanged, skipping pip install.")
    else:
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
                log("Step 1", "Dependencies installed.")
            else:
                log("Step 1", f"pip install returned code {result.returncode} (non-critical)", "WARN")
            # 無論 rc，都寫 hash — 避免每次重啟重跑 20s pip install
            with open(hash_file, "w") as f:
                f.write(req_hash)
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
            # E4: Migration 後自動執行 ER Schema Diff（非阻塞）
            try:
                er_script = os.path.join(
                    os.path.dirname(BACKEND_DIR), "backend", "scripts", "extract_er_model.py"
                )
                if os.path.exists(er_script):
                    er_result = subprocess.run(
                        [sys.executable, er_script, "--diff"],
                        capture_output=True, text=True, timeout=30,
                        encoding="utf-8", errors="replace",
                    )
                    if er_result.returncode == 0 and "無變更" not in er_result.stdout:
                        log("Step 2", "ER Schema 有變更，建議執行: python scripts/extract_er_model.py", "WARN")
            except Exception:
                pass  # ER diff 失敗不阻斷啟動
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
    log("Step 3", f"Starting backend service on port {port}...")

    # 直接用 exec 替換進程，確保 stdout/stderr 完整傳遞給 PM2
    # Windows 的 os.execvp 行為等同 spawn+exit，PM2 會追蹤新進程
    import uvicorn
    # Windows 上 uvicorn reload 子進程有代碼不同步問題（新增的路由/schema 不生效）
    # 改為 reload=False，由 PM2 restart 管理代碼更新
    # 開發環境只綁 127.0.0.1 避免與 Docker Desktop port binding 衝突
    # 生產環境由 Docker 容器 (ck_missive_app) 綁 0.0.0.0
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        timeout_keep_alive=30,      # 閒置連線 30s 後關閉（防 keep-alive 堆積）
        limit_concurrency=50,       # 最大併發請求數（超過則 503）
        timeout_graceful_shutdown=15,  # graceful shutdown 15s 後強制結束
    )


if __name__ == "__main__":
    main()
