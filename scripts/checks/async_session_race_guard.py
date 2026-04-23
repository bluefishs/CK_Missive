#!/usr/bin/env python3
"""
Async Session Race Guard — 靜態檢查 asyncio.gather 不得共用 db session

背景：ADR-0021 + ADR-0028
  asyncpg connection 是單飛模式。`asyncio.gather(task1(self.db), task2(self.db))`
  會觸發 `InterfaceError: another operation is in progress`。
  修正方式：每個 gather task 用 `run_with_fresh_session` 建立獨立 session。

規則：
  若 asyncio.gather(...) 內 2+ 個 task 直接引用 `self.db` / `ctx.db` / `db=self.db`
  （未被 run_with_fresh_session 包裹），視為 race 違規。

執行：
  python scripts/checks/async_session_race_guard.py
  → exit 0 無違規 / exit 1 有違規
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = ROOT / "backend" / "app"

# 被認定為「共用 db session」的表達式（source repr）
SHARED_DB_EXPRS = {
    "self.db",
    "ctx.db",
    "self._db",
    "self.session",
    "self._session",
}

# 被認定為「已隔離」的 wrapper 函式
ISOLATED_WRAPPERS = {
    "run_with_fresh_session",
    "run_in_fresh_session",
}


def _expr_to_str(node: ast.expr) -> str:
    """把簡單的 Attribute / Name 表達式還原為字串（self.db、ctx.db）"""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _is_isolated_call(call: ast.Call) -> bool:
    """判斷 Call 是否為 run_with_fresh_session(...) 包裹"""
    fn = call.func
    if isinstance(fn, ast.Name) and fn.id in ISOLATED_WRAPPERS:
        return True
    if isinstance(fn, ast.Attribute) and fn.attr in ISOLATED_WRAPPERS:
        return True
    return False


def _call_uses_shared_db(call: ast.Call) -> bool:
    """檢查 Call 是否直接使用共用 db"""
    if _is_isolated_call(call):
        return False

    # 位置參數
    for arg in call.args:
        if _expr_to_str(arg) in SHARED_DB_EXPRS:
            return True

    # 關鍵字參數
    for kw in call.keywords:
        if kw.value is None:
            continue
        if _expr_to_str(kw.value) in SHARED_DB_EXPRS:
            return True

    return False


def _task_uses_shared_db(node: ast.expr) -> bool:
    """判斷 gather 的單一 task 是否共用 db"""
    # 直接 call，如 self._planner.preprocess_question(q, self.db)
    if isinstance(node, ast.Call):
        return _call_uses_shared_db(node)

    # lambda: f(..., self.db) — 展開檢查 body
    if isinstance(node, ast.Lambda):
        for child in ast.walk(node.body):
            if isinstance(child, ast.Call) and _call_uses_shared_db(child):
                return True

    return False


def check_file(path: Path) -> list[tuple[int, str]]:
    """回傳 (line_no, message) 清單"""
    issues: list[tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # 只看 asyncio.gather(...)
        func = node.func
        is_gather = (
            (isinstance(func, ast.Attribute) and func.attr == "gather")
            or (isinstance(func, ast.Name) and func.id == "gather")
        )
        if not is_gather:
            continue

        # 至少 2 個 task 才會 race
        tasks = [a for a in node.args if not isinstance(a, ast.Starred)]
        if len(tasks) < 2:
            continue

        shared_count = sum(1 for t in tasks if _task_uses_shared_db(t))
        if shared_count >= 2:
            issues.append((
                node.lineno,
                f"asyncio.gather 內 {shared_count} 個 task 共用 db session — "
                f"違反 ADR-0021/ADR-0028，改用 run_with_fresh_session 包裹",
            ))
        elif shared_count == 1 and len(tasks) >= 2:
            # 只有一個 shared 時視為警告（可能是合法 edge case，如另一個 task 不碰 DB）
            issues.append((
                node.lineno,
                f"asyncio.gather 內 1 個 task 用 self.db/ctx.db；"
                f"若其他 task 也碰 DB 會 race — 請確認或全部改 run_with_fresh_session",
            ))

    return issues


def main() -> int:
    if not SCAN_DIR.is_dir():
        print(f"[SKIP] 掃描目錄不存在: {SCAN_DIR}")
        return 0

    errors = 0
    warnings = 0
    for py_file in SCAN_DIR.rglob("*.py"):
        # 跳過測試與快取
        rel = py_file.relative_to(ROOT).as_posix()
        if "/tests/" in rel or "/__pycache__/" in rel:
            continue

        issues = check_file(py_file)
        for lineno, msg in issues:
            severity = "ERROR" if "個 task 共用" in msg else "WARN"
            print(f"[{severity}] {rel}:{lineno}: {msg}")
            if severity == "ERROR":
                errors += 1
            else:
                warnings += 1

    print()
    if errors:
        print(f"Summary: {errors} ERROR / {warnings} WARN — async session race 違規")
        return 1
    if warnings:
        print(f"Summary: 0 ERROR / {warnings} WARN — 僅警告，CI 通過")
        return 0
    print("Summary: 無 async session race 風險")
    return 0


if __name__ == "__main__":
    sys.exit(main())
