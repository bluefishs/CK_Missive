#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""給靜態判準用的 TypeScript 原始碼讀取器：只回程式碼，不回散文。

## 為什麼有這一支

2026-08-29 一天之內，**五個靜態判準被自己的散文騙過**：
weekly 81 的負向對照回綠（註解裡寫著 isTablet）、weekly 56 放過一個
16 欄表格（註解寫著「刻意不改用 EnhancedTable」）、weekly 82 的負向
對照回綠（`console.warn('...totals...')` 是字串）。

我先用手寫正則剝註解與引號字串，**而它看起來已經處理好了**。
實測 7 種形態後仍有三個洞：**樣板字串／JSX 文字／多行樣板** ——
在 React 專案裡 JSX 文字到處都是。

CK_AaaP 同日獨立踩到同一形狀（正則抓 `add_middleware(...)`，把註解掉的
與字串裡的都算進去），結論一致並抽成他們的 L71：
**不要自己寫剝除邏輯，用語言自己的解析器。**

⇒ 本模組委派 `lib/ts_code_only.cjs`（TypeScript 官方 scanner + AST）。
抹掉的區段以等長空白取代 ⇒ **行號與位移完全不變**，呼叫端報的行號仍正確。

## 明確失敗，不靜默降級

找不到 `typescript` 套件時 **raise `TsToolUnavailable`**，由呼叫端以
退出碼 2（無法判定）結束 —— 不退回手寫正則。
「判準悄悄變弱」與「沒有違規」在輸出上長得一樣（ADR-0028）。

## 判準的邊界（呼叫端要自己知道）

抹得掉：註解、字串、樣板、JSX 文字、regex 字面值。
**抹不掉**：條件式執行。`if (flag) doThing()` 裡的 `doThing()` 是真實
呼叫點，但「這次有沒有走到」靜態看不出來。
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List

_HERE = Path(__file__).resolve().parent
_ENGINE = _HERE / "ts_code_only.cjs"
_BATCH = 60  # 一次丟太多路徑會超過 Windows 命令列長度上限


class TsToolUnavailable(RuntimeError):
    """node 或 typescript 不可用 —— 判準無法成立，呼叫端應回 exit 2。"""


def code_only(paths: Iterable[Path]) -> Dict[str, str]:
    """回 {絕對路徑字串: 只剩程式碼的內容}（行號與原檔一致）。"""
    paths = [str(Path(p).resolve()) for p in paths]
    if not paths:
        return {}
    if shutil.which("node") is None:
        raise TsToolUnavailable("找不到 node —— 無法可靠地剝除註解與字串")
    if not _ENGINE.is_file():
        raise TsToolUnavailable(f"找不到剝除引擎 {_ENGINE}")

    out: Dict[str, str] = {}
    for i in range(0, len(paths), _BATCH):
        chunk: List[str] = paths[i: i + _BATCH]
        proc = subprocess.run(
            ["node", str(_ENGINE), "--stdin"],
            input=json.dumps(chunk),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode == 3:
            raise TsToolUnavailable(
                "typescript 套件不可用（試過 frontend/node_modules）；"
                "跑 `npm ci --prefix frontend` 後重試"
            )
        if proc.returncode != 0:
            raise TsToolUnavailable(
                f"剝除引擎失敗（exit {proc.returncode}）：{(proc.stderr or '').strip()[:200]}"
            )
        out.update(json.loads(proc.stdout))
    return out
