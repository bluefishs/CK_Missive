"""
API 健康監控端點

v3.0 - 2026-02-24: 業務邏輯遷移至 SystemHealthService
"""
import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response
from datetime import datetime

from app.core.rate_limiter import limiter
from app.extended.models import User
from app.core.dependencies import require_admin, get_service
from app.services.system_health_service import (
    SystemHealthService,
    set_startup_time,
    get_uptime,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 向後相容: main.py 呼叫 set_startup_time()
__all__ = ["router", "set_startup_time", "get_uptime"]


@router.get("/health", summary="基本健康檢查")
@limiter.limit("60/minute")
async def basic_health_check(request: Request, response: Response):
    """基本健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
    }


@router.get("/health/detailed", summary="詳細健康檢查")
@limiter.limit("60/minute")
async def detailed_health_check(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """詳細系統健康檢查"""
    start_time = time.time()
    health_data: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "version": "3.0.0",
        "status": "healthy",
        "checks": {},
    }

    # 1. 資料庫連線
    db_check = await service.check_database()
    health_data["checks"]["database"] = db_check
    if db_check["status"] != "healthy":
        health_data["status"] = "unhealthy"

    # 2. 核心資料表
    tables_check = await service.check_core_tables()
    health_data["checks"]["tables"] = tables_check
    if any(t["status"] != "healthy" for t in tables_check.values()):
        health_data["status"] = "unhealthy"

    # 3. 連線池
    health_data["checks"]["connection_pool"] = service.check_connection_pool()

    # 4. 系統資源
    health_data["checks"]["system_resources"] = service.check_system_resources()

    # 5. 回應時間
    total_ms = (time.time() - start_time) * 1000
    health_data["total_response_time_ms"] = round(total_ms, 2)

    # 6. 整體狀態
    if total_ms > 5000:
        health_data["status"] = "slow"
        health_data["message"] = "API response time is slower than expected"
    elif health_data["status"] == "healthy":
        health_data["message"] = "All systems operational"

    return health_data


@router.get("/health/metrics", summary="效能指標")
@limiter.limit("60/minute")
async def get_performance_metrics(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """獲取系統效能指標"""
    try:
        metrics = await service.run_performance_benchmarks()
        return {
            "timestamp": datetime.now().isoformat(),
            "database_metrics": metrics,
            "recommendations": service.get_performance_recommendations(metrics),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"無法獲取效能指標: {str(e)}"
        )


@router.get("/health/readiness", summary="就緒狀態檢查")
@limiter.limit("60/minute")
async def readiness_check(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
):
    """檢查服務是否已準備好接受流量"""
    try:
        await service.check_readiness()
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept traffic",
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "message": "Service is not ready to accept traffic",
            },
        )


@router.get("/health/liveness", summary="存活狀態檢查")
@limiter.limit("60/minute")
async def liveness_check(request: Request, response: Response):
    """檢查服務是否存活"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "message": "Service is alive",
    }


@router.get("/health/pool", summary="連接池狀態")
@limiter.limit("60/minute")
async def connection_pool_status(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得資料庫連接池詳細狀態"""
    try:
        from app.core.db_monitor import DatabaseMonitor

        health = DatabaseMonitor.get_health_status()
        events = DatabaseMonitor.get_recent_events(limit=20)
        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "recent_events": events,
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "monitor_not_available",
            "error": str(e),
            "message": "連接池監控未啟用或發生錯誤",
        }


@router.get("/health/tasks", summary="背景任務狀態")
@limiter.limit("60/minute")
async def background_tasks_status(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得背景任務執行統計"""
    try:
        from app.core.background_tasks import BackgroundTaskManager

        stats = BackgroundTaskManager.get_stats()
        success_rate = 0.0
        if stats["total_tasks"] > 0:
            success_rate = stats["completed_tasks"] / stats["total_tasks"]
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if success_rate >= 0.9 else "degraded",
            "stats": stats,
            "success_rate": round(success_rate * 100, 2),
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "error": str(e),
        }


@router.get("/health/audit", summary="審計服務狀態")
@limiter.limit("60/minute")
async def audit_service_status(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """檢查審計服務運行狀態"""
    result = await service.check_audit_service()
    result["timestamp"] = datetime.now().isoformat()
    return result


@router.get("/health/summary", summary="系統健康摘要")
@limiter.limit("60/minute")
async def health_summary(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """整合所有健康檢查的摘要報告"""
    return await service.build_summary()
