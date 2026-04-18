# -*- coding: utf-8 -*-
"""
Anti-pattern lint: asyncpg concurrent session race detection.

掃 backend/app 找 asyncio.gather(...) 區塊，偵測並行 task 共用同一 session/db 的模式。
若發現必須改用 run_with_fresh_session（見 ADR-0021）。

此 test 隨 CI 執行，防 regression 回歸。
"""
from __future__ import annotations

import re
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[2] / "app"

# 允許的例外清單（已人工驗證無 race，例如純 HTTP 並發 / 每個 task 自建 session）
ALLOWLIST = {
    # 各 task 自建 AsyncSessionLocal：
    "api/endpoints/ai/entity_extraction.py",
    "services/ai/agent/agent_tools.py",
    "services/ai/agent/agent_conductor.py",
    "services/ai/agent/agent_supervisor.py",
    # 純 HTTP / 外部 API 並發，未觸碰 DB：
    "api/endpoints/tender_module/search.py",
    "services/tender_analytics_battle.py",
    "services/tender_analytics_price.py",
    "services/tender_analytics_service.py",
    "services/tender_search_service.py",
    "services/ai/core/embedding_manager.py",
    "services/ai/graph/code_graph_ast_analyzer.py",
    # 框架自身
    "core/service_health_probe.py",
    "db/database.py",  # helper 本身 docstring 有 gather 範例
}


def _extract_gather_lines(py_path: Path):
    """回傳 (line_no, snippet) for each asyncio.gather usage."""
    text = py_path.read_text(encoding="utf-8", errors="ignore")
    hits = []
    for m in re.finditer(r"asyncio\.gather\s*\(", text):
        line = text[:m.start()].count("\n") + 1
        lines = text.splitlines()
        start = max(0, line - 10)
        end = min(len(lines), line + 15)
        snippet = "\n".join(lines[start:end])
        hits.append((line, snippet))
    return hits


_SHARED_SESSION_PATTERNS = [
    # fn(..., db=self.db) or fn(..., db=db) — 常見共用 pattern
    re.compile(r"\bdb\s*=\s*(?:self\.)?db\b"),
    # fn(self.db, ...) 位置參數共用
    re.compile(r"\(\s*self\.db\s*,"),
    # 同一 gather 內多次出現 self.db
    re.compile(r"gather\([^)]*self\.db[^)]*self\.db", re.DOTALL),
]


def _looks_safe(snippet: str) -> bool:
    """偵測已套用防護的 gather。"""
    return (
        "run_with_fresh_session" in snippet
        or "AsyncSessionLocal()" in snippet
        or "async with AsyncSessionLocal" in snippet
    )


def test_no_new_gather_with_shared_session():
    """偵測新增的 gather + 共用 session race（ADR-0021 回歸防線）。

    失敗時：
      1. gather 內 DB task 改用 run_with_fresh_session(...)（ADR-0021）
      2. 或若無觸 DB（純 HTTP），加入 ALLOWLIST
    """
    violations = []

    for py in BACKEND_APP.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(BACKEND_APP).as_posix()
        if rel in ALLOWLIST:
            continue

        for line_no, snippet in _extract_gather_lines(py):
            if _looks_safe(snippet):
                continue
            tail = snippet.split("asyncio.gather", 1)[-1][:800]
            for pat in _SHARED_SESSION_PATTERNS:
                if pat.search(tail):
                    violations.append(
                        f"{rel}:{line_no}\n  snippet tail:\n{tail[:300]}"
                    )
                    break

    if violations:
        msg = "\n\n".join(violations)
        raise AssertionError(
            f"發現 {len(violations)} 處 gather + 疑似共用 session:\n\n{msg}\n\n"
            f"修復：改用 run_with_fresh_session 或加 ALLOWLIST（見 ADR-0021）"
        )


def test_allowlist_files_still_exist():
    """allowlist 名單的檔案必須存在（重構時要同步更新此名單）。"""
    missing = [rel for rel in ALLOWLIST if not (BACKEND_APP / rel).exists()]
    assert not missing, f"ALLOWLIST 有檔案不存在，請更新: {missing}"
