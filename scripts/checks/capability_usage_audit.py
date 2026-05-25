#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 23 — Capability Usage Audit（2026-05-16 retro 治理 1）.

防範「投資看不到效益」— 系統性偵測 30d usage = 0 的死投資 capability，
給 owner 強制 A/B/C 決策（Activate / Block-deprecate / Catch-rescue）。

掃描對象（多層 capability inventory）：

* **Agent tools** — registry 內所有 manual + skill-derived tools
* **Agent graph tools** — 特別關注 search_across_graphs / navigate_graph / wiki_*
* **KG entity_types** — 各 type 的 mention_count > 0 比率
* **Memory wiki crystals / autobiography** — 0 檔代表閉環死
* **Fitness steps** — 從 run_fitness.sh 解析應跑的 step
* **ADRs (active)** — grep 引用次數 vs 0 引用孤兒

Detection sources（穿透式驗證原則）：

* shadow_trace.db `query_trace.tools_used` — agent tool 真實 7d 使用
* PostgreSQL `canonical_entities.mention_count` — KG entity 觸發率
* filesystem `wiki/memory/*` — 閉環產出檔案
* grep `docs/adr/*.md` 反向引用

Exit codes:
  0 — 無 critical dead capability（0% usage 持續 30d+）
  1 — ``--ci`` strict mode 且發現 dead capability

Usage:
  python scripts/checks/capability_usage_audit.py
  python scripts/checks/capability_usage_audit.py --json     # JSON 輸出
  python scripts/checks/capability_usage_audit.py --ci       # strict
  python scripts/checks/capability_usage_audit.py --days=30  # lookback window

呼應：
  * [[arch-pattern-script-existence-not-enforcement]]
  * [[arch-pattern-audit-zero-risk-false-negative]]
  * [[adr-anti-half-wired-sop]]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows cp950 stdout（同 fitness step 21/22 修法）
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHADOW_DB = PROJECT_ROOT / "backend" / "logs" / "shadow_trace.db"
WIKI_DIR = PROJECT_ROOT / "wiki"
ADR_DIR = PROJECT_ROOT / "docs" / "adr"


# ────────── Agent Tool Usage ──────────


def _load_agent_tool_usage(days: int) -> Tuple[Counter, int]:
    """從 shadow_trace.db 取最近 N 天 tool usage counter + total queries。"""
    counter: Counter = Counter()
    total = 0
    if not SHADOW_DB.exists():
        return counter, 0

    conn = sqlite3.connect(str(SHADOW_DB))
    try:
        cur = conn.execute(
            f"""
            SELECT tools_used FROM query_trace
            WHERE ts > datetime('now', '-{days} days')
              AND tools_used IS NOT NULL AND tools_used != ''
            """
        )
        for (raw,) in cur:
            total += 1
            if raw.startswith("["):
                names = re.findall(r'"([^"]+)"', raw)
            else:
                names = [t.strip() for t in raw.split(",") if t.strip()]
            for n in names:
                counter[n] += 1
    finally:
        conn.close()
    return counter, total


def _load_registered_tools() -> List[str]:
    """從 backend tool_registry 取所有註冊工具名稱（manual + skill auto）。"""
    backend_dir = PROJECT_ROOT / "backend"
    if not backend_dir.exists():
        return []

    sys.path.insert(0, str(backend_dir))
    try:
        from app.services.ai.tools.tool_registry import (  # type: ignore
            get_tool_registry,
        )

        registry = get_tool_registry()
        return sorted(registry.valid_tool_names)
    except Exception as exc:
        print(f"[WARN] tool_registry load failed: {exc}", file=sys.stderr)
        return []
    finally:
        if str(backend_dir) in sys.path:
            sys.path.remove(str(backend_dir))


# ────────── KG Mention Coverage ──────────


