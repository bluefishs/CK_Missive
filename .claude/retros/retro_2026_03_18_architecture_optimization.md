# Retro: v1.84.2 全棧架構優化與乾坤智能體審計

> **日期**: 2026-03-18
> **版本**: v1.84.2
> **範圍**: 服務層拆分、SSOT 修復、DB 索引優化、AI Agent 深度審計、知識圖譜/文庫整合評估

---

## 1. 本次已完成的優化 (8 項)

### 1.1 ExcelImportService upsert 模式
- **變更**: `excel_import_service.py` + `import_.py`
- **效果**: 新增 `upsert_mode` 參數，支援 doc_number 重複時更新而非跳過
- **向後相容**: 預設 `False`，現有行為不變

### 1.2 document_service.py 拆分
- **變更**: 866L → 613L (-29%)
- **新增**: `document_dispatch_linker_service.py` (136L) + `document_import_logic_service.py` (229L)
- **測試**: 41 passed, 0 failures

### 1.3 前端 SSOT 修復
- `ERPQuotationListParams` → `types/erp.ts`
- `PMCaseListParams` → `types/pm.ts`
- `CrossModuleLookupResult` → `types/pm.ts`

### 1.4 頁面測試補充
- `TaoyuanDispatchDetailPage.test.tsx` (4 tests)
- `UserFormPage.test.tsx` (7 tests)
- 全部 11 tests passed

### 1.5 資料庫 FK 索引修復
- `entity_relationships.first_document_id` — **P0 critical** (5,581 rows)
- `taoyuan_dispatch_orders.agency_doc_id`
- `taoyuan_dispatch_orders.company_doc_id`

### 1.6 資料品質修復
- 承攬案件 id=15 名稱錯字
- 13 筆 doc_type 通用值 → '函'
- 112 收發文匯入 851 筆 (541 新增 + 310 更新)

### 1.7 測試類型修復
- `TaoyuanDispatchDetailPage.test.tsx:192` — `null` → `undefined`

### 1.8 系統文件更新
- `skills-inventory.md` — v1.84.2 審計結果
- `DEVELOPMENT_GUIDELINES.md` — 匯入/匹配/機關陷阱 (6.1-6.3)
- `MEMORY.md` — DB 統計、未來機會清單

---

## 2. 全棧架構複查結果

### 2.1 整體評級

| 維度 | 等級 | 說明 |
|------|------|------|
| **SSOT 合規** | A+ | 後端 0 BaseModel 違規, 前端 0 型別違規 |
| **安全性** | A | `str(e)` 僅用於內部模式匹配, 不洩漏至客戶端 |
| **TypeScript** | A+ | 0 errors (strict mode) |
| **React Query** | A+ | 0 useEffect+API 違規 |
| **服務模組化** | A- | document_service 已拆分; orchestrator(928L)/planner(901L) 逼近閾值 |
| **測試覆蓋** | A | 2826 前端 + 2484 後端, 0 頁面缺測試 |
| **資料庫** | A- | 3 個 FK 索引已修復, 餘 8 個低風險 |
| **API 設計** | A- | 437 端點, graph_query.py(20 端點) 偏密 |

### 2.2 後端服務層健康度

| 指標 | 數值 |
|------|------|
| 總服務行數 | 45,379L |
| >500L 服務數 | 10 (含 AI) |
| >800L 服務數 | 6 (全為 AI 核心) |
| SSOT 違規 | 0 |
| 安全洩漏 | 0 |

### 2.3 前端架構健康度

| 指標 | 數值 |
|------|------|
| TypeScript 錯誤 | 0 |
| SSOT 違規 | 0 |
| React Query 違規 | 0 |
| >500L 元件 | 18 |
| 缺測試頁面 | 0 |

### 2.4 資料庫健康度

| 表 | 行數 | 說明 |
|---|------|------|
| entity_relationships | 5,581 | 知識圖譜關係 (已建索引) |
| document_entity_mentions | 2,803 | NER 提及 |
| documents | 1,638 | 公文 (匯入後) |
| document_chunks | 1,092 | 分段 embedding |
| dispatch_document_link | 694 | 派工-公文連結 |

