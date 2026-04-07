"""
標案訂閱排程器

每日 3 次檢查所有啟用的訂閱，比對新公告數量變化，
有新增時發送系統通知（+LINE 推播）。

用法: 在 startup.py 中以 APScheduler 排程，或手動觸發 POST /tender/check-subscriptions

Version: 1.0.0
"""
import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.tender import TenderSubscription
from app.services.tender_search_service import TenderSearchService

logger = logging.getLogger(__name__)


async def check_all_subscriptions(db: AsyncSession) -> dict:
    """
    檢查所有啟用的訂閱，比對新公告數量。

    Returns:
        {checked: int, notified: int, details: [...]}
    """
    result = await db.execute(
        select(TenderSubscription).where(TenderSubscription.is_active == True)  # noqa: E712
    )
    subs = result.scalars().all()

    if not subs:
        return {"checked": 0, "notified": 0, "details": []}

    service = TenderSearchService()
    checked = 0
    notified = 0
    details = []

    for sub in subs:
        try:
            search_result = await service.search_by_title(
                query=sub.keyword, page=1, category=sub.category,
            )
            new_total = search_result.get("total_records", 0)
            old_total = sub.last_count or 0
            diff = new_total - old_total

            # 更新 last_checked + diff
            sub.last_checked_at = datetime.utcnow()
            sub.last_diff = max(diff, 0)
            sub.last_count = new_total

            # 記錄最新標案標題 (前 5 筆)
            import json as _json
            new_titles = [r.get("title", "")[:80] for r in search_result.get("records", [])[:5]]
            sub.last_new_titles = _json.dumps(new_titles, ensure_ascii=False) if new_titles else None

            detail = {
                "id": sub.id,
                "keyword": sub.keyword,
                "old_count": old_total,
                "new_count": new_total,
                "diff": diff,
                "notified": False,
            }

            # 有新增公告 → 發送通知
            if diff > 0 and old_total > 0:  # 第一次不通知（避免初始化噪音）
                detail["notified"] = True
                notified += 1

                # 系統通知
                if sub.notify_system:
                    try:
                        from app.services.notification_service import NotificationService
                        await NotificationService.create_notification(
                            db=db,
                            notification_type="tender_alert",
                            severity="info",
                            title=f"標案訂閱: {sub.keyword}",
                            message=f"新增 {diff} 筆「{sub.keyword}」相關標案公告",
                            source_table="tender_subscriptions",
                            source_id=sub.id,
                        )
                    except Exception as e:
                        logger.warning(f"標案訂閱系統通知失敗: {e}")

                # 多通道推播 (LINE + Discord + Telegram via OpenClaw)
                titles = [r["title"][:40] for r in search_result.get("records", [])[:3]]
                push_text = f"標案訂閱通知\n\n關鍵字: {sub.keyword}\n新增 {diff} 筆公告\n\n"
                push_text += "\n".join(f"• {t}" for t in titles)

                if sub.notify_line:
                    try:
                        from app.services.line_bot_service import get_line_bot_service
                        line_service = get_line_bot_service()
                        if line_service:
                            await line_service.broadcast_to_admins(push_text)
                    except Exception as e:
                        logger.warning(f"標案 LINE 推播失敗: {e}")

                # Discord 推播
                try:
                    from app.services.discord_bot_service import DiscordBotService
                    discord = DiscordBotService()
                    await discord.push_message(push_text)
                except Exception:
                    pass  # Discord 非必要，靜默失敗

            details.append(detail)
            checked += 1

        except Exception as e:
            logger.error(f"檢查訂閱 {sub.keyword} 失敗: {e}")
            details.append({
                "id": sub.id, "keyword": sub.keyword,
                "error": str(e),
            })

    await db.commit()

    logger.info(f"標案訂閱檢查完成: {checked} checked, {notified} notified")
    return {"checked": checked, "notified": notified, "details": details}
