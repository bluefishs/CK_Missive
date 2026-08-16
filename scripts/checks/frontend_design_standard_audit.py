#!/usr/bin/env python
"""前端設計規範檢核 —— 規範寫在文件裡沒有人在強制。

## 為什麼需要這一支（2026-08-15 owner 逐項指出）

同一天 owner 連續指出四件事，**每一件都已經有正確範例存在於程式碼中**，
只是沒有擴散，而且**沒有任何機制在問**：

| owner 指出 | 正確範例早就有 | 為何沒被發現 |
|---|---|---|
| `/erp/quotations` 列表仍有操作欄，應對照 `/documents` 整併到詳情 | `/documents` 沒有操作欄 | 沒有檢核 |
| 表格皆需可排序篩選，`/erp/quotations` 缺漏 | `enhanceColumns` 自動加 | 沒有檢核 |
| 統計卡片要能與列表互動篩選 | `ClickableStatCard`（含 active 樣式） | 沒有檢核 |
| 詳情頁分頁要能深連結 | `TaoyuanDispatchPage` 用 `?tab=` | 沒有檢核 |

共同形狀：**規範存在、正確做法存在、但沒有窗口在問「有沒有照做」**，
於是每新增一個頁面就多一份漂移。這與本專案反覆記過的
「有正確範例卻沒擴散」是同一件事。

## 判準（只收靜態可驗證的，且每條都先驗過鑑別力）

1. **列表頁不得有「操作」欄** —— CRUD 收在詳情頁（`/documents` 為範本）。
   例外：沒有詳情頁的頁面（如統一帳本）—— 那些列在 `NO_DETAIL_PAGE`。
2. **表格必須用 `EnhancedTable`** —— 排序與篩選由它自動加；
   直接用 antd `<Table>` 就沒有，而那是規範要求的能力。
3. **詳情頁必須用 `DetailPageLayout`** —— 分頁深連結（`?tab=`）由它提供。

## 刻意不做的

- **不判斷「數字有沒有超框」**：那需要真的渲染量測，靜態看不出來。
  而且行動觀測的 `pageOverflow` 對它是**盲的** ——
  元素在固定寬度欄位裡被裁切不會撐寬文件（2026-08-15 owner 回報
  `/erp/quotations/168` 數字超框時，量測顯示 0 溢出）。
  這一類只能靠真人或視覺走查。
- **不判斷統計卡片有沒有互動**：`Statistic` 用在很多不該互動的地方
  （單純呈現總額），一律判紅會產出整片噪音。
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
PAGES = ROOT / "frontend" / "src" / "pages"

# 沒有詳情頁的列表 —— 操作只能放列上，不算違規
NO_DETAIL_PAGE = {
    "ERPLedgerPage.tsx",          # 統一帳本：分錄無詳情頁
    "ERPEInvoiceSyncPage.tsx",    # 電子發票同步：同步紀錄無詳情頁
}

# 這些不是「列表頁」：表單、儀表板、掃描、詳情
NOT_A_LIST = re.compile(r"(FormPage|CreatePage|EditPage|DetailPage|Dashboard|Hub|Scan)")


def _files():
    for p in sorted(PAGES.rglob("*.tsx")):
        if "__tests__" in str(p) or ".test." in p.name:
            continue
        yield p


def main() -> int:
    print("=" * 72)
    print("前端設計規範檢核（列表操作欄／表格能力／詳情頁模板）")
    print("=" * 72)

    if not PAGES.is_dir():
        print(f"\n✗ 找不到 {PAGES} —— 無法判定（不視為通過）")
        return 2

    action_col, raw_table, no_layout = [], [], []
    scanned = 0

    for p in _files():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        t = p.read_text(encoding="utf-8", errors="ignore")
        scanned += 1

        is_detail = p.name.endswith("DetailPage.tsx")
        is_list = not NOT_A_LIST.search(p.name) and ("columns" in t or "<Table" in t)

        # 1) 列表頁的操作欄 —— **只在該頁已經支援點列進詳情時才算違規**。
        #
        # 首版只看「有沒有 title:'操作'」，得到 13 處，其中多數是假陽性：
        # BackupLogsTab／DeployHistoryCard／TablesTab 是管理診斷頁，沒有詳情頁，
        # 操作只能放列上；InvoiceSubTable 是子表格不是列表頁。
        # 收窄成「已有 onRow 導向詳情，卻還留著操作欄」＝**確定重複**，
        # 而且那些按鈕都要 stopPropagation 才不會打架 —— 那就是判準本身。
        has_row_nav = bool(re.search(r"onRow[\s\S]{0,200}navigate\(", t))
        if has_row_nav and re.search(r"title:\s*['\"]操作['\"]", t):
            action_col.append(rel)

        # 2) 表格能力：**只看業務列表頁**（頁面根目錄的 ListPage/Page），
        # 不看管理診斷與子元件 —— 那些表格不是規範要求可排序篩選的對象，
        # 一律判紅會產出整片噪音（首版 30 處，多為 codeGraph／databaseManagement 診斷表）。
        is_business_list = (
            p.parent == PAGES
            and not NOT_A_LIST.search(p.name)
            and re.search(r"dataIndex", t)
        )
        if is_business_list and re.search(r"<Table[\s<]", t) and "EnhancedTable" not in t:
            raw_table.append(rel)

        # 3) 詳情頁模板
        if is_detail and "DetailPageLayout" not in t:
            no_layout.append(rel)

    print(f"\n  掃描 {scanned} 個頁面檔")

    def report(title, items, why):
        print(f"\n  {'🟡' if items else '🟢'} {title}：{len(items)}")
        for i in items[:8]:
            print(f"      · {i}")
        if items:
            print(f"      → {why}")

    report("列表頁仍有「操作」欄", action_col,
           "CRUD 應收在詳情頁（對照 /documents）。這些按鈕都要 stopPropagation "
           "才不會和點列進詳情打架 —— 那本身就是「不該在這裡」的訊號。")
    report("直接用 antd <Table>（沒有排序篩選）", raw_table,
           "改用 EnhancedTable —— 規範要求表格皆需可排序篩選，"
           "而那是 enhanceColumns 自動加上的。")
    report("詳情頁沒有用 DetailPageLayout", no_layout,
           "分頁深連結（?tab=）由 DetailPageLayout 提供；不用它就無法從晨報／"
           "LINE 直接連到特定分頁，也無法被行動觀測量到非預設分頁。")

    total = len(action_col) + len(raw_table) + len(no_layout)
    print()
    if total:
        print(f"Status: [YELLOW] {total} 處偏離設計規範")
        print("  刻意判 YELLOW 不判 RED：這些不是故障，是規範沒有被強制，")
        print("  而每一條都有正確範例存在於程式碼中，只是沒有擴散。")
        return 1
    print("Status: [GREEN] 列表操作欄／表格能力／詳情頁模板皆合規")
    return 0


if __name__ == "__main__":
    sys.exit(main())
