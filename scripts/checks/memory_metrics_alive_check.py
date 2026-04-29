#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: Memory Wiki metrics alive check

確認坤哥意識體觀測 metrics 真的有被 update（而非 hollow gauge）。

L21 教訓：metrics 定義齊全但 0 caller refresh → Grafana dashboard 永遠
看到 0 → owner 不知道意識體鏈路是死是活。本 check 防止重蹈覆轍。

檢查 5 個 gauge 至少有 1 個 > 0（系統真的有運轉）：
- memory_diary_days_total
- memory_patterns_total
- memory_crystals_total
- memory_proposals_total
- memory_autobiographies_total

用法：
    python scripts/checks/memory_metrics_alive_check.py
    python scripts/checks/memory_metrics_alive_check.py --ci      # CI 模式（gauge 全 0 即 exit 1）
    python scripts/checks/memory_metrics_alive_check.py --url http://localhost:8001/metrics

Version: 1.0.0 (2026-04-29, v5.10.2 Phase 1)
關聯:
- ADR-0022 Memory Wiki Self-Evolving Assistant
- LESSONS_REGISTRY.md L21（Agent Evolution silent failure 同類）
- backend/app/core/memory_wiki_metrics.py
- backend/app/core/scheduler.py: memory_metrics_refresh_job
"""
from __future__ import annotations

import argparse
import re
import sys

try:
    import urllib.request
except ImportError:
    print("missing dep: urllib", file=sys.stderr)
    sys.exit(2)


METRICS_TO_CHECK = [
    "memory_diary_days_total",
    "memory_patterns_total",
    "memory_crystals_total",
    "memory_proposals_total",
    "memory_autobiographies_total",
]


def fetch_metrics(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[FAIL] 無法存取 {url}: {e}", file=sys.stderr)
        return ""


def parse_gauge(text: str, metric: str) -> float | None:
    # 找形如 "memory_diary_days_total 11.0" 的行
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        m = re.match(rf"^{re.escape(metric)}\s+([0-9.eE+-]+)", line)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def main(url: str, ci: bool) -> int:
    print("=== Memory Wiki Metrics Alive Check ===")
    print(f"領域：consciousness observability — 防 hollow metrics（L21）")
    print(f"來源：{url}")
    print()

    text = fetch_metrics(url)
    if not text:
        print("[ERROR] /metrics 端點無回應")
        return 2

    nonzero_count = 0
    null_count = 0
    rows = []
    for metric in METRICS_TO_CHECK:
        v = parse_gauge(text, metric)
        if v is None:
            rows.append((metric, "MISSING"))
            null_count += 1
        elif v > 0:
            rows.append((metric, f"{v:.0f}"))
            nonzero_count += 1
        else:
            rows.append((metric, "0"))

    # Pretty print
    name_w = max(len(r[0]) for r in rows)
    for name, val in rows:
        marker = "[OK]" if val not in ("0", "MISSING") else "[!!]"
        print(f"  {marker} {name:<{name_w}}  {val}")
    print()

    if null_count > 0:
        print(f"[WARN] {null_count} 個 metric 在 /metrics 找不到 — module 可能未載入")
    if nonzero_count == 0:
        print("[FAIL] 5 個 gauge 全為 0 / MISSING — hollow metrics 警報！")
        print()
        print("可能原因：")
        print("  1. memory_metrics_refresh_job 沒被排程（看 scheduler.py）")
        print("  2. wiki/memory/* 真的空（系統剛啟動）")
        print("  3. refresh_from_disk 失敗（看 PM2 log 搜 'Memory metrics'）")
        print("  4. metrics module 沒被 import（看 main.py）")
        return 1 if ci else 0

    print(f"[OK] {nonzero_count}/{len(METRICS_TO_CHECK)} gauge 非 0 — Memory observability alive")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://localhost:8001/metrics",
        help="Prometheus /metrics 端點",
    )
    parser.add_argument("--ci", action="store_true", help="strict 模式：全 0 即 exit 1")
    args = parser.parse_args()
    sys.exit(main(args.url, args.ci))
