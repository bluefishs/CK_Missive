"""Agent Stream Helper -- Shared streaming + status logic for all channels.

Collects SSE events from agent orchestrator and provides:
- Token buffering with periodic flush
- Tool call status tracking
- Final answer assembly
- Channel-agnostic status callbacks

Used by: discord_bot_service, telegram_bot_service, line_bot_service

Version: 1.0.0
Created: 2026-04-05
"""

import logging
import time
from typing import AsyncGenerator, Callable, Awaitable, Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StreamResult:
    """Result of streaming an agent query."""

    answer: str
    tools_used: List[str]
    latency_ms: float
    token_count: int


class AgentStreamCollector:
    """Collects agent SSE events and calls back on status changes.

    The event_stream must yield raw SSE strings (``data: {...}``) as produced
    by ``AgentOrchestrator.stream_agent_query``.  The collector parses each
    line, buffers tokens, tracks tool calls, and invokes optional callbacks
    for status changes and partial-text updates (edit-streaming).
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_text_update: Optional[Callable[[str], Awaitable[None]]] = None,
        update_interval: float = 1.5,
    ):
        """
        Args:
            on_status_change: async callback(emoji, description) when status changes.
            on_text_update: async callback(partial_text) for edit-streaming channels.
            update_interval: minimum seconds between ``on_text_update`` calls.
        """
        self.on_status_change = on_status_change
        self.on_text_update = on_text_update
        self.update_interval = update_interval
        self._tokens: List[str] = []
        self._tools: List[str] = []
        self._last_update = 0.0
        self._start_time = 0.0
        self._had_error = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def collect(
        self,
        event_stream: AsyncGenerator[str, None],
    ) -> StreamResult:
        """Consume all SSE events, calling back as appropriate.

        Args:
            event_stream: async generator yielding ``"data: {json}"`` strings
                          (from ``AgentOrchestrator.stream_agent_query``).

        Returns:
            StreamResult with assembled answer, tools, latency, token count.
        """
        import json

        self._start_time = time.monotonic()
        self._last_update = self._start_time

        if self.on_status_change:
            await self.on_status_change("\U0001f914", "\u601d\u8003\u4e2d")  # thinking

        async for event_str in event_stream:
            if not event_str.startswith("data: "):
                continue
            try:
                event = json.loads(event_str[6:])
            except (json.JSONDecodeError, IndexError):
                continue

            etype = event.get("type", "")

            if etype == "token":
                self._tokens.append(event.get("token", ""))
                # Periodic text update for edit-streaming channels
                now = time.monotonic()
                if (
                    self.on_text_update
                    and (now - self._last_update >= self.update_interval)
                    and self._tokens
                ):
                    try:
                        await self.on_text_update("".join(self._tokens))
                    except Exception:
                        logger.debug("on_text_update callback failed", exc_info=True)
                    self._last_update = now

            elif etype == "tool_call":
                tool = event.get("tool", "")
                if tool and tool not in self._tools:
                    self._tools.append(tool)
                if self.on_status_change:
                    emoji = self._tool_emoji(tool)
                    await self.on_status_change(emoji, f"\u57f7\u884c {tool}")

            elif etype == "thinking":
                if self.on_status_change:
                    await self.on_status_change("\U0001f914", "\u601d\u8003\u4e2d")

            elif etype == "error":
                self._had_error = True
                self._tokens.append(event.get("error", "\u67e5\u8a62\u5931\u6557"))
                if self.on_status_change:
                    await self.on_status_change("\u274c", "\u932f\u8aa4")

        # Final status callback
        if self.on_status_change:
            final_emoji = "\u274c" if self._had_error else "\u2705"
            final_desc = "\u932f\u8aa4" if self._had_error else "\u5b8c\u6210"
            await self.on_status_change(final_emoji, final_desc)

        answer = "".join(self._tokens) or "\u7121\u6cd5\u7522\u751f\u56de\u7b54\uff0c\u8acb\u63db\u500b\u65b9\u5f0f\u63d0\u554f\u3002"
        elapsed = (time.monotonic() - self._start_time) * 1000

        return StreamResult(
            answer=answer,
            tools_used=list(self._tools),
            latency_ms=round(elapsed, 1),
            token_count=len(self._tokens),
        )

    @property
    def had_error(self) -> bool:
        return self._had_error

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_emoji(tool_name: str) -> str:
        """Map a tool name to a representative emoji."""
        lower = (tool_name or "").lower()
        if "search" in lower or "find" in lower:
            return "\U0001f50d"  # magnifying glass
        if "graph" in lower or "entity" in lower:
            return "\U0001f578\ufe0f"  # spider web
        if "diagram" in lower or "draw" in lower:
            return "\U0001f3a8"  # palette
        if "vision" in lower or "ocr" in lower:
            return "\U0001f441\ufe0f"  # eye
        return "\u2699\ufe0f"  # gear

    @staticmethod
    def build_tool_footer(tools: List[str], max_tools: int = 5) -> str:
        """Build a tool-usage footer string."""
        if not tools:
            return ""
        names = "\u3001".join(tools[:max_tools])
        return f"\n\n\U0001f527 {names}"
