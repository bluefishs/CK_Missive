"""Dialogue Learning Coverage Audit — 對話學習真實覆蓋率（2026-06-12）

owner：「重點要真活」+「強化對話學習透過 LINE 或坤哥 chat」。
揭發病灶：對話學習閉環(pattern_extract→crystal)機器真活，但近 7 日 agent_query_traces
**100% synthetic baseline 注入、0 筆真實對話** → 學的是罐頭測試題、非真實使用 → 假真活。

此 audit 區分 synthetic（query_id `synthetic-*`）vs real（owner 經坤哥 chat/LINE 真問），
回報真實覆蓋率 + 各管道分佈，讓「對話學習是否扎根真實」可持續監看。

- RED    : 近 N 日 real 對話 = 0（學習 100% synthetic 空轉）
- YELLOW : real 佔比 < 門檻（synthetic 主導）
- 管道分佈：web(坤哥 chat) / line / hermes / 其他 → 指出強化入口

需容器內跑（DB）。Usage: python /app/scripts/checks/dialogue_learning_coverage_audit.py [--days 7] [--strict]
"""
from __future__ import annotations

# cp950 host robustness (L49.8): printing CJK to Windows terminal raises UnicodeEncodeError
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import os
import sys

REAL_RATIO_THRESHOLD = 0.10  # real 佔比 < 10% → YELLOW


def main(days: int = 7, strict: bool = False) -> int:
    try:
        import psycopg2  # type: ignore
    except Exception:
        print("[SKIP] psycopg2 不可用（host）— 須容器內跑")
        return 0
    url = (os.environ.get("DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[SKIP] 無 DATABASE_URL")
        return 0
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            f"""SELECT
                  COUNT(*) FILTER (WHERE query_id LIKE 'synthetic%%') AS synthetic,
                  COUNT(*) FILTER (WHERE query_id NOT LIKE 'synthetic%%') AS real,
                  COUNT(*) AS total
                FROM agent_query_traces
                WHERE created_at > NOW() - INTERVAL '{int(days)} days'""")
        synthetic, real, total = cur.fetchone()
        cur.close(); conn.close()
    except Exception as e:
        print(f"[SKIP] DB: {e}")
        return 0

    ratio = (real / total * 100) if total else 0
    print("=== Dialogue Learning Coverage Audit（對話學習真實覆蓋率）===")
    print(f"  近 {days} 日 agent 對話: {total} | synthetic(罐頭注入) {synthetic} | "
          f"real(真實對話) {real} ({ratio:.1f}%)\n")

    if total == 0:
        print("Status: INFO（無對話）")
        return 0

    if real == 0:
        status = "RED"
        print("[RED] 真實對話 = 0 → 對話學習 100% 在 synthetic baseline 空轉（機器真活但非扎根真實使用）")
        print("  → 強化入口：坤哥 chat(web /kunge ChatTab, 低摩擦、owner 已登入) 或 LINE(行動觸及、需 Hermes 鏈)")
    elif ratio < REAL_RATIO_THRESHOLD * 100:
        status = "YELLOW"
        print(f"[YELLOW] real 佔比 {ratio:.1f}% < {REAL_RATIO_THRESHOLD*100:.0f}% → synthetic 主導，真實對話偏少")
    else:
        status = "GREEN"
        print(f"[GREEN] real 佔比 {ratio:.1f}% — 對話學習扎根真實使用")

    print(f"\nStatus: {status}")
    if status == "RED" and strict:
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(days=args.days, strict=args.strict))