---

## 3. 乾坤智能體 (OpenClaw Agent v4.0.0) 深度審計

### 3.1 自進化迴路完整性: A (完全整合)

| 元件 | 狀態 | 整合點 |
|------|------|--------|
| 模式學習 | 完整 | orchestrator:500, fire-and-forget |
| 模式匹配 | 完整 | router: MD5 精確 → 語意回退 |
| 自我評估 | 完整 | orchestrator:517-521, 5 維度評分 |
| 進化排程 | 完整 | 每 50 次查詢 或 24h 自動觸發 |
| 信號佇列 | 完整 | evaluate_and_store → Redis FIFO |
| 跨會話學習 | 完整 | planner:212-214, cosine similarity 過濾 |

### 3.2 完整資料流

```
用戶查詢 → Router (閒聊→模式→LLM) → 工具執行 (max 3 iterations)
    → 引用驗證 + 答案合成 → SSE 串流
    → [背景] 模式學習 + 自評 + 進化檢查 + 追蹤記錄
```

### 3.3 工具整合矩陣

22 個工具全部整合：Vector+BM25 混合搜尋、KG 實體擴展、模式學習、跨會話注入。

### 3.4 Agent 架構建議

| 項目 | 現狀 | 建議 | 優先級 |
|------|------|------|--------|
| max_iterations=3 | 足夠 | 維持現狀 | - |
| orchestrator (928L) | 逼近 1000L | 未來考慮提取 SSE 串流邏輯 | P3 |
| planner (901L) | 逼近 1000L | 未來考慮提取跨會話學習注入 | P3 |
| 模式上限 500 | 合理 | 監控實際使用量, 必要時調高 | P3 |
| 進化觸發 50 次 | 合理 | 維持現狀 | - |
| tool_timeout=15s | 合理 | 維持現狀 | - |

---

## 4. 知識圖譜 (Knowledge Graph) 審計

### 4.1 7-Phase 建構管線: 完整

| Phase | 說明 | 狀態 |
|-------|------|------|
| 1. 實體識別 | 5 實體類型, NER via Groq/Ollama | 完整 |
| 2. 正規化 | NFKC + 6 模式 ReceiverNormalizer | 完整 |
| 3. 去重 | Jaro-Winkler 相似度, 3-phase 同源策略 | 完整 |
| 4. 正規映射 | CanonicalEntity + Alias 表 | 完整 |
| 5. 關係建構 | EntityRelationship + Recursive CTE K-hop | 完整 |
| 6. 索引 | PostgreSQL 全文 + pgvector cosine | 完整 |
| 7. 時序 | Mention 時間戳 + GraphStatisticsService | 完整 |

### 4.2 Graph Query Service (853L) 分析

graph_query_service.py 包含 20 個端點的查詢邏輯。建議未來拆分為：
- `graph_query_core.py` — 基礎節點/邊查詢
- `graph_query_analysis.py` — 統計/趨勢/路徑分析

### 4.3 圖譜數據量

| 表 | 行數 | 說明 |
|---|------|------|
| entity_relationships | 5,581 | 主要關係表 |
| document_entity_mentions | 2,803 | NER 提及 |
| document_entities | 321 | 實體 |
| entity_relations | 137 | **疑似舊版表**, 與 entity_relationships 共存 |
| canonical_entities | 40 | 正規化實體 |
| entity_aliases | 49 | 別名 |

**注意**: `entity_relations` (137 rows) 與 `entity_relationships` (5,581 rows) 共存, 需確認是否為舊版遺留。

---

## 5. 知識文庫 (Knowledge Base) 審計

### 5.1 RAG 管線

| 元件 | 狀態 | 說明 |
|------|------|------|
| 文件分段 | 完整 | 1,092 chunks (段落+滑動窗口+合併) |
| Embedding | 完整 | pgvector 768 維 |
| BM25 索引 | 完整 | tsvector 欄位 on document_chunks |
| 混合搜尋 | 完整 | Vector + BM25 加權 |
| 引用驗證 | 完整 | 精確+模糊匹配 citation_validator |

