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


# API 文件路徑：吐出全部端點的 schema，只該給內網。
#: 只准內網來源的路徑。
#:
#: ⚠️ 2026-08-24 加入 `/metrics` —— 它是 08-21 那個外洩的**側門**，
#: 而我當時沒看到，因為 `public_endpoint_auth_audit` **只掃 `/api/*`**。
#: 公網實測未帶憑證回 200、**1,013,354 字元**，內容包括：
#:   kg_entities_total 49899      ← 正是關掉 statistics 端點要擋的那個數字
#:   kg_edges_total / kg_embedding_coverage_ratio
#:   341 條端點路徑（完整 API 地圖，含 admin 端點）
#:   LLM provider 名稱與效能（gemma-local、latency p95、success ratio）
#:
#: 這個盲區是 CK_PileMgmt session 2026-08-24 指出的：runtime dependency 樹
#: 「擅長找出誰忘記加認證，但看不到**非瀏覽器消費者**（Prometheus／webhook
#: 這類基礎設施抓取器）」—— 它們不在前端消費鏈裡，也不在 `/api/*` 底下。
#:
#: Prometheus 走內網抓（實測 log：`host: host.docker.internal:8001`、
#: `user-agent: Prometheus/2.53.0`），所以加這條守衛**不影響採集**。
API_DOC_PATHS = ("/openapi.json", "/api/docs", "/api/redoc", "/docs/oauth2-redirect",
                 "/metrics")


class ApiDocsGuardMiddleware(BaseHTTPMiddleware):
    """API 文件僅限內網（2026-08-03）。

    這幾條路徑會回傳**全部 724 個端點的完整 schema**，而且不需任何憑證。
    實測公網 `https://missive.cksurvey.tw/openapi.json` 直接 200。

    為什麼不是 `FastAPI(docs_url=None)`：同一個容器同時服務內網與經 CF Tunnel
    進來的公網流量，關掉參數就是**兩邊一起沒有**，內網也查不到 API 文件了。
    要的是依請求來源區分，所以做成守衛。

    為什麼不是打開 `TUNNEL_GUARD_ENABLED`：那是明確設成 false 的既有決策
    （打開會連人員流量一起擋），不在這裡順手改動它。本守衛獨立生效、
    只管這四條路徑，與那個開關無關。

    復用同檔的 `_is_tunnel_request` / `_is_internal_ip` —— 來源判斷只該有一份。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in API_DOC_PATHS):
            client_ip = request.client.host if request.client else ""
            if _is_tunnel_request(request) or not _is_internal_ip(client_ip):
                logger.info("API 文件請求被拒（非內網來源）: %s from %s", path, client_ip)
                # 回 404 而非 403：對外不必透露這個路徑存在
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return await call_next(request)


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
