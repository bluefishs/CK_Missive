#!/usr/bin/env python3
"""
SSE Headers Guard — 靜態檢查 SSE 端點必須顯式 Content-Encoding: identity

背景：ADR-0028
  v5.8.1 事故 B — GZipMiddleware 覆蓋 SSE StreamingResponse，導致前端收不到即時 event。
  修正：SSE_HEADERS 加 `Content-Encoding: identity`。

規則：
  任何 `StreamingResponse(...)` 呼叫，若 media_type="text/event-stream"，
  其 headers 必須包含 `Content-Encoding: identity`；
  或以 `create_sse_response(...)` 包裝（已自帶 SSE_HEADERS）。

執行：
  python scripts/checks/sse_headers_guard.py
  → exit 0 無違規 / exit 1 有違規
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = ROOT / "backend" / "app"


def _is_sse_mediatype(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value == "text/event-stream"
    return False


def _has_identity_header(headers_expr: ast.expr) -> bool:
    """檢查 headers 字典中是否含 Content-Encoding: identity"""
    # 直接用 SSE_HEADERS 常數 — 已知安全
    if isinstance(headers_expr, ast.Name) and headers_expr.id == "SSE_HEADERS":
        return True
    # dict literal — 檢查 key/value
    if isinstance(headers_expr, ast.Dict):
        for k, v in zip(headers_expr.keys, headers_expr.values):
            if (
                isinstance(k, ast.Constant)
                and isinstance(v, ast.Constant)
                and k.value == "Content-Encoding"
                and v.value == "identity"
            ):
                return True
    # **SSE_HEADERS spread
    if isinstance(headers_expr, ast.Dict):
        for k in headers_expr.keys:
            if k is None:  # **expr 形式
                return True  # 假設 spread 進來的是合規的
    return False


def check_file(path: Path) -> list[tuple[int, str]]:
    issues: list[tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        # 僅看 StreamingResponse(...)
        is_streaming = (
            (isinstance(func, ast.Name) and func.id == "StreamingResponse")
            or (isinstance(func, ast.Attribute) and func.attr == "StreamingResponse")
        )
        if not is_streaming:
            continue

        # 判斷是否為 SSE
        media_type_expr = None
        headers_expr = None
        for kw in node.keywords:
            if kw.arg == "media_type":
                media_type_expr = kw.value
            elif kw.arg == "headers":
                headers_expr = kw.value

        if media_type_expr is None or not _is_sse_mediatype(media_type_expr):
            continue  # 不是 SSE，跳過

        if headers_expr is None:
            issues.append((
                node.lineno,
                "SSE StreamingResponse 未設 headers — 必須傳 SSE_HEADERS "
                "或 dict 含 Content-Encoding: identity",
            ))
            continue

        if not _has_identity_header(headers_expr):
            issues.append((
                node.lineno,
                "SSE StreamingResponse headers 未含 Content-Encoding: identity — "
                "會被 GZipMiddleware 緩衝，改用 SSE_HEADERS（見 ADR-0028）",
            ))

    return issues


def main() -> int:
    if not SCAN_DIR.is_dir():
        print(f"[SKIP] 掃描目錄不存在: {SCAN_DIR}")
        return 0

    total = 0
    for py_file in SCAN_DIR.rglob("*.py"):
        rel = py_file.relative_to(ROOT).as_posix()
        if "/tests/" in rel or "/__pycache__/" in rel:
            continue

        issues = check_file(py_file)
        for lineno, msg in issues:
            print(f"[ERROR] {rel}:{lineno}: {msg}")
            total += 1

    print()
    if total:
        print(f"Summary: {total} 個 SSE header 違規")
        return 1
    print("Summary: SSE headers 合規")
    return 0


if __name__ == "__main__":
    sys.exit(main())
