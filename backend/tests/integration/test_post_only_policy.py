# -*- coding: utf-8 -*-
"""專案級 POST-only 政策守門（資安規範）。

CLAUDE.md 明定「ALL endpoints POST」。本測試靜態掃描所有 @router.get(...)
宣告，僅允許 allowlist 中的端點（SSE stream 等因技術限制必須 GET）。

違反者：新增 GET endpoint 未更新 allowlist → 測試失敗 → CI 擋下。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Set, Tuple

import pytest


# SSE / EventSource / 健康檢查 等技術必需 GET 的端點，需明確記錄原因
GET_ALLOWLIST: Set[Tuple[str, str]] = {
    # (file 相對 backend/app, route path 子字串)
    ("api/endpoints/ai/digital_twin.py", "/digital-twin/live-activity/stream"),  # SSE
    # Health endpoints — CF Tunnel / k8s / LB 探針業界標準要求 GET
    ("api/endpoints/health.py", "/health"),
    ("api/endpoints/health.py", "/health/detailed"),
    ("api/endpoints/health.py", "/health/metrics"),
    ("api/endpoints/health.py", "/health/readiness"),
    ("api/endpoints/health.py", "/health/liveness"),
    ("api/endpoints/health.py", "/health/pool"),
    ("api/endpoints/health.py", "/health/tasks"),
    ("api/endpoints/health.py", "/health/audit"),
    ("api/endpoints/health.py", "/health/backup"),
    ("api/endpoints/health.py", "/health/summary"),
    ("api/endpoints/health.py", "/health/scheduler"),
    ("api/endpoints/health.py", "/health/services"),
}


BACKEND_APP = Path(__file__).resolve().parents[2] / "app"


def _scan_get_routes(root: Path) -> list[tuple[Path, str]]:
    """回傳 [(file, route_path)] — 所有 @router.get 宣告。"""
    hits: list[tuple[Path, str]] = []
    for py in root.rglob("*.py"):
        try:
            source = py.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "@router.get" not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef) and not isinstance(node, ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                # 過濾 @router.get(...)
                func = dec.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr == "get"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "router"
                ):
                    continue
                # 取第一個位置參數作為 path
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    hits.append((py, dec.args[0].value))
    return hits


def test_no_unauthorized_get_endpoints():
    hits = _scan_get_routes(BACKEND_APP)

    # 排除 service/core 模組內的 docstring 範例（只掃 api/endpoints/）
    real_endpoints = [
        (p, r) for p, r in hits
        if "api" in p.parts and "endpoints" in p.parts
    ]

    allowed = set()
    violations = []
    for path, route in real_endpoints:
        rel = str(path.relative_to(BACKEND_APP)).replace("\\", "/")
        matched = False
        for allow_file, allow_sub in GET_ALLOWLIST:
            if rel == allow_file and allow_sub in route:
                allowed.add((rel, route))
                matched = True
                break
        if not matched:
            violations.append((rel, route))

    assert not violations, (
        f"POST-only 政策違反 — 發現未授權 GET 端點：\n"
        + "\n".join(f"  {f}: {r}" for f, r in violations)
        + "\n\n若為技術必需（如 SSE），請更新 GET_ALLOWLIST。"
    )


def test_allowlist_entries_still_exist():
    """Allowlist 防漂移：若端點被移除應清理 allowlist。"""
    hits = _scan_get_routes(BACKEND_APP)
    real = {
        (str(p.relative_to(BACKEND_APP)).replace("\\", "/"), r)
        for p, r in hits
    }
    for allow_file, allow_sub in GET_ALLOWLIST:
        assert any(
            f == allow_file and allow_sub in r for f, r in real
        ), f"allowlist entry stale: {allow_file}:{allow_sub} 已不存在"
