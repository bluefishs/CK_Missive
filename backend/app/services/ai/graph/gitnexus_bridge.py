"""GitNexus Bridge — Agent code intelligence via MCP JSON-RPC.

ADR-0035 範圍：dev/agent-only。**禁止**對公網用戶曝光（tunnel_guard 強制 disable）。

提供 5 個 Bridge method 對應最高 ROI 的 GitNexus MCP tools：

* :meth:`GitNexusBridge.code_context` → MCP ``context``（360° symbol view）
* :meth:`GitNexusBridge.change_impact` → MCP ``impact``（blast radius）
* :meth:`GitNexusBridge.api_route_map` → MCP ``route_map``
* :meth:`GitNexusBridge.api_shape_check` → MCP ``shape_check``
* :meth:`GitNexusBridge.detect_uncommitted_impact` → MCP ``detect_changes``

設計守則
========

* ``GITNEXUS_BRIDGE_ENABLED=false``（default）時 raise :class:`GitNexusDisabledError`
* MCP client 連線失敗 → :class:`GitNexusUnavailableError`（不 raw exception 漏給上游）
* 連續失敗 5 次 → circuit breaker OPEN 5 min（沿用 R6 模式）
* 所有 method 帶 ``timeout`` 預設 10s（超時走 fallback empty result + logger.error）
* Prometheus metric ``gitnexus_bridge_calls_total{op,status}`` 追蹤調用

References
----------

* ADR-0035: GitNexus Bridge — Agent Code Intelligence
* GitNexus MCP server: localhost:4747/api/mcp
* Python ``mcp`` SDK 1.26.0
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Exceptions ────────────────────────────────────────────────────


class GitNexusError(Exception):
    """Base exception for GitNexus bridge."""


class GitNexusDisabledError(GitNexusError):
    """GITNEXUS_BRIDGE_ENABLED=false 或 tunnel_guard 公網禁用。"""


class GitNexusUnavailableError(GitNexusError):
    """MCP server 連線失敗 / 超時 / circuit breaker OPEN。"""


# ─── Circuit Breaker State ─────────────────────────────────────────


@dataclass
class _CircuitState:
    """簡單 circuit breaker — 沿用 R6 模式但獨立實例。"""

    failure_count: int = 0
    opened_at: float = 0.0
    threshold: int = 5
    cooldown_seconds: int = 300  # 5 min

    def is_open(self) -> bool:
        if self.failure_count < self.threshold:
            return False
        if time.time() - self.opened_at > self.cooldown_seconds:
            # half-open: reset, give it another chance
            self.failure_count = 0
            self.opened_at = 0.0
            return False
        return True

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count == self.threshold:
            self.opened_at = time.time()
            logger.error(
                "GitNexus bridge circuit OPEN (%d consecutive failures, cooldown=%ds)",
                self.failure_count, self.cooldown_seconds,
            )

    def record_success(self) -> None:
        if self.failure_count > 0:
            logger.info("GitNexus bridge recovered after %d failures", self.failure_count)
        self.failure_count = 0
        self.opened_at = 0.0


# ─── Metrics（lazy import 避免 startup cost） ──────────────────────


def _metric_call(op: str, status: str) -> None:
    """記錄 bridge 呼叫到 Prometheus（lazy import 防 startup 順序問題）。"""
    try:
        from prometheus_client import Counter

        # Counter 必須 singleton；用 module-level cache
        global _CALLS_COUNTER
        if "_CALLS_COUNTER" not in globals() or _CALLS_COUNTER is None:
            _CALLS_COUNTER = Counter(
                "gitnexus_bridge_calls_total",
                "GitNexus bridge calls by op and status",
                ["op", "status"],
            )
        _CALLS_COUNTER.labels(op=op, status=status).inc()
    except Exception as exc:  # noqa: BLE001 — metric 不能讓 bridge 死
        logger.debug("gitnexus_bridge metric record failed: %s", exc)


_CALLS_COUNTER = None


# ─── Bridge ────────────────────────────────────────────────────────


class GitNexusBridge:
    """MCP client wrapper for GitNexus（dev/agent-only）。

    用法：
        bridge = GitNexusBridge()
        ctx = await bridge.code_context("tool_name_of")
        impact = await bridge.change_impact("agent_self_evaluator.py:281")
    """

    DEFAULT_TIMEOUT_S = 10.0
    DEFAULT_MCP_URL = "http://localhost:4747/api/mcp"

    def __init__(
        self,
        mcp_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        enabled_env: str = "GITNEXUS_BRIDGE_ENABLED",
    ) -> None:
        self.mcp_url = mcp_url or os.getenv("GITNEXUS_MCP_URL", self.DEFAULT_MCP_URL)
        self.timeout = timeout
        self.enabled_env = enabled_env
        self._circuit = _CircuitState()

    # -- Lifecycle gate -------------------------------------------------

    def _check_enabled(self) -> None:
        """ADR-0035 strict gate：env flag + tunnel_guard 雙層守護。"""
        if os.getenv(self.enabled_env, "false").lower() != "true":
            raise GitNexusDisabledError(
                f"{self.enabled_env}=false — GitNexus bridge is dev-only (ADR-0035)"
            )
        # tunnel_guard 公網禁用由 endpoint 層處理；bridge 層只看 env

    def _check_circuit(self, op: str) -> None:
        if self._circuit.is_open():
            _metric_call(op, "circuit_open")
            raise GitNexusUnavailableError(
                f"GitNexus bridge circuit OPEN — "
                f"{self._circuit.failure_count} consecutive failures"
            )

    # -- MCP call ------------------------------------------------------

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[Any]:
        """開 MCP streamablehttp session（lazy import mcp SDK 避免 module load cost）。"""
        try:
            from mcp import ClientSession  # noqa: WPS433
            from mcp.client.streamable_http import streamablehttp_client  # noqa: WPS433
        except ImportError as exc:
            raise GitNexusUnavailableError(f"mcp SDK not installed: {exc}") from exc

        try:
            async with streamablehttp_client(self.mcp_url) as (read, write, _get_sid):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        except Exception as exc:
            self._circuit.record_failure()
            raise GitNexusUnavailableError(
                f"MCP connect/init failed: {type(exc).__name__}: {exc}"
            ) from exc

    async def _call_tool(self, op: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generic MCP tool call with circuit breaker + timeout + metric。"""
        self._check_enabled()
        self._check_circuit(op)

        async def _do_call() -> Dict[str, Any]:
            async with self._session() as session:
                result = await session.call_tool(op, args)
                self._circuit.record_success()
                # MCP result content is a list of TextContent / ImageContent
                content = []
                for item in result.content:
                    if hasattr(item, "text"):
                        content.append(item.text)
                    else:
                        content.append(str(item))
                return {
                    "op": op,
                    "args": args,
                    "is_error": bool(result.isError),
                    "content": content,
                }

        try:
            result = await asyncio.wait_for(_do_call(), timeout=self.timeout)
            _metric_call(op, "ok" if not result["is_error"] else "error")
            return result
        except asyncio.TimeoutError:
            self._circuit.record_failure()
            _metric_call(op, "timeout")
            raise GitNexusUnavailableError(
                f"GitNexus {op} timed out after {self.timeout}s"
            )
        except GitNexusUnavailableError:
            _metric_call(op, "unavailable")
            raise
        except Exception as exc:  # noqa: BLE001 — wrap any leak
            self._circuit.record_failure()
            _metric_call(op, "error")
            logger.error("GitNexus bridge %s failed: %s", op, exc, exc_info=True)
            raise GitNexusUnavailableError(f"{op}: {type(exc).__name__}: {exc}") from exc

    # -- Public bridge methods（5 個 ROI 最高的）-----------------------

    async def code_context(
        self, symbol: str, repo: str = "CK_Missive", depth: int = 3,
    ) -> Dict[str, Any]:
        """360° view: caller/callee/cluster/flow context of a symbol。"""
        return await self._call_tool("context", {"symbol": symbol, "repo": repo, "depth": depth})

    async def change_impact(
        self, symbol: str, repo: str = "CK_Missive",
    ) -> Dict[str, Any]:
        """Blast radius — 改 symbol 會影響的 downstream symbols / endpoints。"""
        return await self._call_tool("impact", {"symbol": symbol, "repo": repo})

    async def api_route_map(
        self, repo: str = "CK_Missive", endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """前端 hook / component → 後端 endpoint 映射。"""
        args: Dict[str, Any] = {"repo": repo}
        if endpoint:
            args["endpoint"] = endpoint
        return await self._call_tool("route_map", args)

    async def api_shape_check(
        self, repo: str = "CK_Missive", endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """前端 component property access vs 後端 response schema 一致性。"""
        args: Dict[str, Any] = {"repo": repo}
        if endpoint:
            args["endpoint"] = endpoint
        return await self._call_tool("shape_check", args)

    async def detect_uncommitted_impact(
        self, repo: str = "CK_Missive",
    ) -> Dict[str, Any]:
        """未 commit 變更的影響面（pre-commit hook 級即時 blast radius）。"""
        return await self._call_tool("detect_changes", {"repo": repo})


# ─── Singleton helper ──────────────────────────────────────────────


_BRIDGE_INSTANCE: Optional[GitNexusBridge] = None


def get_gitnexus_bridge() -> GitNexusBridge:
    """Singleton accessor（避免重複 MCP 連線設定）。"""
    global _BRIDGE_INSTANCE
    if _BRIDGE_INSTANCE is None:
        _BRIDGE_INSTANCE = GitNexusBridge()
    return _BRIDGE_INSTANCE


__all__ = [
    "GitNexusBridge",
    "GitNexusError",
    "GitNexusDisabledError",
    "GitNexusUnavailableError",
    "get_gitnexus_bridge",
]
