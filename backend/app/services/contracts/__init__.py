"""Bounded Context Contract Layer — v6.12 B 方案收口（2026-05-30）

v6.10 P1 原建 4 ports + 13 facades，30 天 audit 結果 2/4 port + 10/13 facade zero。
ADR-0036 經實證 ROI 不及預期，按 L31「ROI = entities × usage_rate」廢棄 zero entities。

保留 (2 active port + 3 active facade)：
- MessagingPort (DefaultMessagingAdapter, 3 caller via IntegrationFacade)
- RLSPort       (DefaultRLSAdapter, 2 production caller calendar/notification repository)
- IntegrationFacade / MemoryFacade / WikiFacade

廢棄 (2026-05-30)：
- AuditPort + DefaultAuditAdapter (0 caller — audit mixin 直用更簡單)
- CachePort + DefaultCacheAdapter (0 caller — Redis 直用更穩)
- 10 facade (詳 facades/__init__.py)

60 天 trial（2026-07-30 重評）→ 詳 docs/architecture/FACADE_ABC_DECISION_20260530.md
"""
from app.services.contracts.ports.messaging import MessagingPort  # noqa: F401
from app.services.contracts.ports.rls import RLSPort  # noqa: F401

__all__ = ["MessagingPort", "RLSPort"]
