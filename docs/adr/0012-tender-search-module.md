# ADR-0012: 標案檢索模組架構設計

> **狀態**: accepted
> **日期**: 2026-04-01
> **決策者**: CK Development Team
> **關聯**: CHANGELOG v5.4.0, docs/specifications/TENDER_SEARCH.md

## 背景

企業需要整合政府電子採購網標案資料，以便主動追蹤潛在案件機會、分析競爭對手得標歷史、並與現有 PM/ERP 模組串接。目前團隊依賴人工瀏覽政府電子採購網（pcc.gov.tw），效率低且容易遺漏符合資格的標案。需要建立搜尋、詳情、訂閱、圖譜、Agent 等功能，實現標案資訊的自動化監控與智慧推薦。

## 決策

採用以下架構方案：

### 資料來源

使用 `pcc-api.openfun.app` 開放資料 API 作為標案資料來源，不直接爬取政府電子採購網，避免法律風險與反爬蟲機制。

### 後端架構

- **Service**: `tender_search_service.py` — 封裝 PCC API 呼叫、Redis 快取（TTL 30min）、結果正規化
- **Scheduler**: `tender_subscription_scheduler.py` — 每日 3 次（08:00/12:00/18:00）執行訂閱比對，透過 LINE/Discord 推送新標案通知
- **DB Tables**: 2 張表
  - `tender_bookmarks` — 使用者收藏的標案
  - `tender_subscriptions` — 關鍵字/機關/金額訂閱條件
- **Scheduler Jobs**: 3 個排程
  - 訂閱比對推送（每日 3 次）
  - 標案狀態更新（每日 1 次）
  - 過期標案清理（每週 1 次）

### API 端點

17 個端點，分為 5 組：
- **搜尋** (3): search, advanced-search, suggest
- **詳情** (3): detail, timeline, awards
- **圖譜** (3): agency-graph, company-graph, tender-relations
- **訂閱** (4): subscriptions CRUD + trigger
- **收藏** (4): bookmarks CRUD + batch

### 前端頁面

4 個頁面：
- `TenderSearchPage.tsx` — 標案搜尋 3-Tab（搜尋/收藏/訂閱）
- `TenderDetailPage.tsx` — 標案詳情 4-Tab（總覽/生命週期/得標/同機關）
- `TenderCompanyPage.tsx` — 廠商投標歷史（統計+圓餅圖）
- `TenderGraphPage.tsx` — 標案知識圖譜（力導引視覺化）

### Agent 整合

30 個 Agent 工具，涵蓋：
- 標案搜尋與篩選
- 標案詳情查詢
- 訂閱管理
- 競爭分析
- `auto_tender_to_case` — Multi-Agent 自動將符合條件的標案轉為 PM Case 建案

## 後果

### 正面

- 自動化標案監控，大幅減少人工瀏覽時間
- 訂閱推送確保不遺漏重要標案
- 圖譜分析可視化機關/廠商關係網絡，輔助投標決策
- `auto_tender_to_case` 實現標案到案件的無縫銜接
- Redis 快取降低 API 呼叫頻率，避免觸發限流

### 負面

- 依賴第三方 API（pcc-api.openfun.app），需處理 API 不可用的回退方案
- 新增 2 張 DB 表與 3 個排程任務，增加系統維運複雜度
- 30 個 Agent 工具擴充需同步更新 tool_registry 與測試覆蓋
- 標案資料量大（每日數百筆新標案），需注意 Redis 記憶體用量

## 替代方案

1. **直接爬取 pcc.gov.tw** — 排除原因：法律風險、反爬蟲機制、維護成本高
2. **購買商業標案資料庫** — 排除原因：預算限制、API 整合彈性不足
3. **僅做前端嵌入 iframe** — 排除原因：無法整合 Agent、無法建立圖譜、無法訂閱推送
