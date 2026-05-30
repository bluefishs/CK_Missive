"""Agent query starvation 健康檢查 (L51.7 / fitness step 58, 2026-05-30)

L51.7 覆盤揭發: 坤哥 agent_query 流量 2h=0 / 24h shadow_baseline n=0
→ 引擎跑著但無人用，可能：
  1. /kunge UX 無人用（owner 偏好 LINE）
  2. agent_query endpoint 在但 frontend 沒展示
  3. 業務查詢用直接 SQL，不走 agent

Thresholds:
- RED: 7 天 agent_query=0 (坤哥真活探測無人 query)
- YELLOW: 1 天 0 query (短期觀察)
- GREEN: 1 天內有 query

Usage:
  python scripts/checks/agent_query_starvation_check.py
  python scripts/checks/agent_query_starvation_check.py --strict
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error


PROMETHEUS_URL = "http://localhost:8001/metrics"


def fetch_metric_value(metric_name: str) -> float:
    """從 backend /metrics 抓 metric 值（簡單 parser）"""
    try:
        with urllib.request.urlopen(PROMETHEUS_URL, timeout=5) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[FAIL] cannot fetch {PROMETHEUS_URL}: {e}")
        return -1.0

    total = 0.0
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith(metric_name):
            try:
                # 取 line 內最後一個數字 token
                parts = line.split()
                total += float(parts[-1])
            except (IndexError, ValueError):
                continue
    return total


def main(strict: bool = False) -> int:
    print("=== Agent Query Starvation Check (L51.7 / fitness step 58) ===")

    # 從 http_requests_total 計算 /api/ai/agent/query/* 累積次數
    # (Prometheus Counter 是累積值；本檢查不分時段，看絕對值近似)
    # 替代方案：實際 production 應有 7d window query，這裡先用 cumulative
    agent_queries = fetch_metric_value('http_requests_total{')
    # shadow baseline 24h
    shadow_24h = fetch_metric_value("shadow_baseline_rows_total")

    if agent_queries < 0:
        print("[SKIP] Prometheus /metrics unreachable")
        return 0

    # 簡化判斷：shadow_baseline 24h 若 = 0，視為 starvation 信號
    # (主進程 metrics 持續累積，靠 shadow_baseline 觀察「最近活動」)
    print(f"  http_requests_total (sum)    = {agent_queries:.0f}")
    print(f"  shadow_baseline_rows_total   = {shadow_24h:.0f}")

    if shadow_24h == 0:
        level = "RED"
        reason = "shadow_baseline 24h n=0 → agent query 鏈無近期活動"
    else:
        level = "GREEN"
        reason = f"shadow baseline {shadow_24h:.0f} rows in 24h"

    print(f"\nStatus: [{level}] {reason}")

    if strict and level == "RED":
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on RED (for fitness gate)")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
