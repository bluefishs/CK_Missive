"""回歸鎖：repo 回傳的元素數必須等於端點解包的元素數。

## 這支鎖的是什麼

2026-08-29 做 §2.6 ①（統計卡分母）時，`total_amount` 被**同時加到兩個
repo 方法**：`get_pending_receipts`（對的，端點解三個）與 `get_sync_logs`
（錯的，端點只解兩個）⇒ `/api/erp/einvoice-sync/sync-logs` 每次呼叫都
`too many values to unpack (expected 2)`，電子發票同步頁的歷史清單整個壞掉。

**三個地方同時說謊而沒有一個報錯**：repo 的型別註解寫兩個、service 的
註解寫兩個、端點解兩個 —— 只有**執行時**才炸。Python 不驗註解，
而 CI 的 MyPy 是 soft-fail 且 GitHub Actions 自 2026-03-09 全面停用。

抓到它的是既有的頁面走查（`ui-sweep.json` 08-29 20:41 就記了 HTTP 400），
而沒有人看那份產出。⇒ 這支測試讓同樣的錯誤**在測試階段就出聲**。

## 為什麼用 AST 而不是實際呼叫

實際呼叫要 DB 與 session；而這個 bug 是**純結構性**的，靜態就看得出來。
用 AST 比對「repo 的 `return a, b, ...`」與「端點的 `a, b = await ...`」，
不需要任何執行環境，也不會因為測試庫 schema 漂移而假紅。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPO_FILE = ROOT / "backend/app/repositories/erp/einvoice_sync_repository.py"
API_FILE = ROOT / "backend/app/api/endpoints/erp/einvoice_sync.py"

# (repo 方法, 端點呼叫的 service 方法)
PAIRS = [
    ("get_sync_logs", "get_sync_logs"),
    ("get_pending_receipts", "get_pending_receipt_list"),
]


def _return_arities(path: Path, func_name: str) -> set[int]:
    """該函式所有 `return a, b, ...` 的元素數。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[int] = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if fn.name != func_name:
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple):
                out.add(len(n.value.elts))
    return out


def _unpack_arities(path: Path, method_name: str) -> set[int]:
    """`a, b = await xxx.method(...)` 的左側元素數。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[int] = set()
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Tuple)):
            continue
        v = n.value
        if isinstance(v, ast.Await):
            v = v.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) \
                and v.func.attr == method_name:
            out.add(len(n.targets[0].elts))
    return out


@pytest.mark.parametrize("repo_method,service_method", PAIRS)
def test_repo_return_arity_matches_endpoint_unpack(repo_method: str, service_method: str):
    returns = _return_arities(REPO_FILE, repo_method)
    unpacks = _unpack_arities(API_FILE, service_method)

    # 兩邊都必須抓得到 —— 抓不到代表這支測試已經失效（改名／改結構），
    # 而「抓不到」與「一致」在斷言上會長得一樣，必須分開判。
    assert returns, f"抓不到 {REPO_FILE.name}::{repo_method} 的 return tuple —— 本測試已失效"
    assert unpacks, f"抓不到 {API_FILE.name} 裡 {service_method}() 的解包 —— 本測試已失效"

    assert returns == unpacks, (
        f"{repo_method}() 回傳 {sorted(returns)} 個值，"
        f"而端點解包 {sorted(unpacks)} 個 —— 執行時會 "
        f"`too many values to unpack`。型別註解不會擋住這個（Python 不驗它）。"
    )
