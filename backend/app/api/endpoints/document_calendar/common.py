"""
公文行事曆模組 - 共用依賴

包含所有子模組共用的匯入、服務實例和輔助函數。

@version 1.0.0
@date 2026-01-22
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User, OfficialDocument, DocumentCalendarEvent, EventReminder
from app.services.document_calendar_service import DocumentCalendarService
from app.services.document_calendar_integrator import DocumentCalendarIntegrator
from app.schemas.document_calendar import (
    SyncStatusResponse,
    DocumentCalendarEventCreate,
    DocumentCalendarEventUpdate,
    DocumentCalendarEventResponse,
    EventListRequest,
    EventDetailRequest,
    EventDeleteRequest,
    EventSyncRequest,
    BulkSyncRequest,
    UserEventsRequest,
    IntegratedEventCreate,
    ReminderConfig,
    ConflictCheckRequest,
    SyncIntervalRequest
)
import logging

logger = logging.getLogger(__name__)

# 共用服務實例
calendar_service = DocumentCalendarService()
calendar_integrator = DocumentCalendarIntegrator()


def event_to_dict(
    event: DocumentCalendarEvent,
    doc_number: Optional[str] = None,
    contract_project_name: Optional[str] = None
) -> Dict[str, Any]:
    """將事件實體轉換為字典

    Args:
        event: 行事曆事件
        doc_number: 關聯公文號
        contract_project_name: 關聯承攬案件名稱
    """
    start_iso = event.start_date.isoformat()
    end_iso = event.end_date.isoformat() if event.end_date else None

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "start_date": start_iso,
        "end_date": end_iso,
        # 前端 CalendarEventUI 使用 start_datetime/end_datetime 別名
        "start_datetime": start_iso,
        "end_datetime": end_iso,
        "all_day": event.all_day,
        "event_type": event.event_type,
        "priority": event.priority,
        "status": getattr(event, 'status', 'pending'),
        "location": event.location,
        "document_id": event.document_id,
        "doc_number": doc_number,
        "contract_project_name": contract_project_name,
        "assigned_user_id": event.assigned_user_id,
        "created_by": event.created_by,
        "google_event_id": getattr(event, 'google_event_id', None),
        "google_sync_status": getattr(event, 'google_sync_status', None),
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None
    }


async def check_event_permission(
    event: DocumentCalendarEvent,
    current_user: User,
    action: str = "access"
) -> None:
    """檢查使用者對事件的權限"""
    if current_user.is_admin:
        return

    if event.created_by != current_user.id and event.assigned_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"您沒有權限{action}此事件"
        )


async def get_user_project_doc_ids(db: AsyncSession, user_id: int) -> List[int]:
    """取得使用者參與專案的公文 ID 列表（ORM 安全查詢）"""
    from app.extended.models import project_user_assignment

    # Step 1: 取得使用者參與的專案 ID
    project_ids_result = await db.execute(
        select(project_user_assignment.c.project_id)
        .where(
            and_(
                project_user_assignment.c.user_id == user_id,
                func.coalesce(project_user_assignment.c.status, 'active') == 'active'
            )
        )
    )
    user_project_ids = [row[0] for row in project_ids_result.fetchall()]

    if not user_project_ids:
        return []

    # Step 2: 取得這些專案關聯的公文 ID
    doc_ids_result = await db.execute(
        select(OfficialDocument.id)
        .where(OfficialDocument.contract_project_id.in_(user_project_ids))
    )
    return [row[0] for row in doc_ids_result.fetchall()]


# 重新匯出常用依賴
__all__ = [
    # FastAPI
    'Depends', 'HTTPException', 'status',
    # SQLAlchemy
    'AsyncSession', 'select', 'or_', 'func', 'and_',
    # 資料庫
    'get_async_db',
    # 認證
    'get_current_user',
    # Models
    'User', 'OfficialDocument', 'DocumentCalendarEvent', 'EventReminder',
    # Services
    'calendar_service', 'calendar_integrator',
    # Schemas
    'DocumentCalendarEventCreate', 'DocumentCalendarEventUpdate',
    'EventListRequest', 'EventDetailRequest', 'EventDeleteRequest',
    'EventSyncRequest', 'BulkSyncRequest', 'UserEventsRequest',
    'IntegratedEventCreate', 'ReminderConfig',
    'ConflictCheckRequest', 'SyncIntervalRequest',
    # 輔助函數
    'event_to_dict', 'check_event_permission', 'get_user_project_doc_ids',
    # 其他
    'logger', 'datetime', 'timedelta', 'Optional', 'List', 'Dict', 'Any'
]
