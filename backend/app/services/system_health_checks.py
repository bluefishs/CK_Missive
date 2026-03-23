"""
系統健康檢查 — 詳細檢查方法

從 system_health_service.py 提取的效能基準、資料品質、
審計服務、備份狀態等檢查方法。

v1.0.0 - 2026-03-23
"""
import time
import logging
from typing import Dict, Any, List
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, text, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument,
    GovernmentAgency,
)

logger = logging.getLogger(__name__)


class SystemHealthChecks:
    """詳細健康檢查方法集合"""

    def __init__(self, db: AsyncSession):
        self.db = db

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
                logger.error(f"Performance benchmark {query_name} failed: {e}")
                metrics[query_name] = {
                    "execution_time_ms": None,
                    "status": "error",
                    "error": "Benchmark query failed",
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
    # 資料品質檢查
    # ------------------------------------------------------------------

    async def check_data_quality(self) -> Dict[str, Any]:
        """檢查資料標準化品質指標"""
        try:
            result = await self.db.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(normalized_sender) as norm_sender,
                    COUNT(normalized_receiver) as norm_receiver,
                    COUNT(sender_agency_id) as sender_fk,
                    COUNT(receiver_agency_id) as receiver_fk
                FROM documents
            """))
            row = result.one()
            total = row.total or 1

            ner_result = await self.db.execute(text("""
                SELECT
                    COUNT(*) as total_docs,
                    (SELECT COUNT(DISTINCT document_id) FROM document_entity_mentions) as ner_docs
                FROM documents
            """))
            ner_row = ner_result.one()

            sender_pct = round(row.sender_fk * 100.0 / total, 1)
            receiver_pct = round(row.receiver_fk * 100.0 / total, 1)
            ner_pct = round((ner_row.ner_docs or 0) * 100.0 / total, 1)

            status = "healthy"
            if sender_pct < 90 or receiver_pct < 90:
                status = "warning"
            if sender_pct < 70 or receiver_pct < 70:
                status = "unhealthy"

            return {
                "status": status,
                "total_documents": total,
                "normalization": {
                    "sender": row.norm_sender,
                    "receiver": row.norm_receiver,
                },
                "agency_fk": {
                    "sender_pct": sender_pct,
                    "receiver_pct": receiver_pct,
                },
                "ner_coverage_pct": ner_pct,
            }
        except Exception as e:
            logger.error(f"Data quality check failed: {e}")
            return {"status": "error", "error": "Data quality check failed"}

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
            logger.error(f"Audit service check failed: {e}")
            return {"status": "error", "error": "Audit service check failed"}

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
            logger.error(f"Backup status check failed: {e}")
            return {"status": "unknown", "error": "Backup status check failed"}
