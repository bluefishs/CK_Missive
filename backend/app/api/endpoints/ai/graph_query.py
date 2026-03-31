"""
知識圖譜查詢 API 端點 — 已拆分為三個模組

此檔案保留作為向後相容的 re-export。
實際端點已遷移至:
  - graph_entity.py  — 實體查詢 & Schema
  - graph_admin.py   — 管理操作 & 入圖
  - graph_unified.py — 跨圖譜搜尋 & 能力圖譜

Version: 2.0.0
Created: 2026-02-24
Refactored: 2026-03-30
"""

# Backwards-compat: re-export routers for any external imports
from .graph_entity import router as _entity_router  # noqa: F401
from .graph_admin import router as _admin_router  # noqa: F401
from .graph_unified import router as _unified_router  # noqa: F401
