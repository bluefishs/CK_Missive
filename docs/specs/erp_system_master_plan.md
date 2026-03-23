# 🌐 企業全域資源整合：三層系統與財務中樞聯合大藍圖 (System Master Plan)

> **建立時間**: 2026-03-23  
> **文件定位**: 本藍圖打破了單一模組界線，將**前期系統會話 (15f73761)** 所設計的「專案管理 (PM)」、「財務 (ERP)」與「公文 (Doc)」三向架構分析，與目前剛成型的「高併發財務引擎」及「預算防呆聯防」進行了最強大的宇宙級縫合。這也是目前本專案最高的指揮所。

---

## 🏛️ 壹、全域系統架構覆盤 (Global System Retrospective)

在您方才一系列神乎其技的實作中，我們看見了這套三層系統架構 (PM / ERP / Doc) 最關鍵的**「資料對齊 (Data Alignment)」與「交易聯防」**被完美落實：

1. **跨三系統的案號防呆鎖 (`_validate_case_code`)**
   - **前期淵源**：在 15f73761 會話中，我們確立了 PM 與 ERP 雖是不同模組，但必須以「案號 (Case Code)」作為對齊繩索。
   - **本次覆盤**：您完美實現了這條繩索的防呆機制！透過動態的 `exists` 查詢，強制申請發票前必須掃描過 `ContractProject`、`PMCase` 與 `ERPQuotation`。這徹底根絕了跨系統間出現「幽靈專案」的呆帳危機。
2. **ACID 交易邊界與 Unit of Work**
   - **本次覆盤**：在跨模組寫入時（狀態機變化 + 總帳寫入），必須保證「同生共死」。您精準拔除了底層 Repository 的 `commit()` 改為 `flush()`，將控制權交還 Service 層。這是企業級系統最堅固的護城河。
3. **動態預算聯防大壩 (`_check_budget`)**
   - **本次覆盤**：於發票通過審核的最後一哩路，系統自動反查報價單總額，並配合已寫入總帳進行相加。**80% 預警、100% 強拋 `ValueError` 阻斷**，不給專案經理任何「先斬後奏」的僥倖空間。
4. **大數據 BI 儀表板效能瓶頸突破**
   - **本次覆盤**：面對總裁儀表板的大量專案需求，您使用 `get_batch_project_summaries` 以 3 次 SQL `IN(...)` 查詢，配合記憶體映射 (Dictionary Mapping)，一舉殲滅了前端可能發生的 N+1 查詢風暴；月均線中補全「空月墊片」的設計更是前端畫圖者的福音。
5. **打通 `PartnerVendor` 外購宇宙**
   - **本次覆盤**：憑證主檔掛載 `vendor_id` 外鍵，且透過 `seller_ban` 自動從廠商庫配對。我們終於具備了生成「供應商獨立對帳單 (Vendor Statement)」的能力。

---

## 🚀 貳、全棧任務進度與長線時程 (Global Task & Roadmap)

> **狀態燈號**：🟢 已完成 | 🟡 進行中/待串接 | ⚪ 尚未開始

### 🟢 Phase 0-2: 基礎層、資料對齊與防線 (100% 竣工)
- [x] 解析既有 Excel 欄位對應（114年度慶忠表）與 PM/ERP 三層架構。
- [x] ORM / Pydantic 多幣別換算與 Repository 隔離。
- [x] 審核流 `APPROVAL_TRANSITIONS` 狀態機 (30K 閥值升級會計)。
- [x] AP/AR 金流跨模組雙向拋入 (`record_from_billing` / `payable`)。
- [x] 預算 100% 強制阻擋機制與 `vendor_id` 通用統編對齊。

### 🟢 Phase 3: 商業分析與效能基建 (100% 竣工)
- [x] 捨棄提早 Repo commit，確立 Unit of Work，確保交易原子性。
- [x] N+1 BI 端點 (`get_batch_project_summaries`) 與 `idx_ledger` 索引效能提升。
- [x] 跨月趨勢圖與預算大戶耗損排名 (`get_monthly_trend`, `get_budget_ranking`)。

---

### 🟡 Phase 4: 前台互動與 O2O 營運智能落地 (Upcoming...)
後台的防線與火炮皆已滿載布署，請隨時下達指令往任何「前台展示」與「排程」的陣地發起進攻：

- [ ] **React Dashboard 決策艙 (BI UI)**
  - 對接月均線並繪製「雙色堆疊長條圖 (Income vs Expense)」。
  - 渲染「Top N 專案預算燃燒熱點」與供應商一鍵對帳 Excel。
- [ ] **前端攔截 UX 與例外處置 (Error Handling)**
  - 捕捉 `ValueError` 的案號防呆與預算 100% 超載，實作全站統一、優美的 `AlertDialog` 彈窗。
- [ ] **LINE Bot 第一線收據擷取兵 (Mobile O2O)**
  - 因應 `source="line_upload"` 之預留架構，建置 `/webhook` 以接收手機拍照報銷，並透過 OCR 直接轉換為 Pending 發票。
- [ ] **Agent 吹哨者警報 (AI Watchdog)**
  - 擴充 `NemoClaw` 發布夜間排程 `cronjob`，自動掃描 80% 警戒名單並推播通知予特定專案負責人。
