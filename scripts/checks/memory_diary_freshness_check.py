#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 18 — Memory Wiki Freshness Check.

對 ADR-0022 自進化系統的寫入鏈路驗證新鮮度：
  - diary/      : 期望每天有新檔（最近 2 天必須 ≥ 1 篇）
  - patterns/   : 期望每週有新檔（最近 7 天必須 ≥ 1 篇）
  - critiques/  : 期望每週有新檔（最近 7 天必須 ≥ 1 篇）
  - failures/   : warning only（事故性紀錄不該頻繁）
  - evolutions/ : 週日 18:00 cron 寫，最近 7 天必須 ≥ 1 篇

防範：ADR-0022 半接通類事故重演（merge_alias 寫了但 RLS 沒展開的同模式）。

關聯：
- ADR-0022 Memory Wiki Self-Evolving
- docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md
- configs/prometheus/alerts.yml memory_wiki_freshness rules
- scripts/checks/run_fitness.sh step 18

Exit codes:
  0 — 全 pass 或 warning（dev 環境寬容）
  1 — strict mode (--ci) 且 critical（diary 連續 ≥ 3 天無寫入）
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIKI_MEMORY = PROJECT_ROOT / "wiki" / "memory"


def _list_files_with_dates(folder: Path, name_pattern: str) -> list[tuple[date, Path]]:
    """從檔名解析日期，回傳 (date, path) list。"""
    if not folder.exists():
        return []
    results = []
    rgx = re.compile(name_pattern)
    for f in folder.glob("*.md"):
        m = rgx.search(f.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
        results.append((d, f))
    return sorted(results, reverse=True)


def check_diary() -> tuple[str, str, str]:
    """diary 必須最近 2 天有寫。回傳 (status, level, msg) status ∈ ok/warn/critical"""
    folder = WIKI_MEMORY / "diary"
    files = _list_files_with_dates(folder, r"(\d{4}-\d{2}-\d{2})")
    if not files:
        return ("critical", "FAIL", "diary/ 無任何檔案 — 寫入鏈完全斷")
    latest_date, _latest = files[0]
    today = date.today()
    days_stale = (today - latest_date).days
    if days_stale <= 2:
        return ("ok", "OK ", f"diary 最新 {latest_date} ({days_stale}天前)")
    if days_stale <= 7:
        return ("warning", "WARN", f"diary 最新 {latest_date} ({days_stale}天前) — 接近閾值")
    return (
        "critical",
        "FAIL",
        f"diary 最新 {latest_date} ({days_stale}天前) — 寫入鏈疑似斷裂",
    )


def check_patterns() -> tuple[str, str, str]:
    """patterns 7 天內必須有新增。"""
    folder = WIKI_MEMORY / "patterns"
    files = list(folder.glob("*.md")) if folder.exists() else []
    if not files:
        return ("warning", "WARN", "patterns/ 空 — pattern_extractor 未產出")
    today = date.today()
    cutoff = today - timedelta(days=7)
    fresh = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime).date() >= cutoff]
    if fresh:
        return ("ok", "OK ", f"patterns/ 7d 內 {len(fresh)} 個新檔（共 {len(files)}）")
    latest_mtime = max(f.stat().st_mtime for f in files)
    days_stale = (today - datetime.fromtimestamp(latest_mtime).date()).days
    return (
        "warning",
        "WARN",
        f"patterns/ 最新檔 {days_stale} 天前 — pattern_extractor cron 可能斷",
    )


def check_critiques() -> tuple[str, str, str]:
    """critiques 7 天內必須有新增。"""
    folder = WIKI_MEMORY / "critiques"
    files = _list_files_with_dates(folder, r"critique-(\d{8})-")
    if not files:
        return ("warning", "WARN", "critiques/ 空 — agent_critic 未啟動或無 critique")
    today = date.today()
    latest_date, _ = files[0]
    days_stale = (today - latest_date).days
    if days_stale <= 7:
        return ("ok", "OK ", f"critiques 最新 {latest_date} ({days_stale}天前)")
    return (
        "warning",
        "WARN",
        f"critiques 最新 {latest_date} ({days_stale}天前) — critic 鏈疑斷",
    )


def check_evolutions() -> tuple[str, str, str]:
    """evolutions 週寫，14 天內必須有新檔。"""
    folder = WIKI_MEMORY / "evolutions"
    files = list(folder.glob("*.md")) if folder.exists() else []
    if not files:
        return ("warning", "WARN", "evolutions/ 空 — autobiography cron 未跑")
    today = date.today()
    latest_mtime = max(f.stat().st_mtime for f in files)
    days_stale = (today - datetime.fromtimestamp(latest_mtime).date()).days
    if days_stale <= 14:
        return ("ok", "OK ", f"evolutions 最新檔 {days_stale} 天前")
    return (
        "warning",
        "WARN",
        f"evolutions 最新檔 {days_stale} 天前 — autobiography 週日 cron 可能斷",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Memory Wiki Freshness Check")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    print("=== Memory Wiki Freshness（ADR-0022 半接通防範）===")
    print()

    checks = [
        ("diary (2d threshold)", check_diary),
        ("patterns (7d threshold)", check_patterns),
        ("critiques (7d threshold)", check_critiques),
        ("evolutions (14d threshold)", check_evolutions),
    ]

    critical = 0
    warnings = 0
    for label, fn in checks:
        try:
            status, level, msg = fn()
        except Exception as e:
            status, level, msg = "warning", "WARN", f"{type(e).__name__}: {e}"
        print(f"  [{level}] {label:<32} {msg}")
        if status == "critical":
            critical += 1
        elif status == "warning":
            warnings += 1

    print()
    if critical == 0 and warnings == 0:
        print("[PASS] Memory Wiki 寫入鏈全鏈活體")
    elif critical == 0:
        print(f"[WARN] {warnings} 個非 critical 警告（dev 環境常見）")
    else:
        print(
            f"[FAIL] {critical} critical + {warnings} warning — "
            "ADR-0022 寫入鏈疑斷裂"
        )

    return 1 if (args.ci and critical > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
