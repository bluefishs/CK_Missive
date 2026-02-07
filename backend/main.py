# -*- coding: utf-8 -*-
"""
乾坤測繪公文管理系統 - FastAPI 主程式 (已重構)
"""

import logging
import sys
import time
from datetime import datetime
from fastapi import FastAPI, Depends, Response, Request

# from fastapi.middleware.cors import CORSMiddleware  # 禁用原始 CORS 中介軟體
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import api_router
from app.db.database import get_async_db, engine
from app.core.logging_manager import log_manager, LoggingMiddleware, log_info
from app.services.reminder_scheduler import (
    start_reminder_scheduler,
    stop_reminder_scheduler,
)
from app.services.google_sync_scheduler import (
    start_google_sync_scheduler,
    stop_google_sync_scheduler,
)
from app.services.backup_scheduler import start_backup_scheduler, stop_backup_scheduler
from app.core.exceptions import register_exception_handlers
from app.core.schema_validator import validate_schema
from app.extended.models import Base
from app.core.cors import allowed_origins
from app.core.rate_limiter import setup_rate_limiter

# --- 統一日誌編碼配置 (解決 Windows 終端中文亂碼) ---
if sys.platform == "win32":
    # Windows 環境下強制使用 UTF-8 編碼
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期事件處理器"""
    log_info(f"Application starting... v{app.version}")

    # Schema 驗證（開發環境嚴格模式：阻止啟動，生產環境僅警告）
    # 在開發環境中，若模型與資料庫不一致將直接拋出錯誤並阻止啟動
    is_development = (
        settings.DEVELOPMENT_MODE if hasattr(settings, "DEVELOPMENT_MODE") else True
    )
    try:
        is_valid, mismatches = await validate_schema(
            engine=engine,
            base=Base,
            strict=is_development,  # 開發模式下嚴格驗證，阻止啟動
            tables_to_check=None,  # 檢查所有表格
        )
        if not is_valid:
            for mismatch in mismatches:
                logger.error(f"❌ Schema 不一致: {mismatch}")
            if is_development:
                raise RuntimeError(
                    f"🚨 Schema 驗證失敗: 發現 {len(mismatches)} 個不一致。"
                    "請確保 SQLAlchemy 模型與資料庫欄位同步。"
                )
    except Exception as e:
        logger.error(f"Schema 驗證失敗: {e}")
        if is_development:
            raise

    # 啟動提醒排程器
    try:
        await start_reminder_scheduler()
        logger.info("✅ 提醒排程器已啟動")
    except Exception as e:
        logger.warning(f"⚠️ 提醒排程器啟動失敗: {e}")

    # 啟動 Google Calendar 同步排程器
    try:
        await start_google_sync_scheduler()
        logger.info("✅ Google Calendar 同步排程器已啟動")
    except Exception as e:
        logger.warning(f"⚠️ Google Calendar 同步排程器啟動失敗: {e}")

    # 啟動資料庫備份排程器
    try:
        await start_backup_scheduler()
        logger.info("✅ 資料庫備份排程器已啟動")
    except Exception as e:
        logger.warning(f"⚠️ 資料庫備份排程器啟動失敗: {e}")

    # 測試 Redis 連線（AI 快取與統計持久化）
    try:
        from app.core.redis_client import check_redis_health
        redis_health = await check_redis_health()
        if redis_health["status"] == "healthy":
            logger.info(
                f"✅ Redis 連線成功 (v{redis_health.get('redis_version', 'unknown')})"
            )
        else:
            logger.warning(
                f"⚠️ Redis 不可用，AI 快取與統計將使用記憶體模式: "
                f"{redis_health.get('message', redis_health.get('error', ''))}"
            )
    except Exception as e:
        logger.warning(f"⚠️ Redis 初始化失敗，將使用記憶體 fallback: {e}")

    logger.info("應用程式已啟動。")
    yield
    logger.info("應用程式關閉中...")

    # 關閉 Redis 連線
    try:
        from app.core.redis_client import close_redis
        await close_redis()
        logger.info("✅ Redis 連線已關閉")
    except Exception as e:
        logger.warning(f"⚠️ Redis 關閉失敗: {e}")

    # 停止資料庫備份排程器
    try:
        await stop_backup_scheduler()
        logger.info("✅ 資料庫備份排程器已停止")
    except Exception as e:
        logger.warning(f"⚠️ 資料庫備份排程器停止失敗: {e}")

    # 停止 Google Calendar 同步排程器
    try:
        await stop_google_sync_scheduler()
        logger.info("✅ Google Calendar 同步排程器已停止")
    except Exception as e:
        logger.warning(f"⚠️ Google Calendar 同步排程器停止失敗: {e}")

    # 停止提醒排程器
    try:
        await stop_reminder_scheduler()
        logger.info("✅ 提醒排程器已停止")
    except Exception as e:
        logger.warning(f"⚠️ 提醒排程器停止失敗: {e}")
    await engine.dispose()
    logger.info("資料庫連線池已關閉。")


app = FastAPI(
    title="乾坤測繪公文管理系統 API",
    description="公文記錄管理、檢索查詢、案件歸聯系統後端API",
    version="3.0.1",  # Trigger reload for audit fix
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    redirect_slashes=False,  # 避免 307 重導向問題
)


# --- 🎯 CORS 解決方案 - 使用 cors.py 集中管理的來源清單 ---
from fastapi.middleware.cors import CORSMiddleware

# 使用 cors.py 中定義的 allowed_origins（包含 localhost 和所有內網 IP）
# 注意: allow_credentials=True 時不能使用 ["*"] 作為 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # 從 cors.py 導入的完整來源清單
    allow_credentials=True,  # 必須為 True 以支援 httpOnly cookie 認證
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],  # 允許前端讀取的回應標頭
)
# 已移除重複的 CORSMiddleware - 使用上面已驗證可工作的配置
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware, log_manager=log_manager)

# --- 🛡️ 安全標頭中間件 (v1.27.0) ---
from app.core.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# --- 🛡️ CSRF 防護中間件 (v1.44.0) ---
from app.core.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# --- 🛡️ 統一異常處理器 ---
# 確保所有 AppException（NotFoundException, ForbiddenException 等）正確返回對應的 HTTP 狀態碼和 CORS 標頭
register_exception_handlers(app)

# --- 🚀 API 速率限制設定 ---
setup_rate_limiter(app)


@app.middleware("http")
async def add_performance_headers(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# --- 靜態檔案與 API 路由 ---
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    logger.warning("Static directory not found, skipping.")

# 證照附件等上傳檔案目錄
try:
    import os
    uploads_dir = getattr(settings, 'ATTACHMENT_STORAGE_PATH', None) or os.getenv('ATTACHMENT_STORAGE_PATH', 'uploads')
    if os.path.exists(uploads_dir):
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    else:
        os.makedirs(uploads_dir, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
except RuntimeError as e:
    logger.warning(f"Uploads directory mount failed: {e}")


# --- 健康檢查端點 ---
@app.get("/health/detailed", tags=["System Monitoring"])
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)):
    """
    詳細系統健康檢查

    回傳完整的系統健康狀態，包括：
    - 資料庫連線狀態與延遲
    - 資料表記錄數量
    - 系統資源使用 (記憶體、磁碟)
    - 排程器狀態
    - API 速率限制狀態
    """
    import psutil
    from app.core.cors import allowed_origins, local_ips

    start_time = time.time()

    health_data = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "version": app.version,
        "environment": "development" if settings.DEVELOPMENT_MODE else "production",
        "status": "healthy",
        "checks": {},
    }

    # 資料庫檢查
    try:
        db_start = time.time()
        result = await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - db_start) * 1000

        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
        }
    except Exception as e:
        health_data["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    # 資料表檢查
    tables = [
        "documents",
        "government_agencies",
        "partner_vendors",
        "contract_projects",
    ]
    tables_check = {}

    for table in tables:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            tables_check[table] = {"status": "healthy", "record_count": count}
        except Exception as e:
            tables_check[table] = {"status": "error", "error": str(e)}
            health_data["status"] = "unhealthy"

    health_data["checks"]["tables"] = tables_check

    # 系統資源 - 記憶體
    try:
        memory = psutil.virtual_memory()
        memory_status = "healthy"
        if memory.percent > 90:
            memory_status = "critical"
            health_data["status"] = "unhealthy"
        elif memory.percent > 80:
            memory_status = "warning"
            if health_data["status"] == "healthy":
                health_data["status"] = "warning"

        health_data["checks"]["memory"] = {
            "status": memory_status,
            "usage_percent": memory.percent,
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
        }
    except Exception as e:
        health_data["checks"]["memory"] = {"status": "unknown", "error": str(e)}

    # 系統資源 - 磁碟
    try:
        disk = psutil.disk_usage("/")
        disk_status = "healthy"
        disk_percent = disk.percent
        if disk_percent > 95:
            disk_status = "critical"
            health_data["status"] = "unhealthy"
        elif disk_percent > 85:
            disk_status = "warning"
            if health_data["status"] == "healthy":
                health_data["status"] = "warning"

        health_data["checks"]["disk"] = {
            "status": disk_status,
            "usage_percent": disk_percent,
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
        }
    except Exception as e:
        health_data["checks"]["disk"] = {"status": "unknown", "error": str(e)}

    # 系統資源 - CPU
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_status = "healthy"
        if cpu_percent > 90:
            cpu_status = "warning"

        health_data["checks"]["cpu"] = {
            "status": cpu_status,
            "usage_percent": cpu_percent,
            "cores": psutil.cpu_count(),
        }
    except Exception as e:
        health_data["checks"]["cpu"] = {"status": "unknown", "error": str(e)}

    # 排程器狀態
    from app.services.reminder_scheduler import get_reminder_scheduler
    from app.services.google_sync_scheduler import get_google_sync_scheduler
    from app.services.backup_scheduler import get_backup_scheduler

    try:
        reminder_scheduler = get_reminder_scheduler()
        google_scheduler = get_google_sync_scheduler()
        backup_scheduler = get_backup_scheduler()

        health_data["checks"]["schedulers"] = {
            "reminder": {
                "status": "running" if reminder_scheduler.is_running else "stopped",
                "interval_seconds": reminder_scheduler.check_interval,
            },
            "google_sync": {
                "status": "running" if google_scheduler.is_running else "stopped",
                "interval_seconds": google_scheduler.sync_interval,
            },
            "backup": {
                "status": "running" if backup_scheduler and backup_scheduler.is_running else "stopped",
                "scheduled_time": f"{backup_scheduler.backup_hour:02d}:{backup_scheduler.backup_minute:02d}" if backup_scheduler else "02:00",
            },
        }
    except Exception as e:
        health_data["checks"]["schedulers"] = {"status": "error", "error": str(e)}

    # CORS 設定
    health_data["checks"]["cors"] = {
        "origins_count": len(allowed_origins),
        "local_ips_detected": list(local_ips),
    }

    # 速率限制設定
    health_data["checks"]["rate_limit"] = {
        "per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "per_day": settings.RATE_LIMIT_PER_DAY,
    }

    health_data["total_response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    return health_data


app.include_router(api_router, prefix="/api")


# --- 根路徑核心端點 ---
@app.get("/", tags=["System"])
async def root():
    return {
        "message": "乾坤測繪公文管理系統 API",
        "version": app.version,
        "status": "running",
        "documentation": app.docs_url,
    }


@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_async_db)):
    """
    基本健康檢查端點

    回傳系統健康狀態，包含資料庫連線、版本資訊等。
    """
    from app.core.cors import allowed_origins, local_ips

    db_status = "disconnected"
    db_latency_ms = None

    try:
        import time
        start = time.time()
        result = await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - start) * 1000, 2)
        if result.scalar() == 1:
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    is_healthy = db_status == "connected"

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": app.version,
        "environment": "development" if settings.DEVELOPMENT_MODE else "production",
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        },
        "cors": {
            "origins_count": len(allowed_origins),
            "local_ips_detected": len(local_ips),
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/debug/cors", tags=["Debug"])
async def debug_cors(request: Request):
    """
    CORS 配置診斷端點 (僅開發環境可用)

    回傳當前 CORS 配置資訊，用於診斷跨域問題。
    """
    from app.core.cors import allowed_origins, local_ips, is_origin_allowed

    # 僅開發環境可用
    if not settings.DEVELOPMENT_MODE:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="此端點僅在開發環境可用")

    # 獲取請求的 Origin
    request_origin = request.headers.get("origin", "N/A")

    # 按 IP 分組顯示 (只顯示前 20 個)
    origins_sample = sorted(allowed_origins)[:20]

    return {
        "request_origin": request_origin,
        "is_allowed": is_origin_allowed(request_origin) if request_origin != "N/A" else None,
        "config": {
            "total_origins": len(allowed_origins),
            "local_ips_detected": list(local_ips),
            "sample_origins": origins_sample,
        },
        "tips": {
            "add_origin": "使用 CORS_ORIGINS 環境變數添加新來源",
            "format": "CORS_ORIGINS=http://example.com:3000,http://other.com:3000",
        }
    }


@app.post("/api/debug/cors/test", tags=["Debug"])
async def test_cors_origin(request: Request, origin: str = None):
    """
    測試特定 Origin 是否被允許

    可在請求 body 中傳入 origin 參數，或使用請求的 Origin header。
    """
    from app.core.cors import is_origin_allowed, add_origin

    if not settings.DEVELOPMENT_MODE:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="此端點僅在開發環境可用")

    test_origin = origin or request.headers.get("origin")

    if not test_origin:
        return {
            "error": "請提供 origin 參數或在請求中包含 Origin header"
        }

    return {
        "origin": test_origin,
        "is_allowed": is_origin_allowed(test_origin),
        "message": "允許" if is_origin_allowed(test_origin) else "未在允許列表中"
    }


# --- 全域異常處理已移至 app.core.exceptions ---
# 統一異常處理器已透過 register_exception_handlers(app) 註冊

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Keep same port but ensure clean start
        reload=True,
        log_level="info",
        access_log=True,
    )
