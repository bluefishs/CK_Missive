"""
系統健康檢查服務

從 health.py 端點提取的業務邏輯。
端點僅負責 HTTP 處理，所有檢查邏輯在此服務中。

v1.0.0 - 2026-02-24
"""
import time
import logging
import psutil
from typing import Dict, Any, List, Tuple
from datetime import datetime, date, timedelta

from sqlalchemy import select, func, text, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument, GovernmentAgency, PartnerVendor, ContractProject,
)
from app.db.database import engine

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
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed",
            }

    async def check_core_tables(self) -> Dict[str, Any]:
        """檢查核心資料表"""
        result = {}
        for table_name, model in self.CORE_TABLES:
            try:
                start = time.time()
                count_result = await self.db.execute(
                    select(func.count()).select_from(model)
                )
                count = count_result.scalar()
                response_ms = (time.time() - start) * 1000
                result[table_name] = {
                    "status": "healthy",
                    "record_count": count,
                    "response_time_ms": round(response_ms, 2),
                }
            except Exception as e:
                result[table_name] = {"status": "unhealthy", "error": str(e)}
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
            return {"status": "unknown", "error": str(e)}

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
            return {"status": "unknown", "error": str(e)}

    # ------------------------------------------------------------------
    # 效能基準
    # ------------------------------------------------------------------

    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """執行資料庫查詢效能基準測試"""
        orm_queries = {
            "simple_count": lambda: self.db.execute(
                select(func.count()).select_from(OfficialDocument)
            ),
            "complex_join": lambda: self.db.execute(
                select(func.count(OfficialDocument.id))
                .outerjoin(
                    GovernmentAgency,
                    OfficialDocument.sender_agency_id == GovernmentAgency.id,
                )
                .where(
                    OfficialDocument.doc_date > date.today() - timedelta(days=365)
                )
            ),
            "aggregation": lambda: self.db.execute(
                select(
                    extract("year", OfficialDocument.doc_date).label("year"),
                    func.count(),
                )
                .where(OfficialDocument.doc_date.isnot(None))
                .group_by(extract("year", OfficialDocument.doc_date))
            ),
        }

        metrics: Dict[str, Any] = {}
        for query_name, query_fn in orm_queries.items():
            start = time.time()
            try:
                result = await query_fn()
                result.fetchall()
                execution_ms = (time.time() - start) * 1000
                metrics[query_name] = {
                    "execution_time_ms": round(execution_ms, 2),
                    "status": "success",
                }
            except Exception as e:
                metrics[query_name] = {
                    "execution_time_ms": None,
                    "status": "error",
                    "error": str(e),
                }
        return metrics

    @staticmethod
    def get_performance_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """根據效能指標提供優化建議"""
        recommendations = []
        for query_name, metric in metrics.items():
            exec_time = metric.get("execution_time_ms")
            if exec_time and exec_time > 1000:
                recommendations.append(
                    f"{query_name} 查詢耗時過長 ({exec_time:.2f}ms)，建議新增索引優化"
                )
            elif exec_time and exec_time > 500:
                recommendations.append(
                    f"{query_name} 查詢可進一步優化 ({exec_time:.2f}ms)"
                )
        if not recommendations:
            recommendations.append("所有查詢效能良好，無需優化")
        return recommendations

    # ------------------------------------------------------------------
    # 審計服務檢查（使用 text() — audit_logs 無 ORM 模型）
    # ------------------------------------------------------------------

    async def check_audit_service(self) -> Dict[str, Any]:
        """檢查審計服務狀態"""
        try:
            count_result = await self.db.execute(
                text("SELECT COUNT(*) FROM audit_logs")
            )
            total_logs = count_result.scalar() or 0

            recent_result = await self.db.execute(text(
                "SELECT COUNT(*) FROM audit_logs "
                "WHERE created_at > NOW() - INTERVAL '24 hours'"
            ))
            recent_logs = recent_result.scalar() or 0

            action_result = await self.db.execute(text(
                "SELECT action, COUNT(*) as count FROM audit_logs "
                "WHERE created_at > NOW() - INTERVAL '24 hours' "
                "GROUP BY action"
            ))
            action_stats = {row.action: row.count for row in action_result}

            return {
                "status": "healthy",
                "total_logs": total_logs,
                "last_24h": {"total": recent_logs, "by_action": action_stats},
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # 備份狀態檢查
    # ------------------------------------------------------------------

    @staticmethod
    def check_backup_status() -> Dict[str, Any]:
        """檢查備份系統狀態（排程器 + 最近備份 + 異地同步）"""
        try:
            from app.services.backup_scheduler import get_backup_scheduler_status

            scheduler = get_backup_scheduler_status()
            status = "healthy"
            warnings: List[str] = []

            # 檢查排程器運行狀態
            if not scheduler.get("running"):
                warnings.append("備份排程器未運行")
                status = "warning"

            # 檢查連續失敗次數
            consecutive_failures = scheduler.get("consecutive_failures", 0)
            if consecutive_failures >= 3:
                status = "unhealthy"
                warnings.append(f"備份連續失敗 {consecutive_failures} 次")
            elif consecutive_failures >= 1:
                status = "warning"
                warnings.append(f"最近備份失敗 {consecutive_failures} 次")

            # 檢查最後備份時間（超過 48 小時視為異常）
            stats = scheduler.get("stats", {})
            last_result = stats.get("last_backup_result")
            last_backup_time = scheduler.get("last_backup")
            if last_backup_time:
                try:
                    last_dt = datetime.fromisoformat(last_backup_time)
                    hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
                    if hours_ago > 48:
                        warnings.append(f"距上次備份已超過 {hours_ago:.0f} 小時")
                        if status == "healthy":
                            status = "warning"
                except (ValueError, TypeError):
                    pass

            # 異地同步狀態
            remote_sync = scheduler.get("remote_sync", {})

            result: Dict[str, Any] = {
                "status": status,
                "scheduler_running": scheduler.get("running", False),
                "next_backup": scheduler.get("next_backup"),
                "last_backup": last_backup_time,
                "consecutive_failures": consecutive_failures,
                "total_backups": stats.get("total_backups", 0),
                "successful_backups": stats.get("successful_backups", 0),
                "remote_sync": remote_sync,
            }
            if warnings:
                result["warnings"] = warnings

            return result

        except Exception as e:
            return {"status": "unknown", "error": str(e)}

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

        # 5. 備份狀態
        backup_check = self.check_backup_status()
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
