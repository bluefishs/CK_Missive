#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""手動月度架構覆盤有沒有真的在跑（weekly 85）。

## 為什麼有這一支（2026-08-29）

`run_fitness.sh` 是**手動月度**觸發（`/arch-fitness`），不在 Windows 排程裡 ——
那是設計，不是缺陷。問題是它**獨佔 57 支檢核**：weekly 沒有的那些
（`dead_ui_detector`／`db_schema_drift_audit`／`cron_health_check`／
`navigation_live_integrity_audit`／`transaction_pollution_audit`…）。

而它原本**只印到終端機、不留任何檔案** ⇒ 事後完全無法區分
「跑了全過」與「根本沒跑」。57 支檢核掛在一個查不出有沒有跑過的 runner 上。

本 repo 自己的契約規則第 4 條就寫著：**驗證型 job 也必須留下可驗產出**
（`ui_page_sweep.cjs` 檔尾），而這一支是漏網的。

## 這不是「沒排程」，是「排程之外的東西沒有回聲」

同族 L100 是「執行者在、旗標沒帶」；這一支是
**「執行者是人，而人有沒有做，系統不知道」**。
兩者的共同點：能力存在、但沒有任何訊號說它被用過。

## 判準

  RED     產出檔不存在 ⇒ 從未跑過（或跑的是舊版腳本）
  RED     超過 `STALE_DAYS` 天沒跑 ⇒ 那 57 支等於沒有在保護任何東西
  YELLOW  上次跑有 fail_count > 0 且已超過 14 天沒再跑（紅了沒人回頭處理）
  ok      在期限內跑過

⚠️ 門檻 45 天而非 30：建議頻率是「每月」，而月度的事情本來就會漂幾天。
把門檻設在建議值上，會讓它每個月紅一次而那不是真訊號。

## 怎麼知道它是綠的（負向對照紀錄）

2026-08-29 建立時**它就是 RED**（產出檔不存在，因為 runner 剛加上產出、
還沒有人跑過）—— 這一支的第一個狀態就是真陽性，不需要另外注入。
把產出檔的 `checked_at` 改成 60 天前 → RED（過期）；改回今天 → GREEN。

## 誰跑它

weekly step 85（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "wiki" / "memory" / "integration-health" / "fitness-manual.json"
STALE_DAYS = 45
UNRESOLVED_DAYS = 14


def main() -> int:
    print("=" * 74)
    print("手動月度架構覆盤的執行證據（weekly 85）")
    print("=" * 74)

    if not RESULT.is_file():
        print(f"\n  [RED  ] 找不到 {RESULT.relative_to(ROOT).as_posix()}")
        print("           `run_fitness.sh` 從未跑過，或跑的是尚未加上產出的舊版。")
        print("           ⚠️ 它獨佔 57 支檢核（weekly 沒有的那些），")
        print("           而沒有產出就無法區分「跑了全過」與「根本沒跑」。")
        print("           跑一次：bash scripts/checks/run_fitness.sh")
        print("\nStatus: [RED] 沒有執行證據")
        return 1

    try:
        d = json.loads(RESULT.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(d["checked_at"].replace("Z", "+00:00"))
    except Exception as e:
        print(f"\n  [RED  ] 產出檔無法解析：{e}")
        print("\nStatus: [RED] 執行證據損毀")
        return 1

    age = (datetime.now(timezone.utc) - ts).days
    fails = d.get("fail_count", 0)
    print(f"\n  上次執行：{ts.astimezone().strftime('%Y-%m-%d %H:%M')}（{age} 天前）"
          f"｜fail_count={fails}")

    if age > STALE_DAYS:
        print(f"\n  [RED  ] 已 {age} 天沒跑（門檻 {STALE_DAYS} 天）")
        print("           那 57 支檢核目前等於沒有在保護任何東西 ——")
        print("           它們不會自己跑，而沒人跑的檢核與不存在的檢核是同一回事。")
        print(f"\nStatus: [RED] 月度覆盤已停擺 {age} 天")
        return 1

    if fails and age > UNRESOLVED_DAYS:
        print(f"\n  [YELLOW] 上次有 {fails} 項未過，而距今已 {age} 天沒再跑")
        print("           紅燈亮了沒有人回頭處理 —— 這比沒跑更值得注意，")
        print("           因為它代表訊號發出來了而收訊端沒有動作。")
        print(f"\nStatus: [YELLOW] {fails} 項未過且逾 {UNRESOLVED_DAYS} 天未複跑")
        return 1

    print("\n  （月度架構覆盤在期限內跑過）")
    print("\nStatus: [GREEN] 有執行證據且未過期")
    return 0


if __name__ == "__main__":
    sys.exit(main())
