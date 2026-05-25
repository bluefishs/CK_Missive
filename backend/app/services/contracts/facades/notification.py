# -*- coding: utf-8 -*-
"""NotificationFacade - Notification context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發：
  - notification -> integration (9 imports — 已透過 IntegrationFacade 解一半)
  - calendar -> notification (2)
  - 其他 context 推通知散 imports

統一封 notification dispatcher / template / scheduler 操作。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class NotificationFacade:
    """Notification bounded context 對外唯一入口

    所有跨 context 發通知必須走此 facade，禁止直 import
    services/notification/* 內部 module。

    使用範例：
        facade = NotificationFacade(db)
        await facade.send_deadline_reminder(user_id=42, doc_id=123, due_date=...)
        unread = await facade.get_unread_count(user_id=42)
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def send_deadline_reminder(
        self,
        user_id: int,
        doc_id: int,
        due_date: datetime,
        *,
        channel: Optional[str] = None,
    ) -> bool:
        """發 document deadline 提醒（取代 calendar -> notification 直 import）"""
        try:
            from app.services.notification.dispatcher import (
                dispatch_deadline_reminder,
            )
            return await dispatch_deadline_reminder(
                self._db,
                user_id=user_id, doc_id=doc_id, due_date=due_date, channel=channel,
            )
        except (ImportError, AttributeError):
            return False

    async def send_project_update(
        self,
        project_id: int,
        update_text: str,
        *,
        notify_all_staff: bool = True,
    ) -> dict:
        """發專案更新通知（取代 erp→notification 直 import）"""
        try:
            from app.services.notification.project_notification_service import (
                send_project_update_notification,
            )
            return await send_project_update_notification(
                self._db,
                project_id=project_id, update_text=update_text,
                notify_all_staff=notify_all_staff,
            )
        except (ImportError, AttributeError):
            return {"sent": 0, "error": "notification unavailable"}

    async def get_unread_count(
        self,
        user_id: int,
    ) -> int:
        """取得使用者未讀通知數"""
        try:
            from app.repositories.notification_repository import (
                NotificationRepository,
            )
            repo = NotificationRepository(self._db)
            return await repo.count_unread_for_user(user_id)
        except (ImportError, AttributeError):
            return 0

    async def list_notifications(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[dict]:
        """列使用者通知"""
        try:
            from app.repositories.notification_repository import (
                NotificationRepository,
            )
            repo = NotificationRepository(self._db)
            return await repo.list_for_user(
                user_id, unread_only=unread_only, limit=limit,
            )
        except (ImportError, AttributeError):
            return []

    async def mark_read(
        self,
        notification_id: int,
        user_id: int,
    ) -> bool:
        """標記通知已讀"""
        try:
            from app.repositories.notification_repository import (
                NotificationRepository,
            )
            repo = NotificationRepository(self._db)
            return await repo.mark_read(notification_id, user_id)
        except (ImportError, AttributeError):
            return False


__all__ = ["NotificationFacade"]
