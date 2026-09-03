# 欄位語意宣告表（FIELD_SEMANTICS）

> 建立：2026-09-03（全景覆盤 A1）。**這份表是「這欄就是這個意思」的唯一宣告處**；程式在讀寫兩端各自轉換不算宣告。
> weekly 104 `erp_amount_semantics_audit.py` 依本表對帳；改本表要同步改那支。

## 為什麼要有這份

09-02～09-03 出過的事，每一組都是「兩端各自以為」：
- 金額：三表存未稅、總表含稅 ⇒ 請款一建入 weekly 100 RED 87。
- 年份：前端送民國、後端比西元 ⇒ 四個列表的年度篩選從未生效（08-29）。
- 狀態：PM 案英文（contracted）、承攬案中文（執行中）⇒ 結案不同步 48 筆。
- 案號：舊制 `CK2025_01_01_003`、新制 `CK2026_PM_02_007`、成案 `CK2026_02_007` ⇒「01」在兩制裡意思不同。

## 金額

| 欄位 | 語意 | 依據 |
|---|---|---|
| `erp_quotations.total_price` | **含稅總價**（＝總表「總價」） | 09-02 A85 對齊 115 筆；一次請領 199/199 ＝ total_price |
| `erp_quotations.tax_amount` | 營業稅額（5%）；未稅＝`total_price − tax_amount` | 不另存未稅欄，由 view 推導 |
| `erp_quotations.outsourcing_fee／personnel_fee／overhead_fee／other_cost` | 成本結構，未稅 | 毛利＝total_price − tax − 成本 |
| `erp_billings.billing_amount` | 該期請款額，**含稅** | 與 total_price 同語意；多期合計 ≤ total_price × 1.1（`_guard_billing_within_contract`） |
| `erp_billings.payment_amount` | 實收，含稅；`paid` 時必填且 ≤ billing_amount | billing_service.create 守衛 |
| `erp_invoices.amount` | 發票**含稅**額（＝銷售額＋稅額） | 與既有 47 張自動補建一致 |
| `erp_invoices.tax_amount` | 發票稅額；`amount − tax_amount` ＝ 銷售額 | 三聯式 5%，二聯式可為 0 |
| `contract_projects.contract_amount` | 合約額，**含稅**（同步自 PM `contract_amount`） | 三表同步白名單 |
| `pm_cases.contract_amount` | 同上 | |
| 桃園 `taoyuan_contract_payments.current_amount` | 本期付款；`cumulative_amount` 是全案累計、每張派工單各帶一份，**不可 sum** | 09-02 |

## 年份

| 欄位 | 語意 |
|---|---|
| 所有 `year` 欄（pm_cases／contract_projects／erp_quotations） | **西元** |
| API 查詢參數 `year` | 西元；後端收到 `< 1911` 轉換並 `logger.warning`，不靜默 |
| 顯示層 | 民國或西元皆可 |
| 外部資料（財政部、發票 QR、匯入 xls） | 民國，解析後立即轉西元 |

## 狀態

| 表 | 值域 | 語意 |
|---|---|---|
| `pm_cases.status` | `planning`／`bidding`／`contracted`／`closed` | 邀標階段語意；`contracted`＝已承攬（執行由承攬案承接） |
| `contract_projects.status` | `執行中`／`已結案`（中文） | 執行階段語意；主檔；結案時映射 PM → `closed`（sync_from_contract） |
| `erp_quotations.status` | `draft`／`confirmed`／`revised`／`closed` | `confirmed`＝成立；成案與否看 `project_code` 不看 status |
| `erp_quotations.quote_kind` | `tender`／`contract`／`finance_anchor`／NULL | 表裝三種東西的標籤；總表只對 `contract` |
| `erp_billings.payment_status` | `pending`／`partial`／`paid` | 夜間吹哨者只催 pending/partial |
| `erp_billings.billing_period` | `第一期`…`第五期`／`尾款`／`一次請領` | Literal；別名表在 `schemas/erp/billing.py` |

## 案號

| 欄位 | 格式 | 語意 |
|---|---|---|
| `case_code` | `CK{年}_{PM\|GN}_{01\|02}_{序}` | 建案案號＝跨模組唯一鍵；PM＝從建案來、GN＝直接建承攬案；01 委辦招標、02 承攬報價 |
| `project_code` | 新制＝case_code 去 `_PM_`（PM 成案）或＝case_code（GN） | 成案編號；**舊制 `CK{年}_{類}_{性}_{序}` 78 筆存量不轉** |
| `quotation_no` | `QT{年}_{序}` | 線上報價單編號；對外引用的號 |
| `legacy_quotation_no` | `B115-C017b-0` | 個人管理時期編號；匯入比對鍵、回簽 PDF 檔名比對；**不在畫面呈現** |
| `billing_code` | `BL_{年}_{序}`；總表匯入的為 `XLS-{legacy}` | |
| `invoice_number` | `[A-Z]{2}\d{8}`；佔位 `XLS-{legacy}` | 佔位不是真號碼，對帳頁要分開列 |

## 來源

| 欄位 | 值域 |
|---|---|
| `erp_invoices.source` | `manual`／`xls_import`／`auto_from_billing`（20260903a001） |
| `erp_billings.notes` 前綴 `系統自動建立：` | 成案即應收自動第一期（weekly 103 認這個前綴） |
