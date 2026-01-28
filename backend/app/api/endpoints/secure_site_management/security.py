"""
安全網站管理模組 - CSRF 端點

包含: /csrf-token
"""

from fastapi import APIRouter

from app.schemas.secure import SecureResponse

from .common import cleanup_expired_tokens, generate_csrf_token

router = APIRouter()


@router.post("/csrf-token", response_model=SecureResponse)
async def get_csrf_token():
    """獲取 CSRF 令牌"""
    cleanup_expired_tokens()
    token = generate_csrf_token()
    return SecureResponse(
        success=True,
        message="CSRF token generated",
        csrf_token=token
    )
