# -*- coding: utf-8 -*-
"""視覺走查新鮮度（2026-08-05）。

## 為什麼需要這一支

視覺走查是**唯一**能抓到「斷言全過但畫面是錯的」那一類缺陷的機制
（截字、遮蔽、配色語意、版面錯位）。但它有一個先天弱點：
**判讀必須有人在場**，所以不能掛 cron —— cron 裡沒有人在看圖。

不能自動執行的流程，最常見的下場就是悄悄停掉，而且**停掉不會有任何訊號**。
本專案這幾個月一直在治的正是這種形狀，所以這個機制自己不能重蹈覆轍。

這支不驗「圖好不好」（那要人判），只驗「這件事還在做嗎」。
逾期回 YELLOW 不回 RED —— 它是流程提醒，不是系統故障，
把提醒報成故障只會讓人習慣忽略紅字。

執行：
    python scripts/checks/visual_walk_freshness.py
退出碼：0 新鮮 / 1 逾期（YELLOW）/ 2 從未執行或路徑壞掉（未驗完）
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
VISUAL_DIR = ROOT / "docs" / "health" / "visual"

# owner 2026-08-05 決定改 10 天（原設 45 天綁月度架構覆盤）。
#
# 但**單純縮短門檻會製造雜訊**：畫面只有在前端改動後才可能變，
# 前端沒動的期間催走查，得到的是一個永遠該被忽略的提醒 ——
# 而被當成雜訊的提醒，很快就連該響的時候也沒人理。
#
# 所以改成雙條件：**逾 10 天 且 自上次走查後前端有改動**才提醒。
# 安靜期完全不催；改得兇的期間（本專案一個 session 就 build 四次）
# 10 天內幾乎每次都會催，而那正是缺陷出現的時候。
MAX_AGE_DAYS = 10
FRONTEND_PATHS = ("frontend/src", "frontend/package.json")


def _frontend_changed_since(when: datetime):
    """自 `when` 起前端是否有改動。回 (True/False/None, 說明)。

    None ＝ 查不到（例如不在 git repo）—— 據實回報，不要猜。
    猜「沒變」會讓真的該催的時候不催，那比沒有這個機制更糟。
    """
    import subprocess
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", f"--since={when:%Y-%m-%d}", "--", *FRONTEND_PATHS],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return None, (out.stderr or "git 失敗").strip()[:80]
        lines = [x for x in (out.stdout or "").splitlines() if x.strip()]
        if not lines:
            return False, "前端 0 個 commit"
        return True, f"{len(lines)} 個 commit，最近：{lines[0][:60]}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:80]


def main() -> int:
    print("=" * 66)
    print("視覺走查新鮮度（斷言看不到的那一類，只有這個機制抓得到）")
    print("=" * 66)

    if not VISUAL_DIR.is_dir():
        print(f"✗ 未驗完：{VISUAL_DIR.relative_to(ROOT)} 不存在")
        print("  （從未執行過視覺走查，不等於畫面沒問題）")
        return 2

    # 每輪產出一個以日期命名的資料夾，內含 index.md
    rounds = sorted(
        (d for d in VISUAL_DIR.iterdir() if d.is_dir() and (d / "index.md").exists()),
        key=lambda d: d.name,
    )
    if not rounds:
        print("✗ 未驗完：找不到任何一輪走查（缺 index.md）")
        return 2

    latest = rounds[-1]
    shots = len(list(latest.glob("*.png")))
    try:
        when = datetime.strptime(latest.name, "%Y%m%d")
    except ValueError:
        print(f"✗ 未驗完：資料夾名 {latest.name} 不是日期格式，無法判斷新鮮度")
        return 2

    age = (datetime.now() - when).days
    print(f"  最近一輪：{latest.name}（{age} 天前）｜{shots} 張圖｜共 {len(rounds)} 輪")

    if age <= MAX_AGE_DAYS:
        print(f"\nStatus: [GREEN] 距上次 {age} 天（門檻 {MAX_AGE_DAYS} 天）")
        return 0

    # 逾期了，再問第二個條件：這段期間前端到底有沒有變？
    changed, detail = _frontend_changed_since(when)

    if changed is None:
        # 查不到就據實說，不要猜 —— 猜「沒變」會讓真的該催的時候不催
        print(f"\nStatus: [YELLOW] 距上次 {age} 天，且無法判斷前端是否改動（{detail}）")
        print("  保守起見仍提醒：bash scripts/checks/run_visual_walk.sh")
        return 1

    if not changed:
        print(f"\nStatus: [GREEN] 距上次 {age} 天，但自那時起前端未改動 —— 畫面不可能變")
        print(f"  （{detail}）")
        return 0

    print(f"\nStatus: [YELLOW] 距上次視覺走查已 {age} 天，且前端有改動")
    print(f"  {detail}")
    print("  執行：bash scripts/checks/run_visual_walk.sh，然後**逐張看**。")
    print("  提醒：每發現一個缺陷要轉成 ui_flow_smoke 斷言，否則下次還要再看一遍。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
