# -*- coding: utf-8 -*-
"""
Backup Prometheus Metrics（A40②，2026-08-28）

從 backup_operations.json（持久化事實）於每次 /metrics scrape 時讀出：

  1. backup_last_success_timestamp_seconds — 最後一次 create 成功的 unix time
  2. backup_consecutive_failures — 尾部連續失敗次數

判準刻意用「距上次成功多久」而非「上次執行是否失敗」：
  - A39 形態（排程每天失敗但工作被別人接手）→ 有人成功就不告警
  - 2026-05-22 形態（每天有跑但每天失敗 6 天）→ 距上次成功持續拉長，會被抓到
  - 「根本沒跑」→ 同上，同一條規則涵蓋
告警規則見 configs/prometheus/alerts.yml（BackupLastSuccessTooOld / BackupMetricAbsent）。

讀持久化 log 而非排程器記憶體變數：容器重啟後 gauge 不歸零
（`_last_backup_time` 是記憶體變數的教訓見 auto_scheduler.py 2026-08-24 註解）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Optional

from prometheus_client import CollectorRegistry, Gauge

logger = logging.getLogger(__name__)

_gauges: Dict[str, Gauge] = {}


def _init_gauges(reg: CollectorRegistry) -> None:
    if _gauges:
        return
    _gauges["last_success"] = Gauge(
        "backup_last_success_timestamp_seconds",
        "Unix time of last successful in-container backup create "
        "(source: backup_operations.json, survives restarts)",
        registry=reg,
    )
    _gauges["consecutive_failures"] = Gauge(
        "backup_consecutive_failures",
        "Trailing consecutive failed backup create operations",
        registry=reg,
    )


def populate_backup_metrics(reg: CollectorRegistry) -> None:
    """per-scrape populate — 由 prometheus_middleware.get_metrics_endpoint 呼叫"""
    _init_gauges(reg)

    from app.services.backup import backup_service

    log_file = backup_service.backup_log_file
    if not log_file.exists():
        # 沒有 log 檔＝從未備份過；不 set 值讓 absent() 告警接手，
        # 而不是 set 0 假裝「1970 年成功過一次」。
        return

    with open(log_file, "r", encoding="utf-8") as f:
        logs = json.load(f)

    create_logs = [l for l in logs if l.get("action") == "create"]
    if not create_logs:
        return

    last_success_ts: Optional[float] = None
    for log in reversed(create_logs):
        if log.get("status") == "success":
            try:
                last_success_ts = datetime.fromisoformat(
                    str(log.get("timestamp", "")).split("+")[0]
                ).timestamp()
            except (TypeError, ValueError):
                pass
            break

    consecutive = 0
    for log in reversed(create_logs):
        if log.get("status") == "success":
            break
        consecutive += 1

    if last_success_ts is not None:
        _gauges["last_success"].set(last_success_ts)
    _gauges["consecutive_failures"].set(consecutive)
