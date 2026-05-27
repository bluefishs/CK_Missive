#!/usr/bin/env python3
"""tender_freshness_audit.py — fitness step 51

偵測政府標案 tender 資料源 silent dormant（v6.12 P3 forward-looking）。

風險背景（2026-05-27 P0-1 揭發）：
- TenderRecord 兩 source：ezbid（即時補充）+ pcc（權威）
- PCC scraper 程式存在但 scheduler.py 缺 cron → 自 2026-04-08 起 50 天 silent dormant
- 業務面：ezbid 單軌支撐，若 ezbid 也掛 → 全業務 silent fail
- 同 L48 family — silent dormant + missing audit enforcement

判定邏輯：
1. 連 DB 取 tender_records per source MAX(announce_date)
2. 計算 days_since_last per source
3. 各 source 嚴重度：
   - RED：超過 7 天無新資料
   - YELLOW：3-7 天無新資料
   - GREEN：< 3 天
4. 整體嚴重度 = MAX(各 source)
5. 若 DB 連不上 → YELLOW（無法判定）

Usage:
    python scripts/checks/tender_freshness_audit.py [--strict] [--days N]

Exit codes:
    0 = green (all sources fresh)
    1 = yellow (some source 3-7 days stale)
    2 = red (any source >7 days stale)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _get_db_url() -> str:
    """Build sync DB URL from .env."""
    try:
        from dotenv import load_dotenv
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_HOST_PORT", os.getenv("POSTGRES_PORT", "5434"))
    db_user = os.getenv("POSTGRES_USER", "ck_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "ck_password_2024")
    db_name = os.getenv("POSTGRES_DB", "ck_documents")
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def _query_source_freshness() -> list[dict] | None:
    """Query DB for per-source MAX(announce_date) + COUNT."""
    try:
        import psycopg2
    except ImportError:
        try:
            import psycopg2  # type: ignore
        except Exception:
            return None

    try:
        conn = psycopg2.connect(_get_db_url(), connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source, MAX(announce_date), COUNT(*)
                FROM tender_records
                GROUP BY source
                ORDER BY source
            """)
            rows = cur.fetchall()
        conn.close()
        return [
            {"source": r[0], "latest": r[1], "count": int(r[2])}
            for r in rows
        ]
    except Exception as e:
        print(f"  ⚠ DB query failed: {e}")
        return None


def _classify_source(days_since: int) -> tuple[str, str]:
    if days_since > 7:
        return "RED", f"{days_since} days stale (>7 day threshold)"
    if days_since >= 3:
        return "YELLOW", f"{days_since} days stale (3-7 day window)"
    return "GREEN", f"{days_since} days ago (fresh)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    parser.add_argument("--days", type=int, default=7, help="RED threshold days (default 7)")
    args = parser.parse_args()

    print("=" * 60)
    print("Tender source freshness audit (v6.12 P3 — L48 family)")
    print("v1.0 / detect silent dormant tender scrapers")
    print("=" * 60)

    rows = _query_source_freshness()
    if rows is None:
        print("\n  ⚪ unable to query DB — YELLOW (cannot judge)")
        return 1

    if not rows:
        print("\n  🔴 tender_records 0 rows — RED (no data at all)")
        return 2

    overall = "GREEN"
    indicator_map = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}
    now = datetime.now()

    for r in rows:
        source = r["source"]
        latest = r["latest"]
        count = r["count"]
        if latest is None:
            sev, reason = "RED", "no announce_date data"
        else:
            # latest may be date or datetime; normalize to date for diff
            if isinstance(latest, datetime):
                if latest.tzinfo:
                    latest_d = latest.replace(tzinfo=None).date()
                else:
                    latest_d = latest.date()
            elif isinstance(latest, date):
                latest_d = latest
            else:
                latest_d = None
            if latest_d is None:
                sev, reason = "RED", f"unparseable announce_date type {type(latest).__name__}"
            else:
                days_since = (now.date() - latest_d).days
                sev, reason = _classify_source(days_since)

        print(f"\n  source={source}")
        print(f"    latest: {latest}")
        print(f"    count:  {count:,}")
        print(f"    {indicator_map[sev]} {sev}: {reason}")

        # Escalate overall
        if sev == "RED":
            overall = "RED"
        elif sev == "YELLOW" and overall == "GREEN":
            overall = "YELLOW"

    print(f"\n  Overall: {indicator_map[overall]} {overall}")

    if overall == "RED":
        print("\n💡 修法建議（tender source silent dormant）：")
        print("  1. 確認對應 scraper cron job 在 backend/app/core/scheduler.py 有 add_job")
        print("     `grep -E 'pcc_today_scrape|ezbid_cache_refresh' backend/app/core/scheduler.py`")
        print("  2. 確認 scraper 抓取程式碼仍可運作 — 手動跑測試")
        print("     `python -c 'from app.services.tender.pcc_today_scraper import PccTodayScraper; ...'`")
        print("  3. 確認對端站台沒改路徑 / 加 anti-bot 防護")
        print("  4. 看 backend log 抓 scraper 失敗錯誤訊息")
        print("  5. 若是長期 dormant，補 Prometheus alert（tender_freshness_days_stale > 3 持續 6h）")
    elif overall == "YELLOW":
        print("\n💡 informational：")
        print("  - 接近 stale 邊界 — 觀察 24h 內是否 cron 跑了")
        print("  - 若連續 yellow 3 天 → 升 P1 處理")

    if overall == "RED":
        return 2
    if overall == "YELLOW" and args.strict:
        return 2
    if overall == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
