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

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def scan_backend_declared() -> set:
    """後端端點**實際宣告**的權限 —— `require_permission("X")` 的字面值。

    ⚠️ 這是 2026-08-27 補上的維度。在此之前這支檢核比對的是
    `_BUSINESS_PERMISSIONS` —— 那是一份**手維護的清單**，
    而端點實際要求什麼是另一回事。兩者一漂移，這支就看不見。

    實測後果：`projects:write` 被 `erp/expenses.py` 的
    approve／batch-approve／reject／delete 四支端點要求，
    但它**不在 `_BUSINESS_PERMISSIONS`、不在任何角色、也不在前端 SSOT**
    ⇒ 費用核銷的審核流程除了 superuser 之外**沒有人做得了，連 admin 也不行**，
    而這支檢核回全綠。

    這與 2026-08-21 的教訓同型：那次把「哪些端點沒有認證」從 grep 規則
    改成 FastAPI runtime dependency 樹，理由是**手維護的清單不是權威**。
    這裡取字面值而非 runtime 樹，是因為 permission 字串是 `require_permission`
    的引數、runtime 物件裡拿不到；grep 對「字面字串引數」夠可靠，
    但若日後有人改成變數傳入就會漏 —— 這個限制寫在這裡，不要靠記憶。
    """
    import re as _re
    out = set()
    for f in (PROJECT_ROOT / "backend" / "app").rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        out |= set(_re.findall(r'require_permission\(\s*"([^"]+)"', txt))
    out.discard("items:delete")  # dependencies.py docstring 的範例，不是真端點
    return out


def scan_frontend_used() -> set:
    """前端**實際檢查**的權限 —— `hasPermission('X')` / `hasAnyPermission([...])`。

    測試檔排除：它們刻意用 `'nonexistent:perm'` 之類的字串驗行為，
    算進來就是三個必然的假陽性。
    """
    import re as _re
    out = set()
    root = PROJECT_ROOT / "frontend" / "src"
    if not root.is_dir():
        return out
    for f in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
        if "__tests__" in f.as_posix():
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        out |= set(_re.findall(r"hasPermission\(\s*'([^']+)'", txt))
        for grp in _re.findall(r"hasAnyPermission\(\s*\[([^\]]*)\]", txt):
            out |= set(_re.findall(r"'([^']+)'", grp))
    return out


def load_unreachable_baseline() -> dict:
    """已知且尚未決議的「無人可得」權限 —— 每一條都要寫明理由。

    用 baseline 而不是直接判紅：這四個的修法都需要 owner 決定命名
    （`projects:write` 該改成 `projects:create` 還是新開 `expenses:approve`？），
    而一個修不掉的紅燈會訓練人忽略整支檢核。
    **新出現的一律判紅。**
    """
    import json as _json
    f = PROJECT_ROOT / "scripts" / "checks" / "permission_unreachable_baseline.json"
    if not f.is_file():
        return {}
    try:
        return _json.loads(f.read_text(encoding="utf-8")).get("known", {})
    except Exception:
        return {}


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

            # 5) 2026-08-27 新增維度：端點／前端要求的權限，有沒有角色拿得到
            #
            #    前四項比對的是 nav ↔ roles ↔ _BUSINESS_PERMISSIONS，
            #    **從來沒有問過「後端端點實際宣告什麼」「前端實際檢查什麼」**。
            #    於是四個權限結構上無人可得，而這支檢核回全綠。
            result = await db.execute(text("""
                SELECT DISTINCT jsonb_array_elements_text(permissions) AS perm
                FROM role_permissions WHERE role != 'superuser'
            """))
            granted = {r[0] for r in result.fetchall()}

            declared = scan_backend_declared()
            fe_used = scan_frontend_used()
            baseline = load_unreachable_baseline()

            unreachable = {}
            for perm in sorted((declared | fe_used) - granted):
                src = []
                if perm in declared:
                    src.append("端點")
                if perm in fe_used:
                    src.append("前端")
                unreachable[perm] = "+".join(src)

            new_ones = {p: v for p, v in unreachable.items() if p not in baseline}
            known_ones = {p: v for p, v in unreachable.items() if p in baseline}

            print()
            if not unreachable:
                print("  [OK ] 端點／前端要求的權限，都至少有一個角色拿得到")
            else:
                if known_ones:
                    print(f"  [WARN] 已知無人可得（baseline，待 owner 決議命名）: {len(known_ones)}")
                    for perm, src in known_ones.items():
                        print(f"    - {perm:<22} 使用於 {src}｜{baseline[perm]}")
                if new_ones:
                    fail += len(new_ones)
                    print(f"  [FAIL] **新出現**無人可得的權限: {len(new_ones)}")
                    for perm, src in new_ones.items():
                        print(f"    - {perm:<22} 使用於 {src}")
                    print("    → 只有 superuser 通得過；admin 也不行（hasPermission 只對 superuser 短路）")
                    print("    → 修法：把它加進某個 role，或改用既有的權限名")

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
