# -*- coding: utf-8 -*-
"""各層檢核的**統一結果契約** writer（2026-09-06）。

機制圖（`docs/architecture/AUTONOMOUS_TESTING_MAP.md` 缺口 6）照出來的問題不是「引擎太分散」——
那些層跑在四種執行環境裡，硬併只會多一層轉發。真正分散的是**結果長什麼樣**：
`checked_at` / `captured_at` / `ts` 三種時間欄名、rc 語意各 repo 不同、有的只寫 stdout 不留檔。
於是「哪一層沒人在跑」要人逐一翻。

契約（固定七個鍵）：

    {"layer": "rwd_mobile_quality",       # 層的識別（檔名式，跨 repo 不重複）
     "checked_at": "2026-09-06T12:34:56Z",# ISO-8601 UTC，永遠是這個鍵名
     "verdict": "GREEN|YELLOW|RED|REPORT",# REPORT＝僅報告，不判紅
     "rc": 0,                             # 0 綠 / 1 黃 / 2 紅（與 runner 的退出碼同義）
     "summary": "一句話",                 # 人看得懂的一句
     "evidence": {...},                   # 該層自己的數字，形狀自由
     "writer": "result_contract/1"}

用法（新層一律用它；存量層在動到時順手改，同 lib 採用率的節奏）：

    from lib.result_contract import write_result
    write_result("rwd_mobile_quality", rc, "字級 0／點擊目標 59", {"tinyFont": 0, "smallTap": 59})

落點：`wiki/memory/integration-health/<layer>.json`（機制圖 weekly 113 只讀這裡）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .paths import repo_root

VERDICTS = {0: "GREEN", 1: "YELLOW", 2: "RED"}
CONTRACT_VERSION = "result_contract/1"


def contract_dir() -> Path:
    d = repo_root() / "wiki" / "memory" / "integration-health"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_result(
    layer: str,
    rc: int,
    summary: str,
    evidence: Optional[Mapping[str, Any]] = None,
    *,
    report_only: bool = False,
) -> Path:
    """寫一份符合契約的結果；回傳寫到哪個檔。

    `report_only=True` ⇒ verdict 記成 REPORT（那一層本來就不判紅，不該被當成綠燈算進健康度）。
    寫檔失敗不拋例外：**留痕失敗不該讓被檢的那件事變成紅燈**，但會回傳路徑供呼叫端判斷。
    """
    path = contract_dir() / f"{layer}.json"
    payload = {
        "layer": layer,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "REPORT" if report_only else VERDICTS.get(int(rc), "RED"),
        "rc": int(rc),
        "summary": summary,
        "evidence": dict(evidence or {}),
        "writer": CONTRACT_VERSION,
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return path


def read_result(layer: str) -> Optional[dict]:
    """讀回某一層的結果；沒有或壞掉回 None（呼叫端不得把 None 當成綠）。"""
    p = contract_dir() / f"{layer}.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if isinstance(d, dict) and d.get("writer", "").startswith("result_contract/") else None
