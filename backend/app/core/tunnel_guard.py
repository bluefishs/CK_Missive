"""
外網路由守衛 — Cloudflare Tunnel / ngrok 環境下限制外部存取

外部請求（經 tunnel 進入）僅允許存取 webhook 路徑，
其餘 API 端點需內網或已認證使用者存取。

識別方式:
- Cloudflare: CF-Connecting-IP header 存在
- ngrok: X-Forwarded-For header 存在 + ngrok-skip-browser-warning

Version: 1.0.0
Created: 2026-03-25
"""

import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# 允許外部存取的路徑前綴（ADR-0014/0015/0016）
# 機器流量（webhook / ACP / agent API）經 CF Tunnel 進入；
# 人員流量應走 CF Access SSO，不在此清單內。
ALLOWED_EXTERNAL_PATHS = frozenset({
    "/api/health",                    # 健康檢查（CF Tunnel 自動探針）
    "/api/public",                    # 公開端點（免認證）
    # --- 身分驗證（人員登入必經）---
    "/api/auth/",                     # google / line / login / logout / refresh / mfa 等
    # --- 通道 webhook ---
    "/api/line/webhook",              # LINE（過渡期保留）
    "/api/discord/webhook",           # Discord bot
    "/api/discord/interactions",      # Discord Interactions Endpoint
    "/api/telegram/webhook",          # Telegram Bot
    # --- Hermes ACP (ADR-0014) ---
    "/api/hermes/",                   # acp + feedback 同前綴
    # --- Agent public contract (manifest + 同步問答) ---
    "/api/ai/agent/tools",            # manifest v1.2
    "/api/ai/agent/query_sync",       # 通用 Agent 查詢（token 保護）
})

# 內網 IP 判斷
_INTERNAL_PREFIXES = ("127.", "10.", "192.168.", "::1")
_INTERNAL_172 = range(16, 32)


def _is_internal_ip(ip: str) -> bool:
    """判斷是否為內網 IP"""
    if not ip:
        return False
    for prefix in _INTERNAL_PREFIXES:
        if ip.startswith(prefix):
            return True
    # 172.16-31.x.x
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if second in _INTERNAL_172:
                    return True
            except ValueError:
                pass
    return False


def _is_tunnel_request(request: Request) -> bool:
    """判斷請求是否經由 tunnel (Cloudflare / ngrok) 進入"""
    # Cloudflare Tunnel 標記
    if request.headers.get("cf-connecting-ip"):
        return True
    # ngrok 標記
    if (request.headers.get("x-forwarded-for")
            and request.headers.get("ngrok-skip-browser-warning") is not None):
        return True
    # 通用: 有 X-Forwarded-For 但 client 是 localhost (proxy 轉發)
    xff = request.headers.get("x-forwarded-for", "")
    client_ip = request.client.host if request.client else ""
    if xff and _is_internal_ip(client_ip) and not _is_internal_ip(xff.split(",")[0].strip()):
        return True
    return False


def _path_allowed(path: str) -> bool:
    """檢查路徑是否在允許清單中"""
    for allowed in ALLOWED_EXTERNAL_PATHS:
        if path.startswith(allowed):
            return True
    return False


class TunnelGuardMiddleware(BaseHTTPMiddleware):
    """
    外網路由守衛中間件

    當偵測到請求經由 Cloudflare Tunnel 或 ngrok 進入時，
    僅允許存取 webhook 相關路徑，其餘回傳 403。

    透過環境變數 TUNNEL_GUARD_ENABLED 控制開關 (預設 false)。
    """

    async def dispatch(self, request: Request, call_next):
        enabled = os.getenv("TUNNEL_GUARD_ENABLED", "false").lower() == "true"

        if not enabled:
            return await call_next(request)

        path = request.url.path

        if _is_tunnel_request(request) and not _path_allowed(path):
            client_ip = request.headers.get("cf-connecting-ip") or \
                        request.headers.get("x-forwarded-for", "unknown")
            logger.warning(
                "TunnelGuard blocked external access: path=%s ip=%s",
                path, client_ip,
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "External access denied for this endpoint"},
            )

        return await call_next(request)
