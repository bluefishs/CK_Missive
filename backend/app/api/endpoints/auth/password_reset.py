"""
認證模組 - 密碼重設端點

包含:
- POST /password-reset: 請求密碼重設（發送 token）
- POST /password-reset-confirm: 確認密碼重設（驗證 token 並更新密碼）

安全設計:
- Token 使用 secrets.token_urlsafe(32) 生成
- 資料庫只存 SHA-256 hash，不存明文
- Token 15 分鐘有效
- 不論 email 是否存在都回傳相同訊息（防帳號枚舉）
- 使用後立即標記為已使用
- 成功後撤銷該用戶所有 UserSession

@version 1.0.0
@date 2026-02-08
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_service import AuthService
from app.core.password_policy import validate_password
from app.core.rate_limiter import limiter
from app.db.database import get_async_db
from app.extended.models import User, UserSession
from app.schemas.auth import PasswordReset, PasswordResetConfirm
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter()

# Token 有效時間（分鐘）
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 15


def _hash_token(token: str) -> str:
    """將明文 token 轉為 SHA-256 hash"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/password-reset", summary="請求密碼重設")
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_async_db),
):
    """
    請求密碼重設

    - 接受 email，生成 reset token
    - Token 15 分鐘有效
    - 不論 email 是否存在都返回相同成功訊息（防帳號枚舉）
    - 目前僅記錄 token 到日誌供測試（生產環境需整合 Email 發送）

    安全設計:
    - 速率限制: 3 次/分鐘
    - Token 以 SHA-256 hash 儲存，不存明文
    """
    email = reset_data.email.lower()

    # 統一的成功訊息（不論 email 是否存在）
    success_message = "如果此 email 已註冊，您將收到密碼重設信件"

    try:
        # 查詢使用者（包含停用的帳號也查詢，但只處理活躍帳號）
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            # 使用者不存在，仍回傳成功訊息
            logger.info(f"[PASSWORD_RESET] 收到不存在的 email 重設請求: {email}")
            return {"message": success_message}

        if not user.is_active:
            # 帳號停用，仍回傳成功訊息
            logger.info(f"[PASSWORD_RESET] 停用帳號嘗試重設密碼: user_id={user.id}")
            return {"message": success_message}

        if user.auth_provider == "google":
            # Google 帳號不支持密碼重設，仍回傳成功訊息
            logger.info(f"[PASSWORD_RESET] Google 帳號嘗試重設密碼: user_id={user.id}")
            return {"message": success_message}

        # 生成 reset token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRY_MINUTES)

        # 儲存 token hash 到資料庫
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                password_reset_token=token_hash,
                password_reset_expires=expires_at,
            )
        )
        await db.commit()

        # 記錄審計日誌
        ip_address = request.client.host if request.client else None
        await AuditService.log_auth_event(
            event_type="PASSWORD_RESET_REQUESTED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            details={
                "token_expires_at": expires_at.isoformat(),
                "token_expiry_minutes": PASSWORD_RESET_TOKEN_EXPIRY_MINUTES,
            },
            success=True,
        )

        # 目前僅記錄 token 到日誌（生產環境應寄送 Email）
        logger.info(
            f"[PASSWORD_RESET] Token 已生成: user_id={user.id}, "
            f"email={user.email}, token={raw_token}, "
            f"expires_at={expires_at.isoformat()}"
        )

        return {"message": success_message}

    except Exception as e:
        logger.error(f"[PASSWORD_RESET] 處理重設請求時發生錯誤: {e}", exc_info=True)
        # 即使發生錯誤也不洩露資訊
        return {"message": success_message}


@router.post("/password-reset-confirm", summary="確認密碼重設")
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    confirm_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db),
):
    """
    確認密碼重設

    - 驗證 token 有效性
    - 使用 password_policy 驗證新密碼
    - 更新密碼
    - 撤銷該用戶所有 UserSession
    - Token 使用後立即標記為已使用

    安全設計:
    - 速率限制: 5 次/分鐘
    - Token 比對使用 SHA-256 hash
    """
    token_hash = _hash_token(confirm_data.token)

    try:
        # 查詢擁有此 token 的使用者
        result = await db.execute(
            select(User).where(
                User.password_reset_token == token_hash,
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"[PASSWORD_RESET] 無效的重設 token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重設連結無效或已過期，請重新申請密碼重設",
            )

        # 檢查 token 是否過期
        if user.password_reset_expires is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重設連結無效或已過期，請重新申請密碼重設",
            )

        token_expires = user.password_reset_expires
        # 處理時區差異
        if token_expires.tzinfo is not None:
            token_expires = token_expires.replace(tzinfo=None)

        if token_expires < datetime.utcnow():
            logger.warning(
                f"[PASSWORD_RESET] Token 已過期: user_id={user.id}, "
                f"expired_at={user.password_reset_expires}"
            )
            # 清除過期的 token
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    password_reset_token=None,
                    password_reset_expires=None,
                )
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重設連結已過期，請重新申請密碼重設",
            )

        # 密碼策略驗證
        is_valid, message = validate_password(
            confirm_data.new_password,
            username=user.username,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

        # 更新密碼並清除 reset token
        new_password_hash = AuthService.get_password_hash(confirm_data.new_password)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                password_hash=new_password_hash,
                password_reset_token=None,
                password_reset_expires=None,
                # 重置鎖定狀態（密碼重設視為合法身份驗證）
                failed_login_attempts=0,
                locked_until=None,
            )
        )

        # 撤銷該用戶所有活躍的 session
        revoke_result = await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.is_active == True,
            )
            .values(
                is_active=False,
                revoked_at=datetime.utcnow(),
            )
        )
        revoked_count = revoke_result.rowcount

        await db.commit()

        # 記錄審計日誌
        ip_address = request.client.host if request.client else None
        await AuditService.log_auth_event(
            event_type="PASSWORD_RESET_COMPLETED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            details={
                "sessions_revoked": revoked_count,
            },
            success=True,
        )

        logger.info(
            f"[PASSWORD_RESET] 密碼重設成功: user_id={user.id}, "
            f"撤銷 {revoked_count} 個 session"
        )

        return {
            "message": "密碼重設成功，請使用新密碼登入",
            "sessions_revoked": revoked_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PASSWORD_RESET] 確認重設時發生錯誤: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密碼重設處理失敗，請稍後再試",
        )
