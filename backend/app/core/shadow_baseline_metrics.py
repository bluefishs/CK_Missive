# -*- coding: utf-8 -*-
"""
Shadow Baseline Prometheus Metrics

從 backend/logs/shadow_trace.db 讀取 query_trace，匯出為 Prometheus gauges。
作為 Hermes Phase 0 → Phase 1 GO/NO-GO 三指標的儀表板資料源：

  1. p95 latency by provider — shadow_baseline_latency_p95_ms
  2. tool-call equivalence rate — shadow_baseline_tool_equivalence_ratio
  3. success rate by provider — shadow_baseline_success_ratio

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


def _compute_tool_equivalence(rows: List[Dict]) -> Dict[Tuple[str, str], float]:
    """配對相同 request_id 的兩 provider 呼叫，計算 tools_used 集合等價率。

    回傳 {(provider_a, provider_b): ratio_0_to_1}。
    """
    by_request: Dict[str, Dict[str, set]] = defaultdict(dict)
    for r in rows:
        req_id = r.get("request_id")
        provider = r.get("provider") or "unknown"
        if not req_id:
            continue
        try:
            tools = set(json.loads(r.get("tools_used") or "[]"))
        except (TypeError, ValueError):
            tools = set()
        by_request[req_id][provider] = tools

    pair_match: Dict[Tuple[str, str], List[bool]] = defaultdict(list)
    for providers_map in by_request.values():
        provs = sorted(providers_map.keys())
        for i, a in enumerate(provs):
            for b in provs[i + 1 :]:
                pair_match[(a, b)].append(providers_map[a] == providers_map[b])

    return {
        pair: sum(matches) / len(matches) if matches else 0.0
        for pair, matches in pair_match.items()
    }


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

    equivalence = _compute_tool_equivalence(rows)
    if equivalence:
        equiv_gauge = Gauge(
            "shadow_baseline_tool_equivalence_ratio",
            "Tool-call set equivalence between two providers on shared request_id (last 24h)",
            ["provider_a", "provider_b"],
            registry=registry,
        )
        for (a, b), ratio in equivalence.items():
            equiv_gauge.labels(provider_a=a, provider_b=b).set(ratio)
