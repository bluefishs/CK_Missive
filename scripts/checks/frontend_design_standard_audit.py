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

# ─────────────────────────────────────────────────────────────────────────
# 2026-08-29 owner 裁示「表格**皆需**提供篩選排序機制」⇒ 範圍擴到業務子元件。
#
# 在此之前本檔只掃「頁面根目錄的業務列表」，回報 0 —— 那個 0 是對的，
# 但它答的是比 owner 問的更窄的問題。實際有 42 個檔直接用 antd <Table>
# 繞過增強，其中 13 個是使用者會想排序篩選的業務資料（報價明細／作業歷程／
# 承辦證照／關聯公文／付款追蹤…）。
#
# 首版全掃會產出 30 處噪音，多為診斷表 —— 所以這裡不是取消範圍限制，
# 而是**把範圍換成白名單制**：診斷／開發者工具明列豁免，其餘一律要增強。
# 白名單要有人判過型，不是「還沒改的收容所」。
# 診斷／開發者工具 —— **owner 2026-08-29 明示豁免**（「診斷表是豁免 並非依照」）。
# 「表格皆需提供篩選排序機制」這條規範的對象是**業務表格**，不含這些。
DIAGNOSTIC_DIRS = (
    "pages/codeGraph/",            # 程式碼圖譜：開發者診斷
    "pages/databaseManagement/",   # 資料庫管理：DBA 工具
    "pages/memoryWiki/",           # 記憶維基：意識體內部狀態
    "pages/unifiedFormDemo/",      # 表單 demo
    "components/ai/management/",   # AI 管理台：模型/工具診斷
    "components/admin/",           # 系統管理診斷面板
    "pages/systemManagement/",     # 系統管理
    "pages/knowledgeBase/",        # 知識庫：治理文件檢視
    "pages/digitalTwin/",          # 數位孿生診斷面板
    "pages/deployment/",           # 部署歷程：運維診斷
    "components/dashboard/SearchStatsDashboard",  # 搜尋統計診斷
    "components/site-management/",  # 站台設定管理
)

# 檔案級豁免 —— 逐一判過型，理由寫在這裡（不是「還沒改的收容所」）
EXEMPT_FILES = {
    # 排序會打亂輸入順序：這是**編輯用**表格（逐項明細輸入），不是資料檢視
    "pages/erpQuotation/QuotationTemplateCreatePage.tsx":
        "報價明細輸入表，列順序即報價單列順序，不得被排序打亂",
    # 它自己就是另一個表格基礎元件（內建 sortConfig），不是業務表格
    "components/common/UnifiedTable.tsx":
        "表格基礎元件，自帶 sortConfig；EnhancedTable 亦建構於此類包裝之上",
    "components/common/ResponsiveTable.tsx":
        "它就是共用表格包裝本身（antd Table 的封裝），不是業務表格",
    # 2026-08-29：這一個是**有意識的決定**，不是漏改。原註解：「刻意不改用
    # EnhancedTable —— 那會連帶套上自動排序/篩選，對 owner 每天在看的
    # 晨報追蹤表，行為變動的風險高於收益。」它的窄螢幕溢出已另行修正
    # （scroll 判準改 isNarrow），排序則是逐欄手動宣告。
    "components/taoyuan/MorningReportTrackingTable.tsx":
        "owner 每日使用的晨報追蹤表，刻意保留手工欄位宣告；排序已逐欄手動加",
}

# 用了 Table.Summary 等靜態子元件者 —— EnhancedTable 是函式包裝沒有那些成員，
# 其排序篩選需在 columns 手動宣告（該檔內已註記理由）。
TABLE_STATIC_MEMBER = re.compile(r"<Table\.(Summary|Column|ColumnGroup)")


def _files():
    for p in sorted(PAGES.rglob("*.tsx")):
        if "__tests__" in str(p) or ".test." in p.name:
            continue
        yield p


def _sibling_column_sources(p: Path, text: str) -> str:
    """把本檔 import 進來的**同目錄/子目錄欄位模組**內容併進來一起判。

    2026-08-29：`PaymentsTab.tsx` 的 columns 來自 `payments/usePaymentColumns.ts`，
    而本檢核只掃 `.tsx` ⇒ 看不到那裡的 sorter，會誤報「這張表沒有排序」。
    判準看的是「這張表有沒有排序篩選」，那就必須跟著欄位定義走。
    """
    out = []
    for m in re.finditer(r"from\s+'(\.[^']+)'", text):
        spec = m.group(1)
        for ext in (".ts", ".tsx", "/index.ts"):
            cand = (p.parent / (spec + ext)).resolve()
            if cand.is_file():
                try:
                    out.append(cand.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    pass
                break
    return "\n".join(out)


def _biz_component_files():
    """業務子元件：pages/ 子目錄 + components/ 底下，扣掉診斷類。"""
    src = ROOT / "frontend" / "src"
    for base in (PAGES, src / "components"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.tsx")):
            rel = str(p.relative_to(src)).replace("\\", "/")
            if "__tests__" in rel or ".test." in p.name:
                continue
            if base == PAGES and p.parent == PAGES:
                continue  # 頁面根目錄由判準 2 掃過了
            if any(d in rel for d in DIAGNOSTIC_DIRS) or rel in EXEMPT_FILES:
                continue
            yield p, rel


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

    # 2.5) 業務子元件的表格（owner 2026-08-29「表格皆需」）
    raw_sub = []
    for p, rel in _biz_component_files():
        raw = p.read_text(encoding="utf-8", errors="ignore")
        scanned += 1
        # ⚠️ 必須去掉註解再判「有沒有用 EnhancedTable」。
        # 2026-08-29：`MorningReportTrackingTable.tsx` 是 /taoyuan/dispatch 預設分頁的
        # 16 欄表格（實測 768px 外溢 580px），本檢核卻放過它 —— 因為它的註解裡
        # 寫著「這裡刻意不改用 EnhancedTable」，`"EnhancedTable" in t` 就成立了。
        # **判準命中的是說明文字，不是程式碼**（同日在 weekly 81 也犯過同一個錯）。
        t = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", raw)
        if not re.search(r"<Table[\s<]", t) or "EnhancedTable" in t:
            continue
        # ⚠️ 欄位定義可能不在本檔：`PaymentsTab.tsx` 的 columns 來自
        # `payments/usePaymentColumns.ts`（**.ts 不是 .tsx**，不在掃描範圍內）。
        # 只看本檔會①誤報它「沒有排序」②反過來也可能漏掉真的沒排序的表。
        # 故判定要**連同它 import 的同目錄欄位模組一起看**。
        t += _sibling_column_sources(p, t)
        if not re.search(r"dataIndex", t):
            continue  # 沒有欄位定義的不是資料表
        # 逐欄手動宣告也算數 —— 規範要的是「有排序篩選機制」，不限定實作方式。
        # PaymentsTab 用 Table.Summary 不能自動增強，改為手動宣告 5 個 sorter。
        if re.search(r"\bsorter\b|\bfilters:", t):
            continue
        if TABLE_STATIC_MEMBER.search(t):
            continue  # 用了 Table.Summary 等靜態成員，見上方說明
        raw_sub.append(rel)

    print(f"\n  掃描 {scanned} 個前端檔")

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
    report("業務子元件直接用 antd <Table>", raw_sub,
           "owner 2026-08-29「表格皆需提供篩選排序機制」——「皆需」包含子元件。"
           "改用 EnhancedTable 即自動獲得（換 import 即可，不必逐欄宣告）。"
           "若確屬診斷／開發者工具，請加進 DIAGNOSTIC_DIRS 並註明理由。")
    report("詳情頁沒有用 DetailPageLayout", no_layout,
           "分頁深連結（?tab=）由 DetailPageLayout 提供；不用它就無法從晨報／"
           "LINE 直接連到特定分頁，也無法被行動觀測量到非預設分頁。")

    total = len(action_col) + len(raw_table) + len(raw_sub) + len(no_layout)
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
