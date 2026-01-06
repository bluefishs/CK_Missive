# -*- coding: utf-8 -*-
"""
乾坤測繪公文管理系統 - FastAPI 主程式 (已重構)
"""
import logging
import time
from datetime import datetime
from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import api_router
from app.db.database import get_async_db, engine
from app.core.logging_manager import log_manager, LoggingMiddleware, log_info
from app.services.reminder_scheduler import start_reminder_scheduler, stop_reminder_scheduler
from app.core.exceptions import register_exception_handlers

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期事件處理器"""
    log_info(f"Application starting... v{app.version}")
    # await start_reminder_scheduler()  # 暫時禁用直到建立完整的資料表
    logger.info("應用程式已啟動。")
    yield
    logger.info("應用程式關閉中...")
    # await stop_reminder_scheduler()
    await engine.dispose()
    logger.info("資料庫連線池已關閉。")

app = FastAPI(
    title="乾坤測繪公文管理系統 API",
    description="公文記錄管理、檢索查詢、案件歸聯系統後端API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    redirect_slashes=False  # 避免 307 重導向問題
)

# --- 註冊統一異常處理器 ---
register_exception_handlers(app)

# --- 中介軟體 (Middleware) ---
origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware, log_manager=log_manager)

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

# --- 健康檢查端點 ---
@app.get("/health/detailed", tags=["System Monitoring"])
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)):
    """詳細系統健康檢查"""
    import psutil
    start_time = time.time()

    health_data = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API", # Debug fix
        "version": app.version,
        "status": "healthy",
        "checks": {}
    }

    # 資料庫檢查
    try:
        db_start = time.time()
        result = await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - db_start) * 1000

        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2)
        }
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["status"] = "unhealthy"

    # 資料表檢查
    tables = ["documents", "government_agencies", "partner_vendors", "contract_projects"]
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

    # 系統資源
    try:
        memory = psutil.virtual_memory()
        health_data["checks"]["system"] = {
            "status": "healthy",
            "memory_usage_percent": memory.percent,
            "available_memory_gb": round(memory.available / (1024**3), 2)
        }

        if memory.percent > 90:
            health_data["checks"]["system"]["status"] = "warning"
            health_data["status"] = "warning"

    except Exception as e:
        health_data["checks"]["system"] = {"status": "unknown", "error": str(e)}

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
        "documentation": app.docs_url
    }

@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_async_db)):
    db_status = "disconnected"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"database": db_status, "status": "healthy" if db_status == "connected" else "unhealthy"}


# --- 全域異常處理已移至 app.core.exceptions ---
# 統一異常處理器已透過 register_exception_handlers(app) 註冊

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )