# -*- coding: utf-8 -*-
"""
系統監控和錯誤LOG管理API端點
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_manager import log_manager, LogLevel, ErrorCategory, log_info, log_error
from app.db.database import get_async_db

router = APIRouter()


@router.get("/health-detailed", summary="詳細系統健康檢查")
async def get_detailed_health_check(db: AsyncSession = Depends(get_async_db)):
    """
    獲取系統的詳細健康狀況，包括錯誤統計
    """
    log_info("Detailed health check requested", ErrorCategory.SYSTEM)
    
    try:
        # 基本健康檢查
        from sqlalchemy import text
        db_result = await db.execute(text("SELECT 1"))
        db_status = "connected" if db_result.scalar() == 1 else "disconnected"
        
        # 獲取錯誤統計
        error_summary = log_manager.get_error_summary()
        
        # 系統資源信息（優化版本 - 移除阻塞性的CPU檢測）
        import psutil
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=0),  # 非阻塞版本，使用上次的數據
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0
        }
        
        health_data = {
            "status": "healthy" if db_status == "connected" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "status": db_status,
                "connection_pool": "active"
            },
            "system": system_info,
            "logs": error_summary,
            "uptime": "calculated_uptime_placeholder"
        }
        
        return health_data
        
    except Exception as e:
        from app.core.logging_manager import log_error
        log_error(f"Health check failed: {str(e)}", ErrorCategory.SYSTEM)
        raise HTTPException(status_code=503, detail="Health check failed")


@router.get("/error-summary", summary="錯誤統計摘要")
async def get_error_summary():
    """
    獲取系統錯誤統計摘要
    """
    log_info("Error summary requested", ErrorCategory.SYSTEM)
    return log_manager.get_error_summary()


@router.get("/recent-errors", summary="最近錯誤列表")
async def get_recent_errors(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="錯誤類別篩選"),
    level: Optional[str] = Query(None, description="錯誤級別篩選")
):
    """
    獲取最近的錯誤記錄，支持篩選
    """
    log_info(f"Recent errors requested: limit={limit}, category={category}, level={level}", 
             ErrorCategory.SYSTEM)
    
    recent_errors = log_manager.error_stats["recent_errors"]
    
    # 應用篩選
    filtered_errors = recent_errors
    if category:
        filtered_errors = [e for e in filtered_errors if e.get("category") == category]
    if level:
        filtered_errors = [e for e in filtered_errors if e.get("level") == level]
    
    # 限制數量
    filtered_errors = filtered_errors[-limit:]
    
    return {
        "errors": filtered_errors,
        "total": len(filtered_errors),
        "filters": {
            "category": category,
            "level": level,
            "limit": limit
        }
    }


@router.post("/clear-error-stats", summary="清除錯誤統計")
async def clear_error_stats():
    """
    清除錯誤統計數據（僅統計，不刪除日誌文件）
    """
    log_info("Error stats clear requested", ErrorCategory.SYSTEM)
    
    log_manager.error_stats = {
        "total_errors": 0,
        "by_category": {cat.value: 0 for cat in ErrorCategory},
        "by_level": {level.value: 0 for level in LogLevel},
        "recent_errors": []
    }
    
    return {"message": "Error statistics cleared", "timestamp": datetime.now().isoformat()}


@router.get("/log-files", summary="日誌文件狀態")
async def get_log_files_status():
    """
    獲取日誌文件的狀態信息
    """
    import os
    log_info("Log files status requested", ErrorCategory.SYSTEM)
    
    log_files = {
        "system.log": "logs/system.log",
        "errors.log": "logs/errors.log", 
        "api.log": "logs/api.log",
        "database.log": "logs/database.log"
    }
    
    file_stats = {}
    for name, path in log_files.items():
        try:
            if os.path.exists(path):
                stat = os.stat(path)
                file_stats[name] = {
                    "exists": True,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": path
                }
            else:
                file_stats[name] = {
                    "exists": False,
                    "path": path
                }
        except Exception as e:
            file_stats[name] = {
                "error": str(e),
                "path": path
            }
    
    return file_stats


@router.post("/test-logging", summary="測試日誌記錄")
async def test_logging(
    level: str = "INFO",
    category: str = "SYSTEM", 
    message: str = "Test log message"
):
    """
    測試日誌記錄功能
    """
    from app.core.logging_manager import LogEntry
    
    try:
        log_level = LogLevel(level.upper())
        log_category = ErrorCategory(category.upper())
        
        entry = LogEntry(
            level=log_level,
            category=log_category,
            message=message,
            details={"test": True, "timestamp": datetime.now().isoformat()}
        )
        
        log_manager.log(entry)
        
        return {
            "message": "Test log recorded successfully",
            "entry": entry.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid level or category: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logging test failed: {e}")


@router.get("/error-logs", summary="取得錯誤日誌")
async def get_error_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    取得錯誤日誌記錄
    """
    log_info("Error logs requested", ErrorCategory.SYSTEM)
    
    # 簡化版本以測試端點
    return {
        "logs": [
            {
                "timestamp": "2025-09-12T11:44:00.000Z",
                "level": "ERROR",
                "message": "Test error log entry",
                "source": "logs/errors.log"
            }
        ],
        "total": 1,
        "limit": limit,
        "offset": offset
    }


@router.get("/system-metrics", summary="系統性能指標")
async def get_system_metrics():
    """
    獲取系統性能指標
    """
    log_info("System metrics requested", ErrorCategory.SYSTEM)
    
    try:
        import psutil
        import gc
        
        # CPU和記憶體使用情況（優化版本 - 移除阻塞性的CPU檢測）
        cpu_percent = psutil.cpu_percent(interval=0)  # 非阻塞版本，使用上次的數據
        memory = psutil.virtual_memory()
        
        # Python記憶體使用情況
        gc.collect()  # 強制垃圾回收
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": round(memory.total / 1024**3, 2),
                "available_gb": round(memory.available / 1024**3, 2),
                "percent_used": memory.percent
            },
            "python": {
                "garbage_collected": gc.collect(),
                "object_count": len(gc.get_objects())
            }
        }
        
        # 磁碟使用情況（如果可用）
        try:
            disk = psutil.disk_usage('/')
            metrics["disk"] = {
                "total_gb": round(disk.total / 1024**3, 2),
                "used_gb": round(disk.used / 1024**3, 2),
                "free_gb": round(disk.free / 1024**3, 2),
                "percent_used": round((disk.used / disk.total) * 100, 2)
            }
        except Exception:
            metrics["disk"] = {"status": "unavailable"}
        
        return metrics
        
    except ImportError:
        return {
            "error": "psutil not available",
            "message": "Install psutil for detailed system metrics"
        }
    except Exception as e:
        log_error(f"Failed to get system metrics: {str(e)}", ErrorCategory.SYSTEM)
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")