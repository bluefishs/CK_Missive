"""
安全標頭中間件

@version 1.0.0
@date 2026-02-02

提供 OWASP 建議的安全標頭配置:
- X-Frame-Options: 防止點擊劫持
- X-Content-Type-Options: 防止 MIME 類型嗅探
- X-XSS-Protection: 啟用瀏覽器 XSS 過濾器
- Referrer-Policy: 控制 Referrer 資訊
- Permissions-Policy: 控制瀏覽器功能權限

使用方式:
    from app.core.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全標頭中間件

    為所有回應添加安全相關的 HTTP 標頭
    """

    def __init__(
        self,
        app,
        x_frame_options: str = "DENY",
        x_content_type_options: str = "nosniff",
        x_xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str = "geolocation=(), microphone=(), camera=()",
        content_security_policy: str = None,
    ):
        super().__init__(app)
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.x_xss_protection = x_xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.content_security_policy = content_security_policy

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 防止點擊劫持 (Clickjacking)
        response.headers["X-Frame-Options"] = self.x_frame_options

        # 防止 MIME 類型嗅探
        response.headers["X-Content-Type-Options"] = self.x_content_type_options

        # 啟用瀏覽器 XSS 過濾器 (已棄用但仍建議設置)
        response.headers["X-XSS-Protection"] = self.x_xss_protection

        # 控制 Referrer 資訊
        response.headers["Referrer-Policy"] = self.referrer_policy

        # 控制瀏覽器功能權限
        response.headers["Permissions-Policy"] = self.permissions_policy

        # Content Security Policy (如有設置)
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy

        return response


def get_default_csp() -> str:
    """
    取得預設的 Content Security Policy

    注意: CSP 需要根據實際應用需求調整
    """
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com; "
        "frame-src https://accounts.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
