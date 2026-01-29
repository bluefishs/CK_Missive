# -*- coding: utf-8 -*-
"""
API 速率限制模組

使用 slowapi 實現請求速率限制，防止 API 濫用。

@version 1.0.0
@date 2026-01-15
"""

import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_client_identifier(request: Request) -> str:
    """
    取得客戶端識別符號

    優先順序：
    1. X-Forwarded-For header (反向代理後的真實 IP)
    2. X-Real-IP header
    3. 直接連線的 IP
    """
    # 嘗試從 header 取得真實 IP (反向代理情況)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多個 IP，取第一個
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 直接連線
    return get_remote_address(request)


# 建立 Limiter 實例
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=[
        f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
        f"{settings.RATE_LIMIT_PER_DAY}/day"
    ],
    headers_enabled=True,  # 在回應 header 中顯示限制資訊
    strategy="fixed-window"  # 固定時間窗口策略
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    速率限制超過時的自訂處理器（同步版本）

    回傳統一的錯誤格式，並記錄日誌。
    注意：
    1. 必須是同步函數，因為 SlowAPIMiddleware 使用 sync_check_limits
       (async 函數會被 slowapi 忽略，fallback 到默認處理器)
    2. 需要手動加入 CORS 標頭，因為 BaseHTTPMiddleware 會繞過 CORS 中介軟體
    """
    from app.core.cors import allowed_origins

    client_ip = get_client_identifier(request)
    origin = request.headers.get("origin")

    # 詳細日誌用於診斷
    logger.warning(
        f"[自訂處理器] 速率限制超過 - IP: {client_ip}, 路徑: {request.url.path}, "
        f"Origin: {origin}, 限制: {exc.detail}"
    )
    logger.info(f"[自訂處理器] allowed_origins 數量: {len(allowed_origins)}, Origin 是否允許: {origin in allowed_origins if origin else 'N/A'}")

    # 建立 CORS 標頭
    # 注意：當 credentials=true 時，Access-Control-Allow-Origin 不能是 "*"
    cors_headers = {}
    if origin and origin in allowed_origins:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        }

    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "message": "請求過於頻繁，請稍後再試",
            "detail": str(exc.detail),
            "retry_after": exc.headers.get("Retry-After") if exc.headers else None
        },
        headers={
            "Retry-After": exc.headers.get("Retry-After", "60") if exc.headers else "60",
            "X-RateLimit-Limit": exc.headers.get("X-RateLimit-Limit", "") if exc.headers else "",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": exc.headers.get("X-RateLimit-Reset", "") if exc.headers else "",
            # CORS 標頭 - 確保 429 回應也能被前端正確處理
            **cors_headers,
        }
    )


def setup_rate_limiter(app: FastAPI) -> None:
    """
    設定應用程式的速率限制

    Args:
        app: FastAPI 應用程式實例
    """
    # 設定狀態
    app.state.limiter = limiter

    # 註冊異常處理器
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # 加入中介軟體
    app.add_middleware(SlowAPIMiddleware)

    logger.info(
        f"速率限制已啟用 - "
        f"每分鐘: {settings.RATE_LIMIT_PER_MINUTE}, "
        f"每日: {settings.RATE_LIMIT_PER_DAY}"
    )


# 匯出常用的限制裝飾器
def rate_limit(limit_string: str):
    """
    自訂速率限制裝飾器

    用法:
        @router.get("/sensitive")
        @rate_limit("10/minute")
        async def sensitive_endpoint():
            ...

    Args:
        limit_string: 限制字串，格式如 "10/minute", "100/hour", "1000/day"
    """
    return limiter.limit(limit_string)


# 共用的限制裝飾器
limit_per_minute = limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
limit_sensitive = limiter.limit("10/minute")  # 敏感操作使用更嚴格的限制
limit_auth = limiter.limit("5/minute")  # 認證相關端點
