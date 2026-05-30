"""Fitness step 72 (v6.12, 2026-05-31): KG knowledge domain code entity 重複偵測

對齊 GRAPH_ECOSYSTEM_HOLISTIC_REVIEW §5 建議 #2:
knowledge graph 39% 是 code entity 雙寫 (應移至 code-only)

評估 + 規劃刪除範圍，不擅自刪 (待 owner approve)
"""
from __future__ import annotations

import os
import subprocess
import sys


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
    print("=== KG knowledge domain code entity 重複 audit (step 72 / 圖譜建議 #2) ===")
    print()

    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as db:
        # knowledge domain entity_type 分佈
        rows = await db.execute(text('''
            SELECT entity_type, COUNT(*) FROM canonical_entities
            WHERE graph_domain='knowledge' GROUP BY entity_type ORDER BY 2 DESC
        '''))
        total = 0
        code_total = 0
        biz_total = 0
        code_types = {'py_function','py_module','py_class','api_endpoint','service','schema',
                      'ts_interface','ts_module','ts_hook','ts_component','repository','ts_type','middleware'}
        for r in rows:
            total += r[1]
            if r[0] in code_types:
                code_total += r[1]
                print(f"  CODE  {r[0]:25} {r[1]:>6}")
            else:
                biz_total += r[1]
                print(f"  BIZ   {r[0]:25} {r[1]:>6}")
        print(f"---")
        print(f"  TOTAL: {total} | code: {code_total} ({code_total/total*100:.1f}%) | biz: {biz_total} ({biz_total/total*100:.1f}%)")
asyncio.run(main())
"""
    out = run_in_container(code)
    print(out)
    print()

    # 解析 TOTAL 行
    code_pct = 0
    for line in out.splitlines():
        if "TOTAL:" in line:
            try:
                # TOTAL: 7556 | code: 2965 (39.2%) | biz: ...
                code_pct = float(line.split("code:")[1].split("%")[0].split("(")[1])
            except (IndexError, ValueError):
                pass

    print(f"=== 評估結果 ===")
    print(f"knowledge domain 內 code entity 占比: {code_pct:.1f}%")
    print()
    if code_pct > 30:
        print(f"🔴 RED (> 30%) — knowledge graph 變「code graph 副本」")
        print(f"建議: 寫 knowledge_dedup_script.py 刪 code entity from knowledge")
        print(f"      待 owner approve 後執行 (對齊 L43 教訓: tar 備份 + MD5)")
        if strict:
            return 1
    elif code_pct > 10:
        print(f"🟡 YELLOW (10-30%) — 部分重複可接受")
    else:
        print(f"🟢 GREEN (< 10%) — knowledge graph 純業務")
    return 0


if __name__ == "__main__":
    sys.exit(main())
