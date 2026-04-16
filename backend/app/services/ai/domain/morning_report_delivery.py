"""Morning Report Delivery — 派送紀錄與失敗告警輔助模組。

責任：
- 記錄每次 push 的 success/failed/skipped
- 查詢最近 N 天 delivery 狀態（供 status endpoint）
- 連續失敗檢查（供告警）
"""
from __future__ import annotations

import logging
from datetime import date, timedelta, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import MorningReportDeliveryLog

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")


def today_taipei() -> date:
    """取得 Asia/Taipei 的今日日期，避免 server TZ 漂移。"""
    return datetime.now(TZ_TAIPEI).date()


async def log_delivery(
    db: AsyncSession,
    *,
    report_date: date,
    channel: str,
    status: str,
    recipient: str | None = None,
    error_msg: str | None = None,
    summary_length: int | None = None,
    sections_count: int | None = None,
    trigger_source: str = "scheduler",
) -> None:
    """寫入 delivery log。不拋例外（log-only），避免影響主流程。"""
    try:
        entry = MorningReportDeliveryLog(
            report_date=report_date,
            channel=channel,
            status=status,
            recipient=recipient,
            error_msg=(error_msg or "")[:2000] if error_msg else None,
            summary_length=summary_length,
            sections_count=sections_count,
            trigger_source=trigger_source,
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        logger.warning("morning_report delivery log failed: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass


async def get_recent_deliveries(
    db: AsyncSession, days: int = 7
) -> list[dict[str, Any]]:
    """回傳近 N 天派送紀錄（依日期 desc, channel asc）。"""
    since = today_taipei() - timedelta(days=days - 1)
    r = await db.execute(
        select(MorningReportDeliveryLog)
        .where(MorningReportDeliveryLog.report_date >= since)
        .order_by(
            MorningReportDeliveryLog.report_date.desc(),
            MorningReportDeliveryLog.channel.asc(),
            MorningReportDeliveryLog.id.desc(),
        )
    )
    rows = r.scalars().all()
    return [
        {
            "id": row.id,
            "report_date": row.report_date.isoformat(),
            "channel": row.channel,
            "recipient": row.recipient,
            "status": row.status,
            "error_msg": row.error_msg,
            "summary_length": row.summary_length,
            "sections_count": row.sections_count,
            "trigger_source": row.trigger_source,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def consecutive_failure_days(
    db: AsyncSession, channel: str, window_days: int = 7
) -> int:
    """回傳某 channel 連續失敗天數（截至今日）。

    保守定義：
    - 當日有 success → 中斷 streak
    - 當日有 failed 且無 success → streak++
    - 當日無紀錄 → 中斷 streak（避免系統停機誤報）
    """
    today = today_taipei()
    streak = 0
    for offset in range(window_days):
        d = today - timedelta(days=offset)
        r = await db.execute(
            select(
                MorningReportDeliveryLog.status,
                func.count(MorningReportDeliveryLog.id),
            )
            .where(
                MorningReportDeliveryLog.report_date == d,
                MorningReportDeliveryLog.channel == channel,
            )
            .group_by(MorningReportDeliveryLog.status)
        )
        counts = {status: cnt for status, cnt in r.all()}
        if not counts:
            break  # 無紀錄 — 不當作失敗，中斷
        if counts.get("success", 0) > 0:
            break
        if counts.get("failed", 0) > 0:
            streak += 1
        else:
            break
    return streak
