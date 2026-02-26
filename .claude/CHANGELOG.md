# CK_Missive Claude Code 配置變更日誌

> 本文件記錄 `.claude/` 目錄下所有配置文件的變更歷史

---

## [1.73.0] - 2026-02-26

### 系統優化 — SSE 強化 + 串流防護 + 文件規範

**前端 Agent 步驟排序 (B3)**:
- `AgentStepInfo` 新增 `step_index` 欄位，對應後端 SSE `step_index`
- `onThinking` / `onToolCall` / `onToolResult` 回調接收並存儲 `stepIndex`
- `AgentStepsDisplay` 按 `step_index` 排序步驟顯示

**工具圖示差異化 (B4)**:
- `find_similar`: `FileTextOutlined` → `CopyOutlined`（相似公文）
- `get_statistics`: `DatabaseOutlined` → `BarChartOutlined`（統計資訊）

**開發規範文件更新 (C1/C2)**:
- `DEVELOPMENT_STANDARDS.md` v1.4.0 — 新增 §8 Agent 服務開發規範
  - SSE 事件協議表（7 種事件 + 4 種錯誤碼）
  - 工具註冊規範（後端 TOOLS + 前端 ICONS/LABELS 同步）
  - 合成品質控制（thinking 過濾 + 閒聊路由 + 迭代上限）
  - 前端串流防護（timeout + buffer + abort）
- `DEVELOPMENT_GUIDELINES.md` — 新增 Agent 開發前置檢查清單
  - 新增工具 5 項 + SSE 事件 4 項 + 合成品質 4 項

---

## [1.72.0] - 2026-02-26

### Agent 智慧對話模式 + 合成品質強化

**Agent Orchestrator v1.8.0 — 閒聊模式 + 合成答案提取**:

**閒聊路由（反向偵測策略）**:
- 新增 `_is_chitchat()` — 反向偵測法：檢查 `_BUSINESS_KEYWORDS` (55+ 關鍵字)
  - 有業務關鍵字 → Agent 工具流程（完整 4 層意圖解析 + LLM 規劃）
  - 無業務關鍵字 + 短句 ≤40 字 → 閒聊模式（僅 1 次 LLM 呼叫）
  - 精確匹配 `_CHITCHAT_EXACT` (25 個問候詞) + 前綴匹配 `_CHITCHAT_PREFIXES`
- 新增 `_stream_chitchat()` — 非串流 LLM 呼叫 + 後處理
  - `_CHAT_SYSTEM_PROMPT` 明確定義能力邊界（僅公文相關功能）
  - 超範圍請求回覆「這個我幫不上忙」+ 引導可用功能
  - `_clean_chitchat_response()` 3 策略提取：引號回覆 → 回覆開頭行 → 智慧預設
  - `_get_smart_fallback()` 10 組問題類型預設回覆（Ollama 回退時使用）
- 效果：問候/閒聊 13 步驟 → 3 步驟 (thinking + token + done)，延遲 <1s (Groq)

**合成答案提取（v1.8.0 核心改進）**:
- `_strip_thinking_from_synthesis()` 完全重寫 — 從「逐行過濾（黑名單）」改為「答案提取（白名單）」
  - Phase 1: `<think>` 標記移除
  - Phase 2: 短回答快速通過（<300 字元 + 無引用 + 無推理特徵）
  - Phase 3: **答案邊界偵測** — 從末尾向前找「如下：」「可能的回應：」等標記
  - Phase 3.5: **結尾「：」+ 下行結構化引用** — 通用 intro + 列表模式
  - Phase 4: **最後區塊提取** — 多段 `[公文N]`/`[派工單N]` 區塊時取最末段
  - Phase 5: 逐行過濾（最後手段，無引用的純文字回答）
- 合成 system prompt 強化：禁止推理 + 輸出格式範例
- 修正 `AgentQueryRequest.question` min_length 2→1（支援「嗨」單字輸入）

**前端工具標籤**:
- `RAGChatPanel.tsx` 新增 `search_dispatch_orders` 圖示 (`FileTextOutlined`) + 標籤（搜尋派工單）

---

## [1.71.0] - 2026-02-26

### Agent 派工單整合 + 編碼全域防護

**Agent Orchestrator v1.5.0 — 派工單工具 + 空計劃修復**:
- 新增 `search_dispatch_orders` 工具：支援 dispatch_no / search / work_type 三種搜尋策略
- 自動查詢關聯公文：透過 `taoyuan_dispatch_document_link` 帶出派工單關聯的公文
- 空計劃 hints 強制注入：qwen3:4b 回傳無效 JSON 時，用 SearchIntentParser hints 建構 tool_calls
  - 正則提取派工單號 `r"派工單[號]?\s*(\d{2,4})"` → 精確填入 dispatch_no 參數
  - 無 keywords 時使用原始問題文字作為 search 條件
- 自動修正策略 2.5：search_documents 0 結果 → 自動嘗試 search_dispatch_orders
- Few-shot 規劃範例新增 2 個派工單場景
- Planning prompt 規則強化：涉及「派工單」時必須使用 search_dispatch_orders
- `_build_synthesis_context` 派工單區塊含關聯公文資訊
- `_summarize_tool_result` 摘要含關聯公文數量

**Windows 編碼全域防護**:
- `.env` 新增 `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`
- `ecosystem.config.js` PM2 env 新增 `PYTHONUTF8: '1'`
- `startup.py` 新增 `PYTHONUTF8=1` 環境變數
- `deployment.py` 2 處 subprocess.run 加 `encoding="utf-8", errors="replace"`
- 全面審計：18+ open() + 20+ json.dumps 均已使用 UTF-8 ✓

---

## [1.70.0] - 2026-02-26

### 智能體品質強化 — 自我修正 + Hybrid Reranking + AI 機關匹配

**Phase C3: Agent 自我修正 (agent_orchestrator.py v1.2.0)**:
- `_auto_correct()` 規則式自我修正引擎 (4 策略, 不需 LLM):
  - 策略 1: 文件搜尋空結果 → 放寬條件 (移除篩選器) + 觸發實體搜尋
  - 策略 2: 實體搜尋空結果 → 改用公文全文搜尋
  - 策略 3: 所有工具均無結果 → 取得系統統計概覽
  - 策略 4: find_similar 失敗 → 降級為關鍵字文件搜尋
- `_evaluate_and_replan()` 整合: 先跑規則修正，再走 LLM 評估

**Hybrid Reranking 整合至 RAG 服務 (rag_query_service.py v2.2.0)**:
- `_retrieve_documents()` 增加 `query_terms` 參數
- 多取 2x 候選文件 → 向量+關鍵字混合重排 → 截取 top_k
- `_extract_query_terms()` 從問題提取有效查詢詞 (過濾停用詞)
- `query()` 和 `stream_query()` 自動傳遞 query_terms

**安全與品質修復 (Code Review 後)**:
- C1: 錯誤訊息不再洩漏內部異常詳情，改為通用使用者提示
- C2: Agent 端點整合服務層速率限制器 (BaseAIService.RateLimiter)
- I1: 自我修正防重複觸發：同一工具 0 結果超過 2 次不再重試
- I3: find_similar 來源補齊 category/receiver 欄位
- I4: AgencyMatchInput unmount 時清理 debounce 計時器
- I6: AgentQueryRequest 搬至 schemas/ai.py (SSOT)
- S1: done 事件 iterations 改為真實迴圈迭代次數

**Phase 4: AgencyMatchInput 智慧機關匹配元件 (v1.0.0)**:
- 新增 `AgencyMatchInput.tsx` — Ant Design Select + AI 匹配
  - 基本行為同 Select showSearch (向下相容)
  - 搜尋文字無精確匹配時，自動 debounce (600ms) 呼叫 `aiApi.matchAgency()`
  - AI 建議插入下拉頂部，帶紫色 AI 標籤 + 匹配信心度
  - 匹配結果提示欄: 高信心 (>=80%) 綠色勾、中信心黃色問號
- 整合至 `DocumentCreateInfoTab`:
  - 收文模式: 發文單位 Select → AgencyMatchInput
  - 發文模式: 受文單位 Select → AgencyMatchInput
- `useDocumentCreateForm`: 新增 `agencyCandidates` 計算欄位
- 收/發文建立頁面: 傳遞 `agencyCandidates` prop

---

## [1.69.0] - 2026-02-26

### Agentic 文件檢索引擎 — 借鑑 OpenClaw 智能體模式

