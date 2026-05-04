"""
安全網站管理模組 - CSRF 端點

包含: /csrf-token
"""

from fastapi import APIRouter, Response

from app.core.config import settings
from app.core.csrf import set_csrf_cookie
from app.schemas.secure import SecureResponse

from .common import cleanup_expired_tokens, generate_csrf_token

router = APIRouter()


@router.post("/csrf-token", response_model=SecureResponse)
async def get_csrf_token(response: Response):
    """獲取 CSRF 令牌

    F16 (2026-05-04 事故修復後加碼)：除回傳 JSON body 外，同時設定 csrf_token cookie。
    解 stale access_token + 缺 csrf cookie 的死結 — 任何訪客只要 hit 此 endpoint
    即可拿到對應 cookie + token，後續 secureRequest 不再 403。
    """
    await cleanup_expired_tokens()
    token = await generate_csrf_token()
    is_dev = bool(getattr(settings, "DEVELOPMENT_MODE", False))
    set_csrf_cookie(response, token, is_development=is_dev)
    return SecureResponse(
        success=True,
        message="CSRF token generated",
        csrf_token=token
    )
