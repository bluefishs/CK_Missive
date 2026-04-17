# -*- coding: utf-8 -*-
"""
DB Query Event Listener — SQLAlchemy → Prometheus

掛接 SQLAlchemy before/after_cursor_execute 事件，
自動追蹤每條 SQL 查詢的延遲並匯出到 Prometheus。

Usage:
    from app.core.db_query_listener import setup_query_listener
    setup_query_listener(engine)
"""
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# SQL operation 偵測 pattern
_OP_PATTERN = re.compile(
    r"^\s*(?:/\*.*?\*/\s*)?(SELECT|INSERT|UPDATE|DELETE|WITH)\b",
    re.IGNORECASE,
)

# WITH ... SELECT 也算 select
_WITH_SELECT = re.compile(r"^\s*WITH\b", re.IGNORECASE)


def detect_operation(statement: str) -> str:
    """從 SQL 語句推斷 operation type。"""
    m = _OP_PATTERN.match(statement)
    if not m:
        return "other"
    op = m.group(1).upper()
    if op == "WITH":
        return "select"  # CTE 最終都是 SELECT
    return op.lower()


def setup_query_listener(engine) -> None:
    """掛接 SQLAlchemy event listener 追蹤查詢延遲。"""
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start = start_times.pop()
            duration_ms = (time.perf_counter() - start) * 1000
            operation = detect_operation(statement)
            try:
                from app.core.db_query_metrics import get_query_metrics
                get_query_metrics().record(operation=operation, duration_ms=duration_ms)
            except Exception:
                pass  # metrics 不應中斷查詢

    logger.info("DB query duration listener attached")
