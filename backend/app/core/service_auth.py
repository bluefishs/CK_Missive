# -*- coding: utf-8 -*-
"""
Service Token 認證模組 — scope-based 細粒度存取控制

學習自 CK_lvrland_Webmap/backend/app/core/service_auth.py

支援：
  - HMAC 常數時間比較（防 timing attack）
  - 雙 token 輪替（MCP_SERVICE_TOKEN + _PREV）
  - Scope-based 權限（read:agent, write:kg, admin:system）
  - 開發模式 localhost bypass
  - Dependency Injection（FastAPI Depends）

Usage:
    from app.core.service_auth import require_scope

    @router.post("/agent/query")
    async def query(auth=Depends(require_scope("read:agent"))):
        ...

    @router.post("/kg/entity")
    async def create_entity(auth=Depends(require_scope("write:kg"))):
        ...

Version: 1.0.0
Created: 2026-04-18
"""
import hmac
import logging
import os
from typing import Optional

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

# 2026-08-29：scope 實際使用量的觀測（B9／A11 決策所需的資料）。
#
# `require_scope` 目前是裝飾性的（見下方 _verify 內的說明），而要修它需要
# token → scope 對照表 —— 那張表要怎麼設計，取決於**每個 scope 實際被誰用、
# 用多少**，而那個資料此前只存在於「每次通過印一行 log」裡，會被淹沒也無法聚合。
#
# CK_Website 2026-08-29 問「要不要乾脆不接」時的判斷是：不構成不接的理由，
# 但構成**接之前先修 B9** 的理由。要修就要先有資料，這支就是那個資料。
#
# ⚠️ 名稱不帶 `_total`：prometheus_client 會自己補，寫成 `xxx_total` 會變成
# `xxx_total_total`（CK_Website 踩過，查原名會讀到 0.0 而以為計數壞了）。
_SCOPE_USAGE = None


def _record_scope_usage(scope: str) -> None:
    """記錄某個 scope 被通過一次（best-effort，絕不影響認證流程）。"""
    global _SCOPE_USAGE
    try:
        if _SCOPE_USAGE is None:
            from prometheus_client import REGISTRY, Counter
            _SCOPE_USAGE = Counter(
                "service_token_scope_usage",
                "service token 通過各 scope 的次數"
                "（⚠️ 目前未做 token→scope 對照，此為使用量觀測非授權紀錄）",
                ["scope"],
                registry=REGISTRY,
            )
        _SCOPE_USAGE.labels(scope=scope).inc()
    except Exception:
        # 觀測失敗不得影響認證 —— 但也不吞成靜默：重複註冊是唯一預期的例外
        pass

# Scope 定義（擴展時加入此處）
VALID_SCOPES = {
    "read:agent",       # Agent 查詢
    "write:agent",      # Agent 修改（學習、設定）
    "read:kg",          # 知識圖譜查詢
    "write:kg",         # 知識圖譜修改
    "read:tender",      # 標案查詢
    "read:wiki",        # Wiki 查詢
    "admin:system",     # 系統管理（備份、掃描、排程）
}

# Token → Scope 對照（可擴展為 DB/Redis 管理）
# 目前 MCP_SERVICE_TOKEN 預設擁有所有 scope（向後相容）
_ALL_SCOPES = VALID_SCOPES


def _get_tokens() -> tuple[Optional[str], Optional[str]]:
    """取得 current + previous token"""
    return (
        os.getenv("MCP_SERVICE_TOKEN"),
        os.getenv("MCP_SERVICE_TOKEN_PREV"),
    )


def _verify_token(token: str) -> bool:
    """HMAC 常數時間比較驗證 token"""
    current, prev = _get_tokens()
    if not current:
        return False
    token_bytes = token.encode("utf-8")
    if hmac.compare_digest(token_bytes, current.encode("utf-8")):
        return True
    if prev and hmac.compare_digest(token_bytes, prev.encode("utf-8")):
        return True
    return False


def _is_dev_localhost(request: Request) -> bool:
    """開發模式 + localhost → bypass"""
    is_dev = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
    client_host = request.client.host if request.client else ""
    return is_dev and client_host in ("127.0.0.1", "::1")


def require_scope(*scopes: str):
    """FastAPI Depends — 驗證 service token + 檢查 scope。

    Usage:
        Depends(require_scope("read:agent"))
        Depends(require_scope("read:agent", "read:kg"))  # 需同時具備
    """
    def _verify(
        request: Request,
        x_service_token: Optional[str] = Header(None),
    ) -> bool:
        current, _ = _get_tokens()

        # 未設定 token — 開發模式 localhost bypass
        if not current:
            if _is_dev_localhost(request):
                return True
            raise HTTPException(status_code=403, detail="Service token not configured")

        # 無 token header
        if not x_service_token:
            raise HTTPException(status_code=401, detail="X-Service-Token header required")

        # 驗證 token
        if not _verify_token(x_service_token):
            raise HTTPException(status_code=401, detail="Invalid service token")

        # ⚠️ 2026-08-21：這段**只驗 scope 名稱合不合法，不驗這把 token 有沒有被授予它**。
        #
        # `_ALL_SCOPES = VALID_SCOPES` ⇒ `require_scope("admin:system")` 與
        # `require_scope("read:kg")` 的實際效果**完全相同**：有 token 就過。
        # 也就是說 scope 目前是**裝飾性的** —— 而它讀起來像有授權控制，
        # 那比沒有更糟（會讓人以為有保護）。這是本專案記過的
        # 「宣告了一個沒實作的機制」家族。
        #
        # 具體後果（CK_Website session 2026-08-21 指出）：該站為了送一則通知
        # 呼叫 `/api/notify/digest`（宣告 admin:system），實際拿到的是
        # **能讀 KG、改 agent、跑備份**的憑證。
        #
        # 要真的修需要 token → scope 對照，而 MCP_SERVICE_TOKEN 目前由
        # Hermes／LINE／CK_Website 共用 ⇒ 跨 repo 改動，屬 owner 決策。
        # 在那之前**至少讓它出聲**，不要只寫在註解裡沒有人看得到。
        for scope in scopes:
            if scope not in _ALL_SCOPES:
                logger.warning("Unknown scope requested: %s", scope)
                raise HTTPException(status_code=403, detail=f"Unknown scope: {scope}")
        if scopes:
            for scope in scopes:
                _record_scope_usage(scope)
            logger.info(
                "service_auth: scope %s 通過（⚠️ 目前未做 token→scope 對照，"
                "任何合法 token 皆可通過任何 scope）", ",".join(scopes),
            )

        return True

    return _verify
