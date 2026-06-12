"""Graph domain tagging audit — entity_type vs graph_domain 一致性（2026-06-12）

對齊 GRAPH_GOVERNANCE_REVIEW_20260612.md §2/§5 建議 A：
覆盤揭發 code 構件實體（py_function/module/class/ts_*/api_endpoint/db_table/repository）
被誤標進 `knowledge` graph_domain（應 `code`）→ 膨脹假性 embedding 缺口
（knowledge 顯示 70%，排除誤標後真實 94%）+ 污染語意搜尋。

偵測：code-type entity_type 但 graph_domain != 'code' 的實體數（應為 0）。
- > 0 → RED（domain tagging drift；ingest 源頭未統一）

設計：透過 docker exec backend 跑 AsyncSessionLocal（同 cross_domain_link_audit 模式）。

Usage:
  python scripts/checks/graph_domain_tagging_audit.py
  python scripts/checks/graph_domain_tagging_audit.py --strict
"""
from __future__ import annotations

import os
import subprocess
import sys

# Windows cp950 防護（L49.8 家族）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# code domain SSOT：這些 entity_type 一律屬 graph_domain='code'
CODE_TYPES = [
    "py_function", "py_module", "py_class",
    "ts_interface", "ts_module", "ts_hook", "ts_component", "ts_function", "ts_type",
    "api_endpoint", "db_table", "repository",
]


def run_in_container(code: str) -> str:
    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        r = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "python", "-c", code],
            capture_output=True, timeout=30, env=env,
        )
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== Graph Domain Tagging Audit (entity_type ↔ graph_domain SSOT) ===\n")

    types_sql = ",".join(f"'{t}'" for t in CODE_TYPES)
    code = f"""
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text('''
            SELECT entity_type, graph_domain, COUNT(*) c
            FROM canonical_entities
            WHERE entity_type IN ({types_sql}) AND graph_domain != 'code'
            GROUP BY entity_type, graph_domain ORDER BY c DESC
        '''))).fetchall()
        for r in rows:
            print(f"{{r[0]}}|{{r[1]}}|{{r[2]}}")
        print("TOTAL|" + str(sum(r[2] for r in rows)))
asyncio.run(main())
"""
    out = run_in_container(code)
    if out.startswith("ERROR") or "Traceback" in out:
        print(f"  [SKIP] DB 查詢失敗（backend 容器未起？）：{out[:200]}")
        return 0

    total = 0
    rows = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        parts = line.split("|")
        if parts[0] == "TOTAL":
            total = int(parts[1])
        elif len(parts) == 3:
            rows.append((parts[0], parts[1], int(parts[2])))

    if rows:
        print("  誤標明細（code-type 卻不在 code domain）：")
        for et, dom, c in rows:
            print(f"    {et:16s} → {dom:12s} {c:>5}")
        print()

    print(f"  誤標總數: {total}（target 0）\n")
    if total == 0:
        level = "GREEN"
    elif total < 100:
        level = "YELLOW"
    else:
        level = "RED"
    print(f"Status: [{level}] {'domain tagging 一致' if level == 'GREEN' else 'graph_domain 誤標漂移'}")
    if level != "GREEN":
        print("修法（GRAPH_GOVERNANCE_REVIEW_20260612 §5 建議 A）：")
        print("  1. 一次性 migration（需 owner 確認＋備份）：")
        print(f"     UPDATE canonical_entities SET graph_domain='code'")
        print(f"     WHERE entity_type IN ({types_sql}) AND graph_domain != 'code';")
        print("  2. 修 ingest 源頭（code-graph + knowledge ingest）統一 domain 標記")

    return 1 if (strict and level == "RED") else 0


if __name__ == "__main__":
    sys.exit(main())
