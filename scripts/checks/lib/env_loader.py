#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""從專案根的 `.env` 補齊環境變數 —— 給在 host 執行的稽核用。

## 為什麼有這一支

2026-08-30 實查：`calendar_sync_reconciliation_audit` 與
`calendar_title_standard_audit` 在它們**唯一的執行者**
（`run_fitness.sh`，手動月度覆盤，跑在 host）裡：

    [SKIP] 無 DATABASE_URL   →  exit 0  →  **永遠綠燈、永遠沒驗**

而 `.env` 第 32 行就有 `DATABASE_URL` —— 那兩支只讀 `os.environ`，
不讀 `.env`，而 host 的 shell 沒有 source 過它。

⇒ **「無法驗證」被記成「驗過了沒問題」的第二種形態**：
   不是依賴掛了，是**依賴就在旁邊而腳本不知道去拿**。

同日已修的第一種形態：`container_image_freshness_check` 在容器沒跑時
`return 0`（改為 YELLOW=1）。

## 為什麼不用 python-dotenv

它不在 `requirements.txt` 裡，而檢核腳本要能在**沒有安裝任何額外套件**
的 host 上跑（weekly 就是這樣跑的）。這裡只做最小解析：
`KEY=VALUE`、忽略空行與 `#` 開頭、去掉首尾引號。

⚠️ **不覆寫已存在的環境變數** —— 容器內已經有正確的值，
不該被 host 的 `.env` 蓋掉。
"""
import os
from pathlib import Path


def load_env_file(path: Path | None = None, *, override: bool = False) -> int:
    """把 `.env` 的內容補進 `os.environ`。回傳補了幾個。

    Args:
        path: `.env` 位置；預設為本檔往上兩層的專案根。
        override: 是否覆寫已存在的變數。**預設 False** ——
                  容器內已有正確值時不該被覆蓋。
    """
    if path is None:
        # ⚠️ 本檔在 `scripts/checks/lib/`，往上**三層**才是專案根。
        # 首版寫 `parents[2]` ⇒ 指到 `scripts/.env`（不存在）⇒ 補 0 個
        # 而 `if not path.is_file(): return 0` 讓它**靜靜地什麼都沒做**。
        # 同 L99（檔案搬家後路徑推導沒改）與本日 docker label 那次：
        # **機制看起來在，而它的輸入不存在。**
        path = Path(__file__).resolve().parents[3] / ".env"
    if not path.is_file():
        # 找不到要能被呼叫端分辨 —— 回 -1 而非 0（0 是「找到了但沒東西可補」）
        return -1

    added = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key or (not override and key in os.environ):
            continue
        val = val.strip()
        # 去掉成對的引號（`KEY="value"` / `KEY='value'`）
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        os.environ[key] = val
        added += 1
    return added
