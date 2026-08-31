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

# 2026-08-17：這支跑在 host weekly，但**在容器裡跑會印出誤導的訊息** ——
# 容器內 `backend/app/schemas/…` 不存在（那裡是 `/app/app/schemas/…`），
# 而原本的輸出寫「檔案不存在（清單過期？）」＝ **把路徑問題說成清單問題**，
# 看到的人會去改清單，而清單是對的。這是 L52（host↔容器路徑）
# 疊上 L83（訊息與真因不符）。
#
# 修法不是讓它在容器裡也能跑（前端原始碼本來就不在容器裡，跑不了），
# 而是**讓它說得出「這裡不是我該跑的地方」** —— 找不到 frontend/ 就直接
# 拒絕執行並說明，而不是把每一項都判成違規。
IN_REPO = (ROOT / "frontend" / "src").is_dir() and (ROOT / "backend" / "app").is_dir()

# 受管的寫入端 schema：(檔案, 類別, 欄位, 應有的約束名稱)
# 只列「有既定詞彙表」的欄位 —— 自由文字欄位（description/notes）不在此列。
MANAGED_SCHEMAS = [
    ("backend/app/schemas/erp/ledger.py", "LedgerCreate", "category", "LEDGER_CATEGORIES"),
    ("backend/app/schemas/erp/expense.py", "ExpenseInvoiceCreate", "category", "EXPENSE_CATEGORIES"),
]

# 前端：欄名像列舉、卻用自由輸入元件收的
#
# ⚠️ 2026-08-17 擴充：原本只認 `category|status|type`，於是
# **`billing_period`（期別）不在視野裡** —— owner 回報「建議期別採下拉選單，
# 避免不同專案不一致」時，實測 51 筆已經漂成三種寫法
# （第一期 47／第一期款項 3／資訊系統第一期款 1）。
#
# 那不是判定寬鬆，是**欄名不長那個樣子所以整欄不在被掃描的集合裡** ——
# 與同日「案件待辦五種缺口全從下游表出發」是同一個形狀的盲區。
#
# 加 `period` 與 `level`（期別／等級都是有限詞彙）。**沒有加 `name`／`code`**：
# 那兩個多數是自由文字或外部識別碼，加了會得到一長串假陽性，
# 而不可信的清單比沒有清單更糟（本專案 08-03 已為此砍掉一個維度）。
FORM_ITEM = re.compile(
    r'<Form\.Item[^>]*name="(?P<name>[a-z_]*(?:category|status|type|period|level))"'
    r'(?P<rest>.*?)</Form\.Item>',
    re.S,
)
# `<InputNumber>` 與 `<Input type="number">` 都不算自由輸入收詞彙：
# 前者是數值元件，後者實測是「有界數值」（NavigationItemForm 的 `level`
# 是 `type="number" min={1} max={5}` 的階層深度，不是詞彙表）——
# 那是我 2026-08-17 擴充 `period|level` 時造成的假陽性，
# 用通則收掉而不是個案豁免：往後任何有界數值欄位都不會再誤報。
FREE_INPUT = re.compile(r'<Input(?:\s(?!type="number")|/|>)(?!Number)')

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


# ── §3 前端鏡像 vs 後端權威（2026-08-31 追加）──────────────────────
#
# 為什麼加在這一支而不是新開一支：它問的是同一件事的第三面 ——
# §1「寫入端有沒有約束」、§2「前端表單有沒有約束」、§3「**前端的複本跟上了沒有**」。
#
# 觸發事件：`frontend/src/types/erp.ts` 檔頭寫「對應後端 app/schemas/erp/」，
# 而 `ExpenseSource` 只有 6 個值、後端 `ExpenseInvoiceBase.source` 有 9 個。
# 後果不是型別錯誤：`EXPENSE_SOURCE_LABELS` 是以該聯集為鍵的 `Record`，
# 後端送 `smart_qr` 進來查表得 `undefined` ⇒ **畫面空白而 tsc 全綠**。
# 實測正式庫 9 筆費用發票裡 6 筆正是 `smart_qr` —— 缺的是多數。
#
# ⚠️ **配對必須明列，不得自動發現。** 我第一版用「值集合重疊」自動配對，
#    把後端 `CaseFinanceRecord.type`（expense|billing|invoice，記錄種類）
#    配成前端 `VoucherType`（invoice|receipt|ticket|utility|other，憑證類別）——
#    兩個不同概念只因都含 `invoice`。
#    跨 session（CK_AaaP）同日的同型結論更關鍵：**若用「掃出所有相符者」當分母，
#    一個複本漂移之後只會默默離開集合，而集合仍然全綠。**
#    `erp.ts` 正是如此 —— 它沒有從任何清單裡消失，它只是不再正確。
#
# ⚠️ 只有這兩個前端聯集在後端有 `Literal` 權威；其餘 10 個後端是純 `str`
#    （即「沒有人在守門」，那是 §1 的職責，不在本節重複判）。
MIRROR_PAIRS = [
    # (前端型別名, 後端檔, 後端 class, 後端欄位)
    ("ExpenseSource", "expense.py", "ExpenseInvoiceBase", "source"),
    ("LedgerEntryType", "ledger.py", "LedgerBase", "entry_type"),
]
MIRROR_FILE = "frontend/src/types/erp.ts"


def _fe_union(text: str, name: str):
    m = re.search(rf"export type {re.escape(name)}\s*=\s*((?:[^;])+);", text)
    if not m:
        return None
    return set(re.findall(r"'([^']*)'", m.group(1)))


def _be_literal(text: str, cls: str, field: str):
    ci = text.find(f"class {cls}")
    if ci < 0:
        return None
    nxt = text.find("\nclass ", ci + 1)
    blk = text[ci: nxt if nxt > 0 else len(text)]
    m = re.search(rf"^\s*{re.escape(field)}\s*:\s*(?:Optional\[)?Literal\[([^\]]+)\]",
                  blk, re.M)
    if not m:
        return None
    return set(re.findall(r'["\']([^"\']+)["\']', m.group(1)))


def check_mirrors():
    """回 [(前端型別, 後端來源, 後端有而前端沒有的值)]；查不到來源也算違規。"""
    bad = []
    fe_path = ROOT / MIRROR_FILE
    if not fe_path.is_file():
        return [(MIRROR_FILE, "—", {"（鏡像檔不存在）"})]
    fe = fe_path.read_text(encoding="utf-8", errors="replace")
    for fe_name, be_file, be_cls, be_field in MIRROR_PAIRS:
        src = f"{be_cls}.{be_field}"
        fv = _fe_union(fe, fe_name)
        be_path = ROOT / "backend" / "app" / "schemas" / "erp" / be_file
        bv = _be_literal(be_path.read_text(encoding="utf-8", errors="replace"),
                         be_cls, be_field) if be_path.is_file() else None
        # 任一端讀不到就是違規：明列的配對消失了，而消失不該是靜默的
        if fv is None or bv is None:
            bad.append((fe_name, src, {"（配對的一端已不存在，判準失效）"}))
            continue
        missing = bv - fv
        if missing:
            bad.append((fe_name, src, missing))
    return bad


def main() -> int:
    print("=" * 74)
    print("列舉值儲存慣例稽核")
    print("=" * 74)
    print()

    # 環境守衛：這支要讀 frontend 原始碼與 backend schema，兩者只在 repo 工作區裡。
    # 在容器內（只掛 scripts/、backend/logs…）拿不到 → **明講不是這裡該跑的**，
    # 而不是把每一項判成違規（那會讓人去改一份本來正確的清單）。
    if not IN_REPO:
        print("  ⊘ 此環境不含 repo 工作區（frontend/src 或 backend/app 不在）")
        print("     本稽核須在 host 執行（weekly 58）—— 未判定，不代表通過。")
        return 0

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

    mirror_bad = check_mirrors()
    print(f"  §3 前端鏡像跟上後端權威（{len(MIRROR_PAIRS)} 對明列配對）")
    if mirror_bad:
        for fe_name, src, missing in mirror_bad:
            print(f"       ✗ {MIRROR_FILE} 的 `{fe_name}` 缺 {sorted(missing)}")
            print(f"          後端權威：schemas/erp/{src}")
        print()
        print("       後端能送出而前端聯集不含的值 ⇒ 以該聯集為鍵的 Record 查表得")
        print("       undefined ⇒ **畫面空白，而 tsc 全綠**（資料被宣告成該型別，")
        print("       但那個宣告是假的）。手工維護的鏡像不會告訴你它落後了。")
    else:
        print("       🟢 明列配對皆一致")
    print()

    if schema_bad or form_bad or mirror_bad:
        print("Status: [RED] 違反列舉值儲存慣例")
        print("  依據：docs/architecture/ENUM_STORAGE_CONVENTION.md")
        return 2

    print("Status: [GREEN] 符合慣例")
    return 0


if __name__ == "__main__":
    sys.exit(main())
