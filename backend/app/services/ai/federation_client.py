"""
Federation Client -- 聯邦式 AI 系統間呼叫客戶端

啟用 CK_Missive 智能體委派查詢至外部 AI 系統（如 CK_OpenClaw），
處理超出本系統專業範圍的問題。

設計原則:
- 讀取 OPENCLAW_URL / MCP_SERVICE_TOKEN 環境變數
- httpx 非同步客戶端，30 秒超時
- 未設定或不可達時優雅降級（回傳明確錯誤，不中斷對話）

Version: 1.0.0
Created: 2026-03-16
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class FederationClient:
    """
    聯邦式 AI 系統客戶端

    目前支援的系統:
    - "openclaw": CK_OpenClaw 多頻道 AI 管道

    Usage:
        client = get_federation_client()
        if client.is_available("openclaw"):
            result = await client.query_external("openclaw", "什麼是 OpenClaw?")
    """

    # 已知的外部系統定義
    _SYSTEM_REGISTRY: Dict[str, Dict[str, str]] = {
        "openclaw": {
            "name": "CK_OpenClaw",
            "description": "多頻道 AI 管道系統 (228 agent 模組, 30+ 頻道)",
            "url_env": "OPENCLAW_URL",
            "token_env": "MCP_SERVICE_TOKEN",
            "endpoint": "/api/ai/agent/query",
            "default_url": "http://localhost:3001",
        },
    }

    def __init__(self) -> None:
        self._configs: Dict[str, Dict[str, str]] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """從環境變數載入各系統的連線設定"""
        for system_id, registry in self._SYSTEM_REGISTRY.items():
            url = os.getenv(registry["url_env"], "")
            token = os.getenv(registry["token_env"], "")
            if url:
                self._configs[system_id] = {
                    "url": url.rstrip("/"),
                    "token": token,
                    "endpoint": registry["endpoint"],
                }
                logger.info(
                    "Federation system '%s' configured: %s",
                    system_id,
                    url,
                )

    def is_available(self, system_id: str) -> bool:
        """檢查指定系統是否已設定（URL 存在即視為可用）"""
        return system_id in self._configs

    def list_available_systems(self) -> List[Dict[str, Any]]:
        """列出所有已設定的聯邦 AI 系統"""
        systems = []
        for system_id, registry in self._SYSTEM_REGISTRY.items():
            systems.append({
                "id": system_id,
                "name": registry["name"],
                "description": registry["description"],
                "available": self.is_available(system_id),
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
        向外部聯邦 AI 系統發送查詢

        Args:
            system_id: 系統識別碼 (如 "openclaw")
            question: 查詢問題
            context: 附加上下文 (可選)
            timeout: 請求超時秒數

        Returns:
            {
                "system": str,
                "success": bool,
                "answer": str,
                "tools_used": list,
                "latency_ms": int,
                "error": str | None,
            }
        """
        if system_id not in self._SYSTEM_REGISTRY:
            return self._error_result(
                system_id, f"未知的外部系統: {system_id}"
            )

        if not self.is_available(system_id):
            registry = self._SYSTEM_REGISTRY[system_id]
            return self._error_result(
                system_id,
                f"外部系統 {registry['name']} 未設定 (需設定環境變數 {registry['url_env']})",
            )

        config = self._configs[system_id]
        url = f"{config['url']}{config['endpoint']}"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if config["token"]:
            headers["X-Service-Token"] = config["token"]

        payload: Dict[str, Any] = {
            "question": question,
            "session_id": f"federation_{system_id}",
        }
        if context:
            payload["context"] = context

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

                return {
                    "system": system_id,
                    "success": success,
                    "answer": data.get("answer", ""),
                    "tools_used": data.get("tools_used", []),
                    "latency_ms": elapsed_ms,
                    "error": data.get("error") if not success else None,
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


def get_federation_client() -> FederationClient:
    """取得全域 FederationClient 單例"""
    global _client
    if _client is None:
        _client = FederationClient()
    return _client
