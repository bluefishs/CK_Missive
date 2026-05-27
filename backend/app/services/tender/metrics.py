# -*- coding: utf-8 -*-
"""Tender scraper Prometheus metrics — P1-4 治理（2026-05-27）。

監控 tender 抓取健康度，補 L29 family 治理範疇：
- 抓取失敗計數 labeled by source + reason
- 連續失敗 watermark 觀察（接近 BLOCK_THRESHOLD 時可預警）
- 對齊 PCC 50 天 silent dormant 教訓 — metric 化讓監控可及

L29 教訓：silent dormant 不只 try/except 處理，還需 metric 累積 + Prometheus
alert 才能觸發 owner 注意。

Counters:
- tender_scraper_failures_total{source, reason}
  source: ezbid / pcc
  reason: http_403 / captcha / http_503 / http_429 / network_error / parse_error
- tender_scraper_runs_total{source, status}
  status: ok / blocked / partial / error
"""
from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Gauge, CollectorRegistry, REGISTRY


TENDER_SCRAPER_FAILURES = "tender_scraper_failures_total"
TENDER_SCRAPER_RUNS = "tender_scraper_runs_total"
TENDER_SCRAPER_CONSECUTIVE = "tender_scraper_consecutive_failures"


class TenderMetrics:
    """單例形式提供 tender 監控 metric。"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.failures = Counter(
            TENDER_SCRAPER_FAILURES,
            "Tender scraper failures by source + reason (P1-4 治理)",
            ["source", "reason"],
            registry=reg,
        )
        self.runs = Counter(
            TENDER_SCRAPER_RUNS,
            "Tender scraper invocations by source + status",
            ["source", "status"],
            registry=reg,
        )
        self.consecutive = Gauge(
            TENDER_SCRAPER_CONSECUTIVE,
            "Current consecutive failures per source (預警接近 BLOCK_THRESHOLD)",
            ["source"],
            registry=reg,
        )


_instance: Optional[TenderMetrics] = None


def get_tender_metrics() -> TenderMetrics:
    """單例 getter — 避免重複註冊。"""
    global _instance
    if _instance is None:
        try:
            _instance = TenderMetrics()
        except ValueError:
            # 已註冊（test 重複載入場景） — silent ignore
            _instance = TenderMetrics.__new__(TenderMetrics)
            # 直接 sentinel 空殼，inc 操作將安全 no-op via getattr
            for name in ("failures", "runs", "consecutive"):
                setattr(_instance, name, _NoopMetric())
    return _instance


class _NoopMetric:
    """測試情境用 — labels().inc() 不會拋例外"""

    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass
