"""Event Bus — In-process async event bus with optional Redis pub/sub.

Usage:
    bus = EventBus.get_instance()
    bus.subscribe(EventType.CASE_CREATED, handle_case_created)
    await bus.publish(case_created("CK2026_PM_01_001", "測量案", 2026))
"""
import logging
from typing import Callable, Awaitable, Dict, List

from app.core.domain_events import DomainEvent, EventType

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """In-process async event bus with optional Redis pub/sub for cross-process."""

    _instance = None
    _handlers: Dict[EventType, List[EventHandler]] = {}

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._handlers = {}
        return cls._instance

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type.value)

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to in-process handlers + optionally Redis."""
        handlers = self._handlers.get(event.event_type, [])
        logger.info(
            "Publishing %s to %d handlers", event.event_type.value, len(handlers)
        )

        # In-process handlers (fire-and-forget with error isolation)
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "Event handler %s failed for %s: %s",
                    handler.__name__,
                    event.event_type.value,
                    e,
                )

        # Optional: Redis pub/sub for cross-process
        try:
            from app.core.redis_client import get_redis

            redis = await get_redis()
            if redis:
                channel = f"events:{event.event_type.value}"
                await redis.publish(channel, event.to_json())
        except Exception as e:
            logger.debug("Redis event publish skipped: %s", e)

    def clear(self) -> None:
        """Clear all handlers (for testing)."""
        self._handlers.clear()
