"""手動觸發晨報生成 + snapshot 留存 + 推送 + delivery log（端到端驗證）

使用：
    cd backend && python ../scripts/dev/trigger-morning-report.py
    cd backend && python ../scripts/dev/trigger-morning-report.py --preview  # 僅預覽不推送

走新架構：generate_report → save_snapshot → push + log
"""
import asyncio
import os
import sys
from pathlib import Path

# Windows console UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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

PREVIEW_ONLY = "--preview" in sys.argv


async def main() -> int:
    from app.db.database import async_session_maker
    from app.services.ai.domain.morning_report_service import MorningReportService
    from app.services.ai.domain.morning_report_delivery import (
        log_delivery, save_snapshot, today_taipei,
    )

    report_date = today_taipei()
    MAX_MSG_LEN = 4500

    # Step 1: Generate
    print("[1/4] 生成晨報內容…", flush=True)
    async with async_session_maker() as db:
        svc = MorningReportService(db)
        data = await svc.generate_report()
        summary = await svc.generate_summary_from_data(data)

    if len(summary) > MAX_MSG_LEN:
        summary = summary[:MAX_MSG_LEN] + "\n\n⋯ 完整版請查閱系統"

    print(f"\n--- 摘要（{len(summary)} 字）---")
    print(summary[:600])
    if len(summary) > 600:
        print("--- ... ---")
    print()

    # Step 2: Snapshot
    print("[2/4] 儲存 snapshot…", flush=True)
    sections_count = sum(
        1 for v in data.values()
        if isinstance(v, dict) and (
            v.get("count", 0) or v.get("week_count", 0) or v.get("dispatch_count", 0)
        )
    )
    async with async_session_maker() as db:
        await save_snapshot(
            db, report_date=report_date, sections_json=data,
            summary_text=summary, sections_count=sections_count,
        )
    print(f"  ✓ snapshot saved (date={report_date})")

    if PREVIEW_ONLY:
        print("\n[--preview] 僅預覽，不推送")
        return 0

    # Step 3: Push to Telegram
    print("[3/4] 推送至 Telegram…", flush=True)
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not chat_id:
        print("  ✗ TELEGRAM_ADMIN_CHAT_ID 未設定")
        return 1

    from app.services.telegram_bot_service import get_telegram_bot_service
    tg = get_telegram_bot_service()
    if not tg.enabled:
        print("  ✗ Telegram bot 未啟用")
        return 1

    confirm_msg = f"✅ 晨報端對端驗證（手動觸發）\n\n{summary}"
    try:
        ok = await tg.send_message(int(chat_id), confirm_msg, parse_mode="")
    except Exception as e:
        print(f"  ✗ 推送失敗: {e}")
        ok = False

    # Step 4: Delivery log
    print("[4/4] 寫入 delivery log…", flush=True)
    async with async_session_maker() as db:
        await log_delivery(
            db, report_date=report_date, channel="telegram",
            recipient=str(chat_id),
            status="success" if ok else "failed",
            summary_length=len(summary),
            sections_count=sections_count,
            trigger_source="manual",
        )

    if ok:
        print(f"  ✓ 推送成功 → chat_id={chat_id[:4]}***")
        print(f"  訊息長度: {len(confirm_msg)} 字")
        return 0
    else:
        print("  ✗ 推送失敗")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
