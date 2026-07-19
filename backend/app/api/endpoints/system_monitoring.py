# -*- coding: utf-8 -*-
"""
系統監控和錯誤 LOG 管理 API 端點（薄委派層）。所有端點需要管理員認證。

2026-07-20 DDD 標準化：日誌檔狀態/系統指標/覆盤儀表板彙總邏輯抽至
SystemMonitoringService；詳細健康檢查委派 canonical SystemHealthService。
端點只負責 HTTP（參數/認證/錯誤碼）。
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_manager import ErrorCategory, log_info
from app.core.dependencies import require_admin
from app.extended.models import User
from app.db.database import get_async_db
from app.services.system.system_monitoring_service import SystemMonitoringService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/health-detailed", summary="詳細系統健康檢查")
async def get_detailed_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """獲取系統詳細健康狀況（含錯誤統計）。"""
    log_info("Detailed health check requested", ErrorCategory.SYSTEM)
    try:
        # 2026-07-20 異質同工收斂：委派 canonical SystemHealthService（health.py 同源），
        #   消除本端點自組的重複 psutil/SQL、順修 uptime placeholder。前端僅依賴頂層 status。
        from app.services.system.health_service import SystemHealthService

        svc = SystemHealthService(db)
        db_check = await svc.check_database()
        resources = SystemHealthService.check_system_resources()
        uptime = SystemHealthService.get_uptime()
        error_summary = SystemMonitoringService.error_summary()

        db_ok = db_check.get("status") == "healthy"
        return {
            "status": "healthy" if db_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": db_check,
            "system": resources,
            "logs": error_summary,
            "uptime": uptime,
        }
    except Exception as e:
        from app.core.logging_manager import log_error
        log_error(f"Health check failed: {e}", ErrorCategory.SYSTEM)
        logger.error(f"詳細健康檢查失敗: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="健康檢查失敗，請稍後再試")


@router.post("/error-summary", summary="錯誤統計摘要")
async def get_error_summary(current_user: User = Depends(require_admin())):
    log_info("Error summary requested", ErrorCategory.SYSTEM)
    return SystemMonitoringService.error_summary()


@router.post("/recent-errors", summary="最近錯誤列表")
async def get_recent_errors(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="錯誤類別篩選"),
    level: Optional[str] = Query(None, description="錯誤級別篩選"),
    current_user: User = Depends(require_admin()),
):
    log_info(f"Recent errors requested: limit={limit}, category={category}, level={level}",
             ErrorCategory.SYSTEM)
    return SystemMonitoringService.recent_errors(limit, category, level)


@router.post("/clear-error-stats", summary="清除錯誤統計")
async def clear_error_stats(current_user: User = Depends(require_admin())):
    """清除錯誤統計數據（僅統計，不刪除日誌文件）。"""
    log_info("Error stats clear requested", ErrorCategory.SYSTEM)
    return SystemMonitoringService.clear_error_stats()


@router.post("/log-files", summary="日誌文件狀態")
async def get_log_files_status(current_user: User = Depends(require_admin())):
    log_info("Log files status requested", ErrorCategory.SYSTEM)
    return SystemMonitoringService.log_files_status()


@router.post("/test-logging", summary="測試日誌記錄")
async def test_logging(
    level: str = "INFO",
    category: str = "SYSTEM",
    message: str = "Test log message",
    current_user: User = Depends(require_admin()),
):
    """測試日誌記錄功能。"""
    try:
        return SystemMonitoringService.record_test_log(level, category, message)
    except ValueError as e:
        logger.error(f"日誌測試 - 無效的級別或分類: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="日誌級別或分類無效")
    except Exception as e:
        logger.error(f"日誌測試失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="日誌測試失敗，請稍後再試")


@router.post("/error-logs", summary="取得錯誤日誌")
async def get_error_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin()),
):
    """取得錯誤日誌記錄（簡化 stub）。"""
    log_info("Error logs requested", ErrorCategory.SYSTEM)
    return {
        "logs": [{
            "timestamp": "2025-09-12T11:44:00.000Z",
            "level": "ERROR",
            "message": "Test error log entry",
            "source": "logs/errors.log",
        }],
        "total": 1, "limit": limit, "offset": offset,
    }


@router.post("/system-metrics", summary="系統性能指標")
async def get_system_metrics(current_user: User = Depends(require_admin())):
    log_info("System metrics requested", ErrorCategory.SYSTEM)
    try:
        return SystemMonitoringService.system_metrics()
    except ImportError:
        return {"error": "psutil not available", "message": "Install psutil for detailed system metrics"}
    except Exception as e:
        from app.core.logging_manager import log_error
        log_error(f"Failed to get system metrics: {e}", ErrorCategory.SYSTEM)
        logger.error(f"獲取系統指標失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="獲取系統指標失敗，請稍後再試")


@router.post("/review-dashboard", summary="系統覆盤儀表板")
async def get_review_dashboard(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """彙總子系統狀態 — KG / Code Graph / DB Graph / KB / Skill Evolution / 排程器。"""
    return await SystemMonitoringService().review_dashboard(db)
