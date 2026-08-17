#!/usr/bin/env python
"""型別 SSOT 稽核（weekly）—— endpoints 不得有本地 BaseModel。

依據：`.claude/rules/development-rules.md` §3
「`backend/app/api/endpoints/` **禁止**本地 BaseModel，唯一來源為 `app/schemas/`」

## 為什麼需要這一支

2026-08-16：我在同一輪裡新增了兩個端點檔並各自定義本地 BaseModel ——
規範白紙黑字寫著禁止，`endpoints/erp/` 其餘 13 檔也都乖乖從 schemas 匯入，
**而沒有任何機制會擋下我**。是 stop hook 讀規範時發現的。

順手掃全，才發現這條規範已經累積 **6 檔 18 個違規**：

    wiki.py                            4
    ai/memory.py                       7
    ai/kunge.py                        2
    ai/morning_report_subscriptions.py 2
    tender_module/enrichment_review.py 2
    tender_module/subscriptions.py     1

規範寫了很久、大家大致遵守、但沒有人在強制 —— 於是它慢慢變成「建議」。
這就是本專案反覆記錄的那個形狀：**規範存在不等於規範生效**。

## 為什麼這條規範重要（不是潔癖）

型別定義在端點檔裡，前端要對照契約時得翻端點；欄位一改，
`schemas/` 那份與端點那份會各自演化，而**兩份不一致時沒有任何一方會報錯** ——
序列化只會少一個欄位，畫面少一格，不拋錯。

## 存量已清零（2026-08-17）

owner：「違規請檢視評估並納入作業安排，**不要讓規範變建議**」。

原本打算把 18 個列 baseline 慢慢清 —— 但那正是「規範變建議」的機制本身：
baseline 一旦存在就會一直存在，而「只減不增」在沒有期限的情況下等於「不減」。

18 個逐一檢視後全部是**單純的 request/response DTO**（無驗證器、無交叉引用），
搬遷是機械式的。當天全部搬完：

    wiki.py 4 → schemas/wiki.py
    ai/memory.py 7 → schemas/ai/memory.py
    ai/kunge.py 2 → schemas/ai/kunge.py
    ai/morning_report_subscriptions.py 2 → schemas/ai/morning_report.py
    tender_module/{enrichment_review 2, subscriptions 1} → schemas/tender_admin.py

**baseline 檔已刪除** —— 留一份空基線只會讓人以為還有存量。
現在任何一個本地 BaseModel 都是 RED，沒有例外。

## 這支是範本

本專案是 portfolio 的範例專案。這支的 baseline 機制本身即可複用：
存量列入 → 只減不增 → **清光就刪檔轉嚴格**。
關鍵是最後一步 —— 沒有那一步，baseline 就是規範的墳墓。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = ROOT / "backend" / "app" / "api" / "endpoints"
BASELINE = Path(__file__).with_name(".schema_ssot_baseline.txt")

CLASS_RE = re.compile(r"^class\s+(\w+)\(BaseModel\)", re.M)


def scan() -> set[str]:
    found = set()
    if not ENDPOINTS.exists():
        return found
    for f in ENDPOINTS.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        try:
            src = f.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = f.relative_to(ENDPOINTS).as_posix()
        for name in CLASS_RE.findall(src):
            found.add(f"{rel}::{name}")
    return found


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        ln.strip()
        for ln in BASELINE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def main() -> int:
    print("=" * 74)
    print("型別 SSOT 稽核（endpoints 不得有本地 BaseModel）")
    print("=" * 74)
    print()

    found = scan()
    baseline = load_baseline()

    new = sorted(found - baseline)
    fixed = sorted(baseline - found)

    print(f"  掃描 endpoints/ ｜ 本地 BaseModel {len(found)} 個"
          f"（存量 baseline {len(baseline)}）")
    print()

    if fixed:
        print(f"  🟢 已修好 {len(fixed)} 個 —— 請把它們從 baseline 移除，否則存量只增不減：")
        for x in fixed:
            print(f"       · {x}")
        print()

    if new:
        print(f"  🔴 新增 {len(new)} 個違規：")
        for x in new:
            print(f"       ✗ {x}")
        print()
        print("       依 .claude/rules/development-rules.md §3，")
        print("       型別定義唯一來源是 backend/app/schemas/。")
        print("       端點改為匯入即可（純搬遷，零行為變更）。")
        print()
        print("       為什麼不是潔癖：兩份定義各自演化時**沒有任何一方會報錯** ——")
        print("       序列化只會少一個欄位，畫面少一格，不拋錯。")
        print()
        print("Status: [RED] 有新的本地 BaseModel")
        return 2

    if fixed:
        print("Status: [YELLOW] 存量有減少，baseline 需更新")
        return 1

    print("Status: [GREEN] 沒有新增違規")
    return 0


if __name__ == "__main__":
    sys.exit(main())
