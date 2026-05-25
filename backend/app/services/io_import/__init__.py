"""I/O Import bounded context (DDD Wave 9, 2026-05-05).

Houses CSV/Excel ingest pipelines and shared validation logic.
Pulled out of services/ top-level (3 散戶 → 1 子包) — entropy reduction.

Public API:
    .csv_processor   — DocumentCSVProcessor
    .excel_service   — ExcelImportService
    .validators      — validate_preview_row / prepare_document_data 等
"""
from .csv_processor import DocumentCSVProcessor  # noqa: F401
from .excel_service import ExcelImportService  # noqa: F401
from .validators import validate_preview_row, prepare_document_data  # noqa: F401
