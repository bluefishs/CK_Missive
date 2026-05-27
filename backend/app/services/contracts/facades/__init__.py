"""Bounded Context Facades - v6.10 P1 Phase B (2026-05-18)

12 bounded contexts 各自的對外唯一入口。

依據：
- docs/architecture/CONTRACTS_LAYER_GUIDE.md
- docs/architecture/NAMING_CONVENTIONS.md (Facade 命名規約)
- 5/18 整體架構律定 Phase B

進度：
- CalendarFacade     (6 methods) — 解 document -> calendar 4
- IntegrationFacade  (5 methods) — 解 integration <- N (12 imports)
- WikiFacade         (5 methods) — 解 ai -> wiki 7
- AIFacade           (todo) — 解 N -> ai (12 imports)
- MemoryFacade       (todo) — 解 memory <- N (12 imports)
- NotificationFacade (todo)
- DocumentFacade     (todo)
- ContractFacade     (todo)
- ERPFacade          (todo)
- AgencyFacade       (todo)
- VendorFacade       (todo)
- AuditFacade        (todo - 與 AuditPort 共用)

採用模式：
  # OK - cross-context call via facade
  from app.services.contracts.facades import CalendarFacade
  facade = CalendarFacade(db)
  event = await facade.create_event_from_document(doc_id, due_date)

  # BAD - direct import internal module
  from app.services.calendar.event_auto_builder import build_event
"""
from app.services.contracts.facades.calendar import CalendarFacade
from app.services.contracts.facades.integration import IntegrationFacade
from app.services.contracts.facades.wiki import WikiFacade
from app.services.contracts.facades.ai import AIFacade
from app.services.contracts.facades.memory import MemoryFacade
from app.services.contracts.facades.erp import ERPFacade
from app.services.contracts.facades.contract import ContractFacade
from app.services.contracts.facades.document import DocumentFacade
from app.services.contracts.facades.notification import NotificationFacade
from app.services.contracts.facades.agency import AgencyFacade
from app.services.contracts.facades.vendor import VendorFacade
from app.services.contracts.facades.audit import AuditFacade
# Step 5B (2026-05-28): TenderFacade 加入 v6.10 P1 12 facades 體系（變 13 facades）
from app.services.contracts.facades.tender import TenderFacade

__all__ = [
    "CalendarFacade",
    "IntegrationFacade",
    "WikiFacade",
    "AIFacade",
    "MemoryFacade",
    "ERPFacade",
    "ContractFacade",
    "DocumentFacade",
    "NotificationFacade",
    "AgencyFacade",
    "VendorFacade",
    "AuditFacade",
    "TenderFacade",  # v6.11 Step 5B
]
