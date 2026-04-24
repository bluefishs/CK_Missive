# -*- coding: utf-8 -*-
"""
Admin Push Prometheus 指標

追蹤 admin 推播通道（LINE / Telegram / 其他）的成功失敗率。

背景：2026-04-21 Telegram 個人號永封（ADR-0027），LINE 成為唯一 admin push 通道。
為防 LINE 也發生異常導致 push 靜默失敗，新增此 metrics + 連續失敗告警。

Metrics:
- admin_push_total{channel, status}: 推播次數（status = success|fail）
- admin_push_consecutive_failures{channel}: 連續失敗次數（gauge）
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, REGISTRY

logger = logging.getLogger(__name__)

ADMIN_PUSH_TOTAL = "admin_push_total"
ADMIN_PUSH_CONSECUTIVE_FAILS = "admin_push_consecutive_failures"

# 連續失敗達此閾值 → stderr error log（人工關注）
_ALERT_THRESHOLD = int(os.getenv("ADMIN_PUSH_ALERT_THRESHOLD", "3"))


class AdminPushMetrics:
    """Admin 推播通道指標（單例）"""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        reg = registry or REGISTRY
        self.total = Counter(
            ADMIN_PUSH_TOTAL,
            "Admin push messages by channel and outcome",
            ["channel", "status"],
            registry=reg,
        )
        self.consecutive_fails = Gauge(
            ADMIN_PUSH_CONSECUTIVE_FAILS,
            "Consecutive push failures per channel (reset on success)",
            ["channel"],
            registry=reg,
        )
        self._fail_counter: dict[str, int] = {}

    def record_success(self, channel: str) -> None:
        """推播成功 → 重置連續失敗計數"""
        self.total.labels(channel=channel, status="success").inc()
        if self._fail_counter.get(channel, 0) > 0:
            self._fail_counter[channel] = 0
            self.consecutive_fails.labels(channel=channel).set(0)

    def record_failure(self, channel: str, reason: str = "") -> None:
        """推播失敗 → 累計連續計數 + 達閾值時 error log"""
        self.total.labels(channel=channel, status="fail").inc()
        cnt = self._fail_counter.get(channel, 0) + 1
        self._fail_counter[channel] = cnt
        self.consecutive_fails.labels(channel=channel).set(cnt)

        if cnt >= _ALERT_THRESHOLD:
            logger.error(
                "[admin_push] %s 連續 %d 次推播失敗 (reason=%s) — "
                "請檢查 channel access token / API status",
                channel, cnt, reason or "unknown",
            )
            # 寫入獨立失敗日誌供人工檢視（app logs rotate 時不遺失）
            try:
                log_path = Path("logs") / "admin_push_failures.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                from datetime import datetime
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        f"{datetime.now().isoformat()} {channel} consecutive={cnt} reason={reason}\n"
                    )
            except Exception:
                pass  # best-effort


_metrics: Optional[AdminPushMetrics] = None


def get_admin_push_metrics() -> AdminPushMetrics:
    global _metrics
    if _metrics is None:
        _metrics = AdminPushMetrics()
    return _metrics


__all__ = ["AdminPushMetrics", "get_admin_push_metrics"]
