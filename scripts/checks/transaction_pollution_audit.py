#!/usr/bin/env python3
"""
Transaction Pollution Audit — 偵測「吞錯不 rollback 污染共用 session」反模式

背景（Lesson L64 / 2026-06-03 LINE 推播鏈 / 2026-01-09 BUGFIX_TRANSACTION_POLLUTION 復發）：
  asyncpg/SQLAlchemy 共用 session 在一個 statement 失敗後會進入
  `InFailedSQLTransactionError` 狀態，**該 session 後續所有 query 都會失敗**，
  直到 rollback。若 except 區塊「吞掉」DB 錯誤（log 後 swallow，不 re-raise、
  不 rollback），同一個 session 的後續操作（含後段 LINE 推播、其他 scanner）
  會全部 silent 失敗。

  本次 LINE 推播鏈即此模式第二次復發：
    proactive_triggers.py check_recommendations / predict_risks
    except 吞錯未 rollback → erp_scanner / LINE 推播段全撞交易錯。

規則（high-signal heuristic）：
  一個 try/except，若
    (a) try.body 內對共用 session 做了 DB 操作（self.db.execute / .commit / .scalar...）
    (b) 對應 except 區塊「既沒 raise、也沒 rollback」
  → 視為交易污染候選（YELLOW）。

  注意：這是啟發式，可能有 false-positive（例如該 except 確實不需 rollback，
  或 session 用完即棄）。屬 advisory；--strict 下才 exit 1。

執行：
  python scripts/checks/transaction_pollution_audit.py            # advisory
  python scripts/checks/transaction_pollution_audit.py --strict   # 有候選 → exit 1
"""
from __future__ import annotations

import ast
import sys
import warnings
from pathlib import Path

# 掃描他人原始碼時，個別檔的 SyntaxWarning（如 regex 內 invalid escape）會被
# ast.parse 觸發 — 與本 audit 無關，靜音以保持輸出乾淨。
warnings.filterwarnings("ignore", category=SyntaxWarning)

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [
    ROOT / "backend" / "app" / "services",
    ROOT / "backend" / "app" / "core",
]

# 共用 session 的 DB 操作方法名
DB_OPS = {
    "execute", "commit", "flush", "scalar", "scalars",
    "add", "delete", "merge", "refresh", "get",
}
# 只抓「注入式共用 session」（instance 層），與 async_session_race_guard 對齊。
# 排除 `async with async_session_maker() as db/session` 的拋棄式 local session —
# 那種 session 用完即棄，交易污染不會外溢，不需在 except 內 rollback。
SHARED_DB_TARGETS = {
    "self.db", "ctx.db", "self._db",
    "self.session", "self._session",
}


def _contains_shared_db_op(body: list[ast.stmt]) -> bool:
    """try.body 內是否對「注入式共用 session」做了 DB 操作。"""
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in DB_OPS:
                    try:
                        target = ast.unparse(node.func.value)
                    except Exception:
                        target = ""
                    if target in SHARED_DB_TARGETS:
                        return True
    return False


def _handler_is_safe(handler: ast.ExceptHandler) -> bool:
    """except 區塊是否安全（有 raise 或 rollback）。"""
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "rollback":
                return True
    return False


def scan_file(path: Path) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except (UnicodeDecodeError, SyntaxError):
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not _contains_shared_db_op(node.body):
            continue
        for handler in node.handlers:
            if not _handler_is_safe(handler):
                findings.append((
                    handler.lineno,
                    "try 內共用 session DB 操作，但 except 既未 rollback 也未 re-raise",
                ))
    return findings


def main() -> int:
    strict = "--strict" in sys.argv
    total = 0
    print("=== Transaction Pollution Audit (L64) ===")
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py in sorted(scan_dir.rglob("*.py")):
            if "__pycache__" in py.parts or py.name.startswith("test_"):
                continue
            for lineno, msg in scan_file(py):
                rel = py.relative_to(ROOT)
                print(f"  YELLOW {rel}:{lineno} — {msg}")
                total += 1

    print("")
    if total == 0:
        print("GREEN — 無交易污染候選")
        return 0
    print(f"YELLOW — {total} 個吞錯不 rollback 候選（L64 同型；逐一確認是否需 rollback）")
    if strict:
        print("STRICT mode → exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
