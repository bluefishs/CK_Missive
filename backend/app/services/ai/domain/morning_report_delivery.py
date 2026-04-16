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

from app.extended.models import (
    MorningReportDeliveryLog,
    MorningReportSnapshot,
    UserMorningReportSubscription,
)

# B2: section key 對應 generate_report 的 dict key（供訂閱解析）
SECTION_KEYS = {
    "dispatch", "meeting", "site_visit", "missing",
    "pm_milestone", "erp_expense",
}
DEFAULT_SECTIONS = {"dispatch", "meeting", "site_visit", "missing"}

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


async def save_snapshot(
    db: AsyncSession,
    *,
    report_date: date,
    sections_json: dict,
    summary_text: str,
    sections_count: int,
    generator_version: str = "v1.0",
) -> None:
    """B4: 寫入每日快照；同日重複寫入時 upsert 更新。"""
    try:
        existing = await db.execute(
            select(MorningReportSnapshot).where(
                MorningReportSnapshot.report_date == report_date
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.sections_json = sections_json
            row.summary_text = summary_text
            row.summary_length = len(summary_text)
            row.sections_count = sections_count
            row.generator_version = generator_version
        else:
            db.add(MorningReportSnapshot(
                report_date=report_date,
                sections_json=sections_json,
                summary_text=summary_text,
                summary_length=len(summary_text),
                sections_count=sections_count,
                generator_version=generator_version,
            ))
        await db.commit()
    except Exception as e:
        logger.warning("morning_report snapshot save failed: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass


async def get_snapshots(
    db: AsyncSession, days: int = 14
) -> list[dict[str, Any]]:
    """B4: 回傳近 N 天 snapshot（依日期 desc）。"""
    since = today_taipei() - timedelta(days=days - 1)
    r = await db.execute(
        select(MorningReportSnapshot)
        .where(MorningReportSnapshot.report_date >= since)
        .order_by(MorningReportSnapshot.report_date.desc())
    )
    rows = r.scalars().all()
    return [
        {
            "report_date": row.report_date.isoformat(),
            "summary_length": row.summary_length,
            "sections_count": row.sections_count,
            "generator_version": row.generator_version,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
        for row in rows
    ]


def parse_sections_csv(csv: str | None) -> set[str]:
    """B1: 解析訂閱 sections CSV，過濾無效 key。"""
    if not csv:
        return set(DEFAULT_SECTIONS)
    tokens = {t.strip() for t in csv.split(",") if t.strip()}
    if "all" in tokens:
        return {"all"}
    valid = tokens & SECTION_KEYS
    return valid or set(DEFAULT_SECTIONS)


async def get_active_subscriptions(
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """B1: 取得所有 enabled 訂閱（純 dict 回傳，解耦 ORM session）。"""
    r = await db.execute(
        select(UserMorningReportSubscription).where(
            UserMorningReportSubscription.enabled.is_(True)
        )
    )
    rows = r.scalars().all()
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "display_name": row.display_name,
            "channel": row.channel,
            "channel_recipient": row.channel_recipient,
            "sections": parse_sections_csv(row.sections),
            "handler_filter": row.handler_filter,
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
