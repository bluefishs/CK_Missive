#!/usr/bin/env python3
"""
Schema Lazy-Load Guard — 靜態檢查 Pydantic Schema 不得訪問 ORM lazy-relationship

背景：2026-04-21 事故
  UserResponse.model_validate(user) 內 getattr(obj, 'aliases')
  → SQLAlchemy async lazy-load → MissingGreenlet → 500

規則：
  在 backend/app/schemas/**/*.py 中，`getattr(obj, '<name>')` 的 name
  若匹配已知 ORM relationship，即視為高風險 — 必須改用 __dict__.get。

已知 relationship 白名單（由 models/ 自動掃描可達性 TODO；目前維護常見名單）。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 已知會觸發 lazy-load 的 relationship 名稱
# 來自 models/*.py 的 `= relationship(...)` 定義
KNOWN_LAZY_RELS = {
    "aliases",              # User.aliases, CanonicalEntity.aliases (ADR-0025)
    "canonical",            # User.canonical_user self-ref
    "documents",            # User.documents
    "attachments",
    "calendar_events",
    "notifications",
    "sessions",
    "projects",
    "vendors",
    "staff",
    "certifications",
    "work_records",
    "dispatch_orders",
    "payments",
    "mentions",
    "entity_relations",
}


def check_file(path: Path) -> list[tuple[int, str]]:
    """回傳 (line_no, message) 清單，空 list 表示無問題"""
    issues: list[tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        # getattr(obj, 'rel_name', ...) — 危險（會觸發 lazy-load）
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            rel = node.args[1].value
            if rel in KNOWN_LAZY_RELS:
                issues.append((
                    node.lineno,
                    f"getattr(obj, '{rel}') 會觸發 lazy-load → MissingGreenlet；"
                    f"改用 obj.__dict__.get('{rel}') 只讀已 eager-load 的資料",
                ))

    return issues


def main() -> int:
    schemas_dir = ROOT / "backend" / "app" / "schemas"
    if not schemas_dir.is_dir():
        print(f"schemas 目錄不存在: {schemas_dir}")
        return 0

    total_issues = 0
    for py_file in schemas_dir.rglob("*.py"):
        issues = check_file(py_file)
        if issues:
            rel_path = py_file.relative_to(ROOT)
            for lineno, msg in issues:
                print(f"{rel_path}:{lineno}: {msg}")
                total_issues += 1

    if total_issues:
        print(f"\n❌ 發現 {total_issues} 個 lazy-load 風險點")
        return 1
    print("✅ schemas 無 lazy-load 風險")
    return 0


if __name__ == "__main__":
    sys.exit(main())
