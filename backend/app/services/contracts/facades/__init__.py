"""Bounded Context Facades — v6.12 B 方案收口（2026-05-30）

v6.10 P1 原建 13 facades，30 天 audit 結果 10/13 zero caller。
ADR-0036 經實證 ROI 不及預期，按 L31 「ROI = entities × usage_rate」
廢棄 10 zero facade，留 3 active 補強到 ≥5 caller (60 天 trial)。

保留 (3 active)：
- MemoryFacade      (3 caller — agent_orchestrator/planner/post_processing)
- IntegrationFacade (3 caller — scheduler/orchestrator/tender business_recommendation)
- WikiFacade        (1 caller — agent_orchestrator)

廢棄 (10 zero，2026-05-30 移除)：
- AgencyFacade / AIFacade / AuditFacade / CalendarFacade / ContractFacade
- DocumentFacade / ERPFacade / NotificationFacade / TenderFacade / VendorFacade
- 原因：30 天 zero caller，service layer 直 import 已能滿足
- 對齊：feedback_stop_overengineering / L31 / docs/architecture/FACADE_ABC_DECISION_20260530.md

60 天 trial（2026-07-30 重評）:
- 3 留存 facade 任一未達 ≥5 caller → 升 C 全廢
- 達標 → 維持並補強

採用模式（保留的 3 個）：
  from app.services.contracts.facades import MemoryFacade
  facade = MemoryFacade()
  ...
"""
from app.services.contracts.facades.integration import IntegrationFacade
from app.services.contracts.facades.memory import MemoryFacade
from app.services.contracts.facades.wiki import WikiFacade

__all__ = [
    "IntegrationFacade",
    "MemoryFacade",
    "WikiFacade",
]
