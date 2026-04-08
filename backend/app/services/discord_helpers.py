"""
Discord Bot Helpers -- constants, StatusIndicator, and formatting utilities.

Extracted from discord_bot_service.py to keep the main service under 500L.

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Discord Embed colours
COLOR_SUCCESS = 0x52C41A  # green
COLOR_INFO = 0x1890FF     # blue
COLOR_WARNING = 0xFAAD14  # yellow
COLOR_ERROR = 0xFF4D4F    # red

# Reply length limits
MAX_EMBED_DESCRIPTION = 4096
MAX_MESSAGE_CONTENT = 2000

# Edit-Streaming settings
EDIT_INTERVAL = 1.5       # seconds -- Discord API rate-limit friendly
SAFE_CONTENT_LEN = 1900   # 2000 char limit minus room for cursor/prefix


class StatusIndicator:
    """Message-prefix status indicators for Discord (HTTP webhook mode).

    Since Interactions Endpoint mode has no gateway connection, we cannot
    add/remove reactions. Instead, we prepend a status emoji line to the
    message content during edits.

    Inspired by agent-broker's reaction-based status pattern, adapted
    for HTTP webhook mode.
    """

    THINKING = "\U0001f914"       # thinking face
    TOOL_CODE = "\u2699\ufe0f"    # gear
    TOOL_SEARCH = "\U0001f50d"    # magnifying glass
    TOOL_GRAPH = "\U0001f578\ufe0f"  # spider web
    DONE = "\u2705"               # check mark
    ERROR = "\u274c"              # cross mark
    STALL = "\u23f3"              # hourglass

    def __init__(self):
        self._current = self.THINKING
        self._last_activity = time.monotonic()

    @property
    def current(self) -> str:
        return self._current

    def set_status(self, emoji: str) -> None:
        """Update current status emoji."""
        self._current = emoji
        self._last_activity = time.monotonic()

    def on_tool_call(self, tool_name: str) -> None:
        """Map tool name to appropriate status emoji."""
        lower = tool_name.lower()
        if "search" in lower or "find" in lower:
            self.set_status(self.TOOL_SEARCH)
        elif "graph" in lower or "entity" in lower:
            self.set_status(self.TOOL_GRAPH)
        else:
            self.set_status(self.TOOL_CODE)

    def is_stalled(self, timeout: float = 10.0) -> bool:
        return time.monotonic() - self._last_activity > timeout

    def format_prefix(self) -> str:
        """Generate a status prefix line for the message."""
        return f"{self._current} "


def truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if truncated."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


async def edit_followup(webhook_base: str, content: str) -> None:
    """Edit the original followup message via Discord webhook."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{webhook_base}/messages/@original",
                json={"content": content[:MAX_MESSAGE_CONTENT]},
                timeout=10,
            )
    except Exception as e:
        logger.debug("Discord edit followup failed: %s", e)


def make_embed_response(
    title: str, description: str, color: int = COLOR_INFO,
) -> Dict[str, Any]:
    """Build a Discord Interaction Response (type 4)."""
    return {
        "type": 4,
        "data": {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": "CK Missive Agent"},
            }],
        },
    }


def make_fields_embed(
    title: str, fields: list, color: int = COLOR_INFO,
) -> Dict[str, Any]:
    """Build a Discord Embed with fields (type 4)."""
    embed_fields = [
        {"name": f["name"], "value": f["value"], "inline": f.get("inline", False)}
        for f in fields
    ]
    return {
        "type": 4,
        "data": {
            "embeds": [{
                "title": title,
                "color": color,
                "fields": embed_fields,
                "footer": {"text": "CK Missive Agent"},
            }],
        },
    }
