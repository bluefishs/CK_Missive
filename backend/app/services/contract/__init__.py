"""Contract bounded context (DDD Wave 1 sub-batch B, 2026-04-27).

Houses 承攬案件 (ContractProject) — staff, analytics, case_code bridge,
field sync, and project ↔ agency contact relations.

Why "contract" not "project":
    "project" already means many things in this codebase (taoyuan dispatch project,
    PMCase, etc.). Per ADR-0013, the canonical 承攬案件 entity has its own bounded
    context that bridges PM Case + ERP Quotation via case_code. Naming the
    subpackage "contract" disambiguates from other "project" usages.

Public API:
    ProjectService              — main 承攬案件 CRUD
    ProjectStaffService         — 案件人員配置
    ProjectAnalyticsService     — 案件分析
    CaseCodeService             — case_code 跨模組橋樑（ADR-0013）
    CaseFieldSyncService        — 三模組欄位同步（PM/ERP/contract）
    ProjectAgencyContactService — 專案機關聯絡人
"""
from .core import ProjectService  # noqa: F401
from .staff import ProjectStaffService  # noqa: F401
from .analytics import ProjectAnalyticsService  # noqa: F401
from .case_code import CaseCodeService  # noqa: F401
from .field_sync import CaseFieldSyncService  # noqa: F401
from .agency_contact import ProjectAgencyContactService  # noqa: F401
