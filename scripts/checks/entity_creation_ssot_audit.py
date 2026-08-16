#!/usr/bin/env python
"""業務實體的建立路徑必須單一（weekly）。

## 為什麼需要這一支

2026-08-16 owner 追問「為何三條路徑 異質同工？」時查出來的：
「從標案建立 PM 案件」有**兩份各自獨立的實作**，而它們分歧到

    一鍵建案：查重 5 道、帶金額、帶委託單位、**邀標階段不建報價單**
    AI 工具  ：查重 1 道、不帶金額、無委託單位、**建了報價單 total_price=0**

那 5 道查重每一道都是踩坑後補的（註解寫著「案件 187 即為…」），
AI 工具一道都沒繼承。更嚴重的是最後一項是**業務規則相反**，
而**兩邊都不會報錯** —— 本專案反覆記錄的「同一件事有兩份說法」。

同型的第二例在同一天找到：前端 `caseInput` 在同一個檔案裡寫了兩次，
只有其中一份帶 `tender_id` → `pm_cases.source_tender_id` 74 筆中 **0 筆有值**。

## 這支在問什麼

**帶有建立規則（查重／編碼／必填）的業務實體，是不是只在一個地方被建構。**

`PMCase(...)` 這種直接建構如果散在 N 個地方，那 N 份就會各自演化 ——
不是「可能會」，是本專案已經發生兩次。

## 判準與豁免

每個受管實體宣告一個**允許建構的檔案清單**。清單外出現直接建構就是 RED。
清單本身要小 —— 清單一長就等於沒有規則。

⚠️ 這支**不判斷語意**（兩份實作是否等價需要人看），它只問「有幾個地方在建」。
數量本身就是訊號：能建的地方越多，分歧的機會越大。
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
APP = ROOT / "backend" / "app"

# 受管實體 → 允許直接建構的檔案（相對 backend/app）。
#
# 放進來的條件是「這個實體有建立規則」：查重、編碼產生、必填欄位、
# 或建立時要連動其他資料。純資料表（log / event / snapshot）不必管。
MANAGED = {
    "PMCase": {
        "allow": [
            "services/tender/case_creation.py",   # 從標案建案（一鍵 + AI 工具共用）
            "services/pm/case_service.py",        # 手動建案（不同業務場景：查重條件不同）
        ],
        "why": "案號產生 + 5 道查重 + 委託單位連動 + 金額帶入",
    },
    "ContractProject": {
        "allow": [
            "services/contract/case_code.py",     # 成案（由 PM 案件晉升）
            "services/contract/core.py",
        ],
        "why": "專案編號產生 + 成案前置檢查（合約金額必填）",
    },
    "ERPQuotation": {
        "allow": [
            # 唯一建立點＝**成案時**（`total_price` 取自 PM 案件的合約金額）。
            # 這是「邀標階段不建報價單」那條規則的對應面：報價單只在確定
            # 承攬後才存在。AI 工具原本在邀標階段就建一張 total_price=0 的，
            # 那會讓案件一出生就是「成本 0、毛利率 100%」。
            "services/contract/case_code.py",
        ],
        "why": "只在成案時建立，金額由 PM 案件帶入（邀標階段不得建立）",
    },
}

# 這些不算「建立」：註解、匯入、**類別定義本身**。
# ⚠️ `class PMCase(Base):` 首跑時被判成建構 —— 判準交付前必須先驗鑑別力，
#    這就是為什麼要先跑一次再決定要不要相信它。
SKIP_LINE = re.compile(r"^\s*(#|\"\"\"|'''|from |import |class |@)")


def scan(entity: str) -> list[tuple[str, int, str]]:
    """回傳 [(相對路徑, 行號, 該行)]。"""
    pat = re.compile(rf"(?<![A-Za-z_]){re.escape(entity)}\s*\(")
    hits = []
    for py in APP.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            lines = py.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for n, line in enumerate(lines, 1):
            if SKIP_LINE.match(line) or not pat.search(line):
                continue
            # 排除查詢用法：select(PMCase) / isinstance(x, PMCase)
            before = line[: pat.search(line).start()]
            if re.search(r"(select|isinstance|type|delete|update|insert)\s*\($", before.rstrip()):
                continue
            if re.search(r"(select|isinstance)\s*\(\s*$", before):
                continue
            hits.append((str(py.relative_to(APP)).replace("\\", "/"), n, line.strip()[:88]))
    return hits


def main() -> int:
    print("=" * 74)
    print("業務實體建立路徑 SSOT 稽核")
    print("=" * 74)
    print()

    violations = []
    for entity, spec in MANAGED.items():
        hits = scan(entity)
        allowed = set(spec["allow"])
        bad = [h for h in hits if h[0] not in allowed]
        ok_n = len(hits) - len(bad)

        mark = "🔴" if bad else "🟢"
        print(f"  {mark} {entity:<18} 建構 {len(hits)} 處"
              f"（允許 {ok_n}／未授權 {len(bad)}）")
        print(f"       建立規則：{spec['why']}")
        for path, n, line in bad:
            print(f"       ✗ {path}:{n}")
            print(f"           {line}")
            violations.append((entity, path, n))
        print()

    if violations:
        print("Status: [RED] 有未授權的實體建構點")
        print()
        print("  這些地方繞過了該實體的建立規則。它們今天可能是對的，")
        print("  但**規則改了不會有人同步它們** —— 2026-08-16 的和美案就是這樣來的：")
        print("  一鍵建案有 5 道查重，AI 工具那份只有 1 道，而兩邊都不報錯。")
        print()
        print("  修法：改為呼叫 MANAGED 裡列出的服務；")
        print("  若確定是不同業務場景（如手動建案 vs 從標案建案），")
        print("  把該檔加進 allow 清單並**寫明為什麼是不同場景**。")
        return 2

    print("Status: [GREEN] 受管實體都只在授權處建構")
    return 0


if __name__ == "__main__":
    sys.exit(main())
