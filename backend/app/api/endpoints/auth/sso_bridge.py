"""
SSO Bridge — 接受 www.cksurvey.tw 簽發的 ck_employee cookie，自動建立 Missive session

設計依據：
    - ADR-0001（CK_Website#0001）員工 SSO 策略
    - 「加成式」並存：保留所有既有認證（Google / LINE / 內網 IP），SSO 為新增快速通道
    - 可逆性 100%：CK_SSO_ENABLED feature flag 一鍵停用

流程：
    1. 檢查 feature flag CK_SSO_ENABLED
    2. 從 request 取 ck_employee cookie
    3. 驗 JWT 簽章 + 過期 + issuer (HS256, iss=cksurvey.tw)
    4. 從 JWT 取 email → 查 Missive User table
    5. 檢查 user.is_active + 網域白名單（重用既有邏輯）
    6. 呼叫 AuthService.generate_login_response 建立 Missive session
    7. 設 httpOnly cookies (ck_access_token / ck_refresh_token / csrf_token)
    8. 返回 TokenResponse

注意：本 endpoint 不會自動建立新使用者。員工必須已先以原方式（Google/LINE）登入過至少一次。
若 SSO email 在 Missive User table 找不到對應使用者，回 404 並引導員工走原本登入流程。

v1.0 - 2026-05-20
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.api.endpoints.auth.common import get_client_info
from app.core.auth_service import AuthService
from app.core.ck_sso import verify_ck_sso_jwt, verify_ck_sso_jwt_auto, has_system_permission
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.db.database import get_async_db
from app.extended.models import User
from app.services.audit import AuditService

logger = logging.getLogger(__name__)
router = APIRouter()

# 本系統 system_name（用於檢查 JWT systems claim 是否包含 missive）
SYSTEM_NAME = "missive"


@router.post(
    "/sso-bridge",
    summary="SSO Bridge — 用 www.cksurvey.tw 的 ck_employee cookie 建立 Missive session",
)
@limiter.limit("120/minute")
async def sso_bridge(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """
    SSO Bridge 端點

    成功（200）：返回 TokenResponse 並設定 Missive httpOnly cookies
    失敗：
        - 503 CK_SSO_ENABLED=false（功能未啟用）
        - 401 cookie 缺失或 JWT 驗證失敗
        - 403 員工無 missive 系統權限 / 帳號未啟用
        - 404 SSO email 不在 Missive User table（員工需先用原方式登入過）
    """
    # 1. Feature flag
    if not getattr(settings, "CK_SSO_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO bridge 未啟用",
        )

    secret = getattr(settings, "CK_SSO_JWT_SECRET", None)
    if not secret:
        logger.error("[SSO-BRIDGE] CK_SSO_JWT_SECRET 未設定但 CK_SSO_ENABLED=true")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO bridge 設定不完整",
        )

    ip_address, user_agent = get_client_info(request)

    # 2. 取 cookies（含 debug log 協助定位 cookie domain 問題）
    # ADR-0008 W4：兩個 cookie 都接 — verify_ck_sso_jwt_auto 自動 dispatch
    #   優先 ck_employee_rs (RS256, jwks 公鑰驗) — secret drift 風險 0
    #   fallback ck_employee (HS256, CK_SSO_JWT_SECRET) — W8 退場前向後相容
    token_hs = request.cookies.get("ck_employee")
    token_rs = request.cookies.get("ck_employee_rs")
    cookie_names = sorted(request.cookies.keys())
    logger.info(
        "[SSO-BRIDGE] received cookies=%s, ck_employee=%s, ck_employee_rs=%s, origin=%s",
        cookie_names,
        "present" if token_hs else "MISSING",
        "present" if token_rs else "MISSING",
        request.headers.get("origin") or request.headers.get("referer", "n/a"),
    )
    if not token_hs and not token_rs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 SSO cookie，請先到 https://www.cksurvey.tw/login 登入",
        )

    # 3. 驗 JWT — auto dispatcher（RS256 優先 / HS256 fallback）
    # jwks_url 可選環境變數 override（測試 / staging 用）
    jwks_url = getattr(settings, "CK_SSO_JWKS_URL", "https://www.cksurvey.tw/.well-known/jwks.json")
    employee = verify_ck_sso_jwt_auto(
        cookies=dict(request.cookies),
        secret=secret,
        jwks_url=jwks_url,
    )
    if employee is None:
        await AuditService.log_auth_event(
            event_type="SSO_BRIDGE_INVALID",
            email=None,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "jwt_invalid"},
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSO 憑證無效或已過期，請重新登入",
        )

    # 4. 檢查員工是否有 missive 系統權限（JWT systems claim）
    if not has_system_permission(employee, SYSTEM_NAME):
        await AuditService.log_auth_event(
            event_type="SSO_BRIDGE_BLOCKED",
            email=employee.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "reason": "no_missive_permission",
                "user_systems": list(employee.systems),
            },
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的員工權限不包含公文系統，請聯繫管理員",
        )

    # 5. 查 Missive User table（必須先以原方式登入過）
    user: Optional[User] = await AuthService.get_user_by_email(db, employee.email)
    if user is None:
        await AuditService.log_auth_event(
            event_type="SSO_BRIDGE_BLOCKED",
            email=employee.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "missive_user_not_found"},
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "您的 SSO 帳號尚未在公文系統建立。請先以原 Google 登入方式登入一次，"
                "之後即可使用 SSO 快速通道。"
            ),
        )

    # 6. 帳號狀態檢查
    if not user.is_active:
        await AuditService.log_auth_event(
            event_type="SSO_BRIDGE_BLOCKED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "account_deactivated"},
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的帳戶已被停用，無法登入系統",
        )

    # 7. 更新 last_login（不算新登入，不更新 login_count — generate_login_response 內處理）
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # 8. 建立 Missive session + 發 access/refresh token（重用既有邏輯）
    #    2026-07-21 止血：SSO 用戶 access token / session TTL 拉長為 SSO_ACCESS_TOKEN_EXPIRE_MINUTES(8h)，
    #    降低編輯途中過期→refresh 失敗→存檔白填（L74/L78）。local login 不受影響。
    token_response = await AuthService.generate_login_response(
        db, user, ip_address, user_agent,
        access_token_ttl_minutes=settings.SSO_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    await AuditService.log_auth_event(
        event_type="LOGIN_SUCCESS",
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"auth_provider": "ck_sso_bridge", "sso_role": employee.role},
        success=True,
    )

    logger.info(
        "[SSO-BRIDGE] 登入成功: %s (role=%s, sso_role=%s)",
        user.email, user.role, employee.role,
    )

    # 9. 設 cookies + 返回 JSON
    response = JSONResponse(content=token_response.model_dump(mode="json"))
    AuthService.set_auth_cookies(response, token_response, request=request)
    return response
