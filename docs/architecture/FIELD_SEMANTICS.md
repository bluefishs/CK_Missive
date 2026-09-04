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
| `contract_projects.contract_amount` | **契約金額**，含稅：成案時的報價（投標）金額（同步自 PM `contract_amount`） | 三表同步白名單 |
| `contract_projects.winning_amount` | **議價金額**，含稅：決標／議價後的實際承攬金額；0／NULL＝無議價。**承攬金額＝COALESCE(NULLIF(winning,0), contract)**，應收面（第一期請款、應收總額、承攬案合計、weekly 104 ①）一律用它（09-04 晚 owner：194 實際費用是議價 596,000 不是契約 625,000） | 12/285 有值、3 筆與契約不同 |
| `pm_cases.contract_amount` | 同上 | |
| 桃園 `taoyuan_contract_payments.current_amount` | 本期付款；`cumulative_amount` 是全案累計、每張派工單各帶一份，**不可 sum** | 09-02 |

### `total_price` 的歷史錯法簽名（09-04 金流複查）

| 批次 | 存進去的是 | 認法 | 張數 |
|---|---|---|---|
| 03-17 匯入 | `含稅 − 2×稅`（稅被扣了兩次） | `total_price + 2×tax_amount = pm.contract_amount` | 124 |
| 08-20／09-02 匯入 | `未稅 × 0.85`（＝稅×17） | `tax_amount × 21 = pm.contract_amount` | 91 |

weekly 104 ⑨ 用這兩個簽名判 RED；⑩ 其他不等只 YELLOW（可能是議價）。更正＝A92（待 owner 授權）。
**跨表金額先看比值分布**：`pm.contract_amount / q.total_price` 集中在一個比值就是系統性偏差，門檻式判準（weekly 100 的 >50%）看不見它。

### 契約金額合計 vs 應收總額（2026-09-04 晚 owner 問「為何不一致」）

| 頁 | 卡片 | 算法 | 稅 |
|---|---|---|---|
| `/contract-cases` | **契約金額合計（含稅）**（原標「合約總額」） | Σ `contract_projects.contract_amount`，年度＝`contract_projects.year` | 含稅 |
| `/erp/quotations` | **應收總額（未稅）** | Σ 成案報價單 `total_price − tax_amount`，年度＝案號 `CK{年}` | 未稅 |
| `/erp/quotations` 欄位 | **契約金額**（原標「議價金額」） | 承攬案 `contract_amount`；未成案顯示報價總價 | 含稅 |

2026 實測：契約金額合計 81,710,000（116 案）vs 應收總額 63,785,409（115 案）。差＝①稅 989,591（115 案報價總價 64,775,000 − 未稅）
②**1 案 `year` 欄與案號年不同**：#21 `CK2025_01_03_001`「115年度桃園…開口契約」16,935,000，`year=2026` 而案號是 2025 ⇒ 承攬案頁算進 2026、
報價單頁算進 2025（A100，要 owner 定「年度＝契約年度還是建案年度」）。其餘 113 案契約金額＝報價總價（含稅）一分不差。

**結論**：「合約總額」＝「議價金額」＝**契約金額（含稅）**，三個名字一個數；文字統一為「契約金額」。**不改名為「應收總額」**——
應收總額是未稅口徑，兩張卡若同名而差 5% 稅，比現在更難對。

### 委託單位帳款 vs 損益摘要的口徑差

委託單位帳款＝**所有**（未刪）報價單的請款，含未成案；損益摘要＝**成案**口徑。兩者差＝未成案報價單掛著的請款（09-04：150,024，5 張，屬 A90 那批）。

### 跨表對帳的鍵（09-04 同族第十二處後明寫）

**`case_code` 是唯一的跨模組橋樑**（pm_cases／erp_quotations／contract_projects／finance_ledgers／expense_invoices／project_user_assignments 都有它）。
`project_code` 只是成案編號：PM 制＝case_code 去 `_PM_`，**拿它去對別表的 case_code 永遠只對得到舊制那 34 筆**。
09-04 前財務摘要三處這樣寫，專案一覽因此只剩 17 列。

## 年份

| 欄位 | 語意 |
|---|---|
| 所有 `year` 欄（pm_cases／contract_projects／erp_quotations） | **西元** |
| API 查詢參數 `year` | 西元；後端收到 `< 1911` 轉換並 `logger.warning`，不靜默 |
| 顯示層 | 民國或西元皆可 |
| 外部資料（財政部、發票 QR、匯入 xls） | 民國，解析後立即轉西元 |

