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

        # Scope 檢查（目前 MCP_SERVICE_TOKEN 擁有所有 scope）
        # 未來可擴展為 token → scope mapping（DB/Redis）
        for scope in scopes:
            if scope not in _ALL_SCOPES:
                logger.warning("Unknown scope requested: %s", scope)
                raise HTTPException(status_code=403, detail=f"Unknown scope: {scope}")

        return True

    return _verify