**Phase A: Tool Registry + Agent Loop 核心引擎**:
- 新增 `agent_orchestrator.py` (AgentOrchestrator) — 多步工具呼叫引擎
  - 5 個工具: search_documents, search_entities, get_entity_detail, find_similar, get_statistics
  - LLM 規劃 → 工具執行 → 評估 → 最多 3 輪迭代 → 合成回答
  - 複用現有服務 (DocumentQueryBuilder, GraphQueryService, EmbeddingManager)
  - JSON 容錯解析 (直接/code-block/braces 三策略)
  - 單工具 15 秒超時保護，整體韌性降級至基本 RAG
- 新增 `agent_query.py` — `POST /ai/agent/query/stream` SSE 端點
- 路由註冊: AI `__init__.py` v1.6.0

**Phase B: 前端 Agentic Chat UI**:
- `RAGChatPanel.tsx` v3.0.0: 雙模式 (RAG / Agent)
  - 新增 `agentMode` prop (預設 true)
  - 推理步驟即時視覺化 (Steps 元件, thinking/tool_call/tool_result)
  - 工具呼叫圖示 + 標籤 (搜尋公文/搜尋實體/實體詳情/相似公文/統計)
  - Metadata 顯示: 延遲、模型、引用數、工具數
  - 串流中自動展開推理過程，完成後可摺疊
- `adminManagement.ts`: 新增 `streamAgentQuery()` + `AgentStreamCallbacks` 介面
- `endpoints.ts`: 新增 `AGENT_QUERY_STREAM` 端點常數
- `aiApi` index: 註冊 `streamAgentQuery`

**SSE 事件協議 (向下相容)**:
- 新增事件: `thinking`, `tool_call`, `tool_result`
- 保留事件: `sources`, `token`, `done`, `error`
- `done` 擴展: 新增 `tools_used[]`, `iterations` 欄位

---

## [1.68.0] - 2026-02-26

### 智能化語言查詢服務 — AI 助理統一整合

**Phase 1: 浮動面板搜尋/問答模式切換**:
- `AIAssistantButton.tsx` v3.0.0: 加入 `Segmented` 切換（搜尋 / 問答）
- RAG 問答從管理員專屬提升為全站使用者可用
- `RAGChatPanel.tsx` v2.1.0: 新增 `embedded` prop（省略 Card 外框，flex 填充父容器）
- Lazy load `RAGChatPanel`（僅切換至問答模式時載入，減少初始 bundle）
- 浮動按鈕 Tooltip 更新為「AI 智慧助理」

**Phase 2: 公文詳情頁 AI 分析 Tab**:
- 新增 `DocumentAITab` 元件（`pages/document/tabs/DocumentAITab.tsx`）
- 整合三項零掛載 AI 功能：
  - `AISummaryPanel` — AI 摘要生成（SSE 串流）
  - 語意相似公文推薦（`getSemanticSimilar`，顯示 8 筆，可點擊跳轉）
  - 單篇實體提取（`extractEntities`，顯示實體/關係數量）
- 註冊為 DocumentDetailPage 第 5 個 Tab「AI 分析」

**Phase 3: 公文建立表單 AI 分類建議**:
- 收文/發文建立表單在主旨欄下方嵌入 `AIClassifyPanel`
- 主旨輸入 >= 5 字後自動顯示分類建議面板
- 收文: `onSelect` 自動填入 `doc_type` + `category`
- 發文: `onSelect` 自動填入 `doc_type`（category 固定為發文）
- 使用 `Form.useWatch('subject', form)` 監聽主旨即時變化

**前端 AI 服務覆蓋率提升**: 61% → 87%（46 個 API 中 40 個有 UI）

---

## [1.67.0] - 2026-02-26

### 圖譜服務前端整合 — 5 個後端 API 納入 UI

**前端整合審計結果**: 9 個圖譜 API 中 5 個缺少前端 UI 使用，本次全數補齊。

**已整合服務**:
1. `getTopEntities` → KnowledgeGraphPage 左側面板「高頻實體排行」（Top 10，含類型色點 + 提及次數）
2. `findShortestPath` → KnowledgeGraphPage 左側面板「最短路徑」搜尋（兩個 Select + 路徑視覺化）
3. `mergeGraphEntities` → KnowledgeGraphPage 管理動作「合併實體」按鈕 + Modal
4. `getEntityTimeline` → EntityDetailSidebar v1.1.0 時間軸（Promise.all 平行載入，顯示 15 筆）
5. `findShortestPath` API 層: types/ai.ts + api/ai/types.ts + api/ai/knowledgeGraph.ts + endpoints.ts

**保留不整合**: `getEntityNeighbors` — 圖譜視覺化已透過 `getRelationGraph` 顯示鄰居，獨立 UI 冗餘。

**技術細節**:
- 實體搜尋共用 300ms debounced `handleEntitySearch`（Select `onSearch`）
- 合併 Modal 含方向說明（保留 vs 被合併），合併後自動重載統計
- Top Entities 與覆蓋率統計合併至 `Promise.allSettled` 平行載入
- TypeScript 0 錯誤

---

## [1.66.0] - 2026-02-26

### Phase C 閾值集中化 + 圖譜查詢 Redis 快取

**C1: 殘餘硬編碼閾值遷移**:
- `ai_config.py` v2.1.0: 新增 6 個可配置欄位
  - `agency_match_threshold` (0.7) — 機關名稱匹配最低信心度
  - `hybrid_semantic_weight` (0.4) — 混合搜尋語意權重
  - `graph_cache_ttl_detail/neighbors/search/stats` — 圖譜快取 TTL
- `document_ai_service.py`: 3 處硬編碼遷移
  - `confidence >= 0.7` → `get_ai_config().agency_match_threshold`
  - `weight=0.4` → `get_ai_config().hybrid_semantic_weight`
  - `timeout=20.0` → `get_ai_config().search_query_timeout`
- `relation_graph_service.py`: 2 處 `confidence >= 0.6` → `get_ai_config().ner_min_confidence`
- 所有閾值均支援環境變數覆寫

**C2: 圖譜查詢 Redis 快取 (graph_query_service.py v1.1.0)**:
- 共用 `RedisCache(prefix="graph:query")` 實例（模組級單例）
- 4 個高頻查詢方法加入快取層:
  - `get_entity_detail()` — TTL 300s (可配置)
  - `get_neighbors()` — TTL 300s (含 max_hops/limit 作為快取 key)
  - `search_entities()` — TTL 120s (含 query/entity_type/limit 作為快取 key)
  - `get_graph_stats()` — TTL 1800s (全域統計)
- Redis 不可用時靜默降級（RedisCache 內建 fallback）
- 預估: 重複查詢場景減少 ~90% DB 壓力

**架構複查修正**:
- `embedding_manager.py`: `_max_cache_size`, `_cache_ttl` 改從 AIConfig 讀取（原硬編碼 500/1800）
- `graph_query_service.py`: 清除未使用 imports (`literal_column`, `GraphIngestionEvent`, `List`, `and_`)
- `document_ai.py` (端點): 配置資訊回報中的 `0.7` → `config.agency_match_threshold`
- `graph_query.py` (端點): 7 處函數內 lazy import → 頂層 import（消除重複）
- `types/ai.ts`: `RAGStreamRequest` 從 `api/ai/adminManagement.ts` 遷移至 SSOT（含 re-export 鏈更新）
- AIConfig 集中化覆蓋率: 11/17 AI 服務模組使用 `get_ai_config()`（其餘 6 個無閾值需求）
- SSOT 驗證: API 層無業務型別定義違規（查詢參數型別 `*ListParams` 屬 API 關注點，合理留在 API 層）
- 驗證通過: 15/15 服務 + 10/10 端點 py_compile OK, TypeScript 0 錯誤

---

## [1.65.0] - 2026-02-26

### Phase B 效能優化 — NER 批次寫入 + 入圖管線 N+1 消除 + 元件拆分

**NER 批次寫入優化 (canonical_entity_service.py v1.1.0)**:
- 新增 `resolve_entities_batch()` 方法：批次精確匹配 + 延遲 flush + 批次建立
- Stage 1: 1 次 IN 查詢取代 N 次 per-entity 精確匹配
- Stage 2: 模糊匹配後批次去重別名（1 次查詢 vs N 次）
- Stage 3: 新實體批次 `db.add()` → 2 次 flush（建實體 + 建別名）取代 2N 次
- 預估效能提升: 10 實體文件 ~20 次 DB round-trip → ~5 次（50-75% 減少）

**入圖管線 N+1 消除 (graph_ingestion_pipeline.py v1.1.0)**:
- 使用 `resolve_entities_batch()` 取代 per-entity `resolve_entity()` 迴圈
- 關係預載: 1 次 IN 查詢取代 N 次 per-relation EXISTS 查詢
- 公文預載: 1 次 `db.get()` 取代 per-new-relation 重複查詢
- 同批次關係去重: `rel_lookup` 字典避免 INSERT 重複
- 預估批次入圖效能提升: 50 文件 batch ~50-100x 加速

