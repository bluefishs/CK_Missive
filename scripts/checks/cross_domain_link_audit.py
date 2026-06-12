"""Fitness step 71 (v6.12, 2026-05-31): KG cross-domain 連結率 audit

對齊 GRAPH_ECOSYSTEM_HOLISTIC_REVIEW §5 建議 #5:
量化 tender ↔ knowledge ↔ wiki 三方跨域連結率

3 對連結:
1. tender_agency ↔ knowledge.org (應 ≥80%)
2. tender_record ↔ wiki narrative (應 ≥30%)
3. wiki entity ↔ KG canonical (應 ≥80%, v5.9.8 已達 86%)

設計：透過 /metrics + DB 查
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Windows cp950 防護（L49.8 家族；v6.18 8-audit 硬化漏掉本圖譜 audit，2026-06-12 補）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[2]


def run_in_container(code: str) -> str:
    """在 backend container 內跑 python -c"""
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


def audit_tender_org_link() -> dict:
    """1. tender_agency canonical_name 是否在 knowledge.org 內"""
    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as db:
        # tender_agency total
        total = (await db.execute(text("SELECT COUNT(*) FROM canonical_entities WHERE entity_type='tender_agency'"))).scalar()
        # 有對應 knowledge.org 名稱 (簡化: canonical_name match)
        linked = (await db.execute(text('''
            SELECT COUNT(DISTINCT t.id) FROM canonical_entities t
            JOIN canonical_entities k ON LOWER(TRIM(t.canonical_name))=LOWER(TRIM(k.canonical_name))
            WHERE t.entity_type='tender_agency' AND k.entity_type='org'
        '''))).scalar()
        pct = (linked/total*100) if total else 0
        print(f"{total}|{linked}|{pct:.1f}")
asyncio.run(main())
"""
    out = run_in_container(code)
    try:
        total, linked, pct = out.split("\n")[-1].split("|")
        return {"total": int(total), "linked": int(linked), "pct": float(pct)}
    except Exception:
        return {"total": 0, "linked": 0, "pct": 0, "error": out}


def audit_wiki_kg_link() -> dict:
    """3. wiki entity 是否有 kg_entity_id frontmatter"""
    wiki_dir = ROOT / "wiki" / "entities"
    if not wiki_dir.is_dir():
        return {"total": 0, "linked": 0, "pct": 0}
    total = 0
    linked = 0
    for f in wiki_dir.glob("*.md"):
        total += 1
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")[:1500]
            if "kg_entity_id:" in text:
                linked += 1
        except Exception:
            pass
    pct = (linked/total*100) if total else 0
    return {"total": total, "linked": linked, "pct": pct}


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== KG cross-domain 連結率 audit (step 71 / 圖譜建議 #5) ===")
    print()

    issues = []

    # 1. tender_agency ↔ knowledge.org
    r1 = audit_tender_org_link()
    pct1 = r1.get("pct", 0)
    print(f"1. tender_agency ↔ knowledge.org:")
    print(f"   {r1.get('linked', 0):>5} / {r1.get('total', 0):>5} = {pct1:5.1f}%  ", end="")
    if pct1 >= 80:
        print("✅ GREEN (≥80%)")
    elif pct1 >= 50:
        print("🟡 YELLOW (50-80%)")
    else:
        print("🔴 RED (<50%)")
        issues.append("tender_agency ↔ knowledge.org 連結率不足")
    print()

    # 2. tender_record ↔ wiki — 簡化跳過 (wiki narrative ID 對應未實作)
    print(f"2. tender_record ↔ wiki narrative:")
    print(f"   ⚠ 未實作 (待 document/tender narrative 機制成熟)")
    print()

    # 3. wiki entity ↔ KG canonical (透過 kg_entity_id frontmatter)
    r3 = audit_wiki_kg_link()
    pct3 = r3.get("pct", 0)
    print(f"3. wiki entity ↔ KG canonical:")
    print(f"   {r3['linked']:>5} / {r3['total']:>5} = {pct3:5.1f}%  ", end="")
    if pct3 >= 80:
        print("✅ GREEN (≥80%)")
    elif pct3 >= 50:
        print("🟡 YELLOW (50-80%)")
    else:
        print("🔴 RED (<50%)")
        issues.append("wiki entity ↔ KG canonical 連結率不足")
    print()

    print("=" * 60)
    if issues:
        print(f"⚠ {len(issues)} 議題需 owner action:")
        for i in issues:
            print(f"    - {i}")
        if strict:
            return 1
    else:
        print("✅ 所有跨域連結率達標")
    return 0


if __name__ == "__main__":
    sys.exit(main())
