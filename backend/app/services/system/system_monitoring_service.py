"""SystemMonitoringService — 系統監控/錯誤日誌業務邏輯（DDD 標準化，2026-07-20）

標準化收斂：原 endpoints/system_monitoring.py 端點內直接 psutil / log_manager /
inline SQL，繞過 service 層。抽出本 service 封裝日誌檔狀態、系統指標、覆盤儀表板
彙總邏輯，端點薄委派。行為保真（唯 review-dashboard code_graph 修正 entity_type
'code_module'→'py_module'＝原查詢恆 0 的潛在 bug 順修）。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_manager import (
    ErrorCategory, LogLevel, log_error, log_manager,
)

logger = logging.getLogger(__name__)

_LOG_FILES = {
    "system.log": "logs/system.log",
    "errors.log": "logs/errors.log",
    "api.log": "logs/api.log",
    "database.log": "logs/database.log",
}


class SystemMonitoringService:
    # ── 錯誤統計（log_manager 記憶體單例）─────────────────────────
    @staticmethod
    def error_summary() -> Dict[str, Any]:
        return log_manager.get_error_summary()

    @staticmethod
    def recent_errors(
        limit: int, category: Optional[str], level: Optional[str],
    ) -> Dict[str, Any]:
        errors = log_manager.error_stats["recent_errors"]
        if category:
            errors = [e for e in errors if e.get("category") == category]
        if level:
            errors = [e for e in errors if e.get("level") == level]
        errors = errors[-limit:]
        return {
            "errors": errors,
            "total": len(errors),
            "filters": {"category": category, "level": level, "limit": limit},
        }

    @staticmethod
    def clear_error_stats() -> Dict[str, Any]:
        log_manager.error_stats = {
            "total_errors": 0,
            "by_category": {cat.value: 0 for cat in ErrorCategory},
            "by_level": {lvl.value: 0 for lvl in LogLevel},
            "recent_errors": [],
        }
        return {"message": "Error statistics cleared", "timestamp": datetime.now().isoformat()}

    @staticmethod
    def log_files_status() -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for name, path in _LOG_FILES.items():
            try:
                if os.path.exists(path):
                    st = os.stat(path)
                    stats[name] = {
                        "exists": True,
                        "size_bytes": st.st_size,
                        "size_mb": round(st.st_size / 1024 / 1024, 2),
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "path": path,
                    }
                else:
                    stats[name] = {"exists": False, "path": path}
            except Exception as e:
                logger.error(f"無法獲取日誌檔案狀態 {name}: {e}", exc_info=True)
                stats[name] = {"error": "無法存取檔案", "path": path}
        return stats

    @staticmethod
    def record_test_log(level: str, category: str, message: str) -> Dict[str, Any]:
        """回傳 {message, entry}；level/category 無效時拋 ValueError（端點轉 400）。"""
        from app.core.logging_manager import LogEntry
        entry = LogEntry(
            level=LogLevel(level.upper()),
            category=ErrorCategory(category.upper()),
            message=message,
            details={"test": True, "timestamp": datetime.now().isoformat()},
        )
        log_manager.log(entry)
        return {"message": "Test log recorded successfully", "entry": entry.to_dict()}

    @staticmethod
    def system_metrics() -> Dict[str, Any]:
        import gc
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0)  # 非阻塞
        memory = psutil.virtual_memory()
        gc.collect()

        metrics: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
            "memory": {
                "total_gb": round(memory.total / 1024**3, 2),
                "available_gb": round(memory.available / 1024**3, 2),
                "percent_used": memory.percent,
            },
            "python": {
                "garbage_collected": gc.collect(),
                "object_count": len(gc.get_objects()),
            },
        }
        try:
            disk = psutil.disk_usage("/")
            metrics["disk"] = {
                "total_gb": round(disk.total / 1024**3, 2),
                "used_gb": round(disk.used / 1024**3, 2),
                "free_gb": round(disk.free / 1024**3, 2),
                "percent_used": round((disk.used / disk.total) * 100, 2),
            }
        except Exception:
            metrics["disk"] = {"status": "unavailable"}
        return metrics

    # ── 覆盤儀表板彙總 ─────────────────────────────────────────────
    async def review_dashboard(self, db: AsyncSession) -> Dict[str, Any]:
        from sqlalchemy import text
        from app.core.scheduler import get_scheduler_status

        result: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "subsystems": {},
            "scheduler": get_scheduler_status(),
        }
        subs = result["subsystems"]

        # Knowledge Graph
        try:
            entities = (await db.execute(text("SELECT count(*) FROM canonical_entities"))).scalar() or 0
            relations = (await db.execute(text("SELECT count(*) FROM entity_relationships"))).scalar() or 0
            aliases = (await db.execute(text("SELECT count(*) FROM entity_aliases"))).scalar() or 0
            pending = (await db.execute(text("SELECT count(*) FROM documents WHERE ner_pending = true"))).scalar() or 0
            subs["knowledge_graph"] = {
                "status": "healthy" if pending == 0 else "pending",
                "entities": entities, "relationships": relations, "aliases": aliases,
                "pending_documents": pending,
                "coverage": "100%" if pending == 0 else f"{round((1 - pending / max(entities, 1)) * 100)}%",
            }
        except Exception as e:
            await db.rollback()
            subs["knowledge_graph"] = {"status": "error", "error": str(e)}

        # Code Graph（修正：entity_type 'code_module'→'py_module'，原查詢恆 0）
        try:
            code_modules = (await db.execute(text(
                "SELECT count(*) FROM canonical_entities WHERE entity_type = 'py_module'"
            ))).scalar() or 0
            code_relations = (await db.execute(text(
                "SELECT count(*) FROM entity_relationships "
                "WHERE relation_type IN ('imports', 'calls', 'inherits', 'depends_on')"
            ))).scalar() or 0
            subs["code_graph"] = {
                "status": "healthy" if code_modules > 0 else "empty",
                "modules": code_modules, "dependencies": code_relations,
            }
        except Exception as e:
            await db.rollback()
            subs["code_graph"] = {"status": "error", "error": str(e)}

        # DB Graph
        try:
            from app.services.ai.graph.schema_reflector import SchemaReflectorService
            schema = await SchemaReflectorService.get_full_schema_async()
            subs["db_graph"] = {
                "status": "healthy",
                "tables": len(schema.get("tables", [])),
                "cached": SchemaReflectorService._cache is not None,
            }
        except Exception as e:
            await db.rollback()
            subs["db_graph"] = {"status": "error", "error": str(e)}

        # Knowledge Base (Embedding)
        try:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            stats = await EmbeddingManager.get_coverage_stats(db)
            total = stats.get("total_chunks", 0)
            embedded = stats.get("embedded_chunks", 0)
            coverage = stats.get("coverage_percent", 0)
            subs["knowledge_base"] = {
                "status": "healthy" if coverage >= 95 else "degraded",
                "chunks": total, "embedded": embedded, "coverage": f"{coverage:.1f}%",
            }
        except Exception as e:
            await db.rollback()
            subs["knowledge_base"] = {"status": "error", "error": str(e)}

        # Skill Evolution
        try:
            from app.services.ai.agent.agent_evolution_scheduler import AgentEvolutionScheduler
            should = await AgentEvolutionScheduler().should_evolve()
            subs["skill_evolution"] = {"status": "active", "should_evolve": should}
        except Exception as e:
            subs["skill_evolution"] = {"status": "error", "error": str(e)}

        return result
