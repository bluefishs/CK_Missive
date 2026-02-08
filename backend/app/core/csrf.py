"""
CSRF (Cross-Site Request Forgery) 防護模組

提供 Double Submit Cookie 模式的 CSRF 防護：
- 登入時生成 CSRF token 並設為 non-httpOnly cookie（前端 JS 可讀取）
- 前端讀取 cookie 後附加到 X-CSRF-Token header
- 後端驗證 cookie 中的 csrf_token 與 header X-CSRF-Token 是否一致

豁免規則：
- GET / HEAD / OPTIONS 請求豁免（安全方法）
- /api/auth/login 和 /api/auth/google 豁免（登入時尚無 CSRF token）
- /health 等公開端點豁免

@version 1.0.0
@date 2026-02-07
"""

import secrets
import logging
from typing import Set

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

# CSRF Token 長度（32 bytes = 64 hex chars）
CSRF_TOKEN_LENGTH = 32

# 豁免 CSRF 驗證的路徑前綴
CSRF_EXEMPT_PATHS: Set[str] = {
    "/api/auth/login",
    "/api/auth/google",
    "/api/auth/register",
    "/api/auth/password-reset",
    "/api/auth/password-reset-confirm",
    "/api/auth/verify-email",
    "/health",
    "/health/detailed",
    "/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/debug/cors",
    "/api/debug/cors/test",
}

# 安全的 HTTP 方法（不需要 CSRF 驗證）
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def generate_csrf_token() -> str:
    """
    生成 CSRF token

    Returns:
        64 字元的隨機十六進位字串
    """
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def set_csrf_cookie(response: Response, csrf_token: str, is_development: bool = False) -> None:
    """
    設定 CSRF token cookie（non-httpOnly，前端 JS 需要讀取）

    Args:
        response: FastAPI/Starlette Response 物件
        csrf_token: CSRF token 值
        is_development: 是否為開發環境（影響 Secure flag）
    """
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # 前端 JS 需要讀取此 cookie
        secure=not is_development,  # 開發環境允許 HTTP
        samesite="lax",
        path="/",
        max_age=3600,  # 1 小時，與 access_token 同步
    )


def clear_csrf_cookie(response: Response) -> None:
    """
    清除 CSRF token cookie

    Args:
        response: FastAPI/Starlette Response 物件
    """
    response.delete_cookie(
        key="csrf_token",
        path="/",
    )


def _is_path_exempt(path: str) -> bool:
    """
    檢查路徑是否豁免 CSRF 驗證

    Args:
        path: 請求路徑

    Returns:
        True 表示豁免，False 表示需要驗證
    """
    # 精確匹配
    if path in CSRF_EXEMPT_PATHS:
        return True

    # 靜態資源豁免
    if path.startswith("/static/") or path.startswith("/uploads/"):
        return True

    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF 防護中間件

    使用 Double Submit Cookie 模式：
    比較 cookie 中的 csrf_token 與 request header X-CSRF-Token
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 安全方法豁免
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        # 豁免路徑
        if _is_path_exempt(request.url.path):
            return await call_next(request)

        # 檢查是否有 cookie 中的 CSRF token
        cookie_csrf = request.cookies.get("csrf_token")
        access_token_cookie = request.cookies.get("access_token")

        if not cookie_csrf:
            if access_token_cookie:
                # Cookie 認證模式下 csrf_token 必須存在，否則拒絕
                logger.warning(
                    f"[CSRF] Cookie 認證缺少 csrf_token: "
                    f"method={request.method} path={request.url.path}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF 驗證失敗：缺少 csrf_token cookie",
                )
            # 純 Authorization header 認證（無 cookie）= 豁免 CSRF
            return await call_next(request)

        # 取得 header 中的 CSRF token
        header_csrf = request.headers.get("X-CSRF-Token")

        if not header_csrf:
            logger.warning(
                f"[CSRF] 缺少 X-CSRF-Token header: "
                f"method={request.method} path={request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF 驗證失敗：缺少 X-CSRF-Token header",
            )

        # 比較 cookie 和 header 中的 CSRF token
        if not secrets.compare_digest(cookie_csrf, header_csrf):
            logger.warning(
                f"[CSRF] Token 不匹配: "
                f"method={request.method} path={request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF 驗證失敗：token 不匹配",
            )

        return await call_next(request)
