# -*- coding: utf-8 -*-
"""YAML Safe Editor — 純函式層，安全編輯 synonyms.yaml / intent_rules.yaml

2026-04-19 Memory Wiki Phase 3 新建。

用 ruamel.yaml 保留註解與格式，避免 PyYAML 會丟失所有 comment。
所有變更必經 validate 才算成功。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

logger = logging.getLogger(__name__)


def _make_yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 120
    return y


@dataclass
class ValidationResult:
    ok: bool
    error: Optional[str] = None


def validate_yaml(yaml_text: str) -> ValidationResult:
    """Parse 一次，若成功即視為語法合法。"""
    try:
        y = _make_yaml()
        y.load(yaml_text)
        return ValidationResult(ok=True)
    except ScannerError as e:
        return ValidationResult(ok=False, error=f"YAML scanner error: {e}")
    except Exception as e:
        return ValidationResult(ok=False, error=f"YAML parse error: {e}")


def _dump_to_string(data: Any) -> str:
    y = _make_yaml()
    buf = StringIO()
    y.dump(data, buf)
    return buf.getvalue()


# ────────── Synonyms 操作 ──────────

def add_synonym_group(
    yaml_text: str,
    category: str,
    new_group: List[str],
) -> Tuple[str, bool]:
    """於指定 category 下新增一組 synonym。

    Args:
        yaml_text: 既有 synonyms.yaml 完整內容
        category: top-level key（如 "agency_synonyms" / "dispatch_business_synonyms"）
        new_group: 新的同義詞列表（如 ["通告", "公告"]）

    Returns:
        (new_yaml_text, added)
        added=False 表示該 group 已存在（no-op）
    """
    if not new_group or len(new_group) < 2:
        raise ValueError("new_group must have at least 2 items")

    y = _make_yaml()
    data = y.load(yaml_text) or {}

    if category not in data:
        data[category] = []

    # 檢查是否重複（任一 term 已存在於其他 group 或本 group 完全相同）
    existing_groups = data.get(category, []) or []
    new_set = set(new_group)
    for group in existing_groups:
        group_set = set(group) if isinstance(group, list) else set()
        if new_set == group_set:
            return yaml_text, False  # 完全相同
        if new_set & group_set:
            # 有交集 — 合併進既有 group（保留 ruamel 結構）
            for term in new_group:
                if term not in group:
                    group.append(term)
            return _dump_to_string(data), True

    # 沒交集 → append 新 group
    existing_groups.append(new_group)
    return _dump_to_string(data), True


# ────────── Intent Rules 操作 ──────────

def add_intent_rule(
    yaml_text: str,
    rule_dict: Dict[str, Any],
    position: str = "end",
) -> Tuple[str, bool]:
    """新增一條 intent rule（附 validation）。

    Args:
        yaml_text: 既有 intent_rules.yaml 完整內容
        rule_dict: 必含 'name' 與 'pattern' 欄位
        position: "end" (appendix) | "start" (higher priority)

    Returns:
        (new_yaml_text, added)
    """
    if "name" not in rule_dict or "pattern" not in rule_dict:
        raise ValueError("rule_dict must have 'name' and 'pattern'")

    y = _make_yaml()
    data = y.load(yaml_text) or {}
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("intent_rules.yaml structure invalid: 'rules' not a list")

    # name 重複檢查（已存在則跳過）
    existing_names = {r.get("name") for r in rules if isinstance(r, dict)}
    if rule_dict["name"] in existing_names:
        return yaml_text, False

    if position == "start":
        rules.insert(0, rule_dict)
    else:
        rules.append(rule_dict)

    data["rules"] = rules
    return _dump_to_string(data), True


# ────────── Diff 摘要（供 proposal 顯示） ──────────

def diff_summary(before: str, after: str, max_lines: int = 30) -> str:
    """產生 diff 簡要文字（不輸出整份）。"""
    import difflib
    diff = list(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        n=2,
    ))
    if len(diff) > max_lines:
        diff = diff[:max_lines] + [f"... ({len(diff) - max_lines} more lines)\n"]
    return "".join(diff)