**元件拆分 (AIAssistantManagementPage.tsx)**:
- 1522 行 → ~120 行（主頁面）+ 6 個獨立 Tab 元件
- 新增 `components/ai/management/` 目錄：
  - `OverviewTab.tsx` — 搜尋總覽統計
  - `HistoryTab.tsx` — 搜尋歷史與篩選
  - `EmbeddingTab.tsx` — Embedding 管理
  - `KnowledgeGraphTab.tsx` — 知識圖譜與實體提取
  - `ServiceMonitorTab.tsx` — AI 服務健康監控
  - `OllamaManagementTab.tsx` — Ollama 模型管理
  - `index.ts` — Barrel export

**Deprecated 清理**:
- 移除 `backend/app/models/calendar_event.py`（已 deprecated since v2.0.0, 零引用）

---

## [1.64.0] - 2026-02-26

### AI 閾值集中管理 + RAG Prompt DB 可配置 + 搜尋信心度色彩分級

**AIConfig v2.0.0 (ai_config.py)**:
- 新增 24 個可配置閾值，涵蓋 RAG / NER / Embedding / 知識圖譜 / 語意搜尋
- 所有閾值支援環境變數覆寫（`RAG_TOP_K`, `NER_MIN_CONFIDENCE`, `KG_FUZZY_THRESHOLD` 等）
- 移除 4 個服務中的硬編碼常數，統一讀取 AIConfig singleton

**RAG Prompt 可配置化 (rag_query_service.py v2.1.0)**:
- system prompt 改由 `AIPromptManager.get_system_prompt("rag_system")` 管理
- 優先順序: DB active 版本 > YAML (prompts.yaml) > 內建 fallback
- 新增 `rag_system` prompt 至 prompts.yaml v1.3.0（含 7 條回答規則）
- 所有生成參數（temperature, max_tokens, top_k, context_chars）讀取自 AIConfig
- 新增 embedding 向量維度執行時驗證（768D check）

**閾值統一遷移**:
- `entity_extraction_service.py`: MIN_CONFIDENCE → `AIConfig.ner_min_confidence`
- `canonical_entity_service.py`: FUZZY_SIMILARITY_THRESHOLD → `AIConfig.kg_fuzzy_threshold`
- `search_intent_parser.py`: VECTOR_SIMILARITY_THRESHOLD → `AIConfig.search_vector_threshold`

**搜尋信心度 UI 色彩分級 (NaturalSearchPanel.tsx)**:
- AI 解析信心度標籤改為三級色彩：Green (≥80%) / Orange (60-80%) / Red (<60%)

---

## [1.63.0] - 2026-02-25~26

### RAG 問答服務 v2.0 — SSE 串流 + 多輪對話 + 前端 Chat UI

**RAG Query Service (rag_query_service.py v2.0.0)**:
- 新增 `RAGQueryService`：基於現有 pgvector (728 篇 768D) + Ollama LLM 的輕量 RAG 管線
- 流程: 查詢 embedding → cosine_distance 向量檢索 → 上下文建構 → Ollama LLM 回答生成
- `query()` 同步問答 + `stream_query()` SSE 串流回答
- SSE 事件協議: `sources` → `token`* → `done`（前端先收來源再逐字回答）
- 多輪對話: history 陣列傳遞，`_build_messages()` 限制最近 4 輪 (MAX_HISTORY_TURNS)
- 來源引用追蹤（[公文N] 格式），上下文截斷 6000 字

**API 端點 (rag_query.py v2.0.0)**:
- `POST /api/ai/rag/query` — RAG 同步問答端點（需認證）
- `POST /api/ai/rag/query/stream` — RAG SSE 串流問答（含多輪對話歷史）
- StreamingResponse: `text/event-stream` + no-cache + keep-alive

**Schema (ai.py)**:
- `RAGQueryRequest`, `RAGSourceItem`, `RAGQueryResponse`

**前端 RAG Chat UI (RAGChatPanel.tsx v2.0.0)**:
- SSE 逐字串流顯示: `aiApi.streamRAGQuery()` + ReadableStream 解析
- 多輪對話記憶: 自動建構 history 陣列傳遞後端
- AbortController: 元件卸載/清除對話時自動取消串流
- 來源引用展開面板（Collapse）：doc_number / subject / sender / similarity
- 串流指示器 (LoadingOutlined)、快捷問題按鈕、回答元資料
- 整合至 AI 助理管理頁面首個 Tab（defaultActiveKey="rag-chat"）

**前端 API 整合**:
- `api/endpoints.ts`: `RAG_QUERY` + `RAG_QUERY_STREAM` 端點
- `api/ai/adminManagement.ts`: `ragQuery()` + `streamRAGQuery()` (SSE fetch + callback)
- `api/ai/index.ts`: aiApi 物件新增 ragQuery + streamRAGQuery
- `api/ai/types.ts` + `api/aiApi.ts`: re-export RAG 型別

**LlamaIndex 基礎建設**:
- 安裝 `llama-index-core`, `llama-index-vector-stores-postgres`, `llama-index-embeddings-ollama`, `llama-index-llms-ollama`
- pydantic 2.9.2 → 2.12.5（LlamaIndex 依賴升級，相容性已驗證）

**AI API 端點現況 (46 個)**:
- 公文 AI: 8 個（摘要/分類/關鍵字/搜尋/圖譜/匹配/語意相似）
- 知識圖譜: 8 個（搜尋/鄰居/最短路徑/詳情/時間軸/排名/統計/入圖）
- RAG 問答: 2 個（query + stream）
- Embedding: 2 個（stats/batch）
- NER: 3 個（extract/batch/stats）
- 搜尋歷史: 5 個
- 同義詞: 5 個
- Prompt: 4 個
- Ollama: 3 個
- 統計: 2 個
- 管理: 2 個（health/config）
- 圖譜管理: 2 個（merge-entities/ingest）

---

## [1.62.0] - 2026-02-25

### NER Ollama-First 修復 + 向量維度修正 + HNSW 索引 + 圖譜多跳查詢

