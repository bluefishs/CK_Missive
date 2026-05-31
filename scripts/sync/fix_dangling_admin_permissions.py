"""Fix Dangling Admin Permissions (v6.13, 2026-05-31)

對齊 owner「逐步辦理 + 真活 + 備份安全」訴求

揭發背景:
- 5/31 fitness step Dangling permissions 8 個真實業務 bug
- role_permissions_consistency_check.py 真實揭發:
  nav 用了這 8 permission 但 admin role 沒有
- 隱形 bug — admin 用戶實際上看不到對應 nav items

8 dangling permissions (admin role 應有但缺):
- admin:settings / admin:site_management / admin:users
  → 管理員設定/網站管理/用戶管理 (admin 必有)
- reports:erp:view / reports:finance:view / reports:stats:view / reports:view
  → ERP/財務/統計/總報表 (admin 必有)
- system_docs:read
  → 系統文件閱讀 (admin 已有 create/edit/delete 但缺 read,自相矛盾)

對齊 owner 安全:
- 純加 permission to admin role (只擴不減)
- dry-run 預設,--apply 才執行
- 寫前 backup role_permissions to JSON
- 對齊 alembic migration 模式

執行:
  python scripts/sync/fix_dangling_admin_permissions.py            # dry-run
  python scripts/sync/fix_dangling_admin_permissions.py --apply    # 真實 UPDATE
  python scripts/sync/fix_dangling_admin_permissions.py --rollback # 還原 backup
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path


DANGLING_PERMISSIONS = [
    "admin:settings",
    "admin:site_management",
    "admin:users",
    "reports:erp:view",
    "reports:finance:view",
    "reports:stats:view",
    "reports:view",
    "system_docs:read",
]


def get_backup_dir() -> Path:
    """v6.13 對齊 LOGS_DIR / backup 路徑 (L52 family)"""
    backup_root = Path(os.getenv("CK_BACKUP_DIR", "/app/backups"))
    backup_dir = backup_root / "role_permissions"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


async def fetch_current_admin_perms():
    sys.path.insert(0, "/app")
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        r = await db.execute(text("SELECT permissions FROM role_permissions WHERE role='admin'"))
        return r.scalar() or []


async def backup_role_permissions() -> Path:
    """JSON backup before any change"""
    sys.path.insert(0, "/app")
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        r = await db.execute(text("SELECT role, permissions FROM role_permissions ORDER BY role"))
        data = {row[0]: row[1] for row in r.fetchall()}

    backup_dir = get_backup_dir()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"role_permissions_{ts}.json"
    backup_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_path


async def apply_fix(dry_run: bool = True) -> None:
    sys.path.insert(0, "/app")
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    current = await fetch_current_admin_perms()
    print(f"當前 admin permissions: {len(current)} 個")

    # 計算 to_add (避免重複)
    to_add = [p for p in DANGLING_PERMISSIONS if p not in current]
    already_have = [p for p in DANGLING_PERMISSIONS if p in current]

    print(f"待 INSERT: {len(to_add)}")
    for p in to_add:
        print(f"  + {p}")
    if already_have:
        print(f"已有 (skip): {len(already_have)}")
        for p in already_have:
            print(f"  ✓ {p}")

    if not to_add:
        print("✅ 無需修法 (admin 已有全部)")
        return

    if dry_run:
        print()
        print("🟡 DRY-RUN MODE")
        print("SQL preview:")
        new_list = list(current) + to_add
        print(f"  UPDATE role_permissions SET permissions = '{json.dumps(new_list, ensure_ascii=False)}'::jsonb")
        print(f"  WHERE role='admin';")
        print()
        print("執行真實: python scripts/sync/fix_dangling_admin_permissions.py --apply")
        print("回滾: --rollback (還原最新 backup JSON)")
        return

    # APPLY
    print()
    print("🟢 APPLY MODE — 真實 UPDATE")
    backup_path = await backup_role_permissions()
    print(f"backup: {backup_path}")

    async with AsyncSessionLocal() as db:
        new_list = list(current) + to_add
        await db.execute(
            text("UPDATE role_permissions SET permissions = CAST(:p AS jsonb) WHERE role='admin'"),
            {"p": json.dumps(new_list, ensure_ascii=False)},
        )
        await db.commit()

    # 驗證
    after = await fetch_current_admin_perms()
    print(f"修後 admin permissions: {len(after)} 個 (delta +{len(after) - len(current)})")
    for p in DANGLING_PERMISSIONS:
        if p in after:
            print(f"  ✓ {p}")


async def rollback() -> int:
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("role_permissions_*.json"), reverse=True)
    if not backups:
        print("❌ 無 backup 可還原")
        return 1
    latest = backups[0]
    print(f"還原自: {latest}")
    data = json.loads(latest.read_text(encoding="utf-8"))

    sys.path.insert(0, "/app")
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        for role, perms in data.items():
            await db.execute(
                text("UPDATE role_permissions SET permissions = CAST(:p AS jsonb) WHERE role=:r"),
                {"p": json.dumps(perms, ensure_ascii=False), "r": role},
            )
        await db.commit()
    print(f"✅ 已還原 {len(data)} roles 自 {latest.name}")
    return 0


async def main_async() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    print("=== Fix Dangling Admin Permissions (v6.13, 2026-05-31) ===")
    print("對齊 owner「備份安全」+ 純加可逆")
    print()

    if args.rollback:
        return await rollback()

    await apply_fix(dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
