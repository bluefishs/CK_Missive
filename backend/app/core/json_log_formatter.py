# -*- coding: utf-8 -*-
"""
JSON Log Formatter — Loki / 觀測棧 compatible

每行輸出一個 JSON 物件，包含：
- timestamp (ISO 8601)
- level (INFO/WARNING/ERROR/...)
- message
- logger (模組名稱)
- request_id (從 ContextVar 注入)
- exception (含 traceback，僅在有例外時)

Usage:
    from app.core.json_log_formatter import JsonLogFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
"""
import json
import logging
import traceback
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    """Loki-compatible JSON 日誌格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # request_id from ContextVar
        try:
            from app.core.middleware import request_id_var
            rid = request_id_var.get("")
            if rid:
                log_entry["request_id"] = rid
        except Exception:
            pass

        # Exception traceback
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        return json.dumps(log_entry, ensure_ascii=False, default=str)
