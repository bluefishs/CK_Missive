#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稽催時間錨點的唯一定義（weekly 121，2026-09-07）。

owner：「4 處計算預期無統整稽催機制嗎？」

## 背景

「這筆請款逾期幾天」原本有**三份各自獨立的實作**（主動推播／填報缺口／個人儀表板），
三處都寫著 `CURRENT_DATE - billing_date`，沒有任何一處指向另一處。

2026-09-07 把自動建立的第一期改成**請款日留白**時，代價立刻具體化：
**漏改其中一處，那 86 筆佔位就會從那個消費端的逾期名單整批消失**
（實測：只認 `billing_date` 逾期從 198 掉到 118），而畫面上只會看到「逾期變少了」。

⇒ 定義收到 `app/services/erp/billing_dunning.py`（`COALESCE(請款日, 報價單日期::date)`）。
這一支盯的是**第四份實作有沒有出現**。

## 判準

掃 `backend/app/` 裡「拿 `billing_date` 做時間運算」的寫法：

* `CURRENT_DATE - ...billing_date` / `billing_date < ` / `today - ...billing_date`

在**定義模組以外**出現，而該檔又**沒有** import 那個定義 ⇒ RED。

⚠️ 刻意**不**禁止 `billing_date` 本身：顯示、寫入、排序都會用到它，
一律禁止會讓這支變成一個天天紅、沒有人看的東西。只管「拿它算時間」這件事。

⚠️ 「即將到期」用純 `billing_date` 是**對的**（佔位沒有排定的請款日，
不是即將到期），所以 `proactive_triggers_erp.py` 只要有 import 就算合格 ——
判準管的是「這個檔知不知道有唯一定義」，不是逐行審。
"""
from __future__ import annotations

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
DEF_MODULE = "billing_dunning"

#: 真正 import 了唯一定義（註解提到模組名不算）
IMPORTS_DEF = re.compile(
    r"^\s*(?:from\s+app\.services\.erp\.billing_dunning\s+import|"
    r"import\s+app\.services\.erp\.billing_dunning)", re.M)

#: 「拿 billing_date 做時間運算」的形狀
TIME_MATH = [
    re.compile(r"CURRENT_DATE\s*-\s*[\w.]*billing_date"),
    re.compile(r"[\w.]*billing_date\s*<\s*(CURRENT_DATE|today)"),
    re.compile(r"today\s*-\s*[\w.]*\.billing_date"),
    re.compile(r"[\w.]*billing_date\s*<=\s*CURRENT_DATE"),
]


def main() -> int:
    print("=== 稽催時間錨點的唯一定義（weekly 121）===")
    if not APP.exists():
        print("[YELLOW] 找不到 backend/app，未驗")
        return 1

    offenders: list[tuple[str, int, str]] = []
    scanned = 0
    for f in APP.rglob("*.py"):
        if DEF_MODULE in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if "billing_date" not in text:
            continue
        scanned += 1
        # ⚠️ 只認**真正的 import**，不認字串出現。首版寫成 `DEF_MODULE in text`，
        # 而三個消費端的註解裡都寫著「見 billing_dunning.py」⇒ 註解讓判準以為它知道，
        # 負向控制（把 import 拿掉）因此不會紅 —— 判準等於沒有作用。
        knows = bool(IMPORTS_DEF.search(text))
        if knows:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if s.startswith("#") or s.startswith("--"):
                continue
            if any(p.search(line) for p in TIME_MATH):
                offenders.append((str(f.relative_to(ROOT)), i, s[:90]))

    print(f"  掃過 {scanned} 個碰 billing_date 的檔案")
    if offenders:
        print(f"[RED] {len(offenders)} 處拿 billing_date 做時間運算，而該檔不知道唯一定義：")
        for path, ln, s in offenders[:12]:
            print(f"    {path}:{ln}  {s}")
        print(f"      修法：import `app.services.erp.{DEF_MODULE}` 的 "
              f"`EFFECTIVE_BILLING_DATE_SQL`／`effective_billing_date`。")
        print("      自動建立的第一期請款日是**留白**的，只認 billing_date 會讓那 86 筆"
              "從逾期名單整批消失，而畫面上只會看到『逾期變少了』。")
        return 2
    print("[GREEN] 沒有第四份實作")
    return 0


if __name__ == "__main__":
    sys.exit(main())
