"""
Federation Client -- 聯邦式 AI 系統間呼叫客戶端 v4.1.0

啟用 CK_Missive 智能體委派查詢至外部 AI 系統。
v4.1: 拆分重構 — 服務發現移至 federation_discovery，委派移至 federation_delegation
v4.0: D1-3 跨域委派 — 新增 delegate() 方法，透過 NemoClaw Gateway 將任務
      委派至其他插件（如 ck-tunnel、ck-lvrland），支援直接路由與 auto 模式。
v3.0: P2 流量改道 — OpenClaw 請求改經 NemoClaw Gateway scheduler 調度，
      享受 Queue (併發限制) + Quota (每日配額) + Priority (動態優先權)。
v2.0: 動態服務發現 — 啟動時查詢 NemoClaw Registry API 取得可用系統，
      不再依賴硬編碼清單。Registry 不可達時回退至環境變數。

設計原則:
- 優先從 NemoClaw Registry (http://nemoclaw_tower/api/registry) 動態發現
- 回退至 OPENCLAW_URL / LVRLAND_URL / MCP_SERVICE_TOKEN 環境變數
- httpx 非同步客戶端，30 秒超時
- 未設定或不可達時優雅降級（回傳明確錯誤，不中斷對話）
- TTL 60 秒自動重新整理 Registry
- delegate() 支援 agent→agent 跨域委派（auto capability matching）

Version: 4.1.0
Created: 2026-03-16
Updated: 2026-04-08
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from app.services.ai.federation_discovery import load_configs, maybe_refresh
from app.services.ai import federation_delegation

logger = logging.getLogger(__name__)

# 本系統 ID
_SELF_AGENT_ID = "ck_missive"


class FederationClient:
    """
    聯邦式 AI 系統客戶端 v4.1 — NemoClaw Registry 動態服務發現 + 跨域委派

    啟動時自動查詢 NemoClaw Registry 取得所有 active 插件，
    排除自身後建構可用系統清單。每 60 秒 lazy refresh。

    Usage:
        client = get_federation_client()
        systems = client.list_available_systems()  # 動態清單
        if client.is_available("tunnel"):
            result = await client.query_external("tunnel", "隧道裂縫統計")
    """

    def __init__(self) -> None:
        self._configs: Dict[str, Dict[str, str]] = {}
        self._system_meta: Dict[str, Dict[str, Any]] = {}
        self._last_refresh: float = 0.0
        self._discovery_source: str = "none"
        self._discovery_source = load_configs(self._configs, self._system_meta)
        self._last_refresh = time.monotonic()

    # ── 服務發現 (委派至 federation_discovery) ─────────────

    def _maybe_refresh(self) -> None:
        """TTL 到期時 lazy refresh Registry"""
        new_ts, new_source = maybe_refresh(
            self._last_refresh, self._configs, self._system_meta
        )
        self._last_refresh = new_ts
        if new_source is not None:
            self._discovery_source = new_source

    # ── 查詢介面 ──────────────────────────────────────────────

    def is_available(self, system_id: str) -> bool:
        """檢查指定系統是否已設定（URL 存在即視為可用）"""
        self._maybe_refresh()
        return system_id in self._configs

    def list_available_systems(self) -> List[Dict[str, Any]]:
        """列出所有已設定的聯邦 AI 系統（動態發現）"""
        self._maybe_refresh()
        systems = []
        for system_id in self._configs:
            meta = self._system_meta.get(system_id, {})
            systems.append({
                "id": system_id,
                "name": meta.get("name", system_id),
                "description": meta.get("description", ""),
                "available": True,
                "status": meta.get("status", "unknown"),
                "source": self._discovery_source,
            })
        return systems

    async def query_external(
        self,
        system_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        向外部聯邦 AI 系統發送 Schema v1.0 查詢

        Args:
            system_id: 系統識別碼 (如 "openclaw", "lvrland", "tunnel")
            question: 查詢問題
            context: 附加上下文 (可選)
            timeout: 請求超時秒數

        Returns:
            { system, success, answer, tools_used, latency_ms, error }
        """
        self._maybe_refresh()

        if not self.is_available(system_id):
            return self._error_result(
                system_id,
                f"外部系統 '{system_id}' 未發現 (Registry source: {self._discovery_source})",
            )

        config = self._configs[system_id]
        url = f"{config['url']}{config['endpoint']}"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if config["token"]:
            headers["X-Service-Token"] = config["token"]

        payload: Dict[str, Any] = {
            "agent_id": _SELF_AGENT_ID,
            "action": "reason",
            "payload": {
                "question": question,
                "context": context or {},
            },
            "session_id": f"federation_{system_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        start = time.monotonic()

        try:
            if httpx is None:
                raise ImportError("httpx not installed")

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code != 200:
                    logger.warning(
                        "Federation query to %s failed: HTTP %d",
                        system_id,
                        resp.status_code,
                    )
                    return self._error_result(
                        system_id,
                        f"HTTP {resp.status_code}: {resp.text[:200]}",
                        elapsed_ms,
                    )

                data = resp.json()
                success = data.get("success", False)
                result = data.get("result") or {}
                meta = data.get("meta") or {}
                error_obj = data.get("error") or {}

                return {
                    "system": system_id,
                    "success": success,
                    "answer": result.get("answer", "") if isinstance(result, dict) else "",
                    "tools_used": result.get("tools_used", []) if isinstance(result, dict) else [],
                    "latency_ms": meta.get("latency_ms", elapsed_ms) if isinstance(meta, dict) else elapsed_ms,
                    "error": error_obj.get("message") if isinstance(error_obj, dict) and not success else None,
                }

        except ImportError:
            logger.error("httpx not installed; federation client unavailable")
            return self._error_result(system_id, "httpx 未安裝，無法呼叫外部系統")
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "Federation query to %s failed: %s", system_id, e
            )
            return self._error_result(
                system_id,
                f"連線失敗: {type(e).__name__}: {e}",
                elapsed_ms,
            )

    # ── 跨域委派 (委派至 federation_delegation) ────────────

    async def delegate(
        self,
        target_agent_id: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        forward_action: str = "reason",
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """透過 NemoClaw Gateway 將任務委派至其他插件"""
        self._maybe_refresh()
        return await federation_delegation.delegate(
            target_agent_id, intent, context, forward_action, timeout
        )

    async def delegate_with_patterns(
        self,
        query: str,
        context: str = "",
        max_patterns: int = 5,
    ) -> Dict[str, Any]:
        """Delegate query with learned patterns sharing."""
        return await federation_delegation.delegate_with_patterns(
            query, context, max_patterns
        )

    async def delegate_auto(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """自動路由委派"""
        return await federation_delegation.delegate_auto(intent, context, timeout)

    @staticmethod
    def _delegate_error(
        target: str, error: str, latency_ms: int = 0
    ) -> Dict[str, Any]:
        return federation_delegation.delegate_error(target, error, latency_ms)

    @staticmethod
    def _error_result(
        system_id: str, error: str, latency_ms: int = 0
    ) -> Dict[str, Any]:
        return {
            "system": system_id,
            "success": False,
            "answer": "",
            "tools_used": [],
            "latency_ms": latency_ms,
            "error": error,
        }


# ============================================================================
# 單例
# ============================================================================

_client: Optional[FederationClient] = None
_client_lock = threading.Lock()


def get_federation_client() -> FederationClient:
    """取得全域 FederationClient 單例（thread-safe）"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = FederationClient()
    return _client
