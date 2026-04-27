"""Document bounded context (DDD Wave 1 sub-batch A, 2026-04-27).

Houses 公文 (OfficialDocument) — CRUD, dispatch linking, import pipeline,
filters, statistics, export, processor, serial number generation, and
receiver/sender normalization.

Public API:
    DocumentService              — main 公文 CRUD entry
    DocumentDispatchLinkerService — 公文 ↔ 派工關聯
    DocumentImportLogicService   — 匯入邏輯
    DocumentImportService        — 匯入 facade
    DocumentFilterService        — 篩選專用
    DocumentStatisticsService    — 統計
    DocumentExportService        — 匯出
    DocumentImportProcessor      — 匯入 pipeline 處理器
    DocumentQueryFilterService   — 複合查詢篩選
    DocumentSerialNumberService  — 文號產生

For receiver normalization helpers (functions, not class):
    from .receiver_normalizer import normalize_unit, cc_list_to_json, ...
"""
from .core import DocumentService  # noqa: F401
from .dispatch_linker import DocumentDispatchLinkerService  # noqa: F401
from .import_logic import DocumentImportLogicService  # noqa: F401
from .import_facade import DocumentImportService  # noqa: F401
from .filter import DocumentFilterService  # noqa: F401
from .statistics import DocumentStatisticsService  # noqa: F401
from .export import DocumentExportService  # noqa: F401
from .processor import DocumentImportProcessor  # noqa: F401
from .query_filter import DocumentQueryFilterService  # noqa: F401
from .serial_number import DocumentSerialNumberService  # noqa: F401
