"""Port 預設實作（Hexagonal Architecture / Ports & Adapters）— v6.10 P1

匯總出口（4/4 完成 — 2026-05-18）：
- DefaultRLSAdapter       (rls_default.py)
- DefaultAuditAdapter     (audit_default.py)
- DefaultMessagingAdapter (messaging_default.py)
- DefaultCacheAdapter     (cache_default.py)
"""
from app.services.contracts.adapters.rls_default import DefaultRLSAdapter
from app.services.contracts.adapters.audit_default import DefaultAuditAdapter
from app.services.contracts.adapters.messaging_default import DefaultMessagingAdapter
from app.services.contracts.adapters.cache_default import DefaultCacheAdapter

__all__ = [
    "DefaultRLSAdapter",
    "DefaultAuditAdapter",
    "DefaultMessagingAdapter",
    "DefaultCacheAdapter",
]
