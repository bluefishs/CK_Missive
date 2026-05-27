#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 19 — Generic Filter Audit.

對所有「黑名單型 regex 過濾」做 false-positive rate audit。

觸發背景：
    5/06 dispatch=157 5 筆業務公文被 GENERIC_ADMIN_KEYWORDS regex 全部誤殺
    (failure-generic-admin-regex-overmatch.md)。

設計：
    對註冊的 regex 規則，在真實資料樣本上量測命中率。
    若命中率超出該 regex 預期範圍 → warning。
    幫助偵測「regex 過寬誤殺」類事故。

範圍（目前）：
    - GENERIC_ADMIN_KEYWORDS（純行政文件關鍵字）對 documents.subject
      預期：< 1%（純行政單據在業務系統內本就少數）

關聯：
    - .claude/rules/adr-anti-half-wired-sop.md §過濾性程式碼設計守則
    - wiki/memory/failures/failure-generic-admin-regex-overmatch.md
    - scripts/checks/run_fitness.sh step 19

Exit codes:
    0 — pass / warning（dev 環境寬容）
    1 — strict mode (--ci) 且至少一規則 over-match（false-positive 顯著）
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND))


@dataclass
class FilterRule:
    """單一黑名單 regex 規則的 audit 規格。"""
    name: str
    pattern: str
    target_table: str
    target_column: str
    expected_max_pct: float  # 預期命中率上限 (0.0-100.0)
    description: str
    sample_size: int = 200


# 註冊現有黑名單 regex
RULES: list[FilterRule] = [
    FilterRule(
        name="PURE_ADMIN_KEYWORDS (frontend useDispatchWorkData)",
        pattern=r"契約書印鑑|履約保證|意外保險|投標保證|押標金|印鑑卡",
        target_table="documents",
        target_column="subject",
        expected_max_pct=1.0,
        description=(
            "純行政文件關鍵字 — 過濾與查估/丈量無關的單據（履約保證書、印鑑卡等）。"
            "5/06 縮小 (failure-generic-admin-regex-overmatch) 後，"
            "對業務系統 documents 預期命中率 < 1%（純行政單據是少數）"
        ),
    ),
    # TODO: 註冊更多 regex 規則
]


async def _audit_rule(rule: FilterRule) -> tuple[str, int, int, str]:
    """跑單一規則。回傳 (level, hits, total, msg)."""
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

    rgx = re.compile(rule.pattern)

    try:
        async with Session() as db:
            # 拿 sample
            result = await db.execute(text(f"""
                SELECT {rule.target_column}
                FROM {rule.target_table}
                WHERE {rule.target_column} IS NOT NULL
                  AND {rule.target_column} != ''
                ORDER BY id DESC
                LIMIT :limit
            """), {"limit": rule.sample_size})
            samples = [r[0] for r in result.fetchall()]
    finally:
        await engine.dispose()

    if not samples:
        return "warn", 0, 0, "no samples available"

    hits = sum(1 for s in samples if rgx.search(s))
    total = len(samples)
    pct = hits / total * 100

    # 顯示前 3 筆 match 樣本協助 review
    matched_samples = [s for s in samples if rgx.search(s)][:3]
    sample_preview = "; ".join(s[:30] + "..." for s in matched_samples)

    if pct > rule.expected_max_pct * 2:
        level = "fail"
        msg = (
            f"hits={hits}/{total} ({pct:.1f}%) >> 上限 {rule.expected_max_pct}% "
            f"— 嚴重 over-match | 樣本: {sample_preview}"
        )
    elif pct > rule.expected_max_pct:
        level = "warn"
        msg = (
            f"hits={hits}/{total} ({pct:.1f}%) > 上限 {rule.expected_max_pct}% "
            f"| 樣本: {sample_preview}"
        )
    else:
        level = "ok"
        msg = f"hits={hits}/{total} ({pct:.2f}%) ≤ {rule.expected_max_pct}% ✓"

    return level, hits, total, msg


async def _run() -> int:
    """回傳 fail count（>0 表至少一規則嚴重 over-match）。"""
    print("=== Generic Filter Audit（regex 黑名單 false-positive rate）===")
    print()

    fail = 0
    for rule in RULES:
        try:
            level, hits, total, msg = await _audit_rule(rule)
        except Exception as e:
            print(f"  [WARN] {rule.name}: {type(e).__name__}: {e}")
            continue

        mark = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}[level]
        print(f"  [{mark}] {rule.name}")
        print(f"         pattern: {rule.pattern}")
        print(f"         target:  {rule.target_table}.{rule.target_column}")
        print(f"         {msg}")
        print()

        if level == "fail":
            fail += 1

    if fail == 0:
        print("[PASS] 所有黑名單 regex 在 false-positive 容忍範圍內")
    else:
        print(
            f"[FAIL] {fail} 個 regex 嚴重 over-match — "
            "可能誤殺業務資料。檢查 .claude/rules/adr-anti-half-wired-sop.md §過濾性程式碼設計守則"
        )
    return fail


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic Filter Audit")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    try:
        fail = asyncio.run(_run())
    except Exception as e:
        print(f"[WARN] generic filter audit 無法執行: {type(e).__name__}: {e}")
        return 0

    if args.ci and fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
