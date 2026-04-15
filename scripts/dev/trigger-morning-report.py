"""一次性手動觸發晨報生成 + 推送（驗證端到端）

使用：
    cd backend && python ../scripts/dev/trigger-morning-report.py

效果：
- 跑 MorningReportService.generate_summary()
- 推送至 TELEGRAM_ADMIN_CHAT_ID
- 印出推送結果與摘要前 300 字
"""
import asyncio
import os
import sys
from pathlib import Path

# Windows console UTF-8 (避免 emoji 觸發 cp950 編碼錯誤)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 確保 backend/ 在 sys.path 第一順位（跨 cwd 執行也能 import app）
HERE = Path(__file__).resolve()
BACKEND = HERE.parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# 載入 .env
try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parents[2] / ".env")
except Exception:
    pass


async def main() -> int:
    from app.db.database import async_session_maker
    from app.services.ai.domain.morning_report_service import MorningReportService

    print("[1/3] 生成晨報內容…", flush=True)
    async with async_session_maker() as db:
        svc = MorningReportService(db)
        summary = await svc.generate_summary()

    print("\n--- 摘要前 600 字 ---")
    print(summary[:600])
    print("--- ... ---\n")

    print("[2/3] 推送至 Telegram…", flush=True)
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not chat_id:
        print("✗ TELEGRAM_ADMIN_CHAT_ID 未設定")
        return 1

    from app.services.telegram_bot_service import get_telegram_bot_service
    tg = get_telegram_bot_service()
    if not tg.enabled:
        print("✗ Telegram bot 未啟用 (TELEGRAM_BOT_ENABLED=false)")
        return 1

    # 加 dry-run 標記避免被當正式晨報
    confirm_msg = (
        "✅ 晨報機制端對端驗證\n"
        "（手動觸發 — 確認 6 維度預警組裝正確）\n\n"
        + summary
    )
    try:
        ok = await tg.send_message(int(chat_id), confirm_msg)
    except Exception as e:
        print(f"✗ 推送失敗: {e}")
        return 1

    if ok:
        print(f"[3/3] ✓ 推送成功 → chat_id={chat_id[:4]}***")
        print(f"訊息長度: {len(confirm_msg)} 字")
        return 0
    else:
        print("✗ 推送失敗（API 回 false）")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
