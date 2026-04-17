# -*- coding: utf-8 -*-
"""
Shadow Baseline Prometheus Metrics

從 backend/logs/shadow_trace.db 讀取 query_trace，匯出為 Prometheus gauges。
作為 Hermes Phase 0 → Phase 1 GO/NO-GO 儀表板的資料源：

  1. p95 latency by provider — shadow_baseline_latency_p95_ms
  2. success rate by provider — shadow_baseline_success_ratio
  3. tool usage by provider — shadow_baseline_tool_use_count

⚠️ 架構說明（2026-04-18 修正）：
shadow_logger 為 single-write — 每 request 寫一筆 trace，
provider_resolver 一個 channel 對應固定一個 provider，
故同 request_id 不會出現在兩個 provider。

原設計的 tool_equivalence_ratio（基於 request_id 配對）永遠為空，
已移除。改以 tool usage 分布讓使用者目視比較兩 provider 的 tool 偏好。

Compression 觸發率非本 DB 範圍，由 Hermes 側 inference_provider_metrics 接管。

呼叫於 /metrics 端點，每次請求重算（DB 量小，<10K rows，<50ms）。
"""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from prometheus_client import CollectorRegistry, Gauge

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parents[3] / "logs" / "shadow_trace.db"
_LOOKBACK_HOURS = 24


def _percentile(sorted_values: List[float], p: float) -> Optional[float]:
    if not sorted_values:
        return None
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * p))
    return sorted_values[idx]


def _load_recent_rows() -> List[Dict]:
    if not _DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT ts, channel, provider, success, latency_ms, tools_used, request_id "
            "FROM query_trace "
            "WHERE ts >= datetime('now', ?) "
            "ORDER BY ts",
            (f"-{_LOOKBACK_HOURS} hours",),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning("shadow_baseline: failed to read DB: %s", e)
        return []


def _compute_tool_usage(rows: List[Dict]) -> Dict[Tuple[str, str], int]:
    """統計各 provider 的 tool 使用次數。

    回傳 {(provider, tool_name): count}。
    """
    counts: Dict[Tuple[str, str], int] = defaultdict(int)
    for r in rows:
        provider = r.get("provider") or "unknown"
        try:
            tools = json.loads(r.get("tools_used") or "[]")
        except (TypeError, ValueError):
            continue
        for tool in tools:
            if isinstance(tool, str):
                counts[(provider, tool)] += 1
    return counts


def populate_shadow_metrics(registry: CollectorRegistry) -> None:
    """讀取 shadow_trace.db 後計算指標並註冊到 registry。

    注入式設計：呼叫端傳入 registry（與既有 /metrics 端點一致）。
    """
    rows = _load_recent_rows()

    rows_total = Gauge(
        "shadow_baseline_rows_total",
        "Total query_trace rows in lookback window",
        ["lookback_hours"],
        registry=registry,
    )
    rows_total.labels(lookback_hours=str(_LOOKBACK_HOURS)).set(len(rows))

    if not rows:
        return

    by_provider: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        by_provider[r.get("provider") or "unknown"].append(r)

    latency_p95 = Gauge(
        "shadow_baseline_latency_p95_ms",
        "p95 latency in ms by provider (last 24h)",
        ["provider"],
        registry=registry,
    )
    success_ratio = Gauge(
        "shadow_baseline_success_ratio",
        "Success ratio (success=1 / total) by provider (last 24h)",
        ["provider"],
        registry=registry,
    )
    call_total = Gauge(
        "shadow_baseline_call_total",
        "Total calls by provider (last 24h)",
        ["provider"],
        registry=registry,
    )

    for provider, prov_rows in by_provider.items():
        latencies = sorted(r["latency_ms"] for r in prov_rows if r.get("latency_ms"))
        p95 = _percentile(latencies, 0.95)
        if p95 is not None:
            latency_p95.labels(provider=provider).set(p95)
        ok = sum(1 for r in prov_rows if r.get("success") == 1)
        success_ratio.labels(provider=provider).set(ok / len(prov_rows))
        call_total.labels(provider=provider).set(len(prov_rows))

    tool_usage = _compute_tool_usage(rows)
    if tool_usage:
        tool_gauge = Gauge(
            "shadow_baseline_tool_use_count",
            "Tool invocation count by provider and tool (last 24h)",
            ["provider", "tool"],
            registry=registry,
        )
        for (provider, tool), count in tool_usage.items():
            tool_gauge.labels(provider=provider, tool=tool).set(count)
