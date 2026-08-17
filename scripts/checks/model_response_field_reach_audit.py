#!/usr/bin/env python
"""ORM 欄位有沒有到達 API 回應（weekly）。

## 為什麼需要這一支

2026-08-17：我加 `quotation_no` / `revision` 時只做到 DB 與 ORM 就停了。
Pydantic 對「model 上有、response schema 沒有」的欄位是**靜默丟棄**：

    · migration 執行了、78 筆回填了、唯一索引建了
    · ORM 有欄位、產號器可用
    · **而 API 永遠不回傳它，前端 grep `quotation_no` 零命中**
    · `QT2026_018` 存在資料庫，使用者永遠看不到

那是同一天剛修過的失敗形狀（待填報連結指向沒有人在讀的 query 參數）：
**產出端完成、接收端無人讀取、不拋錯、稽核仍綠、功能目的落空。**

而既有的 `schema_ssot_audit` **結構上抓不到它** —— 它只問
「endpoints 有沒有本地 BaseModel」，不問「欄位有沒有到達回應」。
這正是「檢核問對了問題但座標系不含它」（08-10 資料庫埠同型）。

## 判準

受管的 (ORM model, response schema) 配對，逐欄比對：
model 有而 schema 沒有的欄位 → 列出來。

## 刻意的界限

**不是所有 ORM 欄位都該對外**：`password_hash`、內部 flag、
軟刪除時間戳，不回傳才是對的。所以這支**不判紅**，只列出差異
並要求每個「刻意不對外」的欄位寫進 `INTENTIONALLY_INTERNAL`。
沒有理由的差異就是候選缺陷。
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

# 受管配對：(ORM 檔, ORM 類別, schema 檔, schema 類別)
#
# 先只納管**本輪出過事的**與**金額相關的**。刻意不一次納管全部 77 張表 ——
# 那會產出一份幾百行、沒有人讀得完的差異清單，而讀不完的清單等於沒有清單
# （本專案 08-10 記過：「讀不完的索引與沒有索引是同一件事」）。
MANAGED = [
    ("backend/app/extended/models/erp.py", "ERPQuotation",
     "backend/app/schemas/erp/quotation.py", "ERPQuotationResponse"),
    ("backend/app/extended/models/invoice.py", "ExpenseInvoice",
     "backend/app/schemas/erp/expense.py", "ExpenseInvoiceResponse"),
]

# 刻意不對外的欄位 —— **必須寫理由**。沒有理由的豁免等於沒有豁免。
INTENTIONALLY_INTERNAL: dict[str, dict[str, str]] = {
    "ERPQuotation": {
        "deleted_at": "軟刪除時間戳，屬內部狀態；對外只看得到未刪除的資料",
        "updated_at": "既有 Response 未含，且前端不使用；納入會改變契約",
        "budget_limit": "預算上限屬內部管控，已由 budget_usage_pct 表達",
    },
    "ExpenseInvoice": {
        "deleted_at": "同上",
        "updated_at": "同上",
        "vendor_id": "以 vendor 名稱對外，id 屬內部關聯",
        "approved_by": "以 approved_by_name 對外（2026-08-17 加），id 屬內部",
        "operational_account_id": "已有 attribution_type 表達歸屬",
        "source_image_path": "已由 receipt_image_path 對外",
    },
}

COL_RE = re.compile(r"^\s{4}(\w+)\s*(?::\s*[^=]+)?=\s*Column\(", re.M)
FIELD_RE = re.compile(r"^\s{4}(\w+)\s*:", re.M)


def _class_body(path: Path, cls: str) -> str | None:
    if not path.exists():
        return None
    src = path.read_text(encoding="utf-8")
    m = re.search(rf"^class {cls}\(.*?\):(?P<body>.*?)(?=\nclass |\Z)", src, re.S | re.M)
    return m.group("body") if m else None


def main() -> int:
    print("=" * 74)
    print("ORM 欄位 → API 回應 可達性稽核")
    print("=" * 74)
    print()

    problems: list[str] = []
    for m_rel, m_cls, s_rel, s_cls in MANAGED:
        m_body = _class_body(ROOT / m_rel, m_cls)
        s_body = _class_body(ROOT / s_rel, s_cls)
        if m_body is None or s_body is None:
            problems.append(f"{m_cls}/{s_cls} 找不到（重構過？清單需更新）")
            print(f"  🔴 {m_cls} → {s_cls}：找不到類別")
            continue

        cols = set(COL_RE.findall(m_body))
        # schema 可能繼承 Base；這裡只比對本身宣告的欄位（保守：寧可少報不誤報）
        fields = set(FIELD_RE.findall(s_body))
        exempt = INTENTIONALLY_INTERNAL.get(m_cls, {})

        missing = sorted(cols - fields - set(exempt))
        mark = "🟡" if missing else "🟢"
        print(f"  {mark} {m_cls} → {s_cls}"
              f"（ORM {len(cols)} 欄／回應 {len(fields)} 欄／豁免 {len(exempt)}）")
        for f in missing:
            print(f"       · {f} —— ORM 有、回應沒有")
            problems.append(f"{m_cls}.{f}")
        print()

    if problems:
        print(f"Status: [YELLOW] {len(problems)} 個欄位到不了 API 回應")
        print()
        print("  這**不一定是缺陷** —— 有些欄位刻意不對外（密碼雜湊、內部 flag）。")
        print("  但每一個都要做決定，二選一：")
        print("    ① 加進 response schema（使用者需要看到它）")
        print("    ② 加進 INTENTIONALLY_INTERNAL **並寫理由**（刻意不對外）")
        print()
        print("  不做決定的後果：欄位存在資料庫而使用者永遠看不到，")
        print("  不拋錯、不留紀錄 —— `quotation_no` 2026-08-17 就是這樣。")
        return 1

    print("Status: [GREEN] 受管 ORM 欄位都到得了 API 回應（或已列明刻意不對外）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
