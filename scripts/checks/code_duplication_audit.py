"""Code Duplication & Competing-Standard Audit — 全專案重複樣態（2026-06-11）

擴大圖譜治理（owner：擴大專案系統程式圖譜對應架構標準化與重複樣態）：
AST 掃描 backend/app 全部 function/method，偵測兩類「重複樣態」——

1. 結構重複（copy-paste）：function body 正規化 AST 結構雜湊相同（忽略變數名/字面值）
   且節點數 ≥ MIN_NODES → 高度疑似複製貼上、應抽共用。
2. 競爭標準：同「用途語義」(verb_noun) 有多個實作跨 ≥2 模組 → 應收斂 SSOT
   （如本次 3 套日曆標題 builder / parse_date×N）。

非 0 即錯——informational 盤點，供逐步收斂。

Usage:
  python scripts/checks/code_duplication_audit.py [--min-nodes 25] [--top 20]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

MIN_NODES = 25          # body AST 節點數門檻（濾掉 trivial getter/wrapper）
PRODUCER_VERBS = ("build", "format", "make", "generate", "create", "sync",
                  "parse", "extract", "render", "to", "compute", "calc")


def _norm_body_sig(func: ast.AST) -> tuple[str, int]:
    """function body 正規化結構簽章（節點型別序列，忽略名稱/字面值）+ 節點數"""
    types: list[str] = []
    for node in ast.walk(func):
        # 忽略名稱與常數值（只看結構），保留控制流/呼叫骨架
        if isinstance(node, (ast.Name, ast.Constant, ast.Load, ast.Store, ast.arg,
                             ast.alias, ast.keyword)):
            continue
        types.append(type(node).__name__)
    sig = hashlib.md5("|".join(types).encode()).hexdigest()[:12]
    return sig, len(types)


def _purpose(name: str) -> str | None:
    """verb_noun 用途語義（取前兩段）"""
    parts = name.lstrip("_").split("_")
    if len(parts) >= 2 and parts[0] in PRODUCER_VERBS:
        return f"{parts[0]}_{parts[1]}"
    return None


def main(min_nodes: int = MIN_NODES, top: int = 20) -> int:
    root = Path(__file__).resolve().parents[2]
    app = root / "backend" / "app"

    by_sig: dict[str, list[str]] = defaultdict(list)
    by_purpose: dict[str, set[str]] = defaultdict(set)
    purpose_funcs: dict[str, list[str]] = defaultdict(list)

    for py in app.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = py.relative_to(app)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig, n = _norm_body_sig(node)
                if n >= min_nodes:
                    by_sig[sig].append(f"{rel}::{node.name}")
                p = _purpose(node.name)
                if p:
                    by_purpose[p].add(str(rel.parent))
                    purpose_funcs[p].append(f"{rel}::{node.name}")

    dup_clusters = sorted(
        [(s, fs) for s, fs in by_sig.items() if len(fs) >= 2],
        key=lambda x: -len(x[1]))
    compete = sorted(
        [(p, purpose_funcs[p]) for p, mods in by_purpose.items() if len(mods) >= 2],
        key=lambda x: -len(x[1]))

    print("=== Code Duplication & Competing-Standard Audit（全專案重複樣態）===")
    print(f"  掃描 backend/app | body≥{min_nodes} 節點函式參與雜湊\n")

    print(f"[結構重複 copy-paste 群] {len(dup_clusters)} 群（同 body 結構 ≥2 實作）：")
    for sig, fs in dup_clusters[:top]:
        print(f"  ✗ x{len(fs)}: {fs[0]}  ⟷  {fs[1]}" + (f"  (+{len(fs)-2})" if len(fs) > 2 else ""))
    print()

    print(f"[競爭標準群] {len(compete)} 群（同用途語義跨 ≥2 模組）：")
    for p, fs in compete[:top]:
        mods = sorted({f.split('::')[0].rsplit('/', 1)[0] for f in fs})
        print(f"  ~ {p:20} x{len(fs)} 實作 / {len(mods)} 模組: {', '.join(mods[:4])}")
    print()

    print(f"Summary: 結構重複群 {len(dup_clusters)} | 競爭標準群 {len(compete)}")
    print("（informational — 逐步收斂；抽共用 / 立 SSOT。對齊 L71 圖譜治理）")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-nodes", type=int, default=MIN_NODES)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    sys.exit(main(min_nodes=args.min_nodes, top=args.top))
