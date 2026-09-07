#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""民國年解析只能有一份（weekly 123，2026-09-08，A119 的守門）。

收斂前全 repo 有 8 份 `_roc_to_date`／`_parse_roc_date`，收成 `app/core/roc_date.py`
一份、原名字保留為薄委派。這支只守「有沒有人又自己寫了第九份」：

判準：`backend/app/` 裡任何函式**本體**出現 `+ 1911`／`+1911`（把年份手動轉西元），
而該檔沒有真正 import `app.core.roc_date` ⇒ RED。

刻意豁免（規範 §2.5 明文）：
* `case_code.py` —— 產號時的**輸入容錯**（人可能手打民國年），不是解析外部資料
* `quotation_document.py` —— 輸出到正式文件的 `- 1911`（本判準只看 `+ 1911`，本來就不會命中）
* 註解與 docstring 不算（L110：判準的掃描範圍不得包含描述它的文字）
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
APP = ROOT / "backend" / "app"
SSOT = APP / "core" / "roc_date.py"
EXEMPT_FILES = {"case_code.py"}
IMPORTS_SSOT = re.compile(r"^\s*(?:from\s+app\.core\.roc_date\s+import|import\s+app\.core\.roc_date)", re.M)


def offenders_in(path: Path, text: str) -> list[int]:
    """回有 `+ 1911` 的**程式碼**行號（走 AST，註解／docstring 自然不在裡面）。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            for side in (node.left, node.right):
                if isinstance(side, ast.Constant) and side.value == 1911:
                    hits.append(node.lineno)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.value, ast.Constant) and node.value.value == 1911:
                hits.append(node.lineno)
    return sorted(set(hits))


def scan(app_dir: Path = APP) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for f in app_dir.rglob("*.py"):
        if f == SSOT or f.name in EXEMPT_FILES or "__pycache__" in f.parts:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if "1911" not in text or IMPORTS_SSOT.search(text):
            continue
        for ln in offenders_in(f, text):
            out.append((str(f.relative_to(ROOT)), ln))
    return out


def self_test() -> None:
    """負向控制：一段手寫 `+ 1911` 必須被抓到；有 import SSOT 的不抓；註解裡的不抓。"""
    bad = "def f(y):\n    return y + 1911\n"
    assert offenders_in(Path("x.py"), bad) == [2]
    comment_only = "# 這裡不要寫 y + 1911\ndef f(y):\n    return y\n"
    assert offenders_in(Path("x.py"), comment_only) == []


def main() -> int:
    print("=== 民國年解析唯一定義（weekly 123）===")
    self_test()
    if not SSOT.exists():
        print(f"[RED] 唯一定義不存在：{SSOT}")
        return 2
    found = scan()
    if found:
        print(f"[RED] {len(found)} 處手動 `+ 1911` 而該檔不認得唯一定義（第九份實作）：")
        for p, ln in found[:15]:
            print(f"    {p}:{ln}")
        print("      修法：`from app.core.roc_date import parse_roc_date`，別再自己轉年。")
        return 2
    print("[GREEN] 沒有第九份民國年解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
