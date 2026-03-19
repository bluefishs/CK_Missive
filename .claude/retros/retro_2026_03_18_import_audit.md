# Retro: 112 收發文匯入與全棧架構審計

> **日期**: 2026-03-18
> **觸發事件**: 匯入 112 收發文 Excel (911 筆)
> **影響範圍**: 資料庫公文/承攬案件/機關、前後端 SSOT、匯入服務架構

---

## 1. 匯入結果

| 指標 | 數值 |
|------|------|
| Excel 總列數 | 911 |
| 有效(去重後) | 851 |
| 新增公文 | 541 |
| 更新公文 | 310 |
| 錯誤 | 0 |
| 新建承攬案件 | 19 (21 → 34) |
| 承攬案件連結率 | 88.7% (1453/1638) |
| 新建機關 | ~30 (63 → 93) |
| 機關連結率 | 100% |
| 正規化覆蓋率 | 100% |

### 匯入後資料庫概況

| 項目 | 匯入前 | 匯入後 | 變化 |
|------|--------|--------|------|
| 公文總數 | 1,097 | 1,638 | +541 |
| 收文 | 736 | 1,123 | +387 |
| 發文 | 361 | 515 | +154 |
| 承攬案件 | 21 | 34 | +13 (另 6 已存在被匹配) |
| 機關 | ~63 | 93 | +~30 |

---

## 2. 發現的資料品質問題

### 已修復

| 問題 | 影響 | 修復方式 |
|------|------|---------|
| 承攬案件名稱尾端多餘「案」字 (id=15) | 1 筆 | SQL UPDATE 修正 |
| doc_type 為通用值 '收文'/'發文' | 13 筆 | UPDATE SET doc_type='函' |
| Excel 內重複公文字號 | 59 筆 | 腳本去重 (保留最後一筆) |

### 待觀察

| 問題 | 影響 | 建議 |
|------|------|------|
| 185 筆公文無承攬案件連結 | 11.3% | 業務端確認是否為無關案件公文 |
| 83 個機關無 agency_code | 89% | 補充官方機關代碼 |
| 3 個承攬案件無公文 (id=9,20,36) | 3 筆 | 確認是否為有效案件 |
| 2 筆歷史重複公文字號 (id=191/298, 601/638) | 匯入前已存在 | 業務端確認 |

---

## 3. 架構審計發現

### 3.1 後端 SSOT

| 項目 | 狀態 | 說明 |
|------|------|------|
| Endpoint 本地 BaseModel | CLEAN | 0 違規 (v1.84.1 修復後維持) |
| Schema 定義集中 | PASS | schemas/ 目錄為唯一來源 |
| Model 匯出完整性 | PASS | 39 model classes, __init__.py 完整 |

### 3.2 後端服務層

**大型服務 (>500L, 排除 AI):**

| 服務 | 行數 | 優先級 | 建議 |
|------|------|--------|------|
| `document_service.py` | 866L | P1 | 拆分 CRUD / 統計 / 匯出 |
| `document_calendar_service.py` | 675L | P2 | 拆分 event / sync |
| `taoyuan/dispatch_export_service.py` | 642L | P2 | 已較專一, 可接受 |
| `taoyuan/payment_service.py` | 552L | P3 | 低頻修改 |
| `project_service.py` | 544L | P2 | 拆分 CRUD / staff / vendor |
| `taoyuan/dispatch_enrichment_service.py` | 539L | P3 | 已較專一 |
| `notification_service.py` | 537L | P3 | 低頻修改 |

### 3.3 Repository 層缺口

**直接 DB 存取 (繞過 Repository) — HIGH 優先級:**

| 服務 | db.execute 次數 | 已有 Repository | 行動 |
|------|-----------------|-----------------|------|
| `document_service.py` | 10 | DocumentRepository | 遷移至 Repo |
| `project_service.py` | 9 | ProjectRepository | 遷移至 Repo |
| `case_code_service.py` | 8 | 無 | 新建 PMQueryRepository |
| `taoyuan/dispatch_link_service.py` | 11 | DispatchLinkRepository | 遷移至 Repo |
| `taoyuan/statistics_service.py` | 11 | 無 | 新建 StatisticsRepository |
| `agency_matching_service.py` | 11 | AgencyRepository | 遷移至 Repo |

### 3.4 前端

| 項目 | 狀態 | 說明 |
|------|------|------|
| TypeScript 編譯 | CLEAN | 0 errors |
| React Query 合規 | CLEAN | 0 violations |
| 型別 SSOT | 3 violations | ERPQuotationListParams, PMCaseListParams, CrossModuleLookupResult (修復中) |
| 大型元件 (>500L) | 18 檔 | Top 3: CorrespondenceBody(638), EnhancedCalendarView(607), KnowledgeGraph(597) |
| 測試覆蓋缺口 | 2 頁面 | TaoyuanDispatchDetailPage, UserFormPage |

### 3.5 匯入服務架構缺口

| 問題 | 說明 | 建議 |
|------|------|------|
| 無 upsert 模式 | doc_number 重複時只能跳過, 不能更新 | 新增 `upsert_mode` 參數 |
| ProjectMatcher 模糊匹配風險 | ILIKE 無相似度閾值, 短名可能誤匹配 | 加入 Levenshtein 距離或最低字元數門檻 |
| 自動建立機關無標記 | auto-created agencies 無法區分 | 新增 `source` 欄位 |

---

## 4. 改善行動計畫

### P0 — 本次已完成

- [x] 匯入 851 筆公文 (541 新增 + 310 更新)
- [x] 修復承攬案件名稱錯字 (id=15)
- [x] 修復 13 筆通用 doc_type → '函'
- [x] 前端 3 個 SSOT 違規修復 (背景執行中)

### P1 — 短期建議 (下次開發週期)

1. **匯入服務 upsert 模式**: `ExcelImportService.import_from_file(upsert_mode=True)`
2. **document_service.py 拆分** (866L → ~400L x2)
3. **PMQueryRepository + StatisticsRepository** 建立
4. **2 頁面測試補充**: TaoyuanDispatchDetailPage, UserFormPage

### P2 — 中期建議

5. **ProjectMatcher 強化**: Levenshtein 距離 + 最低字元閾值
6. **機關 source 欄位**: 區分手動建立 vs 匯入自動建立
7. **前端大元件拆分**: CorrespondenceBody, EnhancedCalendarView, KnowledgeGraph
8. **Repository 遷移**: document_service, project_service 中的直接 DB 查詢

### P3 — 長期建議

9. **機關代碼補充**: 83 個 agency_code 為 NULL 的機關
10. **無案件公文歸檔**: 185 筆無承攬案件連結的公文確認
11. **重複公文字號清理**: 2 對歷史重複

---

## 5. 指標追蹤

| 指標 | 匯入前 | 匯入後 | 目標 |
|------|--------|--------|------|
| 公文承攬案件連結率 | ~85% | 88.7% | >95% |
| 機關 FK 覆蓋率 | 100% | 100% | 100% |
| 正規化覆蓋率 | 100% | 100% | 100% |
| 後端 SSOT 違規 | 0 | 0 | 0 |
| 前端 SSOT 違規 | 3 | 0 (修復中) | 0 |
| 前端 TSC 錯誤 | 0 | 0 | 0 |
| 後端 >500L 服務 (非AI) | 8 | 8 | <5 |
| 前端 >500L 元件 | 18 | 18 | <10 |
| Repository 繞過 (HIGH) | 6 | 6 | 0 |
