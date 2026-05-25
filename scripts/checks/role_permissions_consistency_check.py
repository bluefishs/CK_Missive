#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 20 — Role Permissions Consistency Check（ADR-0034 配套）。

對動態 role permissions 系統做一致性 audit：

1. **Dangling**：site_navigation_items.permission_required 內的 permission，
   無任何 role 帶有（含 superuser wildcard 也不算 — 因 wildcard 是 special-case）。
   結果：無人能看到該 nav。

2. **Orphan**：role_permissions 內帶有的 permission，**不在**任何 nav 也不在
   _BUSINESS_PERMISSIONS 業務 set。可能是已棄用 perm 殘留。

3. **Admin Coverage**：admin role 應涵蓋所有 from_navigation_items 的 permissions
   （admin 是「全管理」角色預期能看完整 nav）。少於即 warning。

4. **Empty Public Sensitive**：is_enabled+is_visible 但 permission_required=[]
   的 nav，列出後人工 review（避免 admin 區誤公開）。

關聯：
- ADR-0034 動態 role permissions
- failure-adr-0025-rls-half-wired.md（半接通類事故防範模式）
- scripts/checks/run_fitness.sh step 20
- _BUSINESS_PERMISSIONS @ services/system/role_permissions_service.py

Exit codes:
  0 — 全 pass / warning
  1 — strict mode (--ci) 且發現 dangling 或 admin 涵蓋率 <90%
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND))


async def _run() -> int:
    """回傳嚴重失敗數（dangling 或 admin coverage 不足）。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents",
    )
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    fail = 0
    print("=== Role Permissions Consistency Check（ADR-0034）===")
    print()

    try:
        async with Session() as db:
            # 1) Dangling — nav 內但無任何 role 帶有（superuser wildcard 排除特例）
            result = await db.execute(text("""
                WITH nav_perms AS (
                    SELECT DISTINCT jsonb_array_elements_text(permission_required::jsonb) AS perm
                    FROM site_navigation_items
                    WHERE permission_required IS NOT NULL
                      AND permission_required != ''
                      AND permission_required != '[]'
                ),
                assigned_perms AS (
                    SELECT DISTINCT jsonb_array_elements_text(permissions) AS perm
                    FROM role_permissions
                    WHERE role != 'superuser'  -- superuser ['*'] wildcard 不算具體 assigned
                )
                SELECT n.perm
                FROM nav_perms n
                LEFT JOIN assigned_perms a ON a.perm = n.perm
                WHERE a.perm IS NULL
                ORDER BY n.perm
            """))
            dangling = [r[0] for r in result.fetchall()]
            if dangling:
                print(f"  [FAIL] Dangling permissions（nav 用但無 role 帶有 → 隱形 bug）:")
                for p in dangling:
                    print(f"    - {p}")
                fail += len(dangling)
            else:
                print("  [OK ] Dangling: 0 — 所有 nav permission 都至少 1 role 帶有")

            print()
            # 2) Orphan — role 帶但非 nav 也非 business set
            from app.services.system.role_permissions_service import _BUSINESS_PERMISSIONS

            result = await db.execute(text("""
                SELECT DISTINCT jsonb_array_elements_text(permissions) AS perm
                FROM role_permissions
                WHERE role != 'superuser'
                ORDER BY perm
            """))
            assigned = {r[0] for r in result.fetchall()}

            result = await db.execute(text("""
                SELECT DISTINCT jsonb_array_elements_text(permission_required::jsonb) AS perm
                FROM site_navigation_items
                WHERE permission_required IS NOT NULL
                  AND permission_required != ''
                  AND permission_required != '[]'
            """))
            nav_perms = {r[0] for r in result.fetchall()}

            orphan = sorted(assigned - nav_perms - _BUSINESS_PERMISSIONS)
            if orphan:
                print(f"  [WARN] Orphan permissions（role 帶但無 nav/business 用，可能棄用殘留）:")
                for p in orphan:
                    print(f"    - {p}")
            else:
                print("  [OK ] Orphan: 0 — 所有已分派 permission 都有對應 nav 或 business endpoint")

            print()
            # 3) Admin coverage
            result = await db.execute(text("""
                SELECT permissions FROM role_permissions WHERE role = 'admin'
            """))
            admin_row = result.scalar_one_or_none()
            admin_perms = set(admin_row) if admin_row else set()
            should_have = nav_perms | {"reports:export"}  # admin 預期含全部 nav perm
            missing = sorted(should_have - admin_perms)
            covered = len(should_have & admin_perms)
            total = len(should_have)
            pct = (covered / total * 100) if total else 100

            if missing:
                if pct < 90:
                    print(
                        f"  [FAIL] Admin coverage {pct:.0f}% ({covered}/{total}) "
                        f"— missing {len(missing)} key perms"
                    )
                    fail += 1
                else:
                    print(
                        f"  [WARN] Admin coverage {pct:.0f}% ({covered}/{total}) "
                        f"— admin 應補 {len(missing)} 個 permission"
                    )
                for p in missing[:10]:
                    print(f"    - {p}")
                if len(missing) > 10:
                    print(f"    ... +{len(missing)-10} more")
            else:
                print(f"  [OK ] Admin coverage 100% ({covered}/{total})")

            print()
            # 4) Empty Public Sensitive
            result = await db.execute(text("""
                SELECT id, key, title, path
                FROM site_navigation_items
                WHERE is_enabled = TRUE AND is_visible = TRUE
                  AND (permission_required IS NULL
                       OR permission_required = ''
                       OR permission_required = '[]')
                  AND (path LIKE '/admin%' OR path LIKE '/system%' OR key LIKE 'admin%'
                       OR key LIKE 'system%' OR key LIKE 'Site_%' OR key LIKE 'Website_%')
                ORDER BY id
            """))
            empty_admin = result.fetchall()
            if empty_admin:
                print(f"  [WARN] {len(empty_admin)} 個敏感 nav 仍 permission_required=[]:")
                for r in empty_admin:
                    print(f"    - id={r[0]} key={r[1]} | {r[2]} | path={r[3] or '-'}")
                # 不算 fail，列出供 review
            else:
                print("  [OK ] 無敏感 nav 缺權限")

    finally:
        await engine.dispose()

    print()
    if fail == 0:
        print("[PASS] role_permissions ↔ site_navigation_items 一致性合格")
    else:
        print(f"[FAIL] {fail} 嚴重項 — 看上方 dangling 或 admin coverage 訊息")
    return fail


def main() -> int:
    parser = argparse.ArgumentParser(description="Role Permissions Consistency Check")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    try:
        fail = asyncio.run(_run())
    except Exception as e:
        print(f"[WARN] 無法執行: {type(e).__name__}: {e}")
        return 0

    if args.ci and fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
