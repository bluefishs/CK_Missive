"""Port 預設實作 — v6.12 B 方案收口 (2026-05-30)

v6.10 P1 原 4 adapter，v6.12 B 方案 audit/cache 0 caller 廢棄。

保留 (2 active)：
- DefaultRLSAdapter       (calendar/notification repository 2 production caller)
- DefaultMessagingAdapter (IntegrationFacade 用)

廢棄 (2026-05-30 移除)：
- DefaultAuditAdapter (audit mixin 直用)
- DefaultCacheAdapter (Redis 直用)
"""
from app.services.contracts.adapters.rls_default import DefaultRLSAdapter
from app.services.contracts.adapters.messaging_default import DefaultMessagingAdapter

__all__ = [
    "DefaultRLSAdapter",
    "DefaultMessagingAdapter",
]
