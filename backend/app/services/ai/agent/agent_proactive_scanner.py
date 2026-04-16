"""
Agent Proactive Scanner — 主動告警掃描

Scans for actionable alerts the agent can proactively mention:
1. Documents with calendar events ending within 3 days
2. System health summary (quick check)
3. Unread notifications count

Designed to be injected into agent context, complementing
the existing ProactiveTriggerService (which focuses on
case-level overdue/quality alerts).

Version: 1.0.0
Created: 2026-03-19
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def scan_agent_alerts(db: AsyncSession) -> Dict[str, Any]:
    """
    Scan for alerts the agent should be aware of.

    Returns:
        {
            "deadline_alerts": [{"document_id": N, "title": "...", "end_date": "...", "days_left": N}],
            "health_issues": ["Redis 連線異常", ...],
            "unread_notifications": N,
            "total_alerts": N,
        }
    """
    deadline_alerts = await _scan_deadline_alerts(db)
    health_issues = await _scan_health_issues()
    unread_count = await _count_unread_notifications(db)

    total = len(deadline_alerts) + len(health_issues) + (1 if unread_count > 0 else 0)

    return {
        "deadline_alerts": deadline_alerts,
        "health_issues": health_issues,
        "unread_notifications": unread_count,
        "total_alerts": total,
    }


async def _scan_deadline_alerts(db: AsyncSession) -> List[Dict[str, Any]]:
    """Find calendar events with end_date within the next 3 days."""
    try:
        from app.extended.models.calendar import DocumentCalendarEvent

        now = datetime.utcnow()
        cutoff = now + timedelta(days=3)

        result = await db.execute(
            select(
                DocumentCalendarEvent.id,
                DocumentCalendarEvent.document_id,
                DocumentCalendarEvent.title,
                DocumentCalendarEvent.end_date,
                DocumentCalendarEvent.priority,
                DocumentCalendarEvent.status,
            )
            .where(
                and_(
                    DocumentCalendarEvent.end_date.isnot(None),
                    DocumentCalendarEvent.end_date <= cutoff,
                    DocumentCalendarEvent.end_date >= now,
                    DocumentCalendarEvent.status != "completed",
                    DocumentCalendarEvent.status != "cancelled",
                )
            )
            .order_by(DocumentCalendarEvent.end_date.asc())
            .limit(20)
        )
        rows = result.all()

        alerts = []
        for row in rows:
            days_left = (row.end_date - now).days if row.end_date else 0
            alerts.append({
                "event_id": row.id,
                "document_id": row.document_id,
                "title": row.title or "",
                "end_date": row.end_date.isoformat() if row.end_date else "",
                "days_left": max(0, days_left),
                "priority": row.priority or "normal",
            })
        return alerts

    except Exception as e:
        logger.debug("Deadline alert scan failed: %s", e)
        return []


async def _scan_health_issues() -> List[str]:
    """Quick health check: Redis connectivity."""
    issues: List[str] = []

    # Check Redis
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        if r is None:
            issues.append("Redis 連線不可用")
        else:
            await r.ping()
    except Exception:
        issues.append("Redis 連線異常")

    return issues


async def _count_unread_notifications(db: AsyncSession) -> int:
    """Count total unread system notifications."""
    try:
        from app.extended.models.system import SystemNotification

        result = await db.execute(
            select(func.count()).select_from(SystemNotification).where(
                SystemNotification.is_read == False,
            )
        )
        return result.scalar() or 0
    except Exception as e:
        logger.debug("Unread notification count failed: %s", e)
        return 0