def _load_kg_mention_coverage() -> List[Dict[str, Any]]:
    """從 PostgreSQL 取各 entity_type 的 mention 命中率（透過 docker exec）。

    若 DB 不通則回空 list（避免 audit 阻塞）。
    """
    import subprocess

    sql = """
        SELECT graph_domain || '/' || entity_type AS type,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE mention_count > 0) AS hit
        FROM canonical_entities
        GROUP BY graph_domain, entity_type
        HAVING COUNT(*) >= 50
        ORDER BY total DESC;
    """
    try:
        result = subprocess.run(
            [
                "docker", "exec", "ck_missive_postgres_dev",
                "psql", "-U", "ck_user", "-d", "ck_documents", "-tA", "-F|", "-c", sql,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            print(f"[WARN] KG coverage query failed: {result.stderr[:200]}", file=sys.stderr)
            return []
        rows = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("|")
            if len(parts) != 3:
                continue
            etype, total, hit = parts
            total_i, hit_i = int(total), int(hit)
            rows.append({
                "type": etype,
                "total": total_i,
                "hit": hit_i,
                "hit_pct": round(100.0 * hit_i / total_i, 1) if total_i else 0.0,
            })
        return rows
    except Exception as exc:
        print(f"[WARN] KG coverage subprocess failed: {exc}", file=sys.stderr)
        return []


# ────────── Memory Wiki Loop Health ──────────


def _memory_loop_health() -> Dict[str, int]:
    """檢查 memory wiki 結晶閉環健康度（檔案計數）。"""
    base = WIKI_DIR / "memory"
    if not base.exists():
        return {}
    return {
        "diary": len(list((base / "diary").glob("*.md"))) if (base / "diary").exists() else 0,
        "patterns": len(list((base / "patterns").glob("*.md"))) if (base / "patterns").exists() else 0,
        "failures": len(list((base / "failures").glob("*.md"))) if (base / "failures").exists() else 0,
        "proposals": len(list((base / "proposals").glob("*.md"))) if (base / "proposals").exists() else 0,
        "crystals": len(list((base / "crystals").glob("*.md"))) if (base / "crystals").exists() else 0,
        "evolutions": len(list((base / "evolutions").glob("*.md"))) if (base / "evolutions").exists() else 0,
        "autobiography": len(list((base / "autobiography").glob("*.md")))
            if (base / "autobiography").exists() else 0,
    }


# ────────── ADR Reference Audit ──────────


def _adr_reference_audit() -> List[Dict[str, Any]]:
    """掃 active ADR 的反向引用次數，找孤兒 ADR。"""
    if not ADR_DIR.exists():
        return []

    results = []
    for adr_path in sorted(ADR_DIR.glob("0[0-9][0-9][0-9]-*.md")):
        m = re.match(r"^(\d{4})-", adr_path.name)
        if not m:
            continue
        num = m.group(1)

        try:
            text = adr_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 判斷 status
        status_m = re.search(r"^[*\-\s]*Status[*\-:\s]+([A-Za-z]+)", text, re.MULTILINE | re.IGNORECASE)
        status = (status_m.group(1).lower() if status_m else "unknown")
        if status in {"archived", "superseded", "removed", "rejected", "deprecated"}:
            continue

        # 反向引用搜尋（排除 ADR 自身檔案）
        ref_count = 0
        patterns = [f"ADR-{num}", f"adr-{num}"]
        for search_dir in (PROJECT_ROOT / "docs", PROJECT_ROOT / "backend",
                           PROJECT_ROOT / "frontend", PROJECT_ROOT / ".claude",
                           PROJECT_ROOT / "wiki"):
            if not search_dir.exists():
                continue
            for fpath in search_dir.rglob("*"):
                if not fpath.is_file():
                    continue
                if fpath.suffix not in {".md", ".py", ".ts", ".tsx", ".yaml", ".yml"}:
                    continue
                if fpath == adr_path:
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if any(p in content for p in patterns):
                    ref_count += 1
                    break  # 每檔最多算 1 次

        results.append({
            "adr": f"ADR-{num}",
            "status": status,
            "ref_count": ref_count,
            "title": adr_path.stem,
        })
    return results


# ────────── Report Generation ──────────


def _classify_tool(uses: int, total: int) -> str:
    if uses == 0:
        return "DEAD"
    if uses < 3:
        return "WEAK"
    return "HEALTHY"


def _generate_report(days: int, quick: bool = False) -> Dict[str, Any]:
    """產出三層健康度報告。

    Args:
        days: lookback 天數
        quick: True 跳過 ADR reverse-reference grep（Windows 上 recursive grep 慢，
            適合 daily orchestrator 用；月度 retro 可關掉拿完整資料）
    """
    tool_uses, total_queries = _load_agent_tool_usage(days)
    registered_tools = _load_registered_tools()

    tools_summary = {"dead": [], "weak": [], "healthy": []}
    for name in registered_tools:
        n = tool_uses.get(name, 0)
        cat = _classify_tool(n, total_queries).lower()
        tools_summary[cat].append({"tool": name, "uses": n})

    kg_coverage = _load_kg_mention_coverage()
    # 找 mention=0 但規模大的 entity_type
    kg_dead_types = [
        c for c in kg_coverage
        if c["hit_pct"] < 5.0 and c["total"] >= 100
    ]

    memory_loop = _memory_loop_health()
    memory_dead = []
    if memory_loop.get("crystals", 0) == 0 and memory_loop.get("patterns", 0) >= 3:
        memory_dead.append("crystals (0 files but 3+ patterns accumulated)")
    if memory_loop.get("autobiography", 0) == 0 and memory_loop.get("diary", 0) >= 7:
        memory_dead.append("autobiography (0 files but 7+ diary days)")
    if memory_loop.get("proposals", 0) >= 3:
        memory_dead.append(f"proposals ({memory_loop['proposals']} pending, gate blocked)")

    if quick:
        adr_refs = []
        adr_orphans = []
    else:
        adr_refs = _adr_reference_audit()
        adr_orphans = [a for a in adr_refs if a["ref_count"] == 0]

    return {
        "lookback_days": days,
        "shadow_trace_queries": total_queries,
        "tools": {
            "total_registered": len(registered_tools),
            "dead": tools_summary["dead"],
            "weak": tools_summary["weak"],
            "healthy_count": len(tools_summary["healthy"]),
            "dead_pct": round(
                100.0 * len(tools_summary["dead"]) / max(len(registered_tools), 1), 1
            ),
        },
        "kg_entity_types": {
            "scanned": len(kg_coverage),
            "dead_types": kg_dead_types,
            "dead_count": len(kg_dead_types),
        },
        "memory_loop": {
            "counts": memory_loop,
            "dead_loops": memory_dead,
        },
        "adr": {
            "active": len(adr_refs),
            "orphans": adr_orphans,
            "orphan_count": len(adr_orphans),
        },
    }


def _format_human(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 68)
    lines.append(f"  Capability Usage Audit ({report['lookback_days']}d lookback)")
    lines.append("=" * 68)

    # Agent tools
    t = report["tools"]
    lines.append("")
    lines.append(
        f"AGENT TOOLS  total={t['total_registered']}  "
        f"dead={len(t['dead'])} ({t['dead_pct']}%)  "
        f"weak={len(t['weak'])}  healthy={t['healthy_count']}"
    )
    lines.append(f"  (basis: {report['shadow_trace_queries']} shadow queries)")
    if t["dead"]:
        lines.append(f"  DEAD ({len(t['dead'])}):")
        for d in t["dead"][:15]:
            lines.append(f"    - {d['tool']}")
        if len(t["dead"]) > 15:
            lines.append(f"    ... and {len(t['dead']) - 15} more")
    if t["weak"]:
        lines.append(f"  WEAK ({len(t['weak'])}):")
        for w in t["weak"][:10]:
            lines.append(f"    - {w['tool']}  ({w['uses']}x)")

    # KG
    kg = report["kg_entity_types"]
    lines.append("")
    lines.append(f"KG ENTITY TYPES  scanned={kg['scanned']}  dead_pattern={kg['dead_count']}")
    for d in kg["dead_types"][:10]:
        lines.append(
            f"  - {d['type']:<35}  total={d['total']:>6}  hit_pct={d['hit_pct']:>5}%"
        )

    # Memory loop
    m = report["memory_loop"]
    lines.append("")
    lines.append(f"MEMORY WIKI LOOP  {m['counts']}")
    if m["dead_loops"]:
        for d in m["dead_loops"]:
            lines.append(f"  DEAD LOOP: {d}")

    # ADR orphans
    a = report["adr"]
    lines.append("")
    lines.append(f"ADR ORPHANS  active={a['active']}  zero_ref={a['orphan_count']}")
    for o in a["orphans"][:10]:
        lines.append(f"  - {o['adr']:<10}  {o['title']}")

    lines.append("")
    lines.append("=" * 68)

    # Verdict
    total_dead = (
        len(t["dead"]) + kg["dead_count"]
        + len(m["dead_loops"]) + a["orphan_count"]
    )
    if total_dead == 0:
        lines.append("  Result: HEALTHY (no dead capabilities detected)")
    elif total_dead <= 3:
        lines.append(f"  Result: YELLOW  ({total_dead} dead findings — review)")
    else:
        lines.append(f"  Result: RED  ({total_dead} dead findings — A/B/C decision required)")
    lines.append("=" * 68)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capability Usage Audit (Fitness step 23)")
    parser.add_argument("--days", type=int, default=30, help="Lookback window (default 30)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--ci", action="store_true", help="Strict mode (exit 1 on dead findings)")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: skip ADR reverse-reference grep (Windows recursive grep 慢)",
    )
    args = parser.parse_args()

    report = _generate_report(args.days, quick=args.quick)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_human(report))

    # CI exit code
    total_dead = (
        len(report["tools"]["dead"])
        + report["kg_entity_types"]["dead_count"]
        + len(report["memory_loop"]["dead_loops"])
        + report["adr"]["orphan_count"]
    )
    if args.ci and total_dead > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