**NER 實體提取修復 (entity_extraction_service.py)**:
- 重寫 `EXTRACTION_SYSTEM_PROMPT`：改用英文指令 + 嚴格 JSON-only 要求，提高 Ollama llama3.1:8b JSON 輸出率
- User prompt 改為英文（`Extract entities and relations...`）避免 Ollama 語境切換
- 新增 `_extract_json_from_text()` 四策略 JSON 解析器：
  1. 直接 json.loads() — 純 JSON
  2. Markdown code block 提取 — ```json 包裹
  3. 最大 JSON 物件搜尋 — bracket 計數找完整 `{...}`
  4. Regex 散落物件收集 — 從敘述文字收集個別 entity/relation JSON
- 拆分 `_validate_entities()` 和 `_validate_relations()` 獨立驗證函數
- **成效**: NER 成功率從 0% 提升至 100%，已批次處理 300+ 筆公文

**Ollama 狀態修復 (前端)**:
- `adminManagement.ts`: 移除 `getOllamaStatus()` 等 3 個函數的 try/catch null 回傳，改為錯誤傳播
- `AIAssistantManagementPage.tsx`: 新增 `isError` 狀態處理 + 重試按鈕

**導覽系統修復 (init_navigation_data.py)**:
- 修復 sort_order 衝突（system-management 子項、backup-management）
- AI 助理管理移至 AI 智慧功能分組
- 新增「統一表單示例」導覽項目
- 導覽覆蓋率：26/26 頁面（100%）

**向量維度修正 + HNSW 索引升級**:
- ORM 模型 `Vector(384)` → `Vector(768)` 匹配 nomic-embed-text 實際輸出（document.py, system.py, knowledge_graph.py）
- Alembic migration: `canonical_entities.embedding` 從 vector(384) → vector(768)
- 全部 3 張向量表索引從 IVFFlat 升級為 HNSW（m=16, ef_construction=64）
- Embedding 覆蓋率 97.66% → **100%**（修正維度後 17 筆卡住的公文成功入庫）
- `embedding_manager.py` docstring 修正 384 → 768

**知識圖譜多跳查詢強化 (graph_query_service.py)**:
- `get_neighbors()` 重寫為 Recursive CTE（單次 SQL 取代 N+1 Python BFS）
- 新增 `find_shortest_path()` — 兩實體間最短路徑查詢（Recursive CTE BFS）
- 新增 API 端點 `POST /ai/graph/entity/shortest-path`
- 新增 Schema: `KGShortestPathRequest`, `KGShortestPathResponse`, `KGPathNode`

**系統文件全面更新**:
- `skills/ai-development.md` v2.0.0 → **v3.0.0**：補充 NER/知識圖譜/CanonicalEntity/Ollama-First/4策略解析
- `rules/architecture.md`：ORM 模型新增 AI 模組（8 個新模型），Service 層 AI 目錄從 4 → 17 個模組
- `rules/skills-inventory.md`：ai-development 觸發關鍵字擴充 + 版本更新
- `ai_connector.py` docstring：修正 embedding 維度 384 → 768

---

## [1.61.0] - 2026-02-24

### 備份系統核心強化 + 知識圖譜修復 + CVE 漏洞修補

**備份系統 — 500 錯誤修復**:
- 修復 5 個 backup 端點 slowapi 參數命名衝突（`http_request` → `request`，body `request` → `body`）
- 修復 `uploads_dir` 雙重 backend 路徑（`project_root / "backend" / "uploads"` → `project_root / "uploads"`）
- 修復 `.env` 讀取路徑（`project_root / ".env"` → `project_root.parent / ".env"`）
- 修復 BackupManagementPage `useForm` 警告（`setFieldsValue` 從 queryFn 移至 useEffect）

**備份系統 — 核心強化 (v2.0.0)**:
- 備份失敗通知機制：首次失敗 warning、連續 ≥2 次 critical，透過 `SystemNotification` 廣播
- 自動異地同步排程：根據 `sync_interval_hours` 自動觸發 `sync_to_remote()`
- 健康檢查整合：新增 `GET /health/backup` 端點 + `build_summary()` 包含備份狀態
- `_consecutive_failures` 計數器從日誌載入，服務重啟不歸零

**知識圖譜修復**:
- NER `project` 映射為 `ner_project` 避免與業務 project 類型衝突
- `EntityDetailSidebar` 查詢時反向映射 `ner_project` → `project`
- `visibleTypes` 工具列勾選與 `GraphNodeSettings` 面板設定同步（`configVersion` 觸發）
- Drawer `mask={false}` 防止圖譜互動阻擋
- `graphNodeConfig.ts` 新增 `ner_project` 配置

**CVE 漏洞修補**:
- lodash 升級至 4.17.23 (CVE-2021-23337, High)
- requests 升級至 >=2.32.4 (CVE-2023-32681)
- `npm audit fix` 減少漏洞 35 → 24

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| Backup 500 錯誤 | 5 端點 | 0 |
| 備份失敗通知 | 無 | warning/critical |
| 異地自動同步 | 手動 | 自動排程 |
| 健康檢查含備份 | 否 | `/health/backup` |
| npm 漏洞 | 35 | 24 |
| CVE (High) | 2 | 0 |

---

## [1.60.0] - 2026-02-24

### SSOT 全面強化 + 架構優化 + 安全修復

基於系統全面架構審查，分 4 階段執行 9 項優化任務。

**P0 — 安全緊急修復**:
- SQL Injection 修復：`document_statistics_service.py` + `document_numbers.py` 的 `text(f"...")` 替換為 ORM `func.cast(func.substring(...), Integer)` 查詢
- asyncio.gather 注釋修正：`documents/list.py` 的誤導性 "asyncio.gather 並行" 註解更正
- 硬編碼 API 路徑修復：`useDocumentCreateForm.ts` 的 `/projects/list`, `/users/list` 遷移至 `API_ENDPOINTS` 常數

**P1 — 型別 SSOT 遷移**:
- AI 型別集中化：新增 `types/ai.ts` (SSOT, 757 行)，`api/ai/types.ts` 改為 re-export 相容層
- 9 個元件檔案 import 路徑更新至 `types/ai`
- 7 個 API 檔案型別清理：15 個本地 interface 定義遷移至 `types/api.ts`
- `types/document.ts` 合併 `doc_word`, `doc_class`, update-only 欄位
- `ProjectVendor`, `ProjectStaff` 基礎型別合併 API 擴展欄位

**P1 — Service 層遷移**:
- `search_history.py` 直接 `db.execute(update(...))` → `AISearchHistoryRepository.submit_feedback()`
- `synonyms.py` 直接 ORM mutation → `AISynonymRepository.update_synonym()`
- `entity_extraction.py` 計數查詢 → `get_pending_extraction_count()` service 函數
- `embedding_pipeline.py` 統計查詢 → `EmbeddingManager.get_coverage_stats()` class method

**P2 — 端點重構**:
- `agencies.py` fix_parsed_names 業務邏輯遷移至 `AgencyService.fix_parsed_names()`
- 移除 5 個 deprecated 重複路由 (agencies 2 + document_numbers 3)
- `document_numbers.py` 630→557 行, `agencies.py` 507→375 行

**P3 — 架構規範化 (二次優化)**:
- `health.py`, `relation_graph.py` 的本地 `_get_service()` 統一改用 `get_service()` 工廠模式
- `SystemHealthService._startup_time` 從模組級全域變數改為 class variable（保留向後相容函數）
- `AISynonymRepository.update_synonym()` 的 `commit()` 改為 `flush()`，commit 交由端點統一管理
- Docker Compose Ollama GPU 配置文件化（無 GPU 環境 fallback 說明）

**新增前端元件**:
- `GlobalApiErrorNotifier` — 全域 API 錯誤自動通知 (403/5xx/網路)，`ApiErrorBus` 事件匯流排
- `GraphNodeSettings` — 知識圖譜節點設定面板 (顏色/標籤/可見度，localStorage 持久化)
- `useAIPrompts` / `useAISynonyms` — AI 管理 React Query hooks

**文件同步更新**:
- `CLAUDE.md` 版本號 1.59.0 → 1.60.0
- `architecture.md` 補充 Service 層目錄結構、前端型別 SSOT 結構、全域錯誤處理架構
- `DEVELOPMENT_STANDARDS.md` §2.4 補充 `SystemHealthService` 和 `RelationGraphService`
- `DEVELOPMENT_GUIDELINES.md` 核心服務表格補充 2 項
- `TYPE_CONSISTENCY.md` §2.3 補充 `ProjectVendor` / `ProjectStaff` 擴展欄位
- `skills-inventory.md` 更新 AI 開發 skill 版本、新增 v1.60.0 元件清單

**BREAKING CHANGES**:
- `health.py` 部分端點權限從 `require_auth` 提升為 `require_admin`（detailed, metrics, pool, tasks, audit, summary）
- 移除 5 個 deprecated 路由 (agencies 2 + document_numbers 3)

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| SQL Injection 漏洞 | 2 | 0 |
| API 層本地型別定義 | 15+ | 0 (全部 re-export) |
| AI 端點直接 DB 操作 | 8 | 0 (Phase 1+2) |
| Deprecated 重複路由 | 5 | 0 |
| agencies.py 行數 | 507 | 375 |
| 本地 `_get_service()` | 2 | 0 (統一 `get_service()`) |

---

## [1.59.0] - 2026-02-21

### 全面優化 v1.59.0 — 安全強化 + 架構精煉 + 測試擴充

基於四維度審計結果（測試 4.5→7.0、前端 7.5→8.5、後端 8.7→9.2、文件 8.5→9.0），
系統性修復 15 項識別問題，分 3 個 Sprint 執行完成。

**Sprint 1: 安全 + 品質基線**:
- SQL 注入防禦加深：`audit.py` 白名單驗證 + bind parameters + rate limiting
- Rate Limiting 擴展：6 → **70** 個端點覆蓋 `@limiter.limit`（認證/寫入/AI/管理）
- `useDocumentDetail.ts` 18 處 `any` 型別修復（全部替換為具體型別）
- Form 型別 SSOT：8 個頁面本地定義集中至 `types/forms.ts`

**Sprint 2: 架構重構 + 測試擴充**:
- `DispatchWorkflowTab` 拆分：1,024 行 → **618 行** + 4 子元件
- Repository 層新增：`StaffCertificationRepository` + `ContactRepository` + agencies 遷移
- 後端測試新增：`test_auth_service.py`, `test_backup_service.py`, `test_notification_service.py`
- 前端 Hook 測試新增 7+ 檔案：useProjects, useAgencies, useCalendarEvents, useAuthGuard, useIdleTimeout 等
- Specification 文件版本標頭：13 個 docs 文件添加 `> Version: x.x.x | Last Updated`

**Sprint 3: 精煉 + 清理**:
- NaturalSearchPanel WCAG 2.1 AA 修復：role/tabIndex/aria-expanded/aria-label/onKeyDown
- Deprecated 服務清理：agency(5) + project(3) + vendor(8) 方法移除 + navigation_service 刪除
- `backup_service.py` 拆分：1,055 行 → 4 模組 (utils/db_backup/attachment_backup/scheduler)
- 部署文件整合：3 個分散文件 → 統一 `DEPLOYMENT_GUIDE.md` v2.0.0
- 覆蓋率門檻提升：60% → **70%**（pyproject.toml + CI）

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| Rate Limiting 端點 | 6 | 70 |
| Deprecated 方法 | 16 | 0 |
| DispatchWorkflowTab | 1,024 行 | 618 行 |
| backup_service.py | 1,055 行 | 4 模組 (~960 行) |
| 覆蓋率門檻 | 60% | 70% |
| Hook 測試檔案 | 3 | 12 |
| 後端服務測試 | 2 | 7 |
| Repository | 5 | 7 |

---

## [1.58.0] - 2026-02-21

### 全面優化 — CI 覆蓋率門檻 + Hooks 自動化 + Skills 擴充

**文件同步與清理 (Step 1)**:
- CHANGELOG.md 回填 v1.34→v1.57 (24 版本, +269 行)
- `pyproject.toml` 覆蓋率門檻 `fail_under=60`
- Architecture 文件更新服務遷移/Repository 狀態
- 10 個陳舊文件歸檔至 `docs/archive/`

**CI 覆蓋率門檻強制化 (Step 2)**:
- `test-coverage` job 移除 `continue-on-error`
- pytest 加入 `--cov-fail-under=60`

**Hooks 自動化擴展 (Step 3)**:
- `api-serialization-check.ps1` 升級 v2.0.0 (stdin JSON 協議)
- `performance-check.ps1` 升級 v2.0.0 (stdin JSON 協議)
- 兩者加入 PostToolUse 自動觸發
- 新增 `migration-check` prompt hook (ORM 修改提醒遷移)

**新增 Skills (Step 4)**:
- `accessibility.md` v1.0.0 — WCAG 2.1 AA + ARIA + axe-core
- `alembic-migrations.md` v1.0.0 — 遷移流程 + pgvector 檢查
- `caching-patterns.md` v1.0.0 — Redis fallback + React Query

**配置更新 (Step 5)**:
- CLAUDE.md 版本更新至 v1.58.0
- `hooks-guide.md` 新增 3 個 PostToolUse hooks
- `skills-inventory.md` 新增 3 個 Skills

**檔案統計**: 23 個檔案, +1,087 / -256 行

---

## [1.57.0] - 2026-02-21

### CLAUDE.md 模組化拆分 + Hooks 升級至官方格式

- CLAUDE.md 從 2,437 行縮減至 89 行 (96% 精簡)
- 新增 7 個 `.claude/rules/` 自動載入規範檔案
- 升級 3 個現有 hook scripts 至 stdin JSON 協議 (v2.0.0)
- 新增 SessionStart / PermissionRequest / Stop 三種 hooks
- settings.json 遷移至官方三層巢狀格式
- 新增 `hooks-development.md` skill
- 修復 PowerShell 5.1 UTF-8 BOM 編碼問題 (8 個 .ps1 檔案)
- 修復 python-lint.ps1 Push-Location 路徑前綴問題

---

## [1.56.0] - 2026-02-19

### SSOT 全面強化 + Schema-ORM 對齊 + 型別集中化

- 後端 26 個本地 BaseModel 遷移至 `schemas/` (ai, deployment, calendar, links)
- Schema-ORM 對齊：ContractProject 14 欄位 + UserResponse.email_verified
- 前端 8 個頁面本地型別集中至 `types/admin-system.ts` + `types/api.ts`
- SSOT 合規率：後端 95%→100%, 前端 85%→95%, Schema-ORM 87%→98%
- 57 個檔案修改 (+1,032 / -1,833 行，淨減少 801 行)

---

## [1.55.0] - 2026-02-19

### 全面健康檢查 + 修復執行 + Phase 6 規劃

- system_health.py SQL 注入修復 (6 個 raw SQL → ORM 白名單)
- DocumentDetailPage 拆分：897 → 204 行 (-77%)
- NaturalSearchPanel Hook 提取：774 → 274 行 (-64%)
- 24 個元件新增 ARIA 可訪問性語意屬性
- Phase 6 規劃 (6A 可訪問性 / 6B 服務拆分 / 6C 測試擴充 / 6D Repository)
- 系統健康度：9.5 → 9.6/10

---

## [1.54.0] - 2026-02-17

### 鏈式時間軸 + 架構審查修復 + 測試擴充

- ORM 模型拆分 `extended/models.py` → 7 個模組
- ChainTimeline 鏈式時間軸元件 (chain + correspondence + table 三種視圖)
- InlineRecordCreator Tab 內 Inline 新增表單
- 架構審查修復 10 項 (CRITICAL 權限檢查、分頁上限、複合索引)
- 49 個新測試 (chainUtils 31 + work_record_service 18)
- 新增 `workflow-management.md` skill

---

## [1.53.0] - 2026-02-09

### Docker+PM2 混合開發環境優化與系統韌性強化

- 新增 `docker-compose.infra.yml` (僅 PostgreSQL + Redis)
- 重寫 `dev-start.ps1` v2.0.0 支援 -FullDocker/-Stop/-Status/-Restart
- 新增 `dev-stop.ps1` 支援 -KeepInfra/-All
- 資料庫連線韌性：statement_timeout 30s + pool event listeners
- Feature Flags 架構 (PGVECTOR_ENABLED, MFA_ENABLED)

---

## [1.52.0] - 2026-02-09

### Phase 4 審查修復：SSOT 一致性 + 安全強化 + 自動回填

- 24 個 AI 端點路徑集中至 `endpoints.ts` 的 `AI_ENDPOINTS`
- MFA 型別集中至 `types/api.ts`
- Session 端點限流 (30/10/5 per minute)
- Embedding 自動回填背景任務 (main.py lifespan)

---

## [1.51.0] - 2026-02-08

### Phase 4 全面完成：RWD + AI 深度優化 + 帳號管控

- Phase 4A RWD：Sidebar Drawer + ResponsiveTable/FormRow/Container
- Phase 4B AI：SSE 串流 + pgvector 語意搜尋 + Prompt 版控 + 同義詞管理
- Phase 4C 帳號：密碼策略 + 帳號鎖定 + MFA + Email 驗證 + Session 管理
- 32 個新增檔案、105 個修改檔案 (+10,312 / -1,752 行)
- 系統健康度：9.9 → 10.0/10

---

## [1.50.0] - 2026-02-08

### Phase 4 規劃文件

- 系統文件全面更新 (已被 v1.51.0 實作取代)

---

## [1.49.0] - 2026-02-07

### 全面架構優化：安全遷移 + Redis 快取 + 測試擴充

- httpOnly Cookie 認證遷移 + CSRF 防護 (Double Submit Cookie)
- Redis 非同步連線 + AI 結果快取 + 統計持久化
- AI 回應驗證層 `_call_ai_with_validation()`
- 搜尋歷史 localStorage + 結果快取 5 分鐘 TTL
- Refresh Token 速率限制 10/minute
- 測試擴充：認證整合 8 個 + Repository 24 個 + E2E 認證 5 個

---

## [1.48.0] - 2026-02-07

### 認證安全全面強化 + 管理後台優化

- CRITICAL: 移除明文密碼回退 + Refresh Token Rotation (SELECT FOR UPDATE)
- 診斷路由保護 → admin-only
- 強制 SECRET_KEY + 啟動 Token 驗證 + 閒置 30 分鐘超時
- 跨分頁 token 同步 (storage event)
- 系統健康度：9.9 → 10.0/10

---

## [1.47.0] - 2026-02-06

### AI 助理公文搜尋全面優化

- 提示注入防護：XML 標籤隔離 + 特殊字元清理
- RLS 權限篩選 `with_assignee_access()`
- asyncio.gather 並行取得附件與專案
- 前端 AbortController 防競態 + 30 秒超時
- AI 搜尋遷移至 DocumentQueryBuilder

---

## [1.46.0] - 2026-02-06

### Repository 層全面採用

- 5 個端點模組遷移至 Repository (users, user_management, profile, config, navigation)
- 新增 NavigationRepository
- UserRepository 新增 `get_users_filtered()`
- Repository 採用率：44% → 65%

---

## [1.45.0] - 2026-02-06

### 服務層工廠模式全面遷移 + AI 管理統一

- AgencyService v3.0.0 + ProjectService v4.0.0 工廠模式遷移
- UnitOfWork 移除 4 個 Adapter 類別
- 新增 UserRepository + ConfigurationRepository
- AI 管理頁面統一至 `/admin/ai-assistant` Tab 分頁
- CSRF AUTH_DISABLED 修復
- 架構驗證腳本 `verify_architecture.py` (7 項檢查)

---

## [1.44.0] - 2026-02-06

### 連鎖崩潰防護機制

- 事故：useEffect 無限迴圈 → 請求風暴 → 後端 OOM → PM2 重啟 421 次
- 五層防護：編碼規範 + RequestThrottler + slowapi 限流 + CI 驗證 + 部署驗證
- RequestThrottler：同 URL 1s 間隔、20/10s、全域 50/10s
- 3 個高頻端點限流 (documents/list, statistics, unread-count)

---

## [1.43.0] - 2026-02-06

### Phase 2 架構優化：Query Builder 擴展

- 新增 ProjectQueryBuilder (RLS 權限控制、多條件篩選)
- 新增 AgencyQueryBuilder (智慧模糊匹配)
- VendorService 合併為工廠模式 v2.0.0

---

## [1.42.0] - 2026-02-06

### 服務層架構優化與規範建立

- 新增 DocumentQueryBuilder 流暢介面查詢
- AI 自然語言搜尋 `/ai/document/natural-search`
- NaturalSearchPanel + AIAssistantButton 搜尋整合
- 前端 AI 元件配置集中化 `aiConfig.ts`

---

## [1.41.0] - 2026-02-05

### 派工安排 work_type 欄位修復

- 修復公文詳情頁 `work_type` 多選陣列 → 逗號分隔字串轉換

---

## [1.40.0] - 2026-02-05

### AI 助手 Portal 架構重構

- 移除 Drawer 抽屜模式，改用 Card 浮動面板
- createPortal 渲染與主版面 CSS 隔離
- 可拖曳面板 + 縮合/展開 + 漸層設計

---

## [1.39.0] - 2026-02-05

### AI 助理 UI 優化與配置集中化

- 新增 `aiConfig.ts` 集中 AI 配置
- 修復 FloatButton z-index 顯示問題

---

## [1.38.0] - 2026-02-05

### AI 服務優化與測試擴充

- RateLimiter 速率限制 (30 req/min) + SimpleCache 記憶體快取 (TTL 1h)
- E2E 測試擴充：documents 12 + dispatch 14 + projects 13
- 新增 mypy.ini Python 型別檢查配置

---

## [1.37.0] - 2026-02-04

### AI 語意精靈

- 整合 Groq API (免費方案 30 req/min) + Ollama 離線備援
- 公文摘要生成 + 分類建議 + 關鍵字提取 + 機關匹配
- 後端 7 個新檔案 + 前端 4 個新檔案
- 5 個 AI API 端點

---

## [1.36.0] - 2026-02-04

### 系統效能全面優化

- asyncio.gather 並行查詢 (API 響應 -40%)
- 5 個投影查詢方法 (資料傳輸 -30%)
- 4 個新索引 (複合 + 部分索引)
- 前端 12 個 useMemo 記憶化

---

## [1.35.0] - 2026-02-04

### 前端錯誤處理系統性修復

- 修復 6 處 catch 區塊錯誤清空列表的問題
- 7 個回歸測試 (useDocumentRelations)
- 新增錯誤處理規範：catch 中保留現有資料

---

## [1.34.0] - 2026-02-04

### E2E 測試框架與 Bug 修復

- 安裝 Playwright + 10 個 E2E 煙霧測試
- 修復派工安排存檔後紀錄消失 (重複 linkDispatch)
- 新增 E2E CI 工作流 `ci-e2e.yml`
- 前端覆蓋率門檻 50% → 80%

---

## [1.33.0] - 2026-02-03

### 派工單多對多關聯一致性修復與 GitOps 評估

**關鍵修復** 🔧:
- 修復派工單-公文關聯的資料一致性問題
- 建立/更新派工單時自動同步公文到關聯表
- 刪除派工單時清理孤立的公文-工程關聯
- 解除工程-派工關聯時反向清理自動建立的關聯

**新增檔案**:
- `backend/app/scripts/sync_dispatch_document_links.py` - 資料遷移腳本
- `docs/GITOPS_EVALUATION.md` - GitOps 評估與實施計畫
- `docs/MANUAL_DEPLOYMENT_GUIDE.md` - 手動部署指引
- `docs/OPTIMIZATION_REPORT_v1.32.md` - 系統優化報告

**修改檔案**:
- `backend/app/services/taoyuan/dispatch_order_service.py` - 新增 `_sync_document_links()` 方法
- `backend/app/api/endpoints/taoyuan_dispatch/project_dispatch_links.py` - 新增反向清理邏輯
- `.github/workflows/deploy-production.yml` - 修復 secrets 語法錯誤

**整合項目**:
- Everything Claude Code 配置（5 Commands, 2 Agents, 2 Rules, 1 Skill）
- Skills 目錄重構（移除重複，統一 shared/ 結構）

**測試修復**:
- `frontend/src/utils/logger.ts` - 匯出 LogLevel 型別
- `frontend/src/config/__tests__/queryConfig.test.ts` - 修正 calendar 測試
- `frontend/src/services/__tests__/navigationService.test.ts` - 修正 undefined 錯誤

**系統健康度**: 8.8/10 → **8.9/10** (提升 0.1 分)

**待完成**:
- ⏳ 生產環境部署（SSH 連線問題待解決）
- ⏳ Self-hosted Runner 安裝（GitOps 實施）

---

## [1.29.0] - 2026-02-02

### 資安強化與 CI/CD 優化

**資安強化**:
- 新增 `security_headers.py` - 安全標頭中間件 (OWASP 建議)
- 新增 `password_policy.py` - 密碼策略模組 (12 字元、複雜度要求)
- 整合密碼驗證至 `auth_service.py`
- SQL 注入風險評估完成 (7/8 處已修復)

**CI/CD 優化**:
- 移除 ESLint continue-on-error (強化品質檢查)
- 新增 Bandit Python 安全掃描

**系統健康度**: 9.6/10 → **9.7/10** (提升 0.1 分)

---

## [1.28.0] - 2026-02-02

### 部署架構優化與系統文件更新 (原 1.27.0)

---

## [1.27.0] - 2026-02-02

### 部署架構優化與系統文件更新

**部署優化完成**:
- ✅ 統一依賴管理：移除 poetry.lock，改用 pip + requirements.txt
- ✅ 部署前置腳本：pre-deploy.sh/ps1 + init-database.py
- ✅ Alembic 遷移文檔：ALEMBIC_MIGRATION_GUIDE.md
- ✅ Docker Compose 改進：添加註解和 logging 配置

**CI/CD 管線完整性**:
- 8 個 CI jobs 全部運作正常
- Docker 建置驗證整合
- 測試覆蓋率報告整合

**文件更新**:
- `SYSTEM_OPTIMIZATION_REPORT.md` 升級至 v7.0.0
- `OPTIMIZATION_ACTION_PLAN.md` 同步更新
- `CLAUDE.md` 升級至 v1.27.0

**系統健康度**: 9.5/10 → **9.6/10** (提升 0.1 分)

---

## [1.26.0] - 2026-02-02

### 派工-工程關聯自動同步功能

**新功能實現**：
當派工單關聯工程時，自動在派工關聯的所有公文中建立相同的工程關聯。

**修改檔案**：
- `backend/app/api/endpoints/taoyuan_dispatch/project_dispatch_links.py`
- `frontend/src/api/taoyuan/projectLinks.ts`
- `frontend/src/pages/TaoyuanDispatchDetailPage.tsx`

**業務邏輯**：
```
派工單 A 關聯工程 X
  ↓
