"""
Code Graph 共用資料類別

CodeEntity / CodeRelation — 提取器與入圖服務共用的中間表示。

Version: 1.0.0
Created: 2026-03-10
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Set


# ---------------------------------------------------------------------------
# Intermediate representations
# ---------------------------------------------------------------------------

@dataclass
class CodeEntity:
    """Extracted code entity (intermediate)."""
    canonical_name: str
    entity_type: str  # py_module | py_class | py_function | db_table | api_endpoint | service | ...
    description: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelation:
    """Extracted code relationship (intermediate)."""
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relation_type: str


# ---------------------------------------------------------------------------
# Entity & Relation categories (v2.0 — inspired by Understand-Anything)
# ---------------------------------------------------------------------------

CODE_ENTITY_CATEGORIES: Dict[str, Set[str]] = {
    "code": {"py_module", "py_class", "py_function", "ts_module", "ts_component", "ts_hook"},
    "infrastructure": {"api_endpoint", "service", "repository", "schema", "config", "middleware"},
    "data": {"db_table"},
}

CODE_RELATION_CATEGORIES: Dict[str, Set[str]] = {
    "structural": {"defines_class", "defines_function", "has_method", "defines_component", "defines_hook"},
    "dependency": {"imports", "inherits", "calls", "depends_on"},
    "data_flow": {"references_table", "validates_with"},
    "infrastructure": {"uses_service", "uses_repository", "serves_route", "provides_middleware"},
}

# ---------------------------------------------------------------------------
# Constants shared between code_graph_service and code_graph_ingest
# ---------------------------------------------------------------------------

CODE_RELATION_TYPES: Set[str] = {
    "defines_class",
    "defines_function",
    "has_method",
    "imports",
    "inherits",
    "references_table",
    "calls",
    "defines_component",
    "defines_hook",
    # Infrastructure relations (v2.0 — inspired by Understand-Anything)
    "uses_service",
    "uses_repository",
    "validates_with",
    "serves_route",
    "provides_middleware",
    "depends_on",
}

CODE_GRAPH_LABEL: str = "code_graph"  # relation_label provenance tag