### 年度篩選的口徑（09-04 金流複查補）

| 頁面／端點 | 年度＝ | 理由 |
|---|---|---|
| **報價單列表（專案帳款頁）** | **案件年度**（建案案號 `CK{年}_`）——09-04 owner：舊案在 2026 補建的錨點報價單 year=2026，用報價單年會把 114 年案列進 2026 |
| 損益摘要、委託單位帳款、廠商帳款、應收應付 | **報價單年 `erp_quotations.year`** | 財務以報價單為錨點；此前委託單位頁用案件年，同一個 2026 少 563 萬 |
| 發票彙總 | **發票日年 `erp_invoices.invoice_date`** | 稅務用途：2026 年開的發票；此前用報價單年只算到 54 張（實際 118 張） |
| 統一帳本 | **交易日 `finance_ledgers.transaction_date`**（前端轉 date_from／date_to） | 會計期間 |
| 承攬案列表、PM 案列表 | 案件年 `year` | 案件管理視角 |
| ERP Hub 總覽 | 不分年（全量），**排除 soft-delete** | 此前含 64 張已刪報價單 |

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
| `erp_vendor_payables.notes` 前綴 `[auto:vendor_association]` | 承攬案「協力廠商」指派自動建的應付（**指派即應付**，2026-09-04；weekly 106 認這個前綴）。人工建的應付不帶前綴、指派金額改動不覆蓋它 |

## 識別碼（2026-09-04 owner「代碼 vs 統一編號」）

| 欄位 | 語意 |
|---|---|
| `partner_vendors.tax_id` | **統一編號**（8 碼）。畫面一律標「統一編號」、讀這欄 |
| `partner_vendors.vendor_code` | **內部代碼**（選填）。此前協力廠商 15 家把統編填在這裡（已搬到 `tax_id`），委託單位卻填 `tax_id`——同一件事兩個欄位。查廠商 `get_id_by_vendor_code` 兩欄都認、`tax_id` 優先 |
| `erp_vendor_payables.vendor_code` | 建立時抄廠商的 `tax_id`（無則 `vendor_code`）；唯讀快照，不是鍵 |

## 主檔鍵與名稱快照（2026-09-04 /loop「名稱標準化與語意定義」）

**規則：`*_id` 是鍵，`*_name`／`client_agency` 是顯示快照。關聯、篩選、對帳一律走鍵；名稱只在鍵為空時當後備。**

| 實體 | 鍵（唯一） | 快照欄（不作關聯） | 備註 |
|---|---|---|---|
| 委託單位 | `partner_vendors.id`：`pm_cases.client_vendor_id`、**`contract_projects.client_vendor_id`（20260904a003 新增，回填 271/285）** | `pm_cases.client_name`、`contract_projects.client_agency` | 此前承攬案沒有這把鍵，帳款／篩選／主檔全靠字串對，一天出三次事（竹崎地政無法點、張啟良三筆主檔、大有國際在主檔是 subcontractor） |
| 委託機關（公部門） | `contract_projects.client_agency_id` → `government_agencies` | — | 34/285 有值，只有 01 公部門案用；**不是委託單位的鍵** |
| 協力廠商 | `partner_vendors.id`：`erp_vendor_payables.vendor_id`、`project_vendor_association.vendor_id` | `erp_vendor_payables.vendor_name`、`vendor_code`（統編快照） | 應付建立時 `_resolve_vendor_id` 自動配；配不到＝主檔缺（勤典工程行 09-04 補建） |
| 廠商身分 | `partner_vendors.vendor_type`（client／subcontractor）**單值** | — | 同一家可能兩種身分（大有國際／秋森萬既是協力也是委託單位）⇒ 選項清單不得只看 type，要看它在案件裡實際扮演的角色（`client-options` 端點） |
| 案件 | `case_code`（三表共有） | `case_name`／`project_name` | 見「案號」節；`project_code` 只在成案後有 |

**守門**：weekly 107 `name_id_pair_consistency_audit`——名稱精確對得到主檔卻沒填鍵 ⇒ RED；快照漂移／主檔缺 ⇒ YELLOW。
**同步**：PM 改委託單位 ⇒ `CaseFieldSyncService` 同步 `client_vendor_id` 與 `client_agency`（`CONTRACT_SYNC_FIELDS`）；成案 `promote_to_project` 帶鍵。

