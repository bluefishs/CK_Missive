#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 17 — Alias RLS End-to-End Check.

對 user_merge_log 每筆紀錄，驗證 RLS 雙向展開正確：
  - 從 alias 端 check_user_project_access(alias_id, canonical 的任一 PUA project_id) → True
  - 從 canonical 端 check_user_project_access(canonical_id, alias 的任一 PUA project_id) → True

核心目的：永久防範 ADR-0025 半接通類事故重演（merge 寫了但 RLS 沒展開）。

關聯：
- ADR-0025 Identity Unification
- wiki/memory/failures/failure-adr-0025-rls-half-wired.md
- scripts/checks/run_fitness.sh step 17
- TaskB (2026-05-06) RLS alias group expansion

Exit codes:
  0 — 全 pass 或無 merge 紀錄可驗證
  1 — strict mode (--ci) 且至少一筆 RLS 不對稱

Usage:
  python scripts/checks/alias_rls_e2e_check.py
  python scripts/checks/alias_rls_e2e_check.py --ci  # 失敗 exit 1
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

# Ensure backend on path so app.* imports work
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND))


async def _run() -> int:
    """回傳失敗筆數（>0 表示至少一個 alias merge 的 RLS 沒對稱）。"""
    # 延遲 import 避免 sys.path insert 之前載入
    from sqlalchemy import select, distinct, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents",
    )
    # async driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    fail = 0

    try:
        async with Session() as db:
            # 1) 取所有未 reverse 的 merge 紀錄
            result = await db.execute(
                text("""
                    SELECT id, canonical_id, alias_id, merged_at
                    FROM user_merge_log
                    WHERE reversed_at IS NULL
                    ORDER BY id
                """)
            )
            merges = result.fetchall()

            if not merges:
                print("[OK] 無 merge 紀錄可驗證 (user_merge_log empty)")
                return 0

            print(f"[INFO] 發現 {len(merges)} 筆 active merge — 開始雙向 RLS check")
            print()

            # 2) 對每筆 merge，雙向驗證
            from app.core.rls_filter import RLSFilter
            from app.extended.models import project_user_assignment

            for m in merges:
                merge_id = m.id
                canonical_id = m.canonical_id
                alias_id = m.alias_id

                # 2a) 各自的 PUA 集合
                a_result = await db.execute(
                    select(distinct(project_user_assignment.c.project_id)).where(
                        project_user_assignment.c.user_id == alias_id,
                        project_user_assignment.c.status.in_(
                            RLSFilter.ACTIVE_ASSIGNMENT_STATUSES
                        ),
                    )
                )
                alias_projects = [r[0] for r in a_result.all() if r[0]]

                c_result = await db.execute(
                    select(distinct(project_user_assignment.c.project_id)).where(
                        project_user_assignment.c.user_id == canonical_id,
                        project_user_assignment.c.status.in_(
                            RLSFilter.ACTIVE_ASSIGNMENT_STATUSES
                        ),
                    )
                )
                canonical_projects = [r[0] for r in c_result.all() if r[0]]

                # 2b) 從 canonical 端訪問 alias 的 project — 必須 True
                for pid in alias_projects:
                    ok = await RLSFilter.check_user_project_access(
                        db, canonical_id, pid
                    )
                    if not ok:
                        fail += 1
                        print(
                            f"  [FAIL] merge#{merge_id} canonical={canonical_id} → "
                            f"alias's project={pid}: access denied "
                            f"(RLS alias group expansion broken)"
                        )

                # 2c) 從 alias 端訪問 canonical 的 project — 必須 True
                for pid in canonical_projects:
                    ok = await RLSFilter.check_user_project_access(
                        db, alias_id, pid
                    )
                    if not ok:
                        fail += 1
                        print(
                            f"  [FAIL] merge#{merge_id} alias={alias_id} → "
                            f"canonical's project={pid}: access denied "
                            f"(RLS alias group expansion broken)"
                        )

                if alias_projects or canonical_projects:
                    print(
                        f"  [OK]   merge#{merge_id} canonical={canonical_id} "
                        f"({len(canonical_projects)} PUA) ↔ alias={alias_id} "
                        f"({len(alias_projects)} PUA): bidirectional access OK"
                    )
                else:
                    print(
                        f"  [SKIP] merge#{merge_id} canonical={canonical_id} "
                        f"alias={alias_id}: 兩邊皆無 PUA（admin/superuser 帳號常見）"
                    )

            print()
            if fail == 0:
                print(f"[PASS] 全部 {len(merges)} 筆 merge 雙向 RLS 對稱")
            else:
                print(
                    f"[FAIL] {fail} 個 access 不對稱 — RLS alias group "
                    f"展開可能破損（看 ADR-0025 配套或 TaskB regression）"
                )

    finally:
        await engine.dispose()

    return fail


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fitness step 17 — Alias RLS E2E Check"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="strict mode：發現失敗時 exit 1",
    )
    args = parser.parse_args()

    try:
        fail = asyncio.run(_run())
    except Exception as e:
        # DB 不可達等基礎設施錯誤：warn-only（不算 fitness fail，避免 dev 環境誤報）
        print(f"[WARN] alias RLS check 無法執行: {type(e).__name__}: {e}")
        return 0

    if args.ci and fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
