"""
API 健康監控端點
v2.1 - 安全強化: ORM 查詢替換 + readiness auth (2026-02-06)
"""
import time
import logging
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from datetime import datetime

from app.db.database import get_async_db, engine

logger = logging.getLogger(__name__)
from app.extended.models import OfficialDocument, GovernmentAgency, PartnerVendor, ContractProject, User
from app.core.dependencies import require_auth, require_admin

# 應用啟動時間
_startup_time: datetime = None


def set_startup_time():
    """設定應用啟動時間（在 main.py 啟動時呼叫）"""
    global _startup_time
    _startup_time = datetime.now()


def get_uptime() -> str:
    """取得應用運行時間"""
    if _startup_time is None:
        return "unknown"
    delta = datetime.now() - _startup_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

router = APIRouter()

@router.get("/health", summary="基本健康檢查")
async def basic_health_check():
    """基本健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API"
    }

@router.get("/health/detailed", summary="詳細健康檢查")
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
) -> Dict[str, Any]:
    """詳細系統健康檢查"""
    start_time = time.time()
    health_data = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "version": "3.0.0",
        "status": "healthy",
        "checks": {}
    }

    # 1. 資料庫連線檢查
    try:
        db_start = time.time()
        # 安全修正 (v2.1): 使用 ORM 取代 raw SQL
        result = await db.execute(select(func.now()))
        db_response_time = (time.time() - db_start) * 1000

        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
        health_data["status"] = "unhealthy"

    # 2. 核心資料表檢查
    tables_check = {}
    tables = [
        ("documents", OfficialDocument),
        ("agencies", GovernmentAgency),
        ("vendors", PartnerVendor),
        ("projects", ContractProject)
    ]

    for table_name, model in tables:
        try:
            table_start = time.time()
            # 安全性修正 (v2.0.0): 使用 ORM select() 取代動態 SQL
            result = await db.execute(select(func.count()).select_from(model))
            count = result.scalar()
            table_response_time = (time.time() - table_start) * 1000

            tables_check[table_name] = {
                "status": "healthy",
                "record_count": count,
                "response_time_ms": round(table_response_time, 2)
            }
        except Exception as e:
            tables_check[table_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "unhealthy"

    health_data["checks"]["tables"] = tables_check

    # 3. 連線池狀態
    try:
        pool_info = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin()
        }
        health_data["checks"]["connection_pool"] = {
            "status": "healthy",
            "pool_info": pool_info,
            "utilization_percent": round((pool_info["checked_out"] / pool_info["size"]) * 100, 2)
        }
    except Exception as e:
        health_data["checks"]["connection_pool"] = {
            "status": "unknown",
            "error": str(e)
        }

    # 4. 系統資源檢查
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_data["checks"]["system_resources"] = {
            "status": "healthy",
            "memory": {
                "used_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            },
            "disk": {
                "used_percent": disk.percent,
                "free_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2)
            }
        }

        # 警告閾值檢查
        if memory.percent > 90 or disk.percent > 90:
            health_data["checks"]["system_resources"]["status"] = "warning"
            health_data["checks"]["system_resources"]["warnings"] = []

            if memory.percent > 90:
                health_data["checks"]["system_resources"]["warnings"].append("High memory usage")
            if disk.percent > 90:
                health_data["checks"]["system_resources"]["warnings"].append("High disk usage")

    except Exception as e:
        health_data["checks"]["system_resources"] = {
            "status": "unknown",
            "error": str(e)
        }

    # 5. API 回應時間
    total_response_time = (time.time() - start_time) * 1000
    health_data["total_response_time_ms"] = round(total_response_time, 2)

    # 6. 整體狀態評估
    if total_response_time > 5000:  # 5秒
        health_data["status"] = "slow"
        health_data["message"] = "API response time is slower than expected"
    elif health_data["status"] == "healthy":
        health_data["message"] = "All systems operational"

    return health_data

@router.get("/health/metrics", summary="效能指標")
async def get_performance_metrics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """獲取系統效能指標"""
    try:
        # 資料庫查詢效能測試
        metrics = {}

        # 安全修正 (v2.1): 使用 ORM 查詢取代 raw SQL
        from sqlalchemy import extract
        from datetime import date, timedelta

        orm_queries = {
            "simple_count": lambda: db.execute(
                select(func.count()).select_from(OfficialDocument)
            ),
            "complex_join": lambda: db.execute(
                select(func.count(OfficialDocument.id))
                .outerjoin(GovernmentAgency, OfficialDocument.sender_agency_id == GovernmentAgency.id)
                .where(OfficialDocument.doc_date > date.today() - timedelta(days=365))
            ),
            "aggregation": lambda: db.execute(
                select(
                    extract('year', OfficialDocument.doc_date).label('year'),
                    func.count()
                )
                .where(OfficialDocument.doc_date.isnot(None))
                .group_by(extract('year', OfficialDocument.doc_date))
            ),
        }

        for query_name, query_fn in orm_queries.items():
            start_time = time.time()
            try:
                result = await query_fn()
                result.fetchall()  # 確保完全執行
                execution_time = (time.time() - start_time) * 1000

                metrics[query_name] = {
                    "execution_time_ms": round(execution_time, 2),
                    "status": "success"
                }
            except Exception as e:
                metrics[query_name] = {
                    "execution_time_ms": None,
                    "status": "error",
                    "error": str(e)
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "database_metrics": metrics,
            "recommendations": _get_performance_recommendations(metrics)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法獲取效能指標: {str(e)}")

def _get_performance_recommendations(metrics: Dict[str, Any]) -> list:
    """根據效能指標提供優化建議"""
    recommendations = []

    for query_name, metric in metrics.items():
        if metric.get("execution_time_ms"):
            execution_time = metric["execution_time_ms"]

            if execution_time > 1000:  # 1秒
                recommendations.append(f"{query_name} 查詢耗時過長 ({execution_time:.2f}ms)，建議新增索引優化")
            elif execution_time > 500:  # 500ms
                recommendations.append(f"{query_name} 查詢可進一步優化 ({execution_time:.2f}ms)")

    if not recommendations:
        recommendations.append("所有查詢效能良好，無需優化")

    return recommendations

@router.get("/health/readiness", summary="就緒狀態檢查")
async def readiness_check(db: AsyncSession = Depends(get_async_db)):
    """檢查服務是否已準備好接受流量"""
    try:
        # 安全修正 (v2.1): 使用 ORM 取代 raw SQL
        await db.execute(select(func.now()))
        await db.execute(select(func.count()).select_from(OfficialDocument))

        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept traffic"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        # 安全修正: 不洩漏內部錯誤細節
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "message": "Service is not ready to accept traffic"
            }
        )

@router.get("/health/liveness", summary="存活狀態檢查")
async def liveness_check():
    """檢查服務是否存活"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "message": "Service is alive"
    }


