#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RWD 整頁溢出閘門（weekly 109）——把每日行動探針的「觀測」變成「會紅」。

owner 2026-09-05：「優先處理 RWD，多數透過手機檢視」「資訊卡片呈現與風格為 RWD 檢視目標」。

## 為什麼

`ui_page_sweep` 的 mobile_probe 每天 04:30 量 41 頁 × 390／768／1024，但它**只印報告不告警**
（引擎註解寫明「觀測不告警」，且門檻是表格外溢 ≥ 400px）。09-04 基準有 11 列整頁溢出（7–84px），
沒有一列會讓任何人看到——問題只能靠 owner 撞到。這支讀它的結果檔，對「整頁溢出」設嚴格門檻。

## 判準

RED    任一頁在任一寬度 `pageOverflow ≥ fail_px`（預設 24）——整頁被撐寬＝手機要左右滑
YELLOW `layoutViewport > viewportWidth`（頁面被撐開但 scrollWidth 沒反映）或結果檔超過 36 小時
GREEN  整頁溢出全 < fail_px
**表格內的橫向捲動（tableOverflow）刻意不計**：09-05 起窄螢幕表格保留欄寬、改橫向捲動，那是設計，不是缺陷；
真手機（< 768）給了 mobileCard 的頁面根本不畫表格。
不碰 `.shared-selfaudit/`（vendored，改了 sync-vendored 會 DRIFT）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "wiki" / "memory" / "integration-health" / "ui-sweep.json"
FAIL_PX = 24
MAX_AGE_H = 36


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== RWD 整頁溢出閘門（weekly 109）===")
    if not RESULT.exists():
        print(f"[YELLOW] 找不到探針結果 {RESULT}（每日 04:30 的 ui_page_sweep 沒跑？）")
        return 1
    d = json.loads(RESULT.read_text(encoding="utf-8"))
    checked = d.get("checked_at")
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
    except Exception:
        age = timedelta(hours=999)
    rows = ((d.get("mobile_probe") or {}).get("rows")) or []
    if not rows:
        print("[YELLOW] 結果檔沒有 mobile_probe.rows——探針被關了或設定沒載到")
        return 1
    reds = [r for r in rows if (r.get("pageOverflow") or 0) >= FAIL_PX]
    yels = [r for r in rows if (r.get("layoutViewport") or 0) > (r.get("viewportWidth") or 0) and r not in reds]
    print(f"結果 {checked}（{age.total_seconds()/3600:.1f} 小時前）；{len(rows)} 列（頁 × 寬度）；整頁溢出 ≥{FAIL_PX}px：{len(reds)}")
    for r in sorted(reds, key=lambda x: -(x.get("pageOverflow") or 0)):
        w = (r.get("widest") or [{}])[0]
        print(f"  [RED] {r.get('route')} @{r.get('viewportWidth')}px 溢出 {r.get('pageOverflow')}px（撐寬元素 {w.get('sel')} 右緣 {w.get('right')}）")
    for r in yels[:10]:
        print(f"  [YELLOW] {r.get('route')} @{r.get('viewportWidth')}px layout viewport {r.get('layoutViewport')} > 設定寬")
    if age > timedelta(hours=MAX_AGE_H):
        print(f"  [YELLOW] 結果檔已 {age.total_seconds()/3600:.0f} 小時未更新")
    if reds:
        print(f"[RED] {len(reds)} 列整頁溢出——手機要左右滑")
        return 2
    if yels or age > timedelta(hours=MAX_AGE_H):
        print("[YELLOW] 見上")
        return 1
    print("[GREEN] 三個寬度整頁都不溢出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
