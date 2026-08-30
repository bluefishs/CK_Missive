#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""新的檢核腳本不得自己重造共用層已經有的東西。

## 為什麼有這一支

owner 2026-08-30：**「每個 session 獨立建構事件、資料庫、執行腳本、
服務路徑與文件、檢核機制，導致架構臨散無統籌」**。

實測支持這個判斷（`scripts/checks/*.py` 共 182 支）：

| 同一件事 | 各自實作 | 當日是否因此出事 |
|---|---|---|
| 自算專案根路徑 | **110 支**（122 處） | ✅ **兩次** |
| 自己開 `docker exec` | 39 支 | — |
| 各自連 DB | 11 支 | — |

而共用層 `scripts/checks/lib/` **早就存在**，採用率 **6/182 = 3.3%**。

> **不是沒有共用層，是共用層沒有成為預設路徑。**
> 引用它要先知道它存在、知道它的介面；自己寫 `parents[2]` 是三秒的事。
> 而寫錯是**靜默**的（Windows 上 `Path("/app/logs")` 解析成 `D:\app\`，
> 而那個目錄可能真的存在）⇒ 下一個 session 不知道前一個踩過。

## 判準

掃 `scripts/checks/*.py`（不含 `lib/` 自己與 `test_*`），找三種自造：

| 樣式 | 應改用 |
|---|---|
| `Path(__file__)...parents[N]` | `lib.paths.repo_root()` 等 |
| `docker exec` / `docker", "exec` | `lib.docker_exec.exec_in()` |
| `create_engine(` / `async_session_maker` 直連 | `lib.paths` ＋ 既有 `env_loader` |

**已 `from lib...` 匯入對應模組者不計** —— 混用是遷移途中的正常狀態。

## 存量走基線、新增才擋

一律判紅會讓它第一天就報 120 個，而本 repo 記過
「永遠是紅的訊號與沒有訊號是同一個下場」。
⇒ 存量寫進 `.lib_adoption_baseline.json`（**帶當時的樣式數**），
**新增一支、或既有腳本增加自造處，才判紅**。

基線筆數與總處數每次執行都印 —— **數字不動就代表沒有人在清**。
遷移方式刻意設計成「因別的原因動到某支腳本時順手清一支」，
不專案化（本 repo 有範本鋪太廣而失血的前例 L58／L59）。

## 誰跑它

weekly step 93（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402  ← 本檔自己也走共用層

CHECKS = repo_root() / "scripts" / "checks"
BASELINE = CHECKS / ".lib_adoption_baseline.json"

PATTERNS = {
    "self_path": (
        # ⚠️ 判準校準（2026-08-30）：首版寫成 `Path\(__file__\)[^\n]*\.parents\[\d\]`
        #    —— 要求兩者**同一行**。而最常見的寫法是分兩行：
        #        here = Path(__file__).resolve()
        #        ...
        #        here.parents[2] / "backend" / ...
        #    ⇒ `cron_silent_dormant_check.py`（今天因路徑出事的當事人）
        #      同行命中 0、任何 parents 命中 3，**整支從未被算進基線**。
        #    ⚠️ 更糟的是我第一次比對寬窄判準時是在**遷移之後**跑的，
        #      兩者都得 0，於是得到「沒漏」的結論 —— **量錯了狀態**。
        #      比對判準寬窄，一定要在**還沒修的那份**上比。
        re.compile(r"\.parents\[\d\]"),
        "lib.paths.repo_root() 等",
    ),
    "self_docker": (
        re.compile(r"docker\s+exec|[\"']docker[\"']\s*,\s*[\"']exec[\"']"),
        "lib.docker_exec.exec_in()",
    ),
    "self_db": (
        re.compile(r"create_engine\s*\(|async_session_maker"),
        "lib.paths ＋ lib.env_loader",
    ),
}
# 已匯入對應模組就不算自造（遷移途中混用是正常的）
IMPORTED = {
    "self_path": re.compile(r"from\s+lib\.paths\s+import|from\s+lib\s+import\s+paths"),
    "self_docker": re.compile(r"from\s+lib\.docker_exec\s+import"),
    "self_db": re.compile(r"from\s+lib\.env_loader\s+import"),
}


def scan() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for p in sorted(CHECKS.glob("*.py")):
        if p.name.startswith("test_"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        counts = {}
        for key, (pat, _) in PATTERNS.items():
            if IMPORTED[key].search(t):
                continue
            n = len(pat.findall(t))
            if n:
                counts[key] = n
        if counts:
            out[p.name] = counts
    return out


def main() -> int:
    print("=" * 74)
    print("共用層採用率：新腳本不得自己重造 paths／docker／db（weekly 93）")
    print("=" * 74)

    if not CHECKS.is_dir():
        print(f"\n✗ 找不到 {CHECKS} —— 無法判定（不視為通過）")
        return 2

    found = scan()
    total_sites = sum(sum(v.values()) for v in found.values())
    scanned = len([p for p in CHECKS.glob("*.py") if not p.name.startswith("test_")])
    if scanned < 100:
        print(f"\n✗ 只掃到 {scanned} 支腳本（預期 150+）—— 掃描範圍可能壞了，不視為通過")
        return 2

    base = {}
    if BASELINE.is_file():
        base = json.loads(BASELINE.read_text(encoding="utf-8")).get("known", {})

    new_files, grown = [], []
    for name, counts in found.items():
        if name not in base:
            new_files.append((name, counts))
            continue
        for key, n in counts.items():
            if n > base[name].get(key, 0):
                grown.append((name, key, base[name].get(key, 0), n))

    print(f"\n  掃描 {scanned} 支腳本｜自造 {len(found)} 支／{total_sites} 處")
    print(f"  基線內 {len(base)} 支（每次都印；數字不動＝沒有人在清）")

    for name, counts in new_files:
        print(f"\n  [RED  ] {name} —— 新腳本自己重造了共用層已有的東西")
        for key, n in counts.items():
            print(f"           {key} × {n}　→ 改用 {PATTERNS[key][1]}")
    for name, key, was, now in grown:
        print(f"\n  [RED  ] {name} —— {key} 從 {was} 增加到 {now} 處")
        print(f"           → 改用 {PATTERNS[key][1]}")

    if new_files or grown:
        print("\n⚠️ 自己重造的錯誤是**靜默**的：路徑算錯不會拋例外，會讀到別的檔案；")
        print("   漏掉 MSYS_NO_PATHCONV 會讓容器路徑被改寫而看起來像「檔案不存在」。")
        print("   ⇒ 下一個 session 不會知道這一個踩過。")
        print(f"\nStatus: [RED] 新增 {len(new_files)} 支自造／{len(grown)} 處增長")
        return 1

    print("\nStatus: [GREEN] 沒有新增的自造")
    return 0


if __name__ == "__main__":
    sys.exit(main())