@router.get("/health/pool", summary="連接池狀態")
async def connection_pool_status(
    current_user: User = Depends(require_admin())
):
    """
    取得資料庫連接池詳細狀態

    包含：
    - 連接池監控指標
    - 健康狀態評估
    - 最近連接事件
    """
    try:
        from app.core.db_monitor import DatabaseMonitor
        health = DatabaseMonitor.get_health_status()
        events = DatabaseMonitor.get_recent_events(limit=20)

        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "recent_events": events
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "monitor_not_available",
            "error": str(e),
            "message": "連接池監控未啟用或發生錯誤"
        }


@router.get("/health/tasks", summary="背景任務狀態")
async def background_tasks_status(
    current_user: User = Depends(require_admin())
):
    """
    取得背景任務執行統計

    包含：
    - 任務總數
    - 成功/失敗數
    - 最後執行時間
    """
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
            "success_rate": round(success_rate * 100, 2)
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "error": str(e)
        }


@router.get("/health/audit", summary="審計服務狀態")
async def audit_service_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """
    檢查審計服務運行狀態

    包含：
    - 審計日誌表狀態
    - 最近審計記錄統計
    """
    try:
        # 檢查審計日誌表
        count_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        total_logs = count_result.scalar() or 0

        # 最近 24 小時審計記錄
        recent_result = await db.execute(text("""
            SELECT COUNT(*) FROM audit_logs
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """))
        recent_logs = recent_result.scalar() or 0

        # 各操作類型統計
        action_result = await db.execute(text("""
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY action
        """))
        action_stats = {row.action: row.count for row in action_result}

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "total_logs": total_logs,
            "last_24h": {
                "total": recent_logs,
                "by_action": action_stats
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }


@router.get("/health/summary", summary="系統健康摘要")
async def health_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """
    整合所有健康檢查的摘要報告

    適用於 Dashboard 監控面板
    """
    summary = {
        "timestamp": datetime.now().isoformat(),
        "uptime": get_uptime(),
        "overall_status": "healthy",
        "components": {}
    }

    issues = []

    # 1. 資料庫
    try:
        start = time.time()
        # 安全修正 (v2.1): 使用 ORM 取代 raw SQL
        await db.execute(select(func.now()))
        db_time = (time.time() - start) * 1000
        summary["components"]["database"] = {
            "status": "healthy",
            "response_ms": round(db_time, 2)
        }
    except Exception as e:
        summary["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        issues.append("database")

    # 2. 連接池
    try:
        from app.core.db_monitor import DatabaseMonitor
        pool_health = DatabaseMonitor.get_health_status()
        summary["components"]["connection_pool"] = {
            "status": pool_health["status"],
            "active": pool_health["stats"].get("active_connections", 0)
        }
        if pool_health["status"] != "healthy":
            issues.append("connection_pool")
    except Exception as e:
        logger.debug(f"連接池健康檢查失敗: {e}")
        summary["components"]["connection_pool"] = {"status": "unknown"}

    # 3. 背景任務
    try:
        from app.core.background_tasks import BackgroundTaskManager
        task_stats = BackgroundTaskManager.get_stats()
        summary["components"]["background_tasks"] = {
            "status": "healthy",
            "total": task_stats["total_tasks"],
            "failed": task_stats["failed_tasks"]
        }
    except Exception as e:
        logger.debug(f"背景任務健康檢查失敗: {e}")
        summary["components"]["background_tasks"] = {"status": "unknown"}

    # 4. 系統資源
    try:
        memory = psutil.virtual_memory()
        summary["components"]["system"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "memory_percent": memory.percent,
            "cpu_percent": psutil.cpu_percent()
        }
        if memory.percent > 90:
            issues.append("memory")
    except Exception as e:
        logger.debug(f"系統資源健康檢查失敗: {e}")
        summary["components"]["system"] = {"status": "unknown"}

    # 整體狀態
    if issues:
        summary["overall_status"] = "degraded" if len(issues) < 2 else "unhealthy"
        summary["issues"] = issues

    return summary