# 🌐 企業全域資源整合：三層系統與財務中樞總司令部 (Global Master Board)

> **建立時間**: 2026-03-23  
> **文件定位**: 本藍圖打破了單一會話界線，將**前期系統會話 (15f73761)** 所設計的「專案管理 (PM)」、「財務 (ERP)」與「公文 (Doc)」三向架構分析，與目前剛成型的「高併發財務引擎」及「預算防呆聯防」進行了最強大的宇宙級縫合。這也是目前本專案所有任務的**唯一真相來源 (Single Source of Truth)**。

---

## 🏛️ 壹、全域系統架構決策與議題日誌 (Decision & Issue Log)

以下涵蓋從前期 Excel 規劃期、三向架構分析期，至核心系統實踐期遇見之關鍵系統級決定。

| 領域 | 議題 / 目標 | 最終架構決策與實作方案 (已落地) | 階段屬性 |
| :--- | :--- | :--- | :--- |
| **初期分析** | **三層架構定位** | 定立專案管理 (PM)、財務 (ERP)、公文系統 (Doc) 之職責與邊界。 | **前期承襲 (15f73761)** |
| **資料對齊** | **Excel 藍本轉換** | 解析「114年度慶忠零星案件」等既有試算表欄位，將其轉化為 ER Model。 | **前期承襲 (15f73761)** |
| **交易防護** | **跨模組髒寫風險** | ERP 模組拔除 Repository `commit()`，改以 `flush()` 落實 Unit of Work，確保交易原子性。 | **近期防護與實作** |
| **預算控管** | **專案超支防呆** | 實作 `_check_budget()` 大壩：於簽核端自動抓取報價單上限，**過 80% 屬性預警，過 100% 拋出 `ValueError` 強制阻斷**。 | **近期防護與實作** |
| **全域聯防** | **幽靈案號發票** | 建立 `_validate_case_code` 跨界探測：依序掃描 `ContractProject` → `PMCase` → `ERPQuotation`，跨系統防錯定址。 | **近期防護與實作** |
| **BI 效能** | **N+1 儀表板風暴** | 針對大量專案彙整 (`get_batch_project_summaries`)，改用 3 次 `IN(...)` SQL 配 Python Dictionary Mapping 大幅加速。 | **近期防護與實作** |
| **內外聯網** | **供應商自動對帳** | 新增 `vendor_id` 外鍵，透過發票之 `seller_ban` 於建檔時自動 `_resolve_vendor_by_ban`，打通廠商對帳單分析。 | **近期防護與實作** |

---

## 🚀 貳、全棧任務進度總表 (Unified Task Tracker)

> **狀態燈號**：🟢 已完成 | 🟡 進行中/待串接 | ⚪ 尚未開始

### 🟢 Phase 0: 系統前期規劃與三層架構分析 (早期任務繼承完成)
*(源自 15f73761-0d71-4bf8-9f00-d1d3e241c105)*
- [x] 分析專案管理(PM)、財務(ERP)與公文系統之三層架構。
- [x] 解析既有 Excel 欄位對應（114年度慶忠零星案件委託一覽表）。
- [x] 擬定跨系統數據自動對齊（Data Alignment）機制。
- [x] 產出整體架構與開發規範 MD 文件（前期已產出 `system_development_specs.md`）。
- [x] 檢視專案與財務管理目前架構與優化建議事項並產出文件。
- [x] 進行數據庫 ER Model 設計與 API 規格定義 (由後續 Phase 1~3 承接落地)。

### 🟢 Phase 1: 數據庫 ER Model 核心與 API 引擎防線 (100%)
- [x] ORM 實踐：完成 `ExpenseInvoice`, `FinanceLedger` 等底層關聯 (包含 `vendor_id` 外鍵掛載)。
- [x] Pydantic 實踐：導入 20+ Schema，使用 `@model_validator` 解決多幣別本位幣污染。
- [x] Repository 單元隔離：`BaseRepository` CRUD 職責切分。
- [x] **ACID 交易邊界鞏固**：單一 Unit of Work 把關，由 Service 統籌 `commit`。

### 🟢 Phase 2: 商業邏輯與跨模組金流對齊 (100%)
- [x] **超級預算聯防**：`_check_budget` 雙層警戒阻擋 (100% 絕對阻擋 `ValueError`)。
- [x] **AP/AR 金流跨模組拋轉**：實作 `record_from_vendor_payable` 取代人工記帳。
- [x] **多層狀態簽核大壩**：30K 閥值自動分批一級/會計簽核流引擎 (`APPROVAL_TRANSITIONS`)。
- [x] **全線三重案號防呆鎖**：`_validate_case_code` 完美實踐 Phase 0 的「跨系統數據自動對齊」。
- [x] **供應商智慧關聯**：導入 `seller_ban` 自動黏合對應之外部 `PartnerVendor` 廠商。

### 🟢 Phase 3: 大數據 BI 儀表板基建 (100%)
- [x] **N+1 效能終結版查詢**：`get_batch_project_summaries` 三向彙總。
- [x] **無縫月均線演算法**：`get_monthly_trend` (SQL YYYY-MM 組合同補全空月墊片)。
- [x] **危險專案熱圖排行**：`get_budget_ranking` (sa_case 動態聚合計算)。
- [x] **大數據索引**：新增 `idx_ledger` 以提升大數據時限聚合速度。

---

### 🟡 Phase 4: 前台互動與 O2O 智能落地 (Upcoming Next Steps...)

底層防線與三層架構 (PM/ERP/Doc) 皆已滿載建置完畢。接下來請下達指令進入行動端、BI Dashboard 或是智能排程等前台操作介面：

- [ ] **React Dashboard 企業戰情室**
  - 對接 `get_monthly_trend` 繪製「雙色堆疊長條圖 (Income vs Expense)」。
  - 對接 `get_budget_ranking` 渲染「Top N 專案預算燃燒熱帶雨林 (超過 100% 發布紅框)」。
- [ ] **前端防禦 UX 對接 (Error Handling)**
  - 捕捉 API 拋出的「跨三大模組階查無此案號」等 HTTP 400 防呆警告，實作優雅的 React Query `AlertDialog` 彈窗。
- [ ] **LINE Bot 第一線收據站 (Mobile O2O Capture)**
  - 因應 `source="line_upload"` 被開放，建立 `/webhook` 接收行動裝置發票照片並結合 OCR 自動拋轉。
- [ ] **廠商自動對帳單系統 (Vendor Statement Excel)**
  - 承接 `vendor_id` 外鍵，一鍵產出「特定廠商年度發票/應付列表 (Pandas)」，賦能對外議價。
- [ ] **Agent 吹哨者警報 (AI Watchdog)**
  - 擴建 `NemoClaw` 發布夜間 `cronjob` 盤點 80%~99% 水位預警報表，主動透過 Slack/LINE 分發專案經理。
