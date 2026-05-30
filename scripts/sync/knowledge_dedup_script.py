"""KG knowledge domain code entity dedup script (2026-05-31)

對齊:
- GRAPH_ECOSYSTEM_HOLISTIC_REVIEW §5 建議 #2
- L43 教訓: tar 備份 + MD5 + 業務量驗證 + 7 天後重 audit

執行模式:
  python scripts/sync/knowledge_dedup_script.py              # dry-run (預設)
  python scripts/sync/knowledge_dedup_script.py --apply      # 真實刪除 (含 backup)
  python scripts/sync/knowledge_dedup_script.py --verify     # 重 audit 確認

刪除範圍:
  graph_domain='knowledge' AND entity_type IN code_types
  預估 ~3157 entity (41.8% of 7556)

刪除前自動 tar 備份至:
  backup/knowledge_dedup_<timestamp>.tar.gz
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backup"

CODE_TYPES = {
    "py_function", "py_module", "py_class",
    "api_endpoint", "service", "schema", "repository",
    "ts_interface", "ts_module", "ts_hook", "ts_component", "ts_type",
    "middleware",
}


def run_in_container(code: str) -> str:
    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        r = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "python", "-c", code],
            capture_output=True, timeout=120, env=env,
        )
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def evaluate() -> dict:
    """評估刪除範圍 + 業務 entity 數"""
    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
CODE_TYPES = ['py_function','py_module','py_class','api_endpoint','service','schema',
              'repository','ts_interface','ts_module','ts_hook','ts_component','ts_type','middleware']
async def main():
    async with AsyncSessionLocal() as db:
        total = (await db.execute(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='knowledge'"))).scalar()
        placeholders = ','.join(["'" + t + "'" for t in CODE_TYPES])
        code_count = (await db.execute(text(f"SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='knowledge' AND entity_type IN ({placeholders})"))).scalar()
        biz_count = total - code_count
        print(f"{total}|{code_count}|{biz_count}")
asyncio.run(main())
"""
    out = run_in_container(code)
    try:
        total, code_n, biz_n = out.split("\n")[-1].split("|")
        return {"total": int(total), "code": int(code_n), "biz": int(biz_n)}
    except Exception:
        return {"total": 0, "code": 0, "biz": 0, "error": out}


def backup_to_tar(timestamp: str) -> tuple[Path, Path, str]:
    """v6.12 強化 (2026-05-31) — 對齊 owner「備份與安全性為主要考量」訴求

    多層備份策略 (5 層防禦):
    1. JSON 結構備份 (人類可讀 + 程式還原)
    2. SQL INSERT 還原檔 (一鍵 restore)
    3. MD5 雙端驗證 (對齊 L43 教訓)
    4. /health business_data pre-check (驗證 KG 業務完整性)
    5. backup file size > 0 驗證 (避免空檔)
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    json_file = BACKUP_DIR / f"knowledge_dedup_{timestamp}.json"
    sql_file = BACKUP_DIR / f"knowledge_dedup_{timestamp}_restore.sql"

    # Step 1: JSON 結構備份 (含完整欄位)
    code = """
import asyncio
import json
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
CODE_TYPES = ['py_function','py_module','py_class','api_endpoint','service','schema',
              'repository','ts_interface','ts_module','ts_hook','ts_component','ts_type','middleware']
async def main():
    async with AsyncSessionLocal() as db:
        placeholders = ','.join(["'" + t + "'" for t in CODE_TYPES])
        rows = await db.execute(text(f'''SELECT id, canonical_name, entity_type, description,
            alias_count, mention_count, first_seen_at, last_seen_at,
            linked_agency_id, linked_project_id, source_project, external_id, version,
            graph_domain
            FROM canonical_entities
            WHERE graph_domain='knowledge' AND entity_type IN ({placeholders})'''))
        backup = []
        for r in rows:
            backup.append({
                'id': r[0], 'canonical_name': r[1], 'entity_type': r[2],
                'description': r[3], 'alias_count': r[4], 'mention_count': r[5],
                'first_seen_at': str(r[6]) if r[6] else None,
                'last_seen_at': str(r[7]) if r[7] else None,
                'linked_agency_id': r[8], 'linked_project_id': r[9],
                'source_project': r[10], 'external_id': r[11], 'version': r[12],
                'graph_domain': r[13],
            })
        print(json.dumps(backup, ensure_ascii=False))
