"""
Code Graph 共用資料類別

CodeEntity / CodeRelation — 提取器與入圖服務共用的中間表示。

Version: 1.0.0
Created: 2026-03-10
"""

from dataclasses import dataclass, field
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Intermediate representations
# ---------------------------------------------------------------------------

@dataclass
class CodeEntity:
    """Extracted code entity (intermediate)."""
    canonical_name: str
    entity_type: str  # py_module | py_class | py_function | db_table
    description: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelation:
    """Extracted code relationship (intermediate)."""
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relation_type: str
