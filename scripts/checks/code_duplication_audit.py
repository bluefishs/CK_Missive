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

# cp950 host 韌性（L49.8 同族）：直接印 CJK/✗/~ 到 Windows 終端會 UnicodeEncodeError
try:  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

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

    dup_clusters = [(s, fs) for s, fs in by_sig.items() if len(fs) >= 2]
    # 精煉降 noise（2026-06-12）：跨檔結構重複=真 copy-paste（該抽共用）；
    #   同檔=多為合法 sibling（get_sent/get_received 等對稱方法）→ 降為 info。
    def _files(fs):
        return {f.split("::")[0] for f in fs}
    cross_file = sorted([(s, fs) for s, fs in dup_clusters if len(_files(fs)) >= 2],
                        key=lambda x: -len(x[1]))
    same_file = [(s, fs) for s, fs in dup_clusters if len(_files(fs)) == 1]
    compete = sorted(
        [(p, purpose_funcs[p]) for p, mods in by_purpose.items() if len(mods) >= 2],
        key=lambda x: -len(x[1]))

    print("=== Code Duplication & Competing-Standard Audit（全專案重複樣態）===")
    print(f"  掃描 backend/app | body>={min_nodes} 節點函式參與雜湊\n")

    print(f"[★跨檔結構重複 真 copy-paste] {len(cross_file)} 群（跨 >=2 檔同 body 結構 → 該抽共用 SSOT）：")
    for sig, fs in cross_file[:top]:
        print(f"  ✗ x{len(fs)}: {fs[0]}  <-> {fs[1]}" + (f"  (+{len(fs)-2})" if len(fs) > 2 else ""))
    print()
    print(f"[同檔結構重複] {len(same_file)} 群（同檔 sibling，多為合法對稱方法，info）\n")
    print(f"[競爭標準群（啟發式）] {len(compete)} 群（同用途名跨 >=2 模組）"
          "— 名稱相似非必重複（如 parse_date 西元/文號/年份正規化），需人工判斷\n")

    print(f"Summary: 跨檔真重複 {len(cross_file)}（優先收斂）| 同檔 sibling {len(same_file)}（info）"
          f"| 競爭名群 {len(compete)}（啟發式需人工）")
    print("（informational — 跨檔真重複優先抽共用 SSOT。對齊 L71/L31 圖譜治理）")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-nodes", type=int, default=MIN_NODES)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    sys.exit(main(min_nodes=args.min_nodes, top=args.top))
