"""
認證模組 - Email 驗證端點

包含:
- POST /send-verification: 發送驗證 Email
- POST /verify-email: 驗證 Email token

安全設計:
- Token 使用 secrets.token_urlsafe(32) 生成
- 資料庫只存 SHA-256 hash，不存明文
- Token 24 小時有效
- 發送頻率限制: 3 次/分鐘
- 不論使用者是否存在都回傳一致的成功訊息（防帳號枚舉）

@version 1.0.0
@date 2026-02-08
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email_service import EmailService
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.db.database import get_async_db
from app.extended.models import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter()

# Email 驗證 Token 有效時間（小時）
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24


# === 請求模型 ===

class VerifyEmailRequest(BaseModel):
    """驗證 Email 請求"""
    token: str = Field(..., description="Email 驗證 token")


# === 工具函數 ===

def _hash_token(token: str) -> str:
    """將明文 token 轉為 SHA-256 hash"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_frontend_base_url(request: Request) -> str:
    """
    取得前端基礎 URL

    根據請求來源決定前端 URL：
    - 開發環境：http://localhost:3000
    - 生產環境：從 Origin header 或 Referer 推斷
    """
    origin = request.headers.get("origin")
    if origin:
        return origin

    referer = request.headers.get("referer")
    if referer:
        # 取得 scheme://host:port 部分
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}"

    # 預設使用前端配置
    port = settings.FRONTEND_HOST_PORT
    return f"http://localhost:{port}"


# === API 端點 ===

@router.post("/send-verification", summary="發送 Email 驗證信")
@limiter.limit("3/minute")
async def send_verification_email(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """
    發送 Email 驗證信

    - 需要已登入（透過 cookie 或 header 認證）
    - Token 24 小時有效
    - 速率限制: 3 次/分鐘

    安全設計:
    - Token 以 SHA-256 hash 儲存，不存明文
    - 如果已驗證，返回提示訊息
    """
    # 取得當前使用者
    from app.api.endpoints.auth.common import get_current_user
    current_user = await get_current_user(request, db)

    if current_user.email_verified:
        return {"message": "您的 Email 已經驗證完成"}

    # 生成驗證 token
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(
        hours=EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS
    )

    # 儲存 token hash 到資料庫
    user_repo = UserRepository(db)
    await user_repo.update_fields(
        current_user.id,
        email_verification_token=token_hash,
        email_verification_expires=expires_at,
    )
    await db.commit()

    # 取得前端 URL 並發送驗證信
    base_url = _get_frontend_base_url(request)
    sent = await EmailService.send_verification_email(
        email=current_user.email,
        token=raw_token,
        base_url=base_url,
    )

    if not sent:
        logger.error(
            f"[EMAIL_VERIFY] 驗證信發送失敗: user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="驗證信發送失敗，請稍後再試",
        )

    # 記錄審計日誌
    ip_address = request.client.host if request.client else None
    await AuditService.log_auth_event(
        event_type="EMAIL_VERIFICATION_SENT",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=ip_address,
        details={
            "token_expires_at": expires_at.isoformat(),
            "token_expiry_hours": EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
        },
        success=True,
    )

    logger.info(
        f"[EMAIL_VERIFY] 驗證信已發送: user_id={current_user.id}, "
        f"email={current_user.email}, "
        f"expires_at={expires_at.isoformat()}"
    )

    return {"message": "驗證信已發送至您的電子郵件"}


@router.post("/verify-email", summary="驗證 Email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    verify_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    驗證 Email token

    - 輸入: { token: string }
    - 驗證成功後設定 email_verified = True
    - Token 使用後立即清除

    安全設計:
    - 速率限制: 10 次/分鐘
    - Token 比對使用 SHA-256 hash
    """
    token_hash = _hash_token(verify_data.token)

    try:
        user_repo = UserRepository(db)

        # 查詢擁有此 token 的使用者
        user = await user_repo.get_by_email_verification_token(token_hash)

        if not user:
            logger.warning("[EMAIL_VERIFY] 無效的驗證 token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="驗證連結無效或已過期，請重新發送驗證信",
            )

        # 檢查是否已驗證
        if user.email_verified:
            # 清除已使用的 token
            await user_repo.update_fields(
                user.id,
                email_verification_token=None,
                email_verification_expires=None,
            )
            await db.commit()
            return {"message": "您的 Email 已經驗證完成", "already_verified": True}

        # 檢查 token 是否過期
        if user.email_verification_expires is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="驗證連結無效或已過期，請重新發送驗證信",
            )

        token_expires = user.email_verification_expires
        # 處理時區差異
        if token_expires.tzinfo is not None:
            token_expires = token_expires.replace(tzinfo=None)

        if token_expires < datetime.utcnow():
            logger.warning(
                f"[EMAIL_VERIFY] Token 已過期: user_id={user.id}, "
                f"expired_at={user.email_verification_expires}"
            )
            # 清除過期的 token
            await user_repo.update_fields(
                user.id,
                email_verification_token=None,
                email_verification_expires=None,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="驗證連結已過期，請重新發送驗證信",
            )

        # 驗證成功：更新 email_verified 並清除 token
        await user_repo.update_fields(
            user.id,
            email_verified=True,
            email_verification_token=None,
            email_verification_expires=None,
        )
        await db.commit()

        # 記錄審計日誌
        ip_address = request.client.host if request.client else None
        await AuditService.log_auth_event(
            event_type="EMAIL_VERIFIED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            details={},
            success=True,
        )

        logger.info(
            f"[EMAIL_VERIFY] Email 驗證成功: user_id={user.id}, "
            f"email={user.email}"
        )

        return {"message": "Email 驗證成功", "verified": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EMAIL_VERIFY] 驗證處理時發生錯誤: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="驗證處理失敗，請稍後再試",
        )
