"""
系統健康檢查服務

從 health.py 端點提取的業務邏輯。
端點僅負責 HTTP 處理，所有檢查邏輯在此服務中。

v1.1.0 - 2026-03-23  詳細檢查方法提取至 system_health_checks.py
v1.0.0 - 2026-02-24
"""
import time
import logging
import psutil
from typing import Dict, Any, List, Tuple
from datetime import datetime

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument, GovernmentAgency, PartnerVendor, ContractProject,
)
from app.db.database import engine
from app.services.system_health_checks import SystemHealthChecks

logger = logging.getLogger(__name__)


class SystemHealthService:
    """系統健康檢查服務"""

    # 應用啟動時間（class variable，所有實例共享）
    _startup_time: datetime = None

    CORE_TABLES: List[Tuple[str, type]] = [
        ("documents", OfficialDocument),
        ("agencies", GovernmentAgency),
        ("vendors", PartnerVendor),
        ("projects", ContractProject),
    ]

    def __init__(self, db: AsyncSession):
        self.db = db
        self._checks = SystemHealthChecks(db)

    @classmethod
    def set_startup_time(cls):
        """設定應用啟動時間（在 main.py 啟動時呼叫）"""
        cls._startup_time = datetime.now()

    @classmethod
    def get_uptime(cls) -> str:
        """取得應用運行時間"""
        if cls._startup_time is None:
            return "unknown"
        delta = datetime.now() - cls._startup_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    # ------------------------------------------------------------------
    # 資料庫檢查
    # ------------------------------------------------------------------

    async def check_database(self) -> Dict[str, Any]:
        """檢查資料庫連線"""
        try:
            start = time.time()
            await self.db.execute(select(func.now()))
            response_ms = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "response_time_ms": round(response_ms, 2),
                "message": "Database connection successful",
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": "Database connection failed",
                "message": "Database connection failed",
            }

    async def check_core_tables(self) -> Dict[str, Any]:
        """檢查核心資料表（使用 pg_class 預估值，避免全表掃描）"""
        result = {}
        for display_name, model in self.CORE_TABLES:
            try:
                real_table = model.__tablename__
                start = time.time()
                count_result = await self.db.execute(
                    text(
                        "SELECT reltuples::bigint FROM pg_class WHERE relname = :tbl"
                    ),
                    {"tbl": real_table},
                )
                count = count_result.scalar() or 0
                response_ms = (time.time() - start) * 1000
                result[display_name] = {
                    "status": "healthy",
                    "record_count": max(count, 0),
                    "response_time_ms": round(response_ms, 2),
                    "count_method": "pg_class_estimate",
                }
            except Exception as e:
                logger.error(f"Core table check failed for {display_name}: {e}")
                result[display_name] = {"status": "unhealthy", "error": "Table check failed"}
        return result

    # ------------------------------------------------------------------
    # 連線池檢查
    # ------------------------------------------------------------------

    @staticmethod
    def check_connection_pool() -> Dict[str, Any]:
        """檢查連線池狀態"""
        try:
            pool_info = {
                "size": engine.pool.size(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "checked_in": engine.pool.checkedin(),
            }
            utilization = (
                round((pool_info["checked_out"] / pool_info["size"]) * 100, 2)
                if pool_info["size"] > 0
                else 0
            )
            return {
                "status": "healthy",
                "pool_info": pool_info,
                "utilization_percent": utilization,
            }
        except Exception as e:
            logger.error(f"Connection pool check failed: {e}")
            return {"status": "unknown", "error": "Connection pool check failed"}

    # ------------------------------------------------------------------
    # 系統資源檢查
    # ------------------------------------------------------------------

    @staticmethod
    def check_system_resources() -> Dict[str, Any]:
        """檢查系統資源（記憶體、磁碟）"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            result: Dict[str, Any] = {
                "status": "healthy",
                "memory": {
                    "used_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                "disk": {
                    "used_percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
            }

            warnings = []
            if memory.percent > 90:
                warnings.append("High memory usage")
            if disk.percent > 90:
                warnings.append("High disk usage")
            if warnings:
                result["status"] = "warning"
                result["warnings"] = warnings

            return result
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return {"status": "unknown", "error": "System resources check failed"}

    # ------------------------------------------------------------------
    # 委派至 SystemHealthChecks（向後相容）
    # ------------------------------------------------------------------

    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """委派至 SystemHealthChecks.run_performance_benchmarks()"""
        return await self._checks.run_performance_benchmarks()

    @staticmethod
    def get_performance_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """委派至 SystemHealthChecks.get_performance_recommendations()"""
        return SystemHealthChecks.get_performance_recommendations(metrics)

    async def check_data_quality(self) -> Dict[str, Any]:
        """委派至 SystemHealthChecks.check_data_quality()"""
        return await self._checks.check_data_quality()

    async def check_audit_service(self) -> Dict[str, Any]:
        """委派至 SystemHealthChecks.check_audit_service()"""
        return await self._checks.check_audit_service()

    @staticmethod
    def check_backup_status() -> Dict[str, Any]:
        """委派至 SystemHealthChecks.check_backup_status()"""
        return SystemHealthChecks.check_backup_status()

    # ------------------------------------------------------------------
    # 就緒檢查
    # ------------------------------------------------------------------

    async def check_readiness(self) -> bool:
        """檢查服務是否就緒"""
        await self.db.execute(select(func.now()))
        await self.db.execute(select(func.count()).select_from(OfficialDocument))
        return True

    # ------------------------------------------------------------------
    # 聚合摘要
    # ------------------------------------------------------------------

    async def build_summary(self) -> Dict[str, Any]:
        """建立系統健康摘要"""
        summary: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "uptime": get_uptime(),
            "overall_status": "healthy",
            "components": {},
        }
        issues: List[str] = []

        # 1. 資料庫
        db_check = await self.check_database()
        summary["components"]["database"] = {
            "status": db_check["status"],
            "response_ms": db_check.get("response_time_ms"),
        }
        if db_check["status"] != "healthy":
            issues.append("database")

        # 2. 連接池
        try:
            from app.core.db_monitor import DatabaseMonitor

            pool_health = DatabaseMonitor.get_health_status()
            summary["components"]["connection_pool"] = {
                "status": pool_health["status"],
                "active": pool_health["stats"].get("active_connections", 0),
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
                "failed": task_stats["failed_tasks"],
            }
        except Exception as e:
            logger.debug(f"背景任務健康檢查失敗: {e}")
            summary["components"]["background_tasks"] = {"status": "unknown"}

        # 4. 系統資源
        res = self.check_system_resources()
        summary["components"]["system"] = {
            "status": res["status"],
            "memory_percent": res.get("memory", {}).get("used_percent"),
            "cpu_percent": psutil.cpu_percent() if res["status"] != "unknown" else None,
        }
        if res["status"] == "warning":
            issues.append("memory")

        # 5. 資料品質
        try:
            dq_check = await self._checks.check_data_quality()
            summary["components"]["data_quality"] = dq_check
            if dq_check["status"] == "warning":
                issues.append("data_quality_warning")
            elif dq_check["status"] == "unhealthy":
                issues.append("data_quality")
        except Exception as e:
            logger.debug(f"資料品質檢查失敗: {e}")
            summary["components"]["data_quality"] = {"status": "unknown"}

        # 6. 備份狀態
        backup_check = self._checks.check_backup_status()
        summary["components"]["backup"] = {
            "status": backup_check["status"],
            "scheduler_running": backup_check.get("scheduler_running"),
            "last_backup": backup_check.get("last_backup"),
            "consecutive_failures": backup_check.get("consecutive_failures", 0),
        }
        if backup_check["status"] == "unhealthy":
            issues.append("backup")
        elif backup_check["status"] == "warning":
            issues.append("backup_warning")

        # 整體狀態
        if issues:
            summary["overall_status"] = (
                "degraded" if len(issues) < 2 else "unhealthy"
            )
            summary["issues"] = issues

        return summary


# ---------------------------------------------------------------------------
# 向後相容的模組級函數（health.py 等透過 from ... import set_startup_time 引用）
# ---------------------------------------------------------------------------

def set_startup_time():
    """向後相容：委託至 SystemHealthService.set_startup_time()"""
    SystemHealthService.set_startup_time()


def get_uptime() -> str:
    """向後相容：委託至 SystemHealthService.get_uptime()"""
    return SystemHealthService.get_uptime()
