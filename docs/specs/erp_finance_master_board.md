# 📊 ERP 財務中樞全期總表 (Master Board)

> **建立時間**: 2026-03-23  
> **文件目的**: 將歷次迭代之架構決策 (Architecture Decisions)、議題覆盤 (Issue Log) 與任務進度 (Task Tracker) 整合為單一總表 (Single Source of Truth)，以利全局追蹤。

---

## 🏛️ 壹、全期架構決策與議題日誌 (Decision & Issue Log)

此區塊紀錄我們在開發過程中遇見的關鍵議題，以及最終落定的架構防禦決策。

| 決策編號 | 遭遇議題 / 領域 | 最終架構決策與實作方案 (已落地) | 影響範圍 |
| :--- | :--- | :--- | :--- |
| **ADR-01** | **Repository 越權** | 實施 `BaseRepository` 徹底將資料庫操作與 `Service` 邏輯隔離。 | CRUD 基礎 |
| **ADR-02** | **多幣別本位幣污染** | 於 Pydantic Schema 使用 `@model_validator` 強制非 TWD 貨幣須帶匯率，入帳時一律轉為 TWD 本位幣 (`amount`)。 | 跨國結算 |
| **ADR-03** | **審核退件死結** | 建立 `APPROVAL_TRANSITIONS` 狀態定義陣列，嚴格限制所有流轉；超過 30K TWD 強制掛載財務簽核關卡。 | 簽核流 |
| **ADR-04** | **跨模組髒寫風險** | 拔除 Repository 的提早 `commit()`，統一改為 `flush()`，將 ACID 交易原子性控制權交回 Service，確立 Unit of Work 模式。 | 雙系統寫入 |
| **ADR-05** | **專案超支防呆** | 實作 `_check_budget()` 預算大壩：於 `approval()` 時動態撈取報價單上限，**過 80% 警告，過 100% 拋出 `ValueError` 強制阻斷**。 | 專案預算 |
| **ADR-06** | **N+1 儀表板風暴** | 針對大量專案彙整 (`get_batch_project_summaries`)，捨棄迴圈查詢，改用 3 次 `IN(...)` SQL 配合 Python Dictionary 本地映射。 | BI 效能 |
| **ADR-07** | **幽靈專案發票** | 建立 `_validate_case_code`：申請時透過跨模組 `exists` 探測 `ContractProject` → `PMCase` → `ERPQuotation`，徹底阻絕手抖按錯。 | 全域防呆 |
| **ADR-08** | **供應商自動對帳** | 新增 `vendor_id` 外鍵，透過發票之 `seller_ban` 於建檔時自動 `_resolve_vendor_by_ban`，打通廠商對帳單分析。 | 外包結算 |

---

## 🚀 貳、全棧任務進度總表 (Unified Task Tracker)

> **狀態燈號**：🟢 已完成 | 🟡 進行中/待串接 | ⚪ 尚未開始

### 🟢 Phase 1: 核心資料層與架構防線 (100%)
- [x] ORM Models 架構確立：`ExpenseInvoice`, `FinanceLedger` (關聯 `user_id`, `vendor_id`)
- [x] Schemas 防線建置：導入 20+ Pydantic Schemas，包含正則與 `@model_validator` 本位幣清洗
- [x] Repository 單元隔離：`BaseRepository` CRUD，支援異步 `AsyncSession`
- [x] 交易邊界鞏固：拔除底層 `commit`，嚴格落實 **ACID Unit of Work** 交易模式

### 🟢 Phase 2: 商業邏輯與金流中樞 (100%)
- [x] **AP (應付) 拋轉接口**：實作 `record_from_vendor_payable` 吸納採購付款
- [x] **AR (應收) 拋轉接口**：實作 `record_from_billing` 吸納請款收款
- [x] **超級預算聯防大壩**：`_check_budget` (80% 屬性標記預警、100%強塞 `ValueError`)
- [x] **多層狀態機引擎**：依照 30K 閥值自動分發一級 / 二級主管簽核與駁回流轉
- [x] **全線三重防呆鎖**：`_validate_case_code` 攔截無效案號；`seller_ban` 自動黏合對應之廠商

### 🟢 Phase 3: 商業分析與 BI 儀表板基建 (100%)
- [x] **N+1 效能終結版**：實作 `get_batch_project_summaries` 陣列查詢
- [x] **無縫月均線演算法**：`get_monthly_trend` (包含 SQL YYYY-MM 群組化與空月墊片演算法)
- [x] **危險專案熱圖排行**：`get_budget_ranking` (sa_case 組合式收支統計與 None 陣列後置)
- [x] **資料庫效能優化**：新增 `idx_ledger_case_date` 以提升大數據聚合速度

---

### 🟡 Phase 4: 前台整合與 O2O 智能落地 (Upcoming)
為完成最後一哩路，下方程式碼層皆已準備就緒，僅待前台掛接與伺服器組態：

- [ ] **React Dashboard 匯流**
  - 對接 `get_monthly_trend` 繪製「雙色堆疊長條圖 (Income vs Expense)」
  - 對接 `get_budget_ranking` 渲染「Top N 專案預算燃燒熱力圖 (100% 亮紅燈)」
- [ ] **前端防禦 UX 對接 (Error Handling)**
  - 捕捉 API 拋出的案號錯誤與預算 100% 超載的 HTTP 400 `ValueError`，實作全站統一的 `AlertDialog` 彈窗示警。
- [ ] **LINE Bot 行動端兵站 (O2O Capture)**
  - 建立 `/webhook` 接收行動裝置發票照片 (啟動 `source="line_upload"`)，解放員工出差卡單流程。
- [ ] **Agent 吹哨者排程 (AI Automation)**
  - 擴充 `NemoClaw` 發布夜間 `cronjob`，調用熱圖 API 掃描 80%~99% 水位專案，推送 Slack/LINE 警報給所屬專案經理。
- [ ] **供應商對帳中心 (Vendor Statement)**
  - 利用 Phase 2 完成的 `vendor_id`，開放一鍵產出「特定廠商年度發票/付款 Excel」(`pandas` 引擎)。