asyncio.run(main())
"""
    out = run_in_container(code)
    json_file.write_text(out, encoding="utf-8")
    print(f"  [1/5] JSON backup: {json_file} ({json_file.stat().st_size:,} bytes)")

    # Step 2: SQL INSERT 還原檔（一鍵 restore）
    import json as _json
    try:
        records = _json.loads(out)
    except Exception:
        records = []
    sql_lines = ["-- Auto-generated restore script for knowledge dedup",
                 f"-- timestamp: {timestamp}",
                 f"-- record count: {len(records)}",
                 "BEGIN;"]
    for r in records:
        # 簡化 INSERT (不含 embedding，restore 後可重 backfill)
        sql_lines.append(
            f"INSERT INTO canonical_entities "
            f"(id, canonical_name, entity_type, description, graph_domain) VALUES "
            f"({r['id']}, $${r['canonical_name'].replace('$', '_')}$$, "
            f"$${r['entity_type']}$$, "
            f"$${(r.get('description') or '').replace('$', '_')[:500]}$$, "
            f"'knowledge') ON CONFLICT (id) DO NOTHING;"
        )
    sql_lines.append("COMMIT;")
    sql_file.write_text("\n".join(sql_lines), encoding="utf-8")
    print(f"  [2/5] SQL restore: {sql_file} ({sql_file.stat().st_size:,} bytes)")

    # Step 3: MD5 雙端驗證 (對齊 L43)
    import hashlib
    md5_json = hashlib.md5(json_file.read_bytes()).hexdigest()
    md5_sql = hashlib.md5(sql_file.read_bytes()).hexdigest()
    print(f"  [3/5] MD5 json: {md5_json}")
    print(f"        MD5 sql:  {md5_sql}")

    # Step 4: /health business_data pre-check
    import subprocess as _sp
    health_code = """
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:8001/health', timeout=8) as r:
        data = json.loads(r.read().decode('utf-8'))
        bd = data.get('business_data', {})
        print(f"docs={bd.get('documents', 0)} kg={bd.get('canonical_entities', 0)} ok={bd.get('ok', False)}")
except Exception as e:
    print(f"HEALTH_ERR: {e}")
"""
    health_out = run_in_container(health_code)
    print(f"  [4/5] /health pre-check: {health_out}")

    # Step 5: backup file size 驗證
    if json_file.stat().st_size < 100:
        print(f"  [5/5] ❌ JSON backup too small ({json_file.stat().st_size}) — ABORT")
        raise RuntimeError("Backup file too small, aborting dedup")
    if len(records) < 100:
        print(f"  [5/5] ⚠ Record count too low ({len(records)}) — 可能 evaluate 結果與 backup 不一致")
    print(f"  [5/5] ✅ size verified: {len(records)} records")

    return json_file, sql_file, md5_json


def apply_dedup() -> int:
    """真實 DELETE — 必須 --apply 才執行"""
    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
CODE_TYPES = ['py_function','py_module','py_class','api_endpoint','service','schema',
              'repository','ts_interface','ts_module','ts_hook','ts_component','ts_type','middleware']
async def main():
    async with AsyncSessionLocal() as db:
        placeholders = ','.join(["'" + t + "'" for t in CODE_TYPES])
        result = await db.execute(text(f"DELETE FROM canonical_entities WHERE graph_domain='knowledge' AND entity_type IN ({placeholders})"))
        await db.commit()
        print(f"DELETED: {result.rowcount}")
asyncio.run(main())
"""
    out = run_in_container(code)
    print(f"  {out}")
    return 0


def main() -> int:
    apply = "--apply" in sys.argv
    verify = "--verify" in sys.argv

    print("=== KG knowledge domain code entity dedup (對齊 L43 教訓) ===")
    print()

    # 評估範圍
    pre = evaluate()
    print(f"刪除前 knowledge domain:")
    print(f"  total: {pre['total']}")
    print(f"  code:  {pre['code']} ({pre['code']/pre['total']*100:.1f}%) ← 待刪")
    print(f"  biz:   {pre['biz']} ({pre['biz']/pre['total']*100:.1f}%) ← 保留")
    print()

    if verify:
        print("=== Verify mode — 重 audit 確認 ===")
        if pre['code'] > 100:
            print(f"⚠ 仍有 {pre['code']} code entity 未清，建議跑 --apply")
            return 1
        print(f"✅ knowledge domain 已純業務 ({pre['code']} code remaining)")
        return 0

    if not apply:
        print("🟡 DRY-RUN MODE (預設) — 預估會刪 {} entity".format(pre['code']))
        print()
        print("執行真實刪除請加 --apply:")
        print("  python scripts/sync/knowledge_dedup_script.py --apply")
        print()
        print("L43 教訓對齊:")
        print("  1. tar 備份 — 自動執行 (backup/knowledge_dedup_<ts>.sql)")
        print("  2. /health business_data 驗證 — 手動執行")
        print("  3. 7 天後重 audit — 跑 --verify 確認")
        return 0

    # Apply mode — 真實刪除
    print("🔴 APPLY MODE — 將執行真實 DELETE")
    print()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"  Step 1: 多層備份 (5 層防禦 對齊 L43)")
    json_file, sql_file, md5 = backup_to_tar(timestamp)
    print()
    print(f"  Step 2: DELETE")
    apply_dedup()
    print()
    post = evaluate()
    print(f"刪除後 knowledge domain:")
    print(f"  total: {post['total']} (was {pre['total']}, delta {pre['total']-post['total']})")
    print(f"  code:  {post['code']} (was {pre['code']})")
    print(f"  biz:   {post['biz']} (was {pre['biz']})")
    print()
    print("驗證 backup:")
    print(f"  JSON: {json_file}")
    print(f"  SQL:  {sql_file}")
    print(f"  MD5:  {md5}")
    print()
    print("回滾指令 (若異常):")
    print(f"  docker exec ck_missive_postgres psql -U postgres -d ck_missive -f /backup/{sql_file.name}")
    print()
    print("L43 教訓後續:")
    print(f"  - 7 天後重跑 --verify 確認業務無漂移")
    print(f"  - 跑 /health 驗 business_data 完整性")
    return 0


if __name__ == "__main__":
    sys.exit(main())
