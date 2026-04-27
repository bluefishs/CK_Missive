"""
Sender Context -- Standardized user identity injection for multi-channel agents.

Injects structured <sender_context> into agent prompts so the LLM knows
who is asking and from which channel.

Inspired by: agent-broker's sender_context injection pattern.

Version: 1.0.0
Created: 2026-04-05
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SenderContext:
    """Standardized sender identity for cross-channel agent queries."""

    user_id: str
    display_name: str
    channel: str  # 'discord', 'line', 'telegram', 'web', 'openclaw'
    channel_id: Optional[str] = None  # Discord channel_id, LINE group_id, etc.
    role: Optional[str] = None  # 'admin', 'user', etc.

    def to_xml(self) -> str:
        """Generate XML block for prompt injection."""
        parts = [
            "<sender_context>",
            f"  <user_id>{self.user_id}</user_id>",
            f"  <display_name>{self.display_name}</display_name>",
            f"  <channel>{self.channel}</channel>",
        ]
        if self.channel_id:
            parts.append(f"  <channel_id>{self.channel_id}</channel_id>")
        if self.role:
            parts.append(f"  <role>{self.role}</role>")
        parts.append("</sender_context>")
        return "\n".join(parts)

    def to_system_message(self) -> str:
        """Generate a brief system message for context injection."""
        role_part = f", role={self.role}" if self.role else ""
        return f"[{self.channel}] {self.display_name} ({self.user_id}{role_part})"

    def to_context_prefix(self) -> str:
        """Generate a context prefix to prepend to the question for the agent."""
        return f"[Sender: {self.display_name} via {self.channel}]"
