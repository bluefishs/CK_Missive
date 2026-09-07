#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同一個名字在幾個模組裡各有一份定義（weekly 124，2026-09-08）。

owner：「重複版次等問題，多次程式圖譜或檢核都沒發現。」原因：既有檢核只比對「有人先命名過
的那一對宣告」（角色↔使用者、選單↔路由…），沒有任何一支問「同一個概念在 repo 裡有幾份」。
圖譜記呼叫關係，不記語意等價。

這支用最便宜的代理：**同名函式定義在幾個模組**。它不是語意等價，但今天收掉的兩批
（`_roc_to_date` ×4／`_parse_roc_date` ×4）都會在這裡先冒頭；代價是誤報（`to_dict`、`validate`
這類本來就該各自實作的名字），所以只看 **私有輔助函式（底線開頭）**、且**排除 dunder**——
私有名字重複 ⇒ 多半是各自抄了一份工具，不是介面契約。

判準：同名私有函式定義於 ≥ 3 個模組 ⇒ 列出；存量走基線 `.duplicate_definition_baseline.json`，
**新出現的名字或模組數增加 ⇒ RED**。基線是待清清單不是免死金牌（同 lib_adoption 的規則）。
"""
from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
APP = ROOT / "backend" / "app"
BASELINE = Path(__file__).resolve().parent / ".duplicate_definition_baseline.json"
THRESHOLD = 3
SKIP_DIRS = {"__pycache__", "tests", "migrations", "versions"}


def collect(app_dir: Path = APP) -> dict[str, set[str]]:
    """{函式名: {模組相對路徑}}，只收底線開頭、非 dunder 的 def／async def。"""
    out: dict[str, set[str]] = defaultdict(set)
    for f in app_dir.rglob("*.py"):
        if SKIP_DIRS & set(f.parts):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n = node.name
                if n.startswith("_") and not n.startswith("__"):
                    out[n].add(str(f.relative_to(ROOT)).replace("\\", "/"))
    return out


def offenders(defs: dict[str, set[str]]) -> dict[str, list[str]]:
    return {n: sorted(ms) for n, ms in defs.items() if len(ms) >= THRESHOLD}


def self_test() -> None:
    fake = {"_roc_to_date": {"a.py", "b.py", "c.py", "d.py"}, "_one": {"a.py"}, "_two": {"a.py", "b.py"}}
    assert set(offenders(fake)) == {"_roc_to_date"}


def main() -> int:
    print("=== 同名私有函式定義計數（weekly 124）===")
    self_test()
    cur = offenders(collect())
    if "--init" in sys.argv or not BASELINE.exists():
        BASELINE.write_text(json.dumps({n: len(ms) for n, ms in cur.items()}, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        print(f"[YELLOW] 基線建立：{len(cur)} 個名字各在 ≥{THRESHOLD} 個模組有定義（待清清單，不是免死金牌）")
        for n, ms in sorted(cur.items(), key=lambda kv: -len(kv[1]))[:12]:
            print(f"    {n}  ×{len(ms)}  例：{ms[0]}")
        return 1
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    new = {n: ms for n, ms in cur.items() if n not in base}
    grew = {n: ms for n, ms in cur.items() if n in base and len(ms) > base[n]}
    gone = [n for n in base if n not in cur]
    print(f"  現況 {len(cur)} 個重複名字；基線 {len(base)}；已清 {len(gone)}")
    rc = 0
    if new or grew:
        print(f"[RED] 新的重複定義：{len(new)} 個新名字、{len(grew)} 個模組數增加")
        for n, ms in list(new.items())[:10]:
            print(f"    新 {n} ×{len(ms)}：{', '.join(ms[:4])}")
        for n, ms in list(grew.items())[:10]:
            print(f"    增 {n} {base[n]}→{len(ms)}：{', '.join(ms[:4])}")
        print("      修法：找出既有的那一份、其餘改成委派（同 A119 的做法），不要再抄第 N 份。")
        rc = 2
    if gone:
        print(f"[YELLOW] {len(gone)} 個名字已不再重複，請從基線移除：{', '.join(gone[:6])}")
        rc = max(rc, 1)
    if rc == 0:
        print("[GREEN] 沒有新的重複定義（存量仍在基線裡等人清）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
