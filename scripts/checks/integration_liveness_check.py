#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""F14 (5/04 v3.0 覆盤洞察 11) — 整合鏈活體驗證 Fitness Step 15

對 v3.0 SYSTEM_INTEGRATION_REVIEW 8 接觸面定義 evidence query，每日跑一次：
  ❹ Critic → Memory          : 7 天 critique 篇數 ≥ 1
  ❺ KG ↔ Memory Wiki         : diary 7 天條目含 entity tag 比例 ≥ 50%
  ❻ LLM Wiki ↔ Memory Wiki   : evolutions/ 7 天有檔（autobiography 寫週成長）
  ❼ Hermes ↔ evolution       : diary 7 天 channel 多樣性 ≥ 2 通道
  ❽ SOUL Missive ↔ Hermes    : SOUL.md 與 hermes mirror drift hash 距離 ≤ 5 行

低於門檻的接觸面：warning（記錄）；strict mode (--ci) 才 exit 1。

關聯：
- docs/architecture/SYSTEM_INTEGRATION_REVIEW_v3.md 洞察 11
- scripts/checks/run_fitness.sh step 15
- task #5 F14
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIKI_MEMORY = PROJECT_ROOT / "wiki" / "memory"


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def check_critique_7d() -> tuple[str, bool, str]:
    """❹ Critic → Memory：7 天 critique 篇數。"""
    d = WIKI_MEMORY / "critiques"
    if not d.exists():
        return ("❹ critic→memory", False, "critiques/ dir missing")
    cutoff = date.today() - timedelta(days=7)
    recent = []
    for f in d.glob("critique-*.md"):
        m = re.search(r"critique-(\d{8})-", f.name)
        if not m:
            continue
        try:
            dt = date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:8]))
            if dt >= cutoff:
                recent.append(f.name)
        except ValueError:
            continue
    ok = len(recent) >= 1
    msg = f"7d critique count = {len(recent)} (target ≥ 1)"
    return ("❹ critic→memory", ok, msg)


def check_kg_memwiki_entity_tag() -> tuple[str, bool, str]:
    """❺ KG ↔ Memory Wiki：diary 7 天條目含 entity 引用比例。"""
    d = WIKI_MEMORY / "diary"
    if not d.exists():
        return ("❺ kg↔memwiki", False, "diary/ dir missing")
    cutoff = date.today() - timedelta(days=7)
    total_entries = 0
    with_entity = 0
    for f in d.glob("20*.md"):
        try:
            dt = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if dt < cutoff:
            continue
        text = _read_text(f)
        # 計 entry 數（每條以 "## " timestamp header 起）
        entries = re.findall(r"^## \d{2}:\d{2}:\d{2}", text, re.MULTILINE)
        total_entries += len(entries)
        # entity 引用模式：「**entities**: ...」或行內 `公司`、`機關` 等
        with_entity += len(re.findall(r"\*\*entities\*\*:", text))
    if total_entries == 0:
        return ("❺ kg↔memwiki", False, "no diary entries last 7d")
    pct = (with_entity / total_entries) * 100
    ok = pct >= 50.0
    msg = f"7d entity-tag rate = {with_entity}/{total_entries} ({pct:.0f}%, target ≥ 50%)"
    return ("❺ kg↔memwiki", ok, msg)


def check_evolutions_7d() -> tuple[str, bool, str]:
    """❻ LLM Wiki ↔ Memory Wiki：evolutions/ 7 天 autobiography 檔。"""
    d = WIKI_MEMORY / "evolutions"
    if not d.exists():
        return ("❻ wiki↔memwiki", False, "evolutions/ dir missing")
    cutoff = date.today() - timedelta(days=7)
    recent = []
    for f in d.glob("20*.md"):
        try:
            stat_mtime = f.stat().st_mtime
            mod_dt = date.fromtimestamp(stat_mtime)
            if mod_dt >= cutoff:
                recent.append(f.name)
        except Exception:
            continue
    # autobiography 通常每週 1 篇，7 天至少 1
    ok = len(recent) >= 1
    msg = f"7d autobiography count = {len(recent)} (target ≥ 1)"
    return ("❻ wiki↔memwiki", ok, msg)


def check_diary_channel_diversity() -> tuple[str, bool, str]:
    """❼ Hermes ↔ evolution：diary 7 天 channel 多樣性（line/telegram/web/discord）。"""
    d = WIKI_MEMORY / "diary"
    if not d.exists():
        return ("❼ hermes→evolution", False, "diary/ dir missing")
    cutoff = date.today() - timedelta(days=7)
    channels: Counter = Counter()
    for f in d.glob("20*.md"):
        try:
            dt = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if dt < cutoff:
            continue
        text = _read_text(f)
        # session: line:U... / telegram:... / web:... / discord:...
        for ch_name in ("line", "telegram", "web", "discord", "mcp", "hermes"):
            if re.search(rf"session.*{ch_name}:", text):
                channels[ch_name] += 1
    distinct = len(channels)
    ok = distinct >= 2
    detail = ", ".join(f"{c}={n}" for c, n in channels.most_common())
    msg = f"7d distinct channels = {distinct} ({detail or 'none'}, target ≥ 2)"
    return ("❼ hermes→evolution", ok, msg)


def check_soul_drift() -> tuple[str, bool, str]:
    """❽ SOUL drift：簡單比對行數差異。完整 hash drift 由 soul_mirror_drift_check.py 處理。"""
    soul_a = PROJECT_ROOT / "wiki" / "SOUL.md"
    if not soul_a.exists():
        return ("❽ soul drift", False, "wiki/SOUL.md missing")
    # AaaP mirror 路徑（與 soul_mirror_drift_check.py 對齊）
    soul_b = PROJECT_ROOT.parent / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md"
    if not soul_b.exists():
        # CK_AaaP 路徑可能不存在於某些 dev 環境
        return ("❽ soul drift", True, "AaaP mirror not present (skip)")
    a_lines = len(_read_text(soul_a).splitlines())
    b_lines = len(_read_text(soul_b).splitlines())
    diff = abs(a_lines - b_lines)
    ok = diff <= 5
    msg = f"line diff = {diff} (Missive={a_lines} vs AaaP={b_lines}, target ≤ 5)"
    return ("❽ soul drift", ok, msg)


CHECKS = [
    check_critique_7d,
    check_kg_memwiki_entity_tag,
    check_evolutions_7d,
    check_diary_channel_diversity,
    check_soul_drift,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Integration liveness check (F14)")
    parser.add_argument(
        "--ci", action="store_true",
        help="strict mode: exit 1 if any check fails",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" F14 Integration Liveness Check (v3.0 8 接觸面 lite)")
    print("=" * 60)

    fails = 0
    for check_fn in CHECKS:
        name, ok, msg = check_fn()
        marker = "OK" if ok else "WARN"
        print(f"  [{marker}] {name}: {msg}")
        if not ok:
            fails += 1

    print("=" * 60)
    if fails == 0:
        print(f" All {len(CHECKS)} liveness checks PASS")
        return 0
    print(f" {fails}/{len(CHECKS)} checks WARNING")
    if args.ci:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
