"""
認證模組 - 登入歷史端點

提供使用者登入歷史查詢功能，從 audit_logs 中篩選認證相關紀錄。

@version 1.0.0
@date 2026-02-08
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import limiter

from app.db.database import get_async_db
from app.extended.models import User
from app.schemas.auth import LoginHistoryItem, LoginHistoryResponse

from .common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 允許查詢的認證事件類型
ALLOWED_AUTH_ACTIONS = (
    "LOGIN_SUCCESS",
    "LOGIN_FAILED",
    "LOGIN_BLOCKED",
    "LOGOUT",
    "TOKEN_REFRESH",
)


@router.post("/login-history", response_model=LoginHistoryResponse, summary="查詢登入歷史")
@limiter.limit("30/minute")
async def get_login_history(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁筆數"),
):
    """
    查詢使用者登入歷史

    從 audit_logs 中篩選 table_name = 'auth_events' 且 record_id = current_user.id 的紀錄，
    action 限定為 LOGIN_SUCCESS, LOGIN_FAILED, LOGIN_BLOCKED, LOGOUT, TOKEN_REFRESH。
    依 created_at DESC 排序，分頁返回。
    """
    offset = (page - 1) * page_size

    # 構建參數化查詢 - audit_logs 無 ORM 模型，使用 text() SQL 查詢
    count_query = text("""
        SELECT COUNT(*) FROM audit_logs
        WHERE table_name = :table_name
          AND record_id = :record_id
          AND action IN :actions
    """)

    data_query = text("""
        SELECT id, action, changes, ip_address, created_at
        FROM audit_logs
        WHERE table_name = :table_name
          AND record_id = :record_id
          AND action IN :actions
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    params = {
        "table_name": "auth_events",
        "record_id": current_user.id,
        "actions": tuple(ALLOWED_AUTH_ACTIONS),
        "limit": page_size,
        "offset": offset,
    }

    # 取得總數
    count_result = await db.execute(count_query, params)
    total = count_result.scalar() or 0

    # 取得資料
    data_result = await db.execute(data_query, params)
    rows = data_result.fetchall()

    items = []
    for row in rows:
        # 解析 changes JSON 欄位取得詳細資訊
        changes_data = {}
        if row.changes:
            try:
                changes_data = json.loads(row.changes) if isinstance(row.changes, str) else row.changes
            except (json.JSONDecodeError, TypeError):
                changes_data = {}

        event_type = changes_data.get("event_type", row.action)
        success = changes_data.get("success", True)
        user_agent = changes_data.get("user_agent")
        ip_addr = changes_data.get("ip_address") or row.ip_address

        # 構建 details 欄位（排除已提取的欄位）
        details = {
            k: v for k, v in changes_data.items()
            if k not in ("event_type", "success", "user_agent", "ip_address", "email")
        }

        items.append(LoginHistoryItem(
            id=row.id,
            event_type=event_type,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=success,
            created_at=row.created_at,
            details=details if details else None,
        ))

    return LoginHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
