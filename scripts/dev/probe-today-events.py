"""探測今日事件 — 找出晨報為何漏抓的真實原因"""
import asyncio
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parents[2] / ".env")
except Exception:
    pass


async def main():
    from datetime import date, timedelta
    from sqlalchemy import text
    from app.db.database import async_session_maker

    today = date.today()
    week = today + timedelta(days=7)

    async with async_session_maker() as db:
        print(f"=== 今日 {today} / 一週後 {week} ===\n")

        # 1. document_calendar_events 全表概況
        print("[1] document_calendar_events 全表 event_type 分佈：")
        r = await db.execute(text(
            "SELECT event_type, COUNT(*) FROM document_calendar_events GROUP BY event_type ORDER BY 2 DESC"
        ))
        for row in r.all():
            print(f"  {row[0] or '(NULL)'}: {row[1]}")

        # 2. 今日 ~ 一週的所有事件（不過濾 type）
        print("\n[2] 今日~一週內所有事件（無論 type / status）：")
        r = await db.execute(text("""
            SELECT id, title, event_type, status, start_date, end_date, all_day, location
            FROM document_calendar_events
            WHERE DATE(start_date) BETWEEN :a AND :b
            ORDER BY start_date
            LIMIT 30
        """), {"a": today, "b": week})
        rows = r.all()
        if not rows:
            print("  (0 筆)")
        for row in rows:
            print(f"  id={row[0]} type={row[2]} status={row[3]} start={row[4]} all_day={row[6]}")
            print(f"    title={row[1]}")
            print(f"    location={row[7]}")

        # 3. 今日（DATE(start) = today）
        print(f"\n[3] 今日 ({today}) 事件：")
        r = await db.execute(text("""
            SELECT id, title, event_type, status, start_date
            FROM document_calendar_events
            WHERE DATE(start_date) = :today
            ORDER BY start_date
        """), {"today": today})
        rows = r.all()
        if not rows:
            print("  (0 筆) — 表內沒有 start_date = 今日 的記錄")
        for row in rows:
            print(f"  id={row[0]} type={row[2]} status={row[3]} start={row[4]}")
            print(f"    title={row[1]}")

        # 4. 是否還有別的事件表？
        print("\n[4] DB 內有 'event' 字樣的表：")
        r = await db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_name ILIKE '%event%'
        """))
        for row in r.all():
            print(f"  - {row[0]}")

        # 5. 是否 events 表（非 document_）
        try:
            r = await db.execute(text("SELECT COUNT(*) FROM events"))
            print(f"\n[5] events 表筆數: {r.scalar()}")
            r = await db.execute(text("""
                SELECT id, title, event_type, start_date FROM events
                WHERE DATE(start_date) BETWEEN :a AND :b LIMIT 10
            """), {"a": today, "b": week})
            for row in r.all():
                print(f"  id={row[0]} type={row[2]} start={row[3]}  title={row[1]}")
        except Exception as e:
            print(f"\n[5] events 表不存在或欄位不同: {e}")

        # 6. 主旨/標題含「會議」「開會」「會勘」最新 10 筆（任何表）
        print("\n[6] document_calendar_events 標題含『會議/開會/會勘』最新 10 筆：")
        r = await db.execute(text("""
            SELECT id, title, event_type, status, start_date
            FROM document_calendar_events
            WHERE title LIKE '%會議%' OR title LIKE '%開會%' OR title LIKE '%會勘%'
            ORDER BY start_date DESC
            LIMIT 10
        """))
        for row in r.all():
            print(f"  id={row[0]} type={row[2]} status={row[3]} start={row[4]}")
            print(f"    title={row[1]}")


if __name__ == "__main__":
    asyncio.run(main())
