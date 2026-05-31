"""Document KG ingest 加入 (2026-05-31, v6.13)

對齊 GRAPH_ECOSYSTEM 建議 #4:
documents 1809 筆無對應 KG entity → AI 公文查詢無法走 KG

對齊 owner 備份安全訴求:
- 純 INSERT (完全可逆)
- 預設 dry-run / --apply 真執行
- 回滾: DELETE WHERE entity_type='document'

ingest 範圍:
- documents 1809 → document entity (knowledge domain)
- canonical_name = doc_number or title (前 100 字)
- 含 linked_agency_id / source_project
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
            capture_output=True, timeout=180, env=env,
        )
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def evaluate() -> str:
    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as db:
        total = (await db.execute(text('SELECT COUNT(*) FROM documents'))).scalar()
        existing = (await db.execute(text("SELECT COUNT(*) FROM canonical_entities WHERE entity_type='document'"))).scalar()
        # 有 doc_number 的
        with_doc_num = (await db.execute(text("SELECT COUNT(*) FROM documents WHERE doc_number IS NOT NULL AND doc_number != ''"))).scalar() if 'doc_number' in [c[0] for c in (await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='documents'"))).fetchall()] else 0
        print(f'documents: total={total} doc_num_有={with_doc_num} existing_entity={existing} todo={max(0, total - existing)}')
asyncio.run(main())
"""
    return run_in_container(code)


def apply_ingest(dry_run: bool = True) -> None:
    code = f"""
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

DRY_RUN = {dry_run}

async def main():
    async with AsyncSessionLocal() as db:
        rows = await db.execute(text('''
            SELECT id, COALESCE(NULLIF(title, \\'\\'), \\'untitled\\') AS name,
                   category, status, send_date, receive_date
            FROM documents
            ORDER BY id
        '''))
        cnt = 0
        for r in rows:
            doc_id, name, category, status, send_date, receive_date = r
            # canonical_name 加 doc_id suffix 避 unique conflict (多 doc 同 title)
            canonical = f'{{(name or "untitled")[:180]}} #{{doc_id}}'
            description = f'類別:{{category}} 狀態:{{status}}'[:500]
            external_id = f'doc-{{doc_id}}'
            if DRY_RUN:
                cnt += 1
            else:
                try:
                    await db.execute(text('''
                        INSERT INTO canonical_entities
                        (canonical_name, entity_type, description, graph_domain, external_id,
                         first_seen_at, last_seen_at)
                        VALUES (:name, 'document', :desc, 'knowledge', :ext, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    '''), {{'name': canonical, 'desc': description, 'ext': external_id}})
                    cnt += 1
                except Exception as e:
                    print(f'ERR doc_id={{doc_id}}: {{str(e)[:80]}}')
                    continue
        if not DRY_RUN:
            await db.commit()
        print(f'{{"DRY-RUN" if DRY_RUN else "INGESTED"}}: {{cnt}}')
asyncio.run(main())
"""
    print(run_in_container(code))


def main() -> int:
    apply = "--apply" in sys.argv
    print("=== Document KG ingest 加入 (對齊 owner 安全訴求 — 純加可逆) ===")
    print()
    print(evaluate())
    print()

    if not apply:
        print("🟡 DRY-RUN MODE")
        apply_ingest(dry_run=True)
        print()
        print("執行真實 ingest: python scripts/sync/document_kg_ingest.py --apply")
        print("回滾: DELETE FROM canonical_entities WHERE entity_type='document';")
        return 0

    print("🟢 APPLY MODE — 真實 INSERT (可逆)")
    apply_ingest(dry_run=False)
    print()
    print(evaluate())
    return 0


if __name__ == "__main__":
    sys.exit(main())
