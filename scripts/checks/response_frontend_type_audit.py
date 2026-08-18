#!/usr/bin/env python
r"""後端 Response schema 的欄位，前端手寫型別宣告了嗎（weekly）。

## 這是契約鏈的第三面

    ① 前端 payload  → 寫入 schema     `write_payload_schema_audit`（weekly 62）
    ② ORM 欄位      → Response schema `model_response_field_reach_audit`（weekly 61）
    ③ Response      → **前端手寫型別**  ← 這一支

三面缺一面，欄位就會在那一段消失而沒有人報錯。

## 為什麼需要（2026-08-18 實例）

我在後端補了 `erp_vendor_payables.payable_period`（owner：「應收與應付
兩者設計不一致」），ORM、migration、Create/Update/Response schema
全部補齊 —— **但漏了 `frontend/src/types/erp.ts`**。

於是「應收有期別、應付沒有」這個不對稱，**在前端型別裡原封不動** ——
我以為修好的東西，在另一層還在。

`tsc` 沒抓到，因為使用端繞過了型別：
`payableToRecord(p: Record<string, unknown>)` 每個欄位都 `as` 轉型。

> **繞過型別的地方，型別就守不住那個欄位。**

順帶比對還揪出 `ERPVendorPayable` 少了 **7 個**後端一直有回傳的欄位
（vendor_code / vendor_id / due_date / invoice_number / notes /
created_at / updated_at）—— 那是既有缺口，只是從來沒有人在比對。

## 判準（刻意寬鬆的地方）

- 只比對**有明確對應**的 Response ↔ 前端介面配對（見 `PAIRS`），
  不做名稱猜測 —— 猜錯配對得到的清單不可信（08-17 那次掃描就是猜錯對象）。
- 前端多出的欄位**不報**：可能是前端組出來的顯示欄位，合理。
- 判 **YELLOW 不判 RED**：欄位沒宣告不會讓功能壞掉（使用端多半有轉型），
  它讓型別檢查失去守備能力 —— 是防護退化，不是現行故障。
  判紅會與真正壞掉的東西混在一起。
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
BE = ROOT / "backend" / "app" / "schemas"
FE_TYPES = ROOT / "frontend" / "src" / "types"

IN_REPO = BE.is_dir() and FE_TYPES.is_dir()

#: (後端 Response schema, 後端檔相對 schemas/, 前端介面, 前端檔相對 types/)
#: 明列而非猜配對 —— 新增模組時在這裡加一行，那一行本身就是「有人在看」的宣告。
PAIRS = [
    ("ERPBillingResponse", "erp/billing.py", "ERPBilling", "erp.ts"),
    ("ERPVendorPayableResponse", "erp/vendor_payable.py", "ERPVendorPayable", "erp.ts"),
    ("ERPQuotationResponse", "erp/quotation.py", "ERPQuotation", "erp.ts"),
]

#: 刻意不對外的欄位（前端不需要宣告），寫明理由
INTERNAL_OK: dict[str, str] = {
    "deleted_at": "軟刪除時間戳，前端不呈現",
    "created_by": "建立者 id，前端顯示用的是名稱不是 id",
}


def be_fields(rel: str, cls: str) -> list[str] | None:
    f = BE / rel
    if not f.exists():
        return None
    m = re.search(rf"class {cls}\([^)]*\):(.*?)(?=\nclass |\Z)", f.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    return re.findall(r"^\s{4}(\w+)\s*:", m.group(1), re.M)


def fe_fields(rel: str, iface: str) -> set[str] | None:
    f = FE_TYPES / rel
    if not f.exists():
        return None
    m = re.search(rf"interface {iface}\b[^{{]*\{{(.*?)\n\}}", f.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    return set(re.findall(r"^\s*(\w+)\??:", m.group(1), re.M))


def main() -> int:
    print("=" * 74)
    print("Response schema → 前端手寫型別（契約鏈第三面）")
    print("=" * 74)
    print()

    if not IN_REPO:
        print("  ⊘ 此環境不含 repo 工作區 —— 須在 host 執行，未判定不代表通過。")
        return 0

    gaps: list[tuple[str, list[str]]] = []
    broken: list[str] = []

    for cls, brel, iface, frel in PAIRS:
        bf = be_fields(brel, cls)
        ff = fe_fields(frel, iface)
        if bf is None or ff is None:
            # 找不到就明講 —— 「配對寫錯」與「完全一致」不得看起來一樣
            broken.append(f"{cls} ↔ {iface}（後端={'找到' if bf else '找不到'}／前端={'找到' if ff else '找不到'}）")
            continue
        missing = [f for f in bf if f not in ff and f not in INTERNAL_OK]
        print(f"  {iface:<22} 後端 {len(bf):>2} 欄／前端缺 {len(missing)}")
        if missing:
            gaps.append((iface, missing))

    if broken:
        print()
        print("🔴 配對解析失敗（清單過期或介面改名）：")
        for b in broken:
            print(f"      ✗ {b}")
        print("\nStatus: [RED] 無法判定 —— 不視為通過")
        return 2

    if gaps:
        print()
        print("🟡 後端會回傳、而前端型別沒有宣告的欄位：")
        for iface, miss in gaps:
            print(f"      · {iface}：{', '.join(miss)}")
        print()
        print("  後果不是功能壞掉，是**型別檢查守不住那些欄位** ——")
        print("  使用端靠 `as` 轉型取值時，加錯名字、漏掉新欄位，tsc 都不會吭聲。")
        print("  （2026-08-18 實例：後端補了 payable_period，前端型別漏掉，")
        print("   而「應收有期別、應付沒有」的不對稱就在前端原封不動地留著。）")
        print("\nStatus: [YELLOW] 前端型別落後於後端回應")
        return 1

    print("\n  🟢 受管配對的 Response 欄位，前端型別都有宣告")
    print("\nStatus: [GREEN] 契約第三面一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
