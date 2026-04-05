"""
Federation Client -- 聯邦式 AI 系統間呼叫客戶端 v4.0.0

啟用 CK_Missive 智能體委派查詢至外部 AI 系統。
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

Version: 4.0.0
Created: 2026-03-16
Updated: 2026-03-21
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

logger = logging.getLogger(__name__)

# 本系統 ID — 從 Registry 發現時排除自身
_SELF_PLUGIN_ID = "ck-missive"
_SELF_AGENT_ID = "ck_missive"

# NemoClaw Registry 端點
_REGISTRY_URL = os.getenv(
    "NEMOCLAW_REGISTRY_URL", "http://nemoclaw_tower:9000/api/registry"
)
_REGISTRY_TIMEOUT = 5.0  # Registry 查詢超時（秒）
_REGISTRY_REFRESH_TTL = 60  # 自動重新整理間隔（秒）

# 靜態回退表 — 僅在 Registry 不可達時使用
_FALLBACK_REGISTRY: Dict[str, Dict[str, str]] = {
    "openclaw": {
        "name": "CK_OpenClaw",
        "description": "多頻道 AI 管道系統 (via NemoClaw Gateway)",
        "url_env": "NEMOCLAW_GATEWAY_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/gateway/reason",
        "default_url": "http://nemoclaw_tower:9000",
    },
    "lvrland": {
        "name": "CK_lvrland_Webmap",
        "description": "地圖測繪引擎",
        "url_env": "LVRLAND_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/map/query",
        "default_url": "http://ck-lvrland:8000",
    },
    "tunnel": {
        "name": "CK_DigitalTunnel",
        "description": "隧道監控引擎",
        "url_env": "TUNNEL_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/tunnel/query",
        "default_url": "http://ck-tunnel:8000",
    },
}


class FederationClient:
    """
    聯邦式 AI 系統客戶端 v4.0 — NemoClaw Registry 動態服務發現 + 跨域委派

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
        self._load_configs()

    # ── 服務發現 ──────────────────────────────────────────────

    def _load_configs(self) -> None:
        """從 NemoClaw Registry 動態載入，失敗時回退至環境變數"""
        if self._try_load_from_registry():
            self._discovery_source = "registry"
        else:
            self._load_from_fallback()
            self._discovery_source = "fallback"
        self._last_refresh = time.monotonic()

    def _try_load_from_registry(self) -> bool:
        """同步查詢 NemoClaw Registry API（啟動/刷新時呼叫）"""
        if httpx is None:
            return False

        token = os.getenv("MCP_SERVICE_TOKEN", "")
        headers: Dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["X-Service-Token"] = token

        try:
            with httpx.Client(timeout=_REGISTRY_TIMEOUT) as client:
                resp = client.get(_REGISTRY_URL, headers=headers)
                if resp.status_code != 200:
                    logger.warning(
                        "NemoClaw Registry returned HTTP %d", resp.status_code
                    )
                    return False

                data = resp.json()
                self._parse_registry_response(data)
                logger.info(
                    "Federation loaded %d systems from NemoClaw Registry",
                    len(self._configs),
                )
                return True

        except Exception as e:
            logger.warning("NemoClaw Registry unreachable: %s", e)
            return False

    def _parse_registry_response(self, data: Dict[str, Any]) -> None:
        """解析 Registry JSON 並建構 _configs + _system_meta"""
        self._configs.clear()
        self._system_meta.clear()

        token = os.getenv("MCP_SERVICE_TOKEN", "")

        # Engine (OpenClaw) — 透過 NemoClaw Gateway scheduler 調度
        # v3.0: 流量改道至 /api/gateway/reason（P2 scheduler: Queue + Quota + Priority）
        engine: Dict[str, Any] = data.get("engine") or {}
        engine_url: str = str(engine.get("url", ""))
        engine_status: str = str(engine.get("status", ""))
        if engine_url and engine_status in ("active", "degraded"):
            engine_name: str = str(engine.get("name", "openclaw"))
            # 改打 NemoClaw Gateway 而非直接打 OpenClaw
            gateway_url = os.getenv(
                "NEMOCLAW_GATEWAY_URL",
                _REGISTRY_URL.rsplit("/api/registry", 1)[0],  # http://nemoclaw_tower:9000
            )
            self._configs[engine_name] = {
                "url": gateway_url.rstrip("/"),
                "token": token,
                "endpoint": "/api/gateway/reason",
            }
            # 若 fallback 表有定義名稱則優先使用，避免 .title() 大小寫不一致
            fallback_name = (_FALLBACK_REGISTRY.get(engine_name) or {}).get("name")
            self._system_meta[engine_name] = {
                "name": fallback_name or f"CK_{engine_name.title()}",
                "description": "多頻道 AI 管道系統",
                "status": engine_status,
            }

        # Plugins（排除自身）
        for plugin in data.get("plugins") or []:
            plugin_id: str = plugin.get("id", "")
            if not plugin_id or plugin_id == _SELF_PLUGIN_ID:
                continue
            if not plugin.get("enabled"):
                continue

            # 將 "ck-lvrland" → "lvrland", "ck-tunnel" → "tunnel"
            system_id = plugin_id.removeprefix("ck-")
            url = plugin.get("url", "")
            api_path = plugin.get("api_path", "")

            if not url:
                continue

            self._configs[system_id] = {
                "url": url.rstrip("/"),
                "token": token,
                "endpoint": api_path or "/health",
            }
            self._system_meta[system_id] = {
                "name": plugin_id,
                "description": plugin.get("description", ""),
                "status": plugin.get("status", "unknown"),
                "capabilities": plugin.get("capabilities", []),
            }

    def _load_from_fallback(self) -> None:
        """從環境變數 + 靜態回退表載入（Registry 不可達時）"""
        self._configs.clear()
        self._system_meta.clear()
        token = os.getenv("MCP_SERVICE_TOKEN", "")

        for system_id, registry in _FALLBACK_REGISTRY.items():
            url = os.getenv(registry["url_env"], "") or registry.get("default_url", "")
            if url:
                self._configs[system_id] = {
                    "url": url.rstrip("/"),
                    "token": token,
                    "endpoint": registry["endpoint"],
                }
                self._system_meta[system_id] = {
                    "name": registry["name"],
                    "description": registry["description"],
                    "status": "unknown",
                }
                source = "env" if os.getenv(registry["url_env"], "") else "default"
                logger.info(
                    "Federation fallback '%s': %s (%s)",
                    system_id,
                    url,
                    source,
                )

    def _maybe_refresh(self) -> None:
        """TTL 到期時 lazy refresh Registry"""
        if time.monotonic() - self._last_refresh > _REGISTRY_REFRESH_TTL:
            self._load_configs()

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

    # ── 跨域委派 (v4.0) ────────────────────────────────────

    async def delegate(
        self,
        target_agent_id: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        forward_action: str = "reason",
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        透過 NemoClaw Gateway 將任務委派至其他插件

        Args:
            target_agent_id: 目標插件 ID（如 "ck-tunnel"）或 "auto" 自動匹配
            intent: 委派意圖描述（自然語言）
            context: 跨域上下文（可選）
            forward_action: 轉發至目標的 action 類型（reason/query）
            timeout: 請求超時秒數

        Returns:
            { system, success, target_agent_id, delegated, target_response,
              routing_reason, latency_ms, error }
        """
        self._maybe_refresh()

        gateway_url = os.getenv(
            "NEMOCLAW_GATEWAY_URL",
            _REGISTRY_URL.rsplit("/api/registry", 1)[0],
        )
        url = f"{gateway_url.rstrip('/')}/api/gateway/delegate"
        token = os.getenv("MCP_SERVICE_TOKEN", "")

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["X-Service-Token"] = token

        payload: Dict[str, Any] = {
            "agent_id": _SELF_AGENT_ID,
            "action": "delegate",
            "payload": {
                "target_agent_id": target_agent_id,
                "intent": intent,
                "forward_action": forward_action,
                "context": context or {},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        start = time.monotonic()

        try:
            if httpx is None:
                raise ImportError("httpx not installed")

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                data = resp.json()
                success = data.get("success", False)
                result = data.get("result") or {}
                error_obj = data.get("error") or {}
                meta = data.get("meta") or {}

                return {
                    "system": target_agent_id,
                    "success": success,
                    "target_agent_id": result.get("target_agent_id", target_agent_id) if isinstance(result, dict) else target_agent_id,
                    "delegated": result.get("delegated", False) if isinstance(result, dict) else False,
                    "target_response": result.get("target_response") if isinstance(result, dict) else None,
                    "routing_reason": result.get("routing_reason", "") if isinstance(result, dict) else "",
                    "latency_ms": meta.get("latency_ms", elapsed_ms) if isinstance(meta, dict) else elapsed_ms,
                    "error": error_obj.get("message") if isinstance(error_obj, dict) and not success else None,
                }

        except ImportError:
            logger.error("httpx not installed; delegate unavailable")
            return self._delegate_error(target_agent_id, "httpx 未安裝")
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Delegate to %s failed: %s", target_agent_id, e)
            return self._delegate_error(
                target_agent_id,
                f"連線失敗: {type(e).__name__}: {e}",
                elapsed_ms,
            )

    async def delegate_with_patterns(
        self,
        query: str,
        context: str = "",
        max_patterns: int = 5,
    ) -> Dict[str, Any]:
        """Delegate query to external agent WITH learned patterns.

        Includes top successful patterns from local agent to aid external.
        Accepts contributed_patterns back from external agent.
        """
        # 1. Gather top local patterns
        local_patterns = await self._get_top_patterns(max_patterns)

        # 2. Build enhanced payload (patterns are informational for the target)
        enhanced_context: Dict[str, Any] = {
            "original_context": context,
            "source_agent": _SELF_AGENT_ID,
            "learned_patterns": local_patterns,
        }

        # 3. Delegate via existing mechanism
        result = await self.delegate(
            target_agent_id="auto",
            intent=query,
            context=enhanced_context,
        )

        # 4. If response includes contributed_patterns, merge locally
        target_resp = result.get("target_response") or {}
        contributed = (
            target_resp.get("contributed_patterns", [])
            if isinstance(target_resp, dict)
            else []
        )
        if contributed:
            merged = await self._merge_external_patterns(contributed)
            result["patterns_merged"] = merged

        return result

    async def _get_top_patterns(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top graduated patterns for sharing."""
        try:
            from app.core.redis_client import get_redis

            redis = await get_redis()
            if not redis:
                return []
            # Get top patterns by hit count from Redis sorted set
            patterns = await redis.zrevrange(
                "agent:patterns:index", 0, limit - 1, withscores=True
            )
            result: List[Dict[str, Any]] = []
            for key, score in patterns:
                if isinstance(key, bytes):
                    key = key.decode()
                detail = await redis.hgetall(f"agent:patterns:detail:{key}")
                if detail:
                    # Normalise bytes keys from Redis
                    tool_seq = detail.get(b"tool_sequence", detail.get("tool_sequence", b""))
                    query_tpl = detail.get(b"query_template", detail.get("query_template", b""))
                    if isinstance(tool_seq, bytes):
                        tool_seq = tool_seq.decode()
                    if isinstance(query_tpl, bytes):
                        query_tpl = query_tpl.decode()
                    result.append({
                        "pattern_key": key,
                        "score": score,
                        "tool_sequence": tool_seq,
                        "query_template": query_tpl,
                    })
            return result
        except Exception:
            return []

    async def _merge_external_patterns(self, patterns: List[Dict[str, Any]]) -> int:
        """Merge externally contributed patterns into local store."""
        merged = 0
        try:
            from app.core.redis_client import get_redis

            redis = await get_redis()
            if not redis:
                return 0
            for p in patterns[:10]:  # Max 10 external patterns
                raw_key = p.get("pattern_key", "")
                if not raw_key:
                    continue
                key = f"ext:{raw_key}"
                # Add with lower initial score (needs local validation)
                await redis.zadd("agent:patterns:index", {key: 0.5})
                await redis.hset(
                    f"agent:patterns:detail:{key}",
                    mapping={
                        "tool_sequence": p.get("tool_sequence", ""),
                        "query_template": p.get("query_template", ""),
                        "source_agent": p.get("source_agent", "external"),
                        "imported_at": str(datetime.now(timezone.utc)),
                    },
                )
                merged += 1
        except Exception as e:
            logger.debug("Failed to merge external patterns: %s", e)
        return merged

    async def delegate_auto(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        自動路由委派 — 由 NemoClaw Gateway 依 capabilities 匹配最佳插件

        Args:
            intent: 委派意圖描述
            context: 跨域上下文
            timeout: 超時秒數
        """
        return await self.delegate("auto", intent, context, timeout=timeout)

    @staticmethod
    def _delegate_error(
        target: str, error: str, latency_ms: int = 0
    ) -> Dict[str, Any]:
        return {
            "system": target,
            "success": False,
            "target_agent_id": target,
            "delegated": False,
            "target_response": None,
            "routing_reason": "",
            "latency_ms": latency_ms,
            "error": error,
        }

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
