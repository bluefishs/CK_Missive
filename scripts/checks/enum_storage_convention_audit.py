#!/usr/bin/env python
"""列舉值儲存慣例稽核（weekly）。

依據：`docs/architecture/ENUM_STORAGE_CONVENTION.md`（2026-08-16）

## 為什麼需要這一支

owner：「分類仍有中英紛雜 如統一帳本」。查證後根因有兩層：

1. **後端不約束**：`schemas/erp/expense.py` 的 `EXPENSE_CATEGORIES` 有 Literal，
   註解寫著「新增分類請同步更新此處與 ledger.py」——
   **而 ledger.py 的 category 是 `Optional[str]`，沒有可同步的東西**。
2. **前端自由輸入**：手動記帳表單的分類欄是
   `<Input placeholder="例：交通費、材料費" />` ——
   兩端都不約束，庫裡就長出 `billing_payment` 這種英文代碼。

這支檢核問兩件事，**兩件都不需要語意判斷**：

- 已知的分類／狀態欄位，寫入端 schema 有沒有 Literal 約束
- 前端表單有沒有拿 `<Input>` 去收列舉值（欄名命中 category/status/type）

⚠️ 它**不判斷值該用中文還是英文**（那是設計決策，見慣例文件規則 1），
只問「有沒有人在守門」。
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

# 受管的寫入端 schema：(檔案, 類別, 欄位, 應有的約束名稱)
# 只列「有既定詞彙表」的欄位 —— 自由文字欄位（description/notes）不在此列。
MANAGED_SCHEMAS = [
    ("backend/app/schemas/erp/ledger.py", "LedgerCreate", "category", "LEDGER_CATEGORIES"),
    ("backend/app/schemas/erp/expense.py", "ExpenseInvoiceCreate", "category", "EXPENSE_CATEGORIES"),
]

# 前端：欄名像列舉、卻用自由輸入元件收的
FORM_ITEM = re.compile(
    r'<Form\.Item[^>]*name="(?P<name>[a-z_]*(?:category|status|type))"'
    r'(?P<rest>.*?)</Form\.Item>',
    re.S,
)
FREE_INPUT = re.compile(r"<Input(?:\s|/|>)(?!Number)")

# 明確豁免：欄名命中但語意其實是自由文字
FORM_EXEMPT = {
    # (檔名, 欄位) → 理由
    ("TenderSearchPage.tsx", "type"): "標案類別來自外部資料源，非本系統詞彙",
}


def check_schemas() -> list[str]:
    bad = []
    for rel, cls, field, expect in MANAGED_SCHEMAS:
        p = ROOT / rel
        if not p.exists():
            bad.append(f"{rel} 不存在（清單過期？）")
            continue
        src = p.read_text(encoding="utf-8")
        # ⚠️ 首跑時我要求「必須在**寫入端**覆寫」—— 那是錯的：
        # `ExpenseInvoiceCreate` 繼承 `ExpenseInvoiceBase`，而約束就寫在 Base 上，
        # 一樣有效。正確的問法是「沿繼承鏈找得到約束嗎」，不是「有沒有覆寫」。
        chain, cur, seen = [], cls, set()
        while cur and cur not in seen:
            seen.add(cur)
            m = re.search(
                rf"class {cur}\((?P<bases>[^)]*)\):(?P<body>.*?)(?=\nclass |\Z)", src, re.S
            )
            if not m:
                break
            chain.append(m.group("body"))
            bases = [b.strip() for b in m.group("bases").split(",")]
            cur = next((b for b in bases if b and b[0].isupper() and b != "BaseModel"), None)

        if not chain:
            bad.append(f"{rel}::{cls} 找不到（重構過？清單需更新）")
            continue

        found = None
        for body in chain:
            line = re.search(rf"^\s*{field}\s*:(?P<t>.*)$", body, re.M)
            if line:
                found = line.group("t")
                break
        if found is None:
            bad.append(f"{rel}::{cls}.{field} 整條繼承鏈都找不到此欄位")
        elif expect not in found:
            bad.append(f"{rel}::{cls}.{field} 缺 {expect} 約束 → {found.strip()[:60]}")
    return bad


def check_forms() -> list[tuple[str, str]]:
    bad = []
    for tsx in (ROOT / "frontend" / "src").rglob("*.tsx"):
        if "node_modules" in tsx.parts or ".test." in tsx.name:
            continue
        try:
            src = tsx.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in FORM_ITEM.finditer(src):
            name, rest = m.group("name"), m.group("rest")
            if (tsx.name, name) in FORM_EXEMPT:
                continue
            # ⚠️ 首跑抓到 `<Form.Item name="milestone_type" hidden><Input /></Form.Item>` ——
            # hidden 欄位的 <Input> 只是值的容器，使用者根本看不到它，不是自由輸入。
            if "hidden" in m.group(0)[: m.group(0).find(">")]:
                continue
            if FREE_INPUT.search(rest):
                rel = str(tsx.relative_to(ROOT / "frontend" / "src")).replace("\\", "/")
                bad.append((rel, name))
    return bad


def main() -> int:
    print("=" * 74)
    print("列舉值儲存慣例稽核")
    print("=" * 74)
    print()

    schema_bad = check_schemas()
    print(f"  §1 寫入端 schema 約束（{len(MANAGED_SCHEMAS)} 個受管欄位）")
    if schema_bad:
        for b in schema_bad:
            print(f"       ✗ {b}")
    else:
        print("       🟢 全部有 Literal 約束")
    print()

    form_bad = check_forms()
    print("  §2 前端表單不得用自由輸入收列舉值")
    if form_bad:
        for rel, name in form_bad:
            print(f"       ✗ {rel} 的 `{name}` 用 <Input> 收")
        print()
        print("       改用 <Select options={...} />，選項取自單一定義處。")
        print("       自由輸入等於沒有詞彙表 —— 統一帳本就是這樣長出 `billing_payment` 的。")
    else:
        print("       🟢 未發現")
    print()

    if schema_bad or form_bad:
        print("Status: [RED] 違反列舉值儲存慣例")
        print("  依據：docs/architecture/ENUM_STORAGE_CONVENTION.md")
        return 2

    print("Status: [GREEN] 符合慣例")
    return 0


if __name__ == "__main__":
    sys.exit(main())
