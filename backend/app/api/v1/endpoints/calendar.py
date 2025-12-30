"""
行事曆管理 API 端點
"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ....core.deps import get_db, get_current_user
from ....models.user import User
from ....models.calendar_event import CalendarEvent, CalendarSyncLog, SyncStatus
from ....schemas.calendar import (
    CalendarEventCreate, 
    CalendarEventUpdate, 
    CalendarEventResponse,
    CalendarEventList,
    SyncResponse
)
from ....integrations.google_calendar.client import google_calendar_client

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events", response_model=CalendarEventList)
async def get_calendar_events(
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取得使用者的行事曆事件"""
    
    # 建立查詢
    query = db.query(CalendarEvent).filter(CalendarEvent.user_id == current_user.id)
    
    # 日期範圍篩選
    if start_date:
        query = query.filter(CalendarEvent.start_datetime >= start_date)
    if end_date:
        query = query.filter(CalendarEvent.end_datetime <= end_date)
    
    # 排序
    query = query.order_by(CalendarEvent.start_datetime)
    
    # 分頁
    total = query.count()
    events = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return CalendarEventList(
        events=[CalendarEventResponse.model_validate(event) for event in events],
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/events", response_model=CalendarEventResponse)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    sync_to_google: bool = Query(False, description="是否同步到 Google Calendar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """建立新的行事曆事件"""
    
    # 建立事件
    event = CalendarEvent(
        title=event_data.title,
        description=event_data.description,
        location=event_data.location,
        start_datetime=event_data.start_datetime,
        end_datetime=event_data.end_datetime,
        timezone=event_data.timezone or "Asia/Taipei",
        is_all_day=event_data.is_all_day or False,
        reminders=event_data.reminders,
        attendees=event_data.attendees,
        visibility=event_data.visibility or "private",
        user_id=current_user.id,
        created_by_id=current_user.id,
        document_id=event_data.document_id,
        contract_case_id=event_data.contract_case_id
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # 如果需要同步到 Google Calendar
    if sync_to_google:
        try:
            # 這裡需要取得使用者的 Google 認證
            # 實際實作時需要儲存使用者的 refresh token
            pass  # 待實作
        except Exception as e:
            logger.error(f"Failed to sync event to Google Calendar: {e}")
            # 不影響本地事件建立
    
    return CalendarEventResponse.model_validate(event)


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取得特定行事曆事件"""
    
    event = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id
        )
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="事件不存在"
        )
    
    return CalendarEventResponse.model_validate(event)


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    event_id: int,
    event_data: CalendarEventUpdate,
    sync_to_google: bool = Query(False, description="是否同步到 Google Calendar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新行事曆事件"""
    
    event = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id
        )
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="事件不存在"
        )
    
    # 更新事件資料
    update_data = event_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    event.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(event)
    
    return CalendarEventResponse.model_validate(event)


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: int,
    delete_from_google: bool = Query(False, description="是否從 Google Calendar 刪除"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """刪除行事曆事件"""
    
    event = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id
        )
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="事件不存在"
        )
    
    db.delete(event)
    db.commit()
    
    return {"message": "事件已刪除"}


# Google Calendar 整合端點

@router.get("/google/connect")
async def google_calendar_connect(
    current_user: User = Depends(get_current_user)
):
    """取得 Google Calendar 連結 URL"""
    try:
        auth_url = google_calendar_client.get_auth_url(current_user.id)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to get Google auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="無法連結 Google Calendar"
        )


@router.get("/google/callback")
async def google_calendar_callback(
    code: str = Query(..., description="授權碼"),
    state: str = Query(..., description="使用者狀態"),
    db: Session = Depends(get_db)
):
    """處理 Google Calendar OAuth 回調"""
    try:
        # 取得認證
        credentials = google_calendar_client.handle_oauth_callback(code, state)
        
        # 儲存使用者的 refresh token
        user_id = int(state)
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="使用者不存在"
            )
        
        # 這裡需要儲存 credentials 到資料庫
        # 實際實作時需要建立 UserGoogleCredentials 模型
        
        return {"message": "Google Calendar 連結成功"}
        
    except Exception as e:
        logger.error(f"Failed to handle Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Calendar 連結失敗"
        )


@router.post("/google/sync", response_model=SyncResponse)
async def sync_google_calendar(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手動同步 Google Calendar"""
    
    # 檢查使用者是否已連結 Google Calendar
    # 實際實作時需要檢查 UserGoogleCredentials
    
    try:
        # 背景任務執行同步
        background_tasks.add_task(
            _sync_google_calendar_task,
            current_user.id,
            db
        )
        
        return SyncResponse(
            status="started",
            message="同步已開始，請稍後查看結果"
        )
        
    except Exception as e:
        logger.error(f"Failed to start Google Calendar sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="同步失敗"
        )


@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取得同步狀態"""
    
    # 查詢最近的同步記錄
    recent_logs = db.query(CalendarSyncLog).filter(
        CalendarSyncLog.user_id == current_user.id
    ).order_by(CalendarSyncLog.created_at.desc()).limit(10).all()
    
    return {
        "recent_syncs": [
            {
                "id": log.id,
                "sync_type": log.sync_type,
                "operation": log.operation,
                "status": log.status.value,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat()
            }
            for log in recent_logs
        ]
    }


async def _sync_google_calendar_task(user_id: int, db: Session):
    """背景同步任務"""
    try:
        # 取得使用者認證
        # credentials = get_user_google_credentials(user_id, db)
        
        # 執行同步
        # events = google_calendar_client.sync_events_from_google(credentials, db, user_id)
        
        # 記錄同步結果
        sync_log = CalendarSyncLog(
            user_id=user_id,
            sync_type="pull",
            operation="sync",
            status=SyncStatus.SYNCED,
            sync_data={"events_synced": 0}  # len(events)
        )
        
        db.add(sync_log)
        db.commit()
        
        logger.info(f"Google Calendar sync completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Google Calendar sync failed for user {user_id}: {e}")
        
        # 記錄錯誤
        sync_log = CalendarSyncLog(
            user_id=user_id,
            sync_type="pull",
            operation="sync",
            status=SyncStatus.FAILED,
            error_message=str(e)
        )
        
        db.add(sync_log)
        db.commit()


# 統計端點

@router.get("/stats")
async def get_calendar_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取得行事曆統計資訊"""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    
    base_query = db.query(CalendarEvent).filter(CalendarEvent.user_id == current_user.id)
    
    stats = {
        "total_events": base_query.count(),
        "today_events": base_query.filter(
            and_(
                CalendarEvent.start_datetime >= today_start,
                CalendarEvent.start_datetime < today_start + timedelta(days=1)
            )
        ).count(),
        "this_week_events": base_query.filter(
            CalendarEvent.start_datetime >= week_start
        ).count(),
        "this_month_events": base_query.filter(
            CalendarEvent.start_datetime >= month_start
        ).count(),
        "upcoming_events": base_query.filter(
            CalendarEvent.start_datetime > now
        ).count(),
        "google_synced_events": base_query.filter(
            CalendarEvent.google_sync_status == SyncStatus.SYNCED
        ).count(),
    }
    
    return stats