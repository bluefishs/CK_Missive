"""驗證 _get_upcoming_meetings 新 SQL 是否實際抓到 review 含會議字樣的事件"""
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
sys.path.insert(0, str(BACKEND))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parents[2] / ".env")
except Exception:
    pass


async def main():
    from datetime import date, timedelta
    from app.db.database import async_session_maker
    from app.services.ai.domain.morning_report_service import MorningReportService

    today = date.today()
    week = today + timedelta(days=7)
    async with async_session_maker() as db:
        svc = MorningReportService(db)
        m = await svc._get_upcoming_meetings(today, week)
        sv = await svc._get_upcoming_site_visits(today, week)
        mc = await svc._get_missing_calendar_events(today)

    print(f"=== upcoming_meetings: count={m['count']} ===")
    for x in m.get("items", []):
        print(f"  days_left={x['days_left']} time_str={x['time_str']}")
        print(f"    title={x['title'][:80]}")
    print(f"\n=== upcoming_site_visits: count={sv['count']} ===")
    for x in sv.get("items", []):
        print(f"  days_left={x['days_left']} src={x.get('source')} time_str={x['time_str']}")
        print(f"    title={x['title'][:80]}")
    print(f"\n=== missing_calendar_events: count={mc['count']} ===")
    for x in mc.get("items", []):
        print(f"  category={x['category']} days_ago={x['days_ago']}")
        print(f"    {x['doc_number']}  {x['subject'][:80]}")


if __name__ == "__main__":
    asyncio.run(main())
