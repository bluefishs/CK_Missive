"""
認證模組 - 使用者 Session 管理端點

提供使用者查看自己的活躍 Session、撤銷指定 Session、撤銷所有其他 Session 的功能。

端點：
- POST /auth/sessions        - 列出使用者所有活躍 Session
- POST /auth/sessions/revoke - 撤銷指定 Session
- POST /auth/sessions/revoke-all - 撤銷所有其他 Session

@version 1.0.0
@date 2026-02-08
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.rate_limiter import limiter
from app.extended.models import User
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import SessionInfo, SessionListResponse, RevokeSessionRequest
from starlette.responses import Response

from .common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_current_jti(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    """從請求中提取當前 session 的 token_jti"""
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        return None

    payload = AuthService.verify_token(token)
    if not payload:
        return None

    return payload.get("jti")


@router.post("/sessions", response_model=SessionListResponse, summary="列出活躍 Session")
@limiter.limit("30/minute")
async def list_sessions(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    列出使用者所有活躍 Session

    返回該使用者的所有 is_active=True 的 Session，
    並標記當前請求所使用的 Session 為 is_current=True。
    """
    current_jti = _get_current_jti(request, credentials)

    session_repo = SessionRepository(db)
    sessions = await session_repo.get_user_active_sessions_ordered(current_user.id)

    session_list = []
    for s in sessions:
        session_info = SessionInfo(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            device_info=s.device_info,
            created_at=s.created_at,
            last_activity=s.last_activity,
            is_active=s.is_active,
            is_current=(s.token_jti == current_jti) if current_jti else False,
        )
        session_list.append(session_info)

    return SessionListResponse(
        sessions=session_list,
        total=len(session_list),
    )


@router.post("/sessions/revoke", summary="撤銷指定 Session")
@limiter.limit("10/minute")
async def revoke_session(
    request: Request,
    response: Response,
    revoke_request: RevokeSessionRequest,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    撤銷指定的 Session

    不能撤銷自己當前正在使用的 Session。
    只能撤銷屬於自己的 Session。
    """
    current_jti = _get_current_jti(request, credentials)

    session_repo = SessionRepository(db)

    # 查詢要撤銷的 session
    target_session = await session_repo.get_active_by_id_and_user(
        revoke_request.session_id, current_user.id
    )

    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定的 Session 或該 Session 已被撤銷",
        )

    # 不允許撤銷當前 session
    if current_jti and target_session.token_jti == current_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法撤銷目前正在使用的 Session，請使用登出功能",
        )

    # 撤銷 session
    await session_repo.revoke_session(revoke_request.session_id)
    await db.commit()

    logger.info(
        f"[SESSION] 使用者 {current_user.email} 撤銷了 Session #{revoke_request.session_id}"
    )

    return {"message": "Session 已成功撤銷", "session_id": revoke_request.session_id}


@router.post("/sessions/revoke-all", summary="撤銷所有其他 Session")
@limiter.limit("5/minute")
async def revoke_all_sessions(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    撤銷所有其他 Session（保留當前 Session）

    將使用者的所有活躍 Session 標記為已撤銷，
    但排除當前正在使用的 Session。
    """
    current_jti = _get_current_jti(request, credentials)

    session_repo = SessionRepository(db)

    # 撤銷所有其他 session（排除當前 jti）
    revoked_count = await session_repo.revoke_all_by_user_excluding_jti(
        current_user.id, exclude_jti=current_jti
    )
    await db.commit()

    logger.info(
        f"[SESSION] 使用者 {current_user.email} 撤銷了 {revoked_count} 個其他 Session"
    )

    return {
        "message": f"已成功撤銷 {revoked_count} 個其他 Session",
        "revoked_count": revoked_count,
    }
