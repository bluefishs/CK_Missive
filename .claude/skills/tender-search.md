---
name: tender-search
description: 標案檢索模組開發規範 — PCC API/訂閱排程/標案分析/戰情室
version: 1.0.0
category: domain
triggers:
  - 標案
  - tender
  - PCC
  - 訂閱
  - 招標
  - 決標
  - 採購
  - 戰情室
  - battle-room
updated: '2026-04-09'
---

# 標案檢索模組開發規範


## 架構概覽

```
PCC 公共工程委員會 API
        ↓
tender_search_service (搜尋+快取)
        ↓
  ┌─────┴─────┐
  Redis 快取   DB 持久化
  (短期)      (tender_cache_service)
        ↓
  前端展示 (5+ 頁面)
        ↓
  ezbid_scraper (當日補充)
```

---

## 服務層

| 服務 | 說明 |
|------|------|
| `tender_search_service.py` | PCC API 封裝 + Redis 快取 (302L) |
| `tender_data_transformer.py` | 資料轉換 (263L, 拆分自 search) |
| `tender_cache_service.py` | DB 持久化 (save/search/refresh/stats) |
| `tender_analytics_service.py` | 分析 Facade (283L, 委派子模組) |
| `tender_analytics_battle.py` | 投標戰情室 + 機關生態 (108L) |
| `tender_analytics_price.py` | 底價分析 + 廠商分析 (184L) |
| `tender_subscription_scheduler.py` | 訂閱排程 (每日 3 次 + 多通道推送) |
| `ezbid_scraper.py` | ezbid.tw 即時爬蟲 (當日資料補充) |

---

## API 層 (`backend/app/api/endpoints/tender_module/`)

`tender.py` 為入口 (12L wrapper)，委派 4 個子模組：

| 子模組 | 端點 | 說明 |
|--------|------|------|
| `search.py` | search/detail/detail-full/recommend/realtime | 搜尋與詳情 (324L) |
| `graph_case.py` | graph/create-case | 圖譜+建案 (152L) |
| `subscriptions.py` | subscriptions/bookmarks/companies CRUD | 訂閱管理 (318L) |
| `analytics.py` | dashboard/battle-room/org/company/price + cache-stats | 分析端點 (130L) |

---

## 前端頁面

| 頁面 | 說明 |
|------|------|
| `TenderSearchPage.tsx` | 3-Tab: 搜尋/收藏/訂閱 (子元件在 tenderSearch/) |
| `TenderDetailPage.tsx` | 4-Tab: 總覽/生命週期/得標/同機關 (子元件在 tenderDetail/) |
| `TenderDashboardPage.tsx` | 採購儀表板 |
| `TenderBattleRoomPage.tsx` | 戰情室 (雷達圖+對手排行) |
| `TenderPriceAnalysisPage.tsx` | 底價分析 |
| `TenderOrgEcosystemPage.tsx` | 機關生態圈分析 |
| `TenderCompanyPage.tsx` | 廠商投標歷史 (統計+圓餅圖) |
| `TenderCompanyProfilePage.tsx` | 廠商分析整合頁 |
| `TenderGraphPage.tsx` | 標案知識圖譜 (力導引) |

---

## 訂閱排程

`tender_subscription_scheduler` 每日 08:00 / 12:00 / 18:00 自動掃描：

1. 讀取所有啟用的 `TenderSubscription`
2. 調用 PCC API 搜尋匹配標案
3. 與上次推送結果比對，過濾新增項目
4. 透過 LINE / Telegram / Discord 推送通知
5. 更新 `last_pushed_at` 時間戳

---

## ezbid 爬蟲防禦

`ezbid_scraper.py` 內建多層防禦機制：

| 機制 | 說明 |
|------|------|
| Retry + Backoff | 指數退避重試 (3 次) |
| 封鎖偵測 | 檢測 403/429 回應，自動暫停 |
| 連續失敗熔斷 | 連續 N 次失敗後停止爬取，等待冷卻 |
| User-Agent 輪換 | 模擬瀏覽器請求 |

---

## Agent 工具整合

| 工具 | 說明 |
|------|------|
| `#29 search_tender` | Agent 可直接搜尋標案，回傳摘要 |
| `#30 auto_tender_to_case` | Multi-Agent 自動建案：標案 → PM Case (僅建 PM，不建 ERP) |

建案規則：
- 僅建 PM Case，不自動建 ERP Quotation
- 重複防護：檢查 `tender_id` 是否已建案
- 年度篩選使用 `date.today().year`（禁止硬編碼年份）

---

## 標案入圖 (KG-5)

`TenderRecord` 透過圖譜入庫管線轉為 canonical_entities：

- 標案名稱 → entity (type: tender)
- 機關名稱 → entity (type: organization)
- 得標廠商 → entity (type: company)
- 關係: tender → awarded_to → company, tender → procured_by → organization

---

## 資料模型

| 模型 | 說明 |
|------|------|
| `TenderSubscription` | 訂閱條件 (關鍵字/金額/機關篩選) |
| `TenderBookmark` | 收藏標案 (user_id + tender_id) |
| `TenderRecord` | DB 持久化快取 (tender_cache_service 管理) |

---

## 常見陷阱

1. **PCC API 限流**: 加 Redis 快取避免重複請求，TTL 依端點調整
2. **圓餅圖年度**: 統一使用動態年度，禁止硬編碼 2025/2026
3. **create-case 欄位映射**: PCC 欄位名與 PM Case 欄位不同，需透過 transformer 轉換
4. **DB 持久化 vs Redis 快取**: 搜尋結果短期用 Redis，長期統計用 DB tender_cache