## 經費名詞字典（2026-09-04 晚；UI 端 SSOT＝`frontend/src/constants/financeTerms.tsx`，本表由它產生）

owner：「各類經費名詞或定義請增列註記補充，以利釐清對應與語意」。統計卡與欄位標題一律 `termTitle(key)`＝文字＋ⓘ 定義；同一個數只准一個名字。

| key | 顯示文字 | 定義 |
|---|---|---|
| `contract_amount` | 契約金額 | 承攬案 contract_projects.contract_amount，含稅：成案時的報價（投標）金額。決標後若有議價，實際承攬金額是「議價金額」。舊稱「合約總額」。 |
| `winning_amount` | 議價金額 | 承攬案 winning_amount，含稅：決標／議價後的實際承攬金額。有值時應收（第一期請款、應收總額、合計）以它為準；空＝無議價，等於契約金額。 |
| `awarded_amount` | 承攬金額 | ＝議價金額，沒有議價則＝契約金額（含稅）。所有應收面的數字都用這個。 |
| `contract_amount_sum` | 承攬金額合計（含稅） | 目前篩選範圍內所有承攬案的承攬金額（議價金額，無則契約金額）加總，含稅。與報價單頁「應收總額（未稅）」差 5% 稅。 |
| `quotation_total` | 報價總價（含稅） | erp_quotations.total_price，含稅；請款、發票都以它為上限。未稅＝總價 − 稅額。 |
| `receivable_total_untaxed` | 應收總額（未稅） | 篩選範圍內成案報價單的（總價 − 稅額）加總，未稅。承攬案頁的「契約金額合計」是同一批案的含稅數。 |
| `billed` | 已請款 | 各期請款金額（erp_billings.billing_amount）加總，含稅；成案時自動建第一期＝承攬金額（議價金額，無則報價總價）。 |
| `unbilled` | 未請款 | 報價總價 − 已請款，含稅。 |
| `received` | 已收款 | 已收款的請款實收金額（erp_billings.payment_amount）加總，含稅。 |
| `outstanding` | 應收未收 | 已請款 − 已收款，含稅。列表頁點此卡只列有未收餘額的案。 |
| `receivable_column` | 應收帳款 | 該案已請款合計（含稅）＋已收比例；「未開請款」＝一筆請款都沒有。 |
| `receipt_rate` | 收款率 | 已收款 ÷ 已請款。 |
| `payable_total` | 應付款項 | 協力廠商應付（erp_vendor_payables.payable_amount）加總，含稅；承攬案協力廠商分頁的指派金額會自動建一筆（指派即應付）。 |
| `payable_column` | 應付帳款 | 該案應付合計（含稅）＋已付比例；「—」＝沒有協力廠商應付。 |
| `paid_total` | 已付 | 應付中已付款的金額（paid_amount）加總，含稅。 |
| `payable_outstanding` | 未付餘額 | 應付 − 已付，含稅。 |
| `payment_rate` | 付款率 | 已付 ÷ 應付。 |
| `cost_total` | 成本總額 | 報價單估列成本：外包費＋人事費＋管銷費＋其他成本（erp_quotations 四欄），未稅。不是實際支出。 |
| `cost_estimated` | 估列成本（報價單） | 同「成本總額」：報價時估的四項成本，未稅。 |
| `cost_actual` | 實際成本（已入帳） | 帳本支出：協力廠商應付已付款＋費用核銷入帳的合計。應付與核銷是帳本的鏡像，三者相加會重複計算。 |
| `gross_profit` | 預估毛利 | （報價總價 − 稅額）− 估列成本。各頁口徑尚未統一，列表頁的毛利卡先隱藏。 |
| `gross_margin` | 預估毛利率 | 預估毛利 ÷ 未稅營收。 |
| `invoice_amount` | 發票金額 | erp_invoices.amount，含稅（銷售額＋稅額）；一筆請款一張票，發票額不得超過該期請款。 |

**改名紀錄**：合約總額 → **契約金額**（原報價）；**議價金額**＝決標後實際金額；**承攬金額**＝議價金額，無則契約金額——應收面用它。報價單詳情頁「應收總額」（含稅總價）→ **報價總價（含稅）**。