查詢派工單 A 關聯的公文（如公文 B, C）
  ↓
自動建立：公文 B ↔ 工程 X
自動建立：公文 C ↔ 工程 X
  ↓
返回同步結果
```

**用戶體驗**：
- 關聯成功後顯示「已自動同步 N 個公文的工程關聯」提示
- 無需手動在公文頁面再次關聯工程

---

## [1.25.0] - 2026-02-02

### 系統檢視與待處理項目識別

**新識別優化項目** 🆕:

1. **前端 console 使用清理**
   - 數量: 165 處
   - 分布: 30+ 個檔案
   - 建議: 遷移至 `utils/logger.ts`

2. **前端測試覆蓋擴充**
   - 現況: 3 個測試檔案
   - 目標: 10+ 個測試檔案
   - 框架: Vitest (已配置)

**文件更新**:
- `SYSTEM_OPTIMIZATION_REPORT.md` v5.1.0
- `OPTIMIZATION_ACTION_PLAN.md` v4.1.0
- `CLAUDE.md` v1.25.0

**系統健康度維持**: 9.2/10

---

## [1.24.0] - 2026-02-02

### any 型別最終清理

**DocumentDetailPage.tsx 型別修復** ✅:
- 修復 5 處 any 型別
- 新增 `ProjectStaff`, `Project`, `User` 型別導入
- API 響應 `{ staff?: any[] }` → `{ staff?: ProjectStaff[] }`
- API 響應 `{ projects?: any[] }` → `{ projects?: Project[] }`
- API 響應 `{ users?: any[] }` → `{ users?: User[] }`

**any 型別最終統計**:
| 指標 | 數值 |
|------|------|
| 原始 | 44 檔案 |
| 最終 | 3 檔案 16 處 |
| 減少 | **93%** |

**剩餘 any (合理使用)**:
- `logger.ts` (11 處) - 日誌工具 `any[]`
- `ApiDocumentationPage.tsx` (3 處) - Swagger UI 第三方庫
- `common.ts` (2 處) - 泛型函數簽名

**文件更新**:
- `OPTIMIZATION_ACTION_PLAN.md` v4.0.0
- `SYSTEM_OPTIMIZATION_REPORT.md` 驗證結果更新
- `CLAUDE.md` v1.24.0

**驗證**:
- TypeScript 編譯: 0 錯誤 ✅

---

## [1.23.0] - 2026-02-02

### 全面優化完成

**any 型別清理** ✅:
- 從 24 檔案減少至 5 檔案 (減少 79%)
- 修復 19 個檔案的型別定義
- 新增 MenuItem、DocumentFormValues 等接口

**路徑別名配置** ✅:
- tsconfig.json 新增 @/api、@/config、@/store 別名
- vite.config.ts 同步更新 resolve.alias

**測試框架完善** ✅:
- 新增 `frontend/src/test/setup.ts`
- 前端 51 個測試全部通過
- 後端 290 個測試配置完善

**CI/CD 安全掃描** ✅:
- 新增 `.github/workflows/ci.yml` security-scan job
- npm audit + pip-audit 整合
- 硬編碼密碼檢測
- 危險模式掃描

**系統健康度**: 8.8/10 → **9.2/10** (提升 0.4 分)

**受影響檔案**:
- 19 個前端型別修復
- `tsconfig.json`、`vite.config.ts` 路徑配置
- `frontend/src/test/setup.ts` 新增
- `.github/workflows/ci.yml` 安全掃描

---

## [1.22.0] - 2026-02-02

### 系統檢視與文件同步更新

**文件更新**:
- `OPTIMIZATION_ACTION_PLAN.md` 升級至 v3.0.0 - 同步修復進度
- `CHANGELOG.md` 補齊 v1.20.0, v1.21.0 歷史記錄
- `CLAUDE.md` 確認版本 v1.21.0

**建議議題整理**:
1. 剩餘 any 型別 (24 檔案) - 低優先級
2. 路徑別名配置 - 可選
3. 測試覆蓋率提升 - 長期目標
4. CI/CD 安全掃描整合 - 建議加入

---

## [1.21.0] - 2026-02-02

### 中優先級任務完成

**後端架構優化**:
- 移除 `schemas/__init__.py` 中 9 個 wildcard import
- 改用具體導入，提升程式碼可追蹤性
- Alembic 遷移狀態健康 (單一 HEAD)

**前端型別優化**:
- any 型別減少 45% (44 → 24 檔案)
- 定義具體介面替代 any
- TypeScript 編譯 0 錯誤

**大型元件評估**:
- 評估 11 個大型檔案 (>600 行)
- 多數使用 Tab 結構，各 Tab 已獨立
- 建議後續針對 PaymentsTab、DispatchOrdersTab 細化

**系統健康度**: 7.8/10 → **8.8/10** (提升 1.0 分)

---

## [1.20.0] - 2026-02-02

### 全面安全與品質修復

**安全漏洞完全修復**:
- 🔐 硬編碼密碼：10 處移除（config.py, docker-compose, 備份腳本, setup_admin.py）
- 🔐 SQL 注入：關鍵路徑改用 SQLAlchemy ORM
- 🔐 CVE 漏洞：lodash (>=4.17.21), requests (>=2.32.0)

**程式碼品質修復**:
- ✅ print() 語句：61 → 0 (替換為 logging)
- ✅ 赤裸 except：11 → 0 (改為 `except Exception as e`)
- ✅ @ts-ignore：7 → 1 (新增 `google-oauth.d.ts`)

**新增模組**:
- `backend/app/core/security_utils.py` - 安全工具模組
- `frontend/src/types/google-oauth.d.ts` - Google OAuth 型別

**系統健康度提升**: 7.8/10 → **8.5/10** (提升 0.7 分)

---

## [1.19.0] - 2026-02-02

### 系統全面檢視與優化

**系統健康度評估**:
- 文件管理: 7.5/10 → 改善中
- 前端品質: 7.6/10
- 後端品質: 7.5/10

**文件更新**:
- CLAUDE.md 日期同步修正
- CHANGELOG.md 補齊 v1.7.0 至 v1.18.0 歷史記錄
- 系統優化報告升級至 v2.0.0

**識別的優化項目**:

| 類別 | 問題 | 數量 |
|------|------|------|
| 前端 | @ts-ignore 標記 | 7 個 |
| 前端 | any 型別使用 | 42 個 |
| 前端 | 大型元件 (>600行) | 5 個 |
| 後端 | print() 語句 | 44 個 |
| 後端 | 赤裸 except 語句 | 11 個 |
| 後端 | wildcard import | 10 個 |

**新增文檔**:
- 系統優化報告 v2.0.0 - 完整程式碼品質分析

---

## [1.18.0] - 2026-01-29

### 型別一致性修正

**前後端型別同步**:
- 移除前端 `TaoyuanProject` 中不存在於後端的欄位：`work_type`, `estimated_count`, `cloud_path`, `notes`
- 強化後端 `DispatchOrder.linked_documents` 型別：`List[dict]` → `List[DispatchDocumentLink]`

**TextArea 欄位優化**:
- `DispatchFormFields.tsx` v1.3.0：分案名稱、履約期限、聯絡備註等改為 TextArea

**驗證通過**: TypeScript ✅ | Python ✅ | 前端建置 ✅ | 後端導入 ✅

---

## [1.17.0] - 2026-01-29

### 共用表單元件架構

**派工表單共用元件重構**:
- 新增 `DispatchFormFields.tsx` 共用表單元件 (448 行)
- 統一 3 處派工表單：新增頁面、詳情編輯、公文內新增
- 支援三種模式：`create`、`edit`、`quick`

**AutoComplete 混合模式**:
- 工程名稱/派工事項欄位支援「選擇 + 手動輸入」混合模式

**Tab 順序調整**:
- `/taoyuan/dispatch` 頁面 Tab 順序：派工紀錄 → 函文紀錄 → 契金管控 → 工程資訊

**Skills 文件更新**:
- `frontend-architecture.md` v1.4.0 - 新增「共用表單元件架構」章節
- `calendar-integration.md` v1.2.0 - 新增 MissingGreenlet 錯誤解決方案

---

## [1.16.0] - 2026-01-29

### Modal 警告修復與備份優化

**Antd Modal + useForm 警告修復**:
- 修復 8 個 Modal 組件的 `useForm not connected` 警告
- 新增 `forceRender` 屬性確保 Form 組件始終渲染

**導航模式規範強化**:
- `DocumentPage.tsx` 完全移除 Modal，採用導航模式
- `DocumentsTab.tsx` 移除死程式碼

**備份機制優化**:
- 實作增量備份（Incremental Backup）機制
- 新增 `attachments_latest` 目錄追蹤最新狀態
- 修復 Windows 環境路徑檢測問題

---

## [1.15.0] - 2026-01-29

### CI 自動化版

**CI/CD 整合**:
- 整合 GitHub Actions CI 流程
- 新增 `skills-sync-check` job
- 支援 Push/PR 自動觸發檢查

**驗證腳本**:
- 新增 `scripts/skills-sync-check.ps1` (Windows)
- 新增 `scripts/skills-sync-check.sh` (Linux/macOS)
- 檢查 42 項配置（Skills/Commands/Hooks/Agents）

**文檔完善**:
- 新增 `.claude/skills/README.md` v1.0.0
- 更新 `.claude/hooks/README.md` v1.2.0

---

## [1.14.0] - 2026-01-28

### UI 規範強化版

**UI 設計規範強化**:
- 日曆事件編輯改用導航模式，移除 Modal
- 新增 `CalendarEventFormPage.tsx` 頁面
- 路由新增 `/calendar/event/:id/edit`

**派工單功能改進**:
- 返回導航機制 (returnTo Pattern) 完善
- 契金維護 Tab 編輯模式統一

**文件更新**:
- `UI_DESIGN_STANDARDS.md` 升級至 v1.2.0
- 新增 `SYSTEM_OPTIMIZATION_REPORT.md`

---

## [1.13.0] - 2026-01-26

### 架構現代化版

**依賴注入系統**:
- 新增 `backend/app/core/dependencies.py` (355 行)
- 支援 Singleton 模式與工廠模式兩種依賴注入方式

**Repository 層架構**:
- 新增 `backend/app/repositories/` 目錄 (3,022 行)
- `BaseRepository[T]` 泛型基類
- `DocumentRepository`, `ProjectRepository`, `AgencyRepository`

**前端元件重構**:
- `DocumentOperations.tsx`：1,229 行 → **327 行** (減少 73%)
- 新增 `useDocumentOperations.ts` (545 行)
- 新增 `useDocumentForm.ts` (293 行)

**程式碼精簡**:
- 總計減少約 **18,040 行**程式碼

---

## [1.12.0] - 2026-01-25

### 桃園派工模組完善

**新增功能**:
- 契金管控 CRUD 完整實作
- 派工單與公文關聯管理
- 函文紀錄 Tab 整合

**API 端點**:
- `POST /taoyuan_dispatch/payments` - 新增契金
- `PUT /taoyuan_dispatch/payments/{id}` - 更新契金
- `DELETE /taoyuan_dispatch/payments/{id}` - 刪除契金

---

## [1.11.0] - 2026-01-24

### 前端狀態管理優化

**Zustand Store 整合**:
- 新增 `taoyuanDispatchStore.ts`
- 新增 `taoyuanProjectStore.ts`

**React Query 整合**:
- 統一 API 快取策略
- 樂觀更新實作

---

## [1.10.0] - 2026-01-23

### 關聯記錄處理規範

**LINK_ID 規範制定**:
- 區分「實體 ID」與「關聯 ID」
- 禁止危險的回退邏輯

**新增規範文件**:
- `LINK_ID_HANDLING_SPECIFICATION.md` v1.0.0
- `MANDATORY_CHECKLIST.md` 升級至 v1.4.0

---

## [1.9.0] - 2026-01-21

### 架構優化版

**架構優化**:
- 前端 DocumentOperations.tsx: 1421 → 1229 行 (減少 13.5%)
- 後端 ORM models.py: 664 → 605 行 (減少 9%)
- 根目錄整理：21 個腳本移至 scripts/

**一致性驗證**:
- 新增 backend/check_consistency.py
- 前後端路由一致性驗證通過

---

## [1.8.0] - 2026-01-20

### 前端狀態管理架構

**雙層狀態管理**:
- React Query (Server State)
- Zustand (UI State)

**整合 Hook 模式**:
- `useDocumentsWithStore`
- `useProjectsWithStore`

---

## [1.7.0] - 2026-01-19

### 序列化規範版

**API 序列化規範**:
- 新增 `api-serialization.md` Skill v1.0.0
- 新增 `api-serialization-check.ps1` Hook

**Python 常見陷阱規範**:
- 新增 `python-common-pitfalls.md` Skill v1.0.0
- 涵蓋 Pydantic forward reference、async MissingGreenlet 等

---

## [1.6.0] - 2026-01-18

### 重大變更：型別定義統一整合 (SSOT 架構)

**背景**: 消除前後端型別重複定義問題，建立單一真實來源

### 新增
- `type-management.md` Skill - 型別管理規範 v1.0.0
- `MANDATORY_CHECKLIST.md` 清單 H - 型別管理開發檢查
- 11 個新 Schema 檔案整合至 `backend/app/schemas/`
- 前端 OpenAPI 自動生成機制 (`npm run api:generate`)
- 型別變更日誌生成器 (`scripts/type-changelog.js`)
- Pre-commit TypeScript 編譯檢查

### 改進
- `type-sync.md` 升級至 v2.0.0 - 完整 SSOT 架構驗證
- `api-development.md` 新增 SSOT 規範說明
- `MANDATORY_CHECKLIST.md` 升級至 v1.3.0

### 整合的 Schema 檔案

| Schema 檔案 | 整合的類別數量 | 來源 |
|------------|--------------|------|
| `notification.py` | 11 | system_notifications.py, project_notifications.py |
| `document_query.py` | 10 | documents_enhanced.py |
| `document_number.py` | 10 | document_numbers.py |
| `document_calendar.py` | +2 | ConflictCheckRequest, SyncIntervalRequest |
| `reminder.py` | 6 | reminder_management.py |
| `backup.py` | 3 | backup.py |
| `case.py` | 3 | cases.py |
| `secure.py` | 2 | secure_site_management.py |
| `agency.py` | +2 | FixAgenciesRequest, FixAgenciesResponse |
| `project.py` | +1 | ProjectListQuery |
| `user.py` | +1 | UserListQuery |
| `vendor.py` | +2 | VendorListQuery, VendorStatisticsResponse |
| `project_staff.py` | +1 | StaffListQuery |
| `project_vendor.py` | +1 | VendorAssociationListQuery |
| `project_agency_contact.py` | +1 | UpdateContactRequest |

### 成果指標
- endpoints 本地 BaseModel：62+ → 0 (100% 減少)
- 新增欄位修改位置：6+ → 2 (僅後端 Schema + 前端自動生成)

---

## [1.5.0] - 2026-01-15

### 新增
- `PUT /auth/profile` - 更新個人資料 API 端點
- `PUT /auth/password` - 修改密碼 API 端點
- `ProfileUpdate` schema 定義
- 共享 Skills 庫文檔化至 CLAUDE.md
- 本 CHANGELOG.md 變更日誌

### 改進
- `useAuthGuard.ts` v1.3.0 - superuser 角色現在擁有所有角色權限
- `auth.py` v2.2 - 新增個人資料與密碼管理端點
- `SiteManagementPage.tsx` - 修復 ValidPath 型別錯誤
- CLAUDE.md 升級至 v1.5.0

### 修復
- 修復 superuser 無法訪問管理員頁面的權限問題
- 修復 ProfilePage 的 404 錯誤 (缺失 API 端點)

---

## [1.4.0] - 2026-01-12 ~ 2026-01-14

### 新增
- `/security-audit` 資安審計檢查指令
- `/performance-check` 效能診斷檢查指令
- `navigation_validator.py` 路徑白名單驗證機制
- 導覽路徑下拉選單自動載入功能
- `route-sync-check.ps1` 路徑同步檢查 Hook
- API Rate Limiting (slowapi)
- Structured Logging (structlog)
- 擴展健康檢查端點 (CPU/Memory/Disk/Scheduler)

### 改進
- `route-sync-check.md` 升級至 v2.0.0 - 新增白名單驗證
- `api-check.md` 升級至 v2.1.0 - POST-only 安全模式檢查
- `MANDATORY_CHECKLIST.md` 升級至 v1.2.0 - 新增導覽系統架構說明
- `frontend-architecture.md` 新增至 Skills (v1.0.0)
- `EntryPage.tsx` 修復快速進入未設定 user_info 問題

### 修復
- bcrypt 版本降級至 4.0.1 (解決 Windows 相容性)
- 動態 CORS 支援多來源
- 統一日誌編碼 (UTF-8)
- 進程管理腳本優化

---

## [1.3.0] - 2026-01-10 ~ 2026-01-11

### 新增
- 環境智慧偵測登入機制 (localhost/internal/ngrok/public)
- 內網 IP 免認證快速進入功能
- Google OAuth 登入整合
- 新帳號審核機制
- 網域白名單檢查

### 改進
- `EntryPage.tsx` 升級至 v2.5.0 - 三種登入方式
- `useAuthGuard.ts` v1.2.0 - 支援內網繞過認證
- `config/env.ts` 集中式環境偵測

---

## [1.2.0] - 2026-01-08 ~ 2026-01-09

### 新增
- `/db-backup` 資料庫備份管理指令
- `/csv-import-validate` CSV 匯入驗證指令
- `/data-quality-check` 資料品質檢查指令
- 備份排程器 (每日凌晨 2:00)

### 改進
- 公文管理 CRUD 完善
- 行事曆 Google Calendar 雙向同步

---

## [1.1.0] - 2026-01-05 ~ 2026-01-07

### 新增
- `/pre-dev-check` 開發前強制檢查指令
- `/route-sync-check` 前後端路由檢查指令
- `/api-check` API 端點一致性檢查指令
- `/type-sync` 型別同步檢查指令
- `MANDATORY_CHECKLIST.md` 強制性開發檢查清單
- `DEVELOPMENT_GUIDELINES.md` 開發指引

### 改進
- Hooks 系統建立 (typescript-check, python-lint)
- Agents 建立 (code-review, api-design)

---

## [1.0.0] - 2026-01-01 ~ 2026-01-04

### 初始版本
- 專案架構建立
- FastAPI + PostgreSQL 後端
- React + TypeScript + Ant Design 前端
- 基本公文管理功能
- 基本認證系統

---

## 版本號說明

採用語義化版本 (SemVer):
- **Major (主版本)**: 重大架構變更或不相容更新
- **Minor (次版本)**: 新增功能，向後相容
- **Patch (修補版本)**: Bug 修復，向後相容

---

*維護者: Claude Code Assistant*
