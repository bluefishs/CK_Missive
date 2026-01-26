# -*- coding: utf-8 -*-
"""
系統通知 API 端點
System Notifications API Endpoints

用途：
1. 查詢系統通知（關鍵欄位變更、匯入結果、錯誤警示）
2. 標記通知已讀
3. 取得未讀通知數量
"""
import logging
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.notification_service import (
    NotificationService,
    NotificationType,
    NotificationSeverity
)
from app.core.dependencies import require_auth
from app.extended.models import User

# 統一從 schemas 匯入型別定義
from app.schemas.notification import (
    NotificationQuery,
    NotificationItem,
    NotificationListResponse,
    MarkReadRequest,
    MarkReadResponse,
    UnreadCountResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# API 端點
# ============================================================================

@router.post(
    "/list",
    response_model=NotificationListResponse,
    summary="查詢系統通知列表"
)
async def get_notifications(
    query: NotificationQuery = Body(default=NotificationQuery()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    查詢系統通知列表

    支援篩選：
    - is_read: 是否已讀 (true/false)
    - severity: 嚴重程度 (info/warning/error/critical)
    - type: 通知類型 (system/critical_change/import/error/security)

    回傳包含總數和未讀數量
    """
    try:
        result = await NotificationService.get_notifications(
            db=db,
            user_id=current_user.id,
            is_read=query.is_read,
            severity=query.severity,
            notification_type=query.type,
            limit=query.limit,
            offset=(query.page - 1) * query.limit
        )

        items = []
        for item in result.get("items", []):
            items.append(NotificationItem(
                id=item["id"],
                type=item["type"],
                severity=item["severity"],
                title=item["title"],
                message=item["message"],
                source_table=item.get("source_table"),
                source_id=item.get("source_id"),
                changes=item.get("changes"),
                user_id=item.get("user_id"),
                user_name=item.get("user_name"),
                is_read=item.get("is_read", False),
                read_at=item.get("read_at"),
                created_at=item.get("created_at")
            ))

        return NotificationListResponse(
            success=True,
            items=items,
            total=result.get("total", 0),
            unread_count=result.get("unread_count", 0),
            page=query.page,
            limit=query.limit
        )

    except Exception as e:
        logger.error(f"查詢系統通知失敗: {e}", exc_info=True)
        return NotificationListResponse(
            success=False,
            items=[],
            total=0,
            unread_count=0
        )


@router.post(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="取得未讀通知數量"
)
async def get_unread_count(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    取得未讀通知數量

    用於前端通知圖示的 badge 顯示
    """
    try:
        result = await NotificationService.get_notifications(
            db=db,
            user_id=current_user.id,
            is_read=False,
            limit=1,
            offset=0
        )

        return UnreadCountResponse(
            success=True,
            unread_count=result.get("unread_count", 0)
        )

    except Exception as e:
        logger.error(f"取得未讀數量失敗: {e}", exc_info=True)
        return UnreadCountResponse(success=False, unread_count=0)


@router.post(
    "/mark-read",
    response_model=MarkReadResponse,
    summary="標記通知為已讀"
)
async def mark_notifications_read(
    request: MarkReadRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    標記指定通知為已讀

    傳入通知 ID 列表，批次標記為已讀
    """
    try:
        updated_count = await NotificationService.mark_as_read(
            db=db,
            notification_ids=request.notification_ids,
            user_id=current_user.id
        )

        return MarkReadResponse(
            success=True,
            updated_count=updated_count,
            message=f"已標記 {updated_count} 筆通知為已讀"
        )

    except Exception as e:
        logger.error(f"標記通知已讀失敗: {e}", exc_info=True)
        return MarkReadResponse(
            success=False,
            updated_count=0,
            message=f"標記失敗: {str(e)}"
        )


@router.post(
    "/mark-all-read",
    response_model=MarkReadResponse,
    summary="標記所有通知為已讀"
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    標記所有未讀通知為已讀

    一鍵清除所有未讀通知
    """
    try:
        updated_count = await NotificationService.mark_all_as_read(
            db=db,
            user_id=current_user.id
        )

        return MarkReadResponse(
            success=True,
            updated_count=updated_count,
            message=f"已標記 {updated_count} 筆通知為已讀"
        )

    except Exception as e:
        logger.error(f"標記所有通知已讀失敗: {e}", exc_info=True)
        return MarkReadResponse(
            success=False,
            updated_count=0,
            message=f"標記失敗: {str(e)}"
        )


@router.post(
    "/types",
    summary="取得通知類型選項"
)
async def get_notification_types(
    current_user: User = Depends(require_auth())
):
    """
    取得通知類型和嚴重程度的選項列表

    用於前端篩選下拉選單
    """
    return {
        "success": True,
        "types": [
            {"value": NotificationType.SYSTEM, "label": "系統通知"},
            {"value": NotificationType.CRITICAL_CHANGE, "label": "關鍵欄位變更"},
            {"value": NotificationType.IMPORT, "label": "匯入結果"},
            {"value": NotificationType.ERROR, "label": "錯誤警示"},
            {"value": NotificationType.SECURITY, "label": "安全警示"},
        ],
        "severities": [
            {"value": NotificationSeverity.INFO, "label": "一般"},
            {"value": NotificationSeverity.WARNING, "label": "警告"},
            {"value": NotificationSeverity.ERROR, "label": "錯誤"},
            {"value": NotificationSeverity.CRITICAL, "label": "嚴重"},
        ]
    }
