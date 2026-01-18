"""
專案通知管理API端點
處理專案通知設定、團隊管理和訊息推送
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User, SystemNotification
from app.services.project_notification_service import ProjectNotificationService
from app.services.document_calendar_integrator import DocumentCalendarIntegrator

# 統一從 schemas 匯入型別定義
from app.schemas.notification import (
    NotificationSettingsRequest,
    TeamNotificationRequest,
    ProjectUpdateRequest,
    SingleMarkReadRequest,
    NotificationResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 服務實例
notification_service = ProjectNotificationService()
calendar_integrator = DocumentCalendarIntegrator()

@router.post("/team-members/{project_id}")
async def get_project_team_members(
    project_id: int,
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取專案團隊成員清單"""
    try:
        team_members = await notification_service.get_project_team_members(
            db, project_id
        )

        # 格式化回傳資料
        formatted_members = []
        for member in team_members:
            user = member["user"]
            formatted_member = {
                "user_id": member["user_id"],
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": member["role"],
                "is_primary": member["is_primary"],
                "assignment_date": member["assignment_date"],
                "status": member["status"],
                "permissions": member["permissions"]
            }
            formatted_members.append(formatted_member)

        return {
            "success": True,
            "data": formatted_members,
            "message": f"成功獲取專案 {project_id} 的團隊成員"
        }

    except Exception as e:
        logger.error(f"獲取專案團隊成員失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取專案團隊成員失敗"
        )

@router.post("/settings")
async def setup_notification_settings(
    request: NotificationSettingsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """設定專案通知偏好"""
    try:
        success = await notification_service.setup_project_notifications(
            db=db,
            project_id=request.project_id,
            user_id=current_user.id,
            notification_settings=request.notification_settings
        )

        if success:
            return {
                "success": True,
                "message": "通知設定已更新"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="通知設定更新失敗"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設定通知偏好失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="設定通知偏好失敗"
        )

@router.post("/send-calendar-event")
async def send_calendar_event_notifications(
    request: TeamNotificationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """發送行事曆事件通知給專案團隊"""
    try:
        # 獲取事件資訊
        events = await calendar_integrator.get_document_events(db, request.event_id)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到指定的行事曆事件"
            )

        event = events[0]  # 假設根據ID只有一個事件

        # 發送通知
        sent_notifications = await notification_service.send_calendar_event_notifications(
            db=db,
            event=event,
            project_id=request.project_id,
            custom_recipients=request.custom_recipients
        )

        return {
            "success": True,
            "data": {
                "sent_count": len(sent_notifications),
                "event_title": event.title
            },
            "message": f"成功發送 {len(sent_notifications)} 個行事曆事件通知"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"發送行事曆事件通知失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="發送行事曆事件通知失敗"
        )

@router.post("/send-project-update")
async def send_project_update_notifications(
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """發送專案更新通知"""
    try:
        sent_count = await notification_service.send_project_update_notifications(
            db=db,
            project_id=request.project_id,
            update_content=request.update_content,
            assignee_name=request.assignee_name,
            exclude_user_ids=request.exclude_user_ids
        )

        return {
            "success": True,
            "data": {"sent_count": sent_count},
            "message": f"成功發送 {sent_count} 個專案更新通知"
        }

    except Exception as e:
        logger.error(f"發送專案更新通知失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="發送專案更新通知失敗"
        )

@router.post("/user-notifications")
async def get_user_notifications(
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取使用者通知清單"""
    try:
        # 從 request 中獲取參數
        data = request.get('data', {})
        unread_only = data.get('unread_only', False)
        limit = data.get('limit', 50)

        notifications = await notification_service.get_user_notifications(
            db=db,
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit
        )

        # 格式化通知資料
        formatted_notifications = []
        for notification in notifications:
            formatted_notification = NotificationResponse(
                id=notification.id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type,
                priority=notification.priority,
                is_read=notification.is_read,
                created_at=notification.created_at,
                related_object_type=notification.related_object_type,
                related_object_id=notification.related_object_id,
                action_url=notification.action_url
            )
            formatted_notifications.append(formatted_notification)

        return {
            "success": True,
            "data": {
                "notifications": formatted_notifications,
                "total_count": len(formatted_notifications),
                "unread_count": sum(1 for n in notifications if not n.is_read)
            },
            "message": "成功獲取使用者通知"
        }

    except Exception as e:
        logger.error(f"獲取使用者通知失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取使用者通知失敗"
        )

@router.post("/mark-read")
async def mark_notification_as_read(
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """標記通知為已讀"""
    try:
        # 從 request 中獲取參數
        data = request.get('data', {})
        notification_id = data.get('notification_id')

        if not notification_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_id 為必填欄位"
            )

        success = await notification_service.mark_notification_as_read(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id
        )

        if success:
            return {
                "success": True,
                "message": "通知已標記為已讀"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到指定的通知或通知已為已讀狀態"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"標記通知已讀失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="標記通知已讀失敗"
        )

@router.post("/unread-count")
async def get_unread_notification_count(
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取未讀通知數量"""
    try:
        unread_notifications = await notification_service.get_user_notifications(
            db=db,
            user_id=current_user.id,
            unread_only=True,
            limit=1000  # 獲取所有未讀通知來計數
        )

        return {
            "success": True,
            "data": {"unread_count": len(unread_notifications)},
            "message": "成功獲取未讀通知數量"
        }

    except Exception as e:
        logger.error(f"獲取未讀通知數量失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取未讀通知數量失敗"
        )

@router.post("/broadcast/{project_id}")
async def broadcast_to_project_team(
    project_id: int,
    title: str,
    message: str,
    priority: int = 3,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """向專案團隊廣播訊息"""
    try:
        # 獲取專案團隊成員
        team_members = await notification_service.get_project_team_members(
            db, project_id
        )

        if not team_members:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到專案團隊成員"
            )

        # 建立廣播通知
        sent_count = 0
        for member in team_members:
            if member["user_id"] != current_user.id:  # 不發送給自己
                success = await notification_service._create_system_notification(
                    db=db,
                    recipient_id=member["user_id"],
                    notification_type="broadcast",
                    template_vars={
                        "user_name": member["user"].full_name or member["user"].username,
                        "title": title,
                        "message": message,
                        "sender_name": current_user.full_name or current_user.username
                    },
                    related_object_type="project",
                    related_object_id=project_id,
                    priority=priority
                )

                if success:
                    sent_count += 1

        return {
            "success": True,
            "data": {"sent_count": sent_count},
            "message": f"成功向 {sent_count} 位團隊成員發送廣播訊息"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"專案團隊廣播失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="專案團隊廣播失敗"
        )