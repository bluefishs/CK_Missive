# -*- coding: utf-8 -*-
"""README 宣告的執行者，是不是真的在跑它（2026-08-27）

## 為什麼需要這一支

`scripts/checks/README.md` 按「**誰在跑它**」分節，而 `declaration_gate.py` 強制
每支腳本都要出現在那張表裡。兩者合起來看很像已經涵蓋了，實際上**只驗了一半**：

    declaration_gate  →  這支腳本「有沒有被宣告」
    （沒有人）        →  那個宣告「是不是真的」

2026-08-27 手動比對，168 支裡有 **7 支宣告錯了**，而其中四支守的是**強制規範**：

| 腳本 | 宣告的執行者 | 實際 |
|---|---|---|
| `async_session_race_guard.py`（ADR-0021 強制） | 後端排程 `scheduler.py` | scheduler.py 一次都沒提到 |
| `sse_headers_guard.py` | 同上 | 同上 |
| `schema_lazy_load_guard.py` | 同上 | 同上 |
| `pattern_yaml_type_guard.py` | 同上 | 同上 |
| `skill_value_audit.py` | 同上 | 同上 |
| `v7_metrics_report.py` | 同上 | 同上 |
| `deploy_verify.py` | 每日 `fitness_daily` | **全 repo 沒有任何東西呼叫它** |

那四支 guard 真正的執行者設計上是 `.git/hooks/pre-commit`，而那支 hook 裡**一支都沒有**
（檔案自 2026-05-27 未再更動）。orchestrator 有一步正是要抓這件事，
但它跑在容器裡而 `.git/` 刻意不 mount ⇒ 自 2026-05-31 起每天回 `info: skipped`。
**能抓到的地方它不跑，跑的地方它抓不到。**

## 判準

每一節的標題自己就寫著執行者是誰 —— 直接拿那個檔案去比對，
**不另建一份「腳本→執行者」對照表**（那會變成第二份會漂移的事實，
正是本 repo 一路在治的東西）。

⚠️ 未知的節標題一律 **RED**，不是略過：新增一節而沒有登記執行者時，
底下所有腳本會靜靜地不被檢查 —— 那正是本檔要防的形狀。

## 已知限制（寫出來，不假裝沒有）

以**檔名子字串**判定「有沒有呼叫」，抓得到「完全沒提到」（本次 7 支全屬此類），
抓不到「提到了但那段是死碼」。後者要靠執行結果，不是靜態掃描能回答的。
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "scripts" / "checks" / "README.md"

# 節標題關鍵字 → 該節宣告的執行者（相對 repo 根）。
# `None` = 這一節本來就沒有執行者（手動／一次性）。
SECTION_RUNNERS: list[tuple[str, list[str] | None]] = [
    ("每日", ["scripts/checks/run_fitness_daily.sh"]),
    ("每週", ["scripts/checks/run_fitness_weekly.sh",
             "scripts/checks/run_fitness_weekly_host.sh"]),
    ("月度架構覆盤", ["scripts/checks/run_fitness.sh"]),
    ("瀏覽器走查", ["scripts/checks/run_ui_smoke.sh",
                 "scripts/checks/run_visual_walk.sh",
                 "selfaudit.config.json"]),
    ("後端排程", ["backend/app/core/scheduler.py",
                "backend/app/services/optimization_pipeline_orchestrator.py"]),
    ("健康監控", None),      # scripts/health/ 底下互相呼叫，執行者是 host 排程
    ("Windows 工作排程器", None),
    ("無排程", None),
    # 非腳本清單的節 —— 明確登記為「沒有執行者」而不是讓它們掉進 UNKNOWN。
    # 第一版沒登記，於是兩個說明性小節被報成缺口（2/7 是假陽性）。
    # ⚠️ 仍**不能**把 UNKNOWN 改成略過：新增一節而沒登記時必須有人知道。
    ("怎麼讀這份表", None),
    ("相關", None),
]

SCRIPT_RE = re.compile(r"^\|\s*`([A-Za-z0-9_.\-]+\.(?:py|sh|cjs|ps1))`")


def _runner_for(heading: str):
    for key, runners in SECTION_RUNNERS:
        if key in heading:
            return key, runners
    return None, "UNKNOWN"


def main() -> int:
    if not README.exists():
        print(f"[RED] 找不到 {README}")
        return 2

    text = io.open(README, encoding="utf-8").read()
    bodies: dict[str, str] = {}
    for rel in {r for _, rs in SECTION_RUNNERS if rs for r in rs}:
        p = ROOT / rel
        try:
            bodies[rel] = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            bodies[rel] = ""          # 檔案不存在 → 下面會判為「宣告的執行者不存在」

    reds: list[str] = []
    notes: list[str] = []
    section = ""
    checked = 0

    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
            key, runners = _runner_for(section)
            if runners == "UNKNOWN":
                reds.append(f"未登記執行者的節：「{section}」"
                            f"—— 底下的腳本不會被檢查，請補進 SECTION_RUNNERS")
            continue
        m = SCRIPT_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        key, runners = _runner_for(section)
        if not runners or runners == "UNKNOWN":
            continue
        checked += 1
        missing = [r for r in runners if r not in bodies or not bodies[r]]
        if len(missing) == len(runners):
            reds.append(f"{name}: 宣告的執行者檔案讀不到（{', '.join(runners)}）")
            continue
        if not any(name in bodies.get(r, "") for r in runners):
            reds.append(f"{name}: 宣告在「{section}」，"
                        f"但 {' / '.join(os.path.basename(r) for r in runners)} 一次都沒提到它")

    print("=" * 66)
    print("README 宣告的執行者 vs 實際（declaration_gate 只驗有沒有宣告）")
    print("=" * 66)
    print(f"  比對 {checked} 支有宣告執行者的腳本")
    for n in notes:
        print(f"  · {n}")
    if reds:
        print(f"\n🔴 宣告與實際不符 {len(reds)} 處：")
        for r in reds:
            print(f"      {r}")
        print("\n  ⚠️ 「宣告了執行者」與「那個執行者真的在跑它」是兩件事。")
        print("     修法二選一：把它接上宣告的執行者，或把宣告改成實話。")
        return 2
    print("\n✅ 每一支宣告的執行者都真的提到了它")
    print("  ⚠️ 限制：以檔名子字串判定，抓不到「提到了但那段是死碼」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
