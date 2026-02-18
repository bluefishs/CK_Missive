"""
MFA (Multi-Factor Authentication) API 端點

提供 TOTP 雙因素認證的設定、驗證、停用功能。

端點:
- POST /auth/mfa/setup    - 開始 MFA 設定（生成 secret + QR code）
- POST /auth/mfa/verify   - 驗證 TOTP code 並啟用 MFA
- POST /auth/mfa/disable  - 停用 MFA（需密碼驗證）
- POST /auth/mfa/validate - 登入時驗證 MFA code
- POST /auth/mfa/status   - 查詢 MFA 狀態

@version 1.0.0
@date 2026-02-08
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.db.database import get_async_db
from app.core.auth_service import AuthService, ALGORITHM
from app.core.config import settings
from app.core.mfa_service import MFAService, MFA_TOKEN_EXPIRE_SECONDS
from app.core.rate_limiter import limiter
from app.extended.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    MFASetupResponse,
    MFAVerifyRequest,
    MFADisableRequest,
    MFAValidateRequest,
    MFAStatusResponse,
    TokenResponse,
)
from app.services.audit_service import AuditService

from .common import get_current_user, get_client_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mfa", tags=["MFA"])


@router.post("/setup", response_model=MFASetupResponse, summary="開始 MFA 設定")
async def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    開始 MFA 設定流程

    生成 TOTP secret、QR code URI 和備用碼。
    此時 MFA 尚未啟用，需要呼叫 /auth/mfa/verify 確認後才正式啟用。

    注意：每次呼叫都會生成新的 secret，覆蓋之前未完成的設定。
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 已經啟用，如需重新設定請先停用",
        )

    # 生成 TOTP secret
    secret = MFAService.generate_secret()
    qr_uri = MFAService.get_totp_uri(secret, current_user.email)
    qr_code_base64 = MFAService.generate_qr_code_base64(qr_uri)

    # 生成備用碼
    plain_codes, hashed_json = MFAService.generate_backup_codes()

    # 暫存 secret 和 backup codes（尚未啟用 MFA）
    user_repo = UserRepository(db)
    await user_repo.update_fields(
        current_user.id,
        mfa_secret=secret,
        mfa_backup_codes=hashed_json,
    )
    await db.commit()

    logger.info(f"[MFA] 使用者 {current_user.id} 開始 MFA 設定")

    return MFASetupResponse(
        secret=secret,
        qr_uri=qr_uri,
        qr_code_base64=qr_code_base64,
        backup_codes=plain_codes,
    )


@router.post("/verify", summary="驗證 TOTP 並啟用 MFA")
async def mfa_verify(
    request_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    驗證 TOTP code 並正式啟用 MFA

    使用者在掃描 QR code 後，輸入驗證器顯示的 6 位數碼進行驗證。
    驗證成功後 MFA 正式啟用。
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 已經啟用",
        )

    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請先呼叫 /auth/mfa/setup 開始設定",
        )

    # 驗證 TOTP code
    if not MFAService.verify_totp(current_user.mfa_secret, request_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="驗證碼不正確，請確認驗證器 App 顯示的代碼",
        )

    # 啟用 MFA
    user_repo = UserRepository(db)
    await user_repo.update_fields(current_user.id, mfa_enabled=True)
    await db.commit()

    logger.info(f"[MFA] 使用者 {current_user.id} 已啟用 MFA")

    await AuditService.log_auth_event(
        event_type="MFA_ENABLED",
        user_id=current_user.id,
        email=current_user.email,
        details={"action": "mfa_enabled"},
        success=True,
    )

    return {"message": "MFA 已成功啟用", "mfa_enabled": True}


@router.post("/disable", summary="停用 MFA")
async def mfa_disable(
    request_data: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    停用 MFA

    需要驗證使用者密碼以確認身份。
    停用後清除 MFA secret 和備用碼。
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 尚未啟用",
        )

    # 驗證密碼
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此帳號未設定密碼，無法透過密碼驗證停用 MFA。請聯繫管理員。",
        )

    if not AuthService.verify_password(request_data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密碼不正確",
        )

    # 停用 MFA 並清除相關欄位
    user_repo = UserRepository(db)
    await user_repo.update_fields(
        current_user.id,
        mfa_enabled=False,
        mfa_secret=None,
        mfa_backup_codes=None,
    )
    await db.commit()

    logger.info(f"[MFA] 使用者 {current_user.id} 已停用 MFA")

    await AuditService.log_auth_event(
        event_type="MFA_DISABLED",
        user_id=current_user.id,
        email=current_user.email,
        details={"action": "mfa_disabled"},
        success=True,
    )

    return {"message": "MFA 已停用", "mfa_enabled": False}


@router.post("/validate", summary="登入時驗證 MFA")
@limiter.limit("10/minute")
async def mfa_validate(
    request: Request,
    request_data: MFAValidateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    登入流程第二步：驗證 MFA code

    當登入時收到 mfa_required=true 回應後，使用者需要提供：
    - mfa_token: 登入第一步返回的臨時 token
    - code: 6 位數 TOTP 驗證碼或備用碼

    驗證成功後返回完整的 JWT access_token。
    """
    ip_address, user_agent = get_client_info(request)

    # 驗證 MFA 臨時 token
    try:
        payload = jwt.decode(
            request_data.mfa_token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA 驗證已過期，請重新登入",
        )

    # 確認 token 類型
    if payload.get("type") != "mfa_pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的 MFA token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的 MFA token",
        )

    # 查找使用者
    user_repo = UserRepository(db)
    user = await user_repo.get_active_by_id(int(user_id))

    if not user or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 驗證失敗",
        )

    code = request_data.code.strip()
    verified = False

    # 嘗試 TOTP 驗證（6 位純數字）
    if len(code) == 6 and code.isdigit():
        verified = MFAService.verify_totp(user.mfa_secret, code)

    # 如果 TOTP 驗證失敗，嘗試備用碼
    if not verified and user.mfa_backup_codes:
        backup_verified, updated_codes = MFAService.verify_backup_code(
            code, user.mfa_backup_codes
        )
        if backup_verified:
            verified = True
            # 更新備用碼（移除已使用的）
            await user_repo.update_fields(user.id, mfa_backup_codes=updated_codes)
            await db.commit()
            logger.info(f"[MFA] 使用者 {user.id} 使用備用碼登入")

    if not verified:
        logger.warning(f"[MFA] 使用者 {user.id} MFA 驗證失敗")
        await AuditService.log_auth_event(
            event_type="MFA_FAILED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "invalid_code"},
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="驗證碼不正確",
        )

    # MFA 驗證成功，生成完整 JWT
    token_response = await AuthService.generate_login_response(
        db, user, ip_address, user_agent
    )

    await AuditService.log_auth_event(
        event_type="MFA_SUCCESS",
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"action": "mfa_validated"},
        success=True,
    )

    logger.info(f"[MFA] 使用者 {user.id} MFA 驗證成功")

    from starlette.responses import JSONResponse
    response = JSONResponse(
        content=token_response.model_dump(mode="json"),
    )
    AuthService.set_auth_cookies(response, token_response)
    return response


@router.post("/status", response_model=MFAStatusResponse, summary="查詢 MFA 狀態")
async def mfa_status(
    current_user: User = Depends(get_current_user),
):
    """
    查詢當前使用者的 MFA 狀態

    返回 MFA 是否啟用，以及剩餘備用碼數量。
    """
    remaining = 0
    if current_user.mfa_enabled and current_user.mfa_backup_codes:
        remaining = MFAService.get_remaining_backup_codes_count(
            current_user.mfa_backup_codes
        )

    return MFAStatusResponse(
        mfa_enabled=current_user.mfa_enabled,
        backup_codes_remaining=remaining,
    )
