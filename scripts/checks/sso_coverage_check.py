#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADR-0033 配套 — SSO 覆蓋率檢查

ADR-0033 關閉密碼登入後，所有 active user 必須至少綁定 Google 或 LINE 才能登入。
本檢查每月跑 + 部署前必跑，避免「上線後發現某帳號永久鎖死」。

關聯：
- docs/adr/0033-disable-password-authentication.md
- docs/runbooks/sso_emergency_rollback.md
- docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md

例外處理：
- alias 帳號（canonical_user_id IS NOT NULL）：
  邏輯上不靠該 email 登入（用戶會用 canonical 那邊登），不算鎖死風險
- last_login IS NULL 的帳號：
  種子/測試資料的可能性高，列出但不算 critical
- SuperUser/admin 但無 SSO：
  CRITICAL — Google/LINE 都掛時失去管理通道

Exit codes:
  0 — 全 pass，或非 strict 模式
  1 — strict mode (--ci) 且發現 CRITICAL（admin 級無 SSO）
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


async def _run() -> tuple[int, int]:
    """回傳 (warning_count, critical_count)。"""
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

    warning = 0
    critical = 0

    try:
        async with Session() as db:
            # 1) 整體統計
            result = await db.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE is_active=TRUE) AS active_total,
                    COUNT(*) FILTER (
                        WHERE is_active=TRUE
                          AND google_id IS NULL
                          AND line_user_id IS NULL
                          AND canonical_user_id IS NULL
                    ) AS canonical_no_sso,
                    COUNT(*) FILTER (
                        WHERE is_active=TRUE
                          AND google_id IS NULL
                          AND line_user_id IS NULL
                          AND canonical_user_id IS NULL
                          AND (is_admin=TRUE OR is_superuser=TRUE
                               OR role IN ('admin', 'superuser'))
                    ) AS admin_no_sso
                FROM users
            """))
            stats = result.fetchone()
            print(f"=== SSO Coverage（ADR-0033 配套）===")
            print(f"Active users (non-alias): {stats.active_total}")
            print(f"  鎖死風險（無 SSO + non-alias）: {stats.canonical_no_sso}")
            print(f"  其中 admin/superuser: {stats.admin_no_sso}  ← CRITICAL")
            print()

            # 2) 列出 admin 級鎖死帳號（CRITICAL）
            if stats.admin_no_sso > 0:
                result = await db.execute(text("""
                    SELECT id, email, full_name, role, last_login
                    FROM users
                    WHERE is_active=TRUE
                      AND google_id IS NULL
                      AND line_user_id IS NULL
                      AND canonical_user_id IS NULL
                      AND (is_admin=TRUE OR is_superuser=TRUE
                           OR role IN ('admin', 'superuser'))
                    ORDER BY id
                """))
                # 2026-08-09 措辭更正：原寫「IdP outage 時失去管理通道」會被讀成
                # 「平常沒事、只有 outage 才有風險」。實測 POST /api/auth/login
                # 回 HTTP 410「帳密登入機制已停用（ADR-0033）」——
                # **未綁 SSO 者現在就沒有任何登入方式**，不是未來式。
                print("[CRITICAL] admin 級無 SSO 帳號（**現在就已鎖死**，密碼登入已於 ADR-0033 停用）:")
                for r in result.fetchall():
                    last = r.last_login.strftime("%Y-%m-%d") if r.last_login else "never"
                    print(
                        f"  id={r.id} | {r.email} | {r.full_name} "
                        f"| role={r.role} last_login={last}"
                    )
                    critical += 1
                print()

            # 3) 列出 staff/user 級鎖死帳號（warning）
            result = await db.execute(text("""
                SELECT id, email, full_name, role, last_login
                FROM users
                WHERE is_active=TRUE
                  AND google_id IS NULL
                  AND line_user_id IS NULL
                  AND canonical_user_id IS NULL
                  AND NOT (is_admin=TRUE OR is_superuser=TRUE
                           OR role IN ('admin', 'superuser'))
                ORDER BY id
            """))
            staff_no_sso = result.fetchall()
            if staff_no_sso:
                print(f"[WARN] staff/user 級無 SSO 帳號 ({len(staff_no_sso)} 筆):")
                for r in staff_no_sso:
                    last = r.last_login.strftime("%Y-%m-%d") if r.last_login else "never"
                    note = " (likely seed/test, never logged in)" if not r.last_login else ""
                    print(
                        f"  id={r.id} | {r.email} | {r.full_name} "
                        f"| role={r.role} last_login={last}{note}"
                    )
                    warning += 1
                print()

            # 4) 結論
            if critical == 0 and warning == 0:
                print("[PASS] 全部 active user 已綁定 Google 或 LINE")
            elif critical == 0:
                print(
                    f"[WARN] {warning} 個非 admin 帳號鎖死風險"
                    "（多數為 seed/test 可忽略；建議標 is_active=FALSE）"
                )
            else:
                print(
                    f"[FAIL] {critical} 個 admin **現在就已鎖死**（不是 outage 時才有風險）。"
                    " 2026-08-09 實測：POST /api/auth/login 回 HTTP 410"
                    "「帳密登入機制已停用（ADR-0033）」→ 未綁 SSO 者沒有任何登入方式。"
                    " 處置：（1）本人用 Google/LINE 登入一次即自動綁定，或"
                    "（2）確認是廢棄帳號 → 標 is_active=FALSE（留著會讓這條告警永遠紅）。"
                )

    finally:
        await engine.dispose()

    return warning, critical


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ADR-0033 SSO Coverage Check"
    )
    parser.add_argument("--ci", action="store_true", help="critical 時 exit 1")
    args = parser.parse_args()

    try:
        warning, critical = asyncio.run(_run())
    except Exception as e:
        # 2026-08-09：跑不起來不是「沒問題」。原本回 0，於是 DB 連不上、
        # schema 改名之類的狀況會與「零風險」長得一模一樣。
        print(f"[FAIL] SSO coverage check 無法執行: {type(e).__name__}: {e}")
        return 2

    # 2026-08-09：退出碼與印出的狀態一致（L83）。
    #
    # 原本只在 `--ci` 時回 1 —— 而 `run_fitness_weekly.sh` **一律不傳旗標**
    # （2026-08-03 立的規矩：傳 --strict 會把 YELLOW 升成 RED）。
    # 於是這支印著「[FAIL] 2 個 admin 鎖死風險」卻回 0，
    # 接進 runner 後會是永遠的綠燈 —— 而它本來就沒有被任何 runner 跑過，
    # 這個缺陷因此從未顯現。
    # 三態：0=GREEN / 1=YELLOW（非 admin 風險）/ 2=RED（admin 鎖死）
    if critical > 0:
        return 2
    if warning > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
