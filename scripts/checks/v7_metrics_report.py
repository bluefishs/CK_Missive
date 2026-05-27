#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M1 (5/04 v3.0 覆盤洞察 14) — v7.0 新指標 lite 報表

「成熟度 %」已死（5/04 self_diagnosis 報 7/7 真活但裂縫已浮現）。
v7.0 用以下 4 指標取代作為衡量基準：

  1. 跨通道 pattern 多樣性 (cross-channel pattern diversity)
     Telegram/LINE/Web/Discord 各自 7 天 diary 條目數

  2. 跨層引用密度 (cross-layer reference density)
     diary/critique/synthesis 平均連結 KG entity 數

  3. SOUL drift hash distance
     Missive ↔ AaaP 7 天滑動視窗 drift（行數差）

  4. Provider fidelity gap
     Ollama vs Groq vs NVIDIA 同 query SOUL 一致率（待後端 endpoint）

本 lite 版專注計算 + 文字輸出。完整 dashboard + Prometheus gauge 留待
v6.9（task M1 完整實作）。

關聯：
- docs/architecture/SYSTEM_INTEGRATION_REVIEW_v3.md 洞察 14
- task #7 M1
"""
from __future__ import annotations

import argparse
import json
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


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def metric_1_channel_diversity() -> dict:
    """指標 1：跨通道 pattern 多樣性（7 天 diary by channel）。

    Diary entry header format (per diary_service.append_entry):
        ## HH:MM:SS — emoji [route_type] channel
    where channel is one of: line / telegram / web / discord / mcp / hermes / -
    """
    d = WIKI_MEMORY / "diary"
    cutoff = date.today() - timedelta(days=7)
    by_channel: Counter = Counter()
    channels = ("line", "telegram", "web", "discord", "mcp", "hermes")
    if d.exists():
        for f in d.glob("20*.md"):
            try:
                if date.fromisoformat(f.stem) < cutoff:
                    continue
            except ValueError:
                continue
            text = _read(f)
            for ch in channels:
                # match `## HH:MM:SS — ✅ [route_type] {channel}` at end of header
                pattern = rf"^## \d{{2}}:\d{{2}}:\d{{2}} —.*\[[^\]]+\] {ch}\s*$"
                count = len(re.findall(pattern, text, re.MULTILINE))
                by_channel[ch] += count
    return {
        "metric": "channel_diversity",
        "by_channel": dict(by_channel),
        "distinct_channels": len([c for c, n in by_channel.items() if n > 0]),
        "total_entries": sum(by_channel.values()),
        "v7_target": "distinct ≥ 4 (line+telegram+web+discord)",
    }


def metric_2_reference_density() -> dict:
    """指標 2：跨層引用密度（diary 含 entity tag 比例 + critique 含 entity）。"""
    diary_dir = WIKI_MEMORY / "diary"
    cutoff = date.today() - timedelta(days=7)
    diary_entries = 0
    diary_with_entity = 0
    critique_entries = 0
    critique_with_entity = 0

    if diary_dir.exists():
        for f in diary_dir.glob("20*.md"):
            try:
                if date.fromisoformat(f.stem) < cutoff:
                    continue
            except ValueError:
                continue
            text = _read(f)
            entries = re.findall(r"^## \d{2}:\d{2}:\d{2}", text, re.MULTILINE)
            diary_entries += len(entries)
            diary_with_entity += len(re.findall(r"\*\*entities\*\*:", text))

    critique_dir = WIKI_MEMORY / "critiques"
    if critique_dir.exists():
        for f in critique_dir.glob("critique-*.md"):
            m = re.search(r"critique-(\d{8})", f.name)
            if not m:
                continue
            try:
                dt = date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:8]))
                if dt < cutoff:
                    continue
            except ValueError:
                continue
            text = _read(f)
            critique_entries += 1
            if re.search(r"entit(?:y|ies)|kg_entity_id|實體", text, re.IGNORECASE):
                critique_with_entity += 1

    diary_pct = (diary_with_entity / diary_entries * 100) if diary_entries else 0.0
    crit_pct = (critique_with_entity / critique_entries * 100) if critique_entries else 0.0

    return {
        "metric": "reference_density",
        "diary": {
            "entries": diary_entries,
            "with_entity": diary_with_entity,
            "pct": round(diary_pct, 1),
        },
        "critique": {
            "entries": critique_entries,
            "with_entity": critique_with_entity,
            "pct": round(crit_pct, 1),
        },
        "v7_target": "diary ≥ 50%, critique ≥ 80%",
    }


def metric_3_soul_drift() -> dict:
    """指標 3：SOUL drift hash distance（Missive vs AaaP 行數差）。

    ⚠️ 2026-05-27 校正：此 metric 原設計假設兩檔互為 mirror，但 ADR-0044 後
    AaaP SOUL.md 已升為「Hermes Meta — 共同大腦」（meta-governance），
    Missive SOUL.md 仍是「坤哥 — Missive 意識體人格」。兩檔本質為不同 entity，
    行數差 60+ 是 by design 不是 drift。

    若要維持此 metric 有意義，應改測：
      (a) Missive SOUL.md 與其 sync_targets 宣告路徑（若仍要 mirror）
      (b) 改名 soul_consistency_with_intent，比對 frontmatter source_of_truth flag
      (c) 廢止此 metric，改以「sync log freshness」替代
    """
    soul_a = PROJECT_ROOT / "wiki" / "SOUL.md"
    soul_b = PROJECT_ROOT.parent / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md"

    if not soul_a.exists():
        return {
            "metric": "soul_drift",
            "status": "Missive SOUL.md missing",
            "drift_lines": None,
            "v7_target": "≤ 5",
        }
    a_lines = len(_read(soul_a).splitlines())

    if not soul_b.exists():
        return {
            "metric": "soul_drift",
            "missive_lines": a_lines,
            "aaap_lines": None,
            "drift_lines": None,
            "status": "AaaP mirror not present (single-repo dev env)",
            "v7_target": "≤ 5",
        }
    b_lines = len(_read(soul_b).splitlines())
    diff = abs(a_lines - b_lines)
    return {
        "metric": "soul_drift",
        "missive_lines": a_lines,
        "aaap_lines": b_lines,
        "drift_lines": diff,
        "status": "OK" if diff <= 5 else "WARN — exceeds threshold 5",
        "v7_target": "≤ 5",
    }


def metric_4_provider_fidelity_gap() -> dict:
    """指標 4：Provider fidelity gap（讀 fidelity_log.jsonl 24h average）。

    M4 (5/04 補完)：fidelity_log.jsonl 由 soul-fidelity-eval.py 累積寫入。
    Owner 月度跑 `python scripts/checks/soul-fidelity-eval.py` 即會 append。
    """
    log_path = PROJECT_ROOT / "wiki" / "memory" / "evolutions" / "fidelity_log.jsonl"
    if not log_path.exists():
        return {
            "metric": "provider_fidelity_gap",
            "status": "no fidelity_log.jsonl (尚未跑過 soul-fidelity-eval)",
            "providers": ["ollama", "groq", "nvidia"],
            "v7_target": "max gap ≤ 10 percentage points",
        }

    from datetime import datetime, timedelta, timezone as _tz
    cutoff = datetime.now(_tz.utc) - timedelta(hours=24)
    by_provider: dict = {}
    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    ts = datetime.fromisoformat(rec.get("ts", "").replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                    prov = rec.get("provider")
                    fid = rec.get("fidelity")
                    if prov and fid is not None:
                        by_provider.setdefault(prov, []).append(float(fid))
                except Exception:
                    continue
    except Exception as e:
        return {
            "metric": "provider_fidelity_gap",
            "status": f"read failed: {e}",
            "v7_target": "max gap ≤ 10 percentage points",
        }

    if len(by_provider) < 2:
        return {
            "metric": "provider_fidelity_gap",
            "status": f"need ≥2 providers, got {len(by_provider)} ({list(by_provider)})",
            "v7_target": "max gap ≤ 10 percentage points",
        }

    avg_by_prov = {p: round(sum(v) / len(v) * 100, 1) for p, v in by_provider.items() if v}
    max_pct = max(avg_by_prov.values())
    min_pct = min(avg_by_prov.values())
    gap_pp = round(max_pct - min_pct, 1)
    return {
        "metric": "provider_fidelity_gap",
        "by_provider_24h_avg_pct": avg_by_prov,
        "gap_pp": gap_pp,
        "status": "OK" if gap_pp <= 10 else "WARN — exceeds 10pp",
        "v7_target": "max gap ≤ 10 percentage points",
    }


METRICS = [
    metric_1_channel_diversity,
    metric_2_reference_density,
    metric_3_soul_drift,
    metric_4_provider_fidelity_gap,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="v7.0 4-metric report (M1)")
    parser.add_argument(
        "--json", action="store_true",
        help="output json (for dashboard consumption)",
    )
    args = parser.parse_args()

    results = [fn() for fn in METRICS]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("=" * 65)
    print(" v7.0 Maturity Replacement Metrics (M1 lite report)")
    print("=" * 65)
    for r in results:
        print()
        print(f"  ## {r['metric']}")
        for k, v in r.items():
            if k == "metric":
                continue
            if isinstance(v, dict):
                print(f"     {k}:")
                for k2, v2 in v.items():
                    print(f"        {k2}: {v2}")
            else:
                print(f"     {k}: {v}")
    print()
    print("=" * 65)
    print(" v7.0+ 取代「成熟度 %」: 4 個指標構成新 baseline")
    print(" 完整 Prometheus gauge + Grafana dashboard 待 v6.9 (M1 完整實作)")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