### 5.2 知識庫瀏覽器

| Tab | 說明 | 狀態 |
|-----|------|------|
| KnowledgeMapTab | 樹狀目錄 + Markdown 渲染 | 完整 |
| AdrTab | ADR 表格 + 狀態標籤 | 完整 |
| DiagramsTab | Segmented + Mermaid 架構圖 | 完整 |

### 5.3 知識管理建議

| 項目 | 現狀 | 建議 | 優先級 |
|------|------|------|--------|
| Chunk 覆蓋率 | 1,092/1,638 = 66.7% | 提升至 90%+ (新匯入 541 筆待分段) | P1 |
| Embedding 覆蓋率 | 需確認 | 執行 `embedding batch` 確保全覆蓋 | P1 |
| entity_relations 舊表 | 137 rows | 確認是否可遷移至 entity_relationships | P2 |
| KB 瀏覽器搜尋 | 無全文搜尋 | 新增 KB 內容搜尋功能 | P3 |

---

## 6. 整體性建議與規劃事項

### Phase A: 資料基礎強化 (P1, 建議下一週期)

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| A1 | 文件分段回補 | 新匯入 541 筆公文進行 chunking | 小 |
| A2 | Embedding 批次更新 | 確保所有 chunks 有 embedding | 小 |
| A3 | NER 提取排程 | 新匯入公文的實體提取 | 小 |
| A4 | 知識圖譜重建 | 基於新匯入資料重建圖譜關係 | 中 |

### Phase B: 架構精煉 (P2, 中期)

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| B1 | Repository 遷移 | 6 個 HIGH 優先服務的直接 DB 查詢遷移 | 大 |
| B2 | graph_query_service 拆分 | 853L → core + analysis (~400L x2) | 中 |
| B3 | 前端大元件拆分 | 18 個 >500L 元件, 優先 3 個 >600L | 大 |
| B4 | ProjectMatcher 強化 | Levenshtein 距離 + 最低字元門檻 | 小 |
| B5 | entity_relations 舊表處理 | 遷移至 entity_relationships 或清理 | 小 |

### Phase C: 智能體進階 (P2-P3, 長期)

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| C1 | Agent 多輪對話強化 | 記憶壓縮 + 上下文窗口優化 | 中 |
| C2 | 圖譜-RAG 深度融合 | KG subgraph 作為 RAG 上下文增強 | 大 |
| C3 | KB 內容搜尋 | 知識庫瀏覽器新增全文搜尋功能 | 小 |
| C4 | Agent 工具動態發現 | 基於 KG schema 自動推薦新工具 | 大 |
| C5 | 聯邦查詢優化 | OpenClaw 跨系統查詢效能最佳化 | 中 |

### Phase D: 資料治理 (P3, 持續)

| # | 項目 | 說明 |
|---|------|------|
| D1 | 機關代碼補充 | 83 個 agency_code 為 NULL |
| D2 | 無案件公文確認 | 185 筆無承攬案件連結 |
| D3 | 機關來源追蹤 | source 欄位區分手動/自動 |
| D4 | 空案件清理 | 3 個無公文的承攬案件 |

---

## 7. 關鍵指標追蹤

| 指標 | 本次前 | 本次後 | 目標 |
|------|--------|--------|------|
| 後端 SSOT 違規 | 0 | 0 | 0 |
| 前端 SSOT 違規 | 3 | 0 | 0 |
| TSC 錯誤 | 1 | 0 | 0 |
| document_service.py | 866L | 613L | <600L |
| 缺測試頁面 | 2 | 0 | 0 |
| FK 缺索引 (HIGH) | 1 | 0 | 0 |
| Chunk 覆蓋率 | 66.7% | 66.7% | >90% |
| 案件連結率 | 88.7% | 88.7% | >95% |
| 機關 FK 覆蓋 | 100% | 100% | 100% |
| Agent 自進化整合 | 完整 | 完整 | 完整 |
| KG 7-Phase | 完整 | 完整 | 完整 |
