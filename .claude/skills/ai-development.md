# AI 功能開發規範

> **版本**: 3.2.0
> **建立日期**: 2026-02-05
> **最後更新**: 2026-02-26 (v1.72.0 Agent v1.8.0 閒聊模式/合成答案提取/能力邊界)
> **觸發關鍵字**: AI, Groq, Ollama, 語意, 摘要, 分類, 同義詞, 知識圖譜, NER, 實體提取, CanonicalEntity, embedding, Agent, 派工單, dispatch, 閒聊, chitchat
> **適用範圍**: AI 相關功能開發與維護

---

## 架構概述

CK_Missive 採用混合 AI 架構，包含 Ollama-First 策略：

```
用戶請求
    ↓
┌─────────────────┐
│   RateLimiter   │ ← 滑動窗口 (Groq 30 req/min)
└────────┬────────┘
         ↓
┌─────────────────┐
│   SimpleCache   │ ← 記憶體快取 (TTL 1h, LRU 1000 項)
└────────┬────────┘
         ↓                 prefer_local=True?
         ├── 是 ──→ Ollama → Groq → Fallback    (NER/批次/Embedding)
         └── 否 ──→ Groq → Ollama → Fallback    (即時對話/摘要)
```

### 四層 AI 搜尋架構

```
用戶查詢 → 1. 規則引擎 (rule_engine.py)
             ↓ (低信心度)
           2. 向量匹配 (pgvector cosine similarity)
             ↓ (無結果)
           3. LLM 意圖解析 (Groq/Ollama)
             ↓
           4. 結果合併 + 同義詞擴展 + 排序
```

### Ollama-First 策略

| 任務類型 | 優先順序 | 理由 |
|---------|---------|------|
| NER 實體提取 | Ollama → Groq | 批次大量、無即時需求、本地無限量 |
| Embedding 生成 | Ollama-only | nomic-embed-text 本地專用 |
| 批次摘要/分類 | Ollama → Groq | 避免消耗 Groq 每日額度 |
| 即時搜尋/對話 | Groq → Ollama | 低延遲優先 (Groq ~100-500ms) |

### Agent Orchestrator 工具列表

| 工具 | 說明 | 參數 |
|------|------|------|
| `search_documents` | 向量+SQL 混合公文搜尋 + Hybrid Reranking | keywords, sender, receiver, doc_type, date_from, date_to, limit |
| `search_dispatch_orders` | 派工單搜尋 (桃園工務局) | dispatch_no, search, work_type, limit |
| `search_entities` | 知識圖譜實體搜尋 | query, entity_type, limit |
| `get_entity_detail` | 實體詳情 (關係+關聯公文) | entity_id |
| `find_similar` | 語意相似公文 | doc_number, limit |
| `get_statistics` | 圖譜/公文統計 | - |

**自動修正策略 (5+1)**:
1. search_documents 0 結果 → 放寬條件重試 + 觸發 search_entities
2. search_entities 0 結果 → 改用 search_documents
2.5. search_documents 0 結果且未搜派工 → search_dispatch_orders
3. 所有工具均無結果 → get_statistics 概覽
4. find_similar 錯誤 → search_documents
5. search_entities 有結果 → 自動展開 get_entity_detail

**空計劃 hints 強制注入**:
- 當 LLM 回傳無效 JSON（qwen3:4b fallback 常見），用 SearchIntentParser hints 建構 tool_calls
- 正則提取派工單號 → dispatch_no 參數
- hints.related_entity == "dispatch_order" → 強制追加 search_dispatch_orders

### 閒聊模式 (v1.7.0+)

Agent 接收到非業務查詢（問候/閒聊/超範圍請求）時，跳過完整工具規劃流程，僅用 1 次 LLM 呼叫回應。

**路由策略：反向偵測**
```
用戶輸入
    ↓
精確匹配 _CHITCHAT_EXACT (25 個問候詞)?  → 是 → 閒聊模式
    ↓ 否
前綴匹配 _CHITCHAT_PREFIXES?             → 是 → 閒聊模式
    ↓ 否
包含 _BUSINESS_KEYWORDS (55+ 關鍵字)?    → 是 → Agent 工具流程
    ↓ 否
長度 ≤ 40 字?                            → 是 → 閒聊模式
    ↓ 否
    → Agent 工具流程（保守路由）
```

**能力邊界**：
- `_CHAT_SYSTEM_PROMPT` 明確列出可做的事（搜尋公文、查詢派工單、探索知識圖譜、統計公文資料）
- 超範圍請求（影片/電影/訂餐/翻譯）→ 回覆「這個我幫不上忙」+ 引導可用功能
- 問候/閒聊正常回應，適時引導回公文功能

**qwen3:4b 思考鏈洩漏處理**：
- 閒聊：`_clean_chitchat_response()` 3 策略提取（引號回覆 → 回覆開頭行 → 智慧預設）
- 合成：`_strip_thinking_from_synthesis()` 5 階段答案提取（邊界偵測 + 區塊提取）

### 合成答案提取 (v1.8.0)

qwen3:4b 即使 `think=false` 仍大量洩漏推理段落。合成回答後處理採「答案提取」策略：

| 階段 | 策略 | 適用場景 |
|------|------|---------|
| Phase 1 | `<think>` 標記移除 | 所有 |
| Phase 2 | 短回答快速通過 | <300 字元 + 無 `[公文N]` 引用 + 無推理特徵 |
| Phase 3 | **答案邊界偵測** | 找「如下：」「可能的回應：」等標記，取後半段 |
| Phase 3.5 | **結尾「：」+ 下行結構化引用** | 通用 intro + 列表模式 |
| Phase 4 | **最後區塊提取** | 多段 `[公文N]` 區塊取最末段 |
| Phase 5 | 逐行過濾 | 無引用的純文字回答（最後手段） |

**開發注意事項**:
- 新增工具的回答如有 `[工具結果N]` 引用格式，Phase 4 的 `ref_pattern` 需同步更新
- 合成 system prompt 必須包含「禁止推理」規則 + 正確輸出範例
- 測試合成品質時需同時測試 Groq (乾淨) 和 Ollama (洩漏) 兩條路徑

### SSE 事件協議

```
閒聊模式（3 事件）:
  thinking → token → done

Agent 工具模式（N 事件）:
  thinking → [tool_call → tool_result]* → sources → thinking → token → done

事件格式：
  data: {"type":"thinking",    "step":"分析中...",        "step_index":0}
  data: {"type":"tool_call",   "tool":"search_documents", "params":{...}, "step_index":1}
  data: {"type":"tool_result", "tool":"search_documents", "summary":"找到 5 篇", "count":5, "step_index":2}
  data: {"type":"sources",     "sources":[...],           "retrieval_count":5}
  data: {"type":"token",       "token":"回答文字"}
  data: {"type":"done",        "latency_ms":1234, "model":"ollama", "tools_used":["search_documents"], "iterations":1}
  data: {"type":"error",       "error":"錯誤訊息"}
```

---

## 核心元件

### 後端 AI 服務模組

| 元件 | 位置 | 版本 | 說明 |
|------|------|------|------|
| `AIConfig` | `services/ai/ai_config.py` | 1.1.0 | AI 配置管理 (Singleton) |
| `AIConnector` | `core/ai_connector.py` | 1.1.0 | 混合 AI 連接器 (Groq + Ollama + qwen3 thinking mode) |
| `BaseAIService` | `services/ai/base_ai_service.py` | 3.0.0 | 基類: 滑動窗口限流 + Redis快取 + 統計持久化 |
| `DocumentAIService` | `services/ai/document_ai_service.py` | 5.0.0 | 公文摘要/分類/關鍵字/意圖解析/同義詞 |
| `EmbeddingManager` | `services/ai/embedding_manager.py` | 1.1.0 | Embedding LRU快取(500筆/30min) + asyncio.Lock |
| `EntityExtractionService` | `services/ai/entity_extraction_service.py` | 1.0.0 | NER 實體提取 (6類型) + 4策略JSON解析 |
| `RelationGraphService` | `services/ai/relation_graph_service.py` | 1.0.0 | 知識圖譜建構 (7-Phase) |
| `CanonicalEntityService` | `services/ai/canonical_entity_service.py` | 1.0.0 | 正規化實體 (4階段策略) |
| `GraphIngestionPipeline` | `services/ai/graph_ingestion_pipeline.py` | 1.0.0 | 圖譜資料入圖管線 |
| `GraphQueryService` | `services/ai/graph_query_service.py` | 1.0.0 | 圖譜查詢服務 |
| `SearchIntentParser` | `services/ai/search_intent_parser.py` | 1.0.0 | 搜尋意圖解析 |
| `SearchEntityExpander` | `services/ai/search_entity_expander.py` | 1.0.0 | 搜尋實體擴展 |
| `SynonymExpander` | `services/ai/synonym_expander.py` | 1.0.0 | 同義詞擴展 |
| `RuleEngine` | `services/ai/rule_engine.py` | 2.0.0 | 規則引擎 |
| `ExtractionScheduler` | `services/ai/extraction_scheduler.py` | 1.0.0 | NER 提取排程器 |
| `AgentOrchestrator` | `services/ai/agent_orchestrator.py` | 2.0.0 | Agentic 主編排 — 模組化 (tools/planner/synthesis/chitchat/utils) |
| `RAGQueryService` | `services/ai/rag_query_service.py` | 2.3.0 | RAG 問答服務 (向量+關鍵字+串流) |
| `AIPromptManager` | `services/ai/ai_prompt_manager.py` | - | Prompt 模板管理 (DB 熱重載) |
| `prompts.yaml` | `services/ai/prompts.yaml` | 1.1.0 | 5 組 Prompt 模板 |
| `synonyms.yaml` | `services/ai/synonyms.yaml` | 1.0.0 | 53 組同義詞字典 |

### 後端 AI API 端點

| 端點檔案 | 主要端點 | 說明 |
|---------|---------|------|
| `document_ai.py` | `/ai/document/summary`, `classify`, `keywords`, `natural-search`, `parse-intent` | 核心文件 AI |
| `relation_graph.py` | `/ai/document/relation-graph`, `semantic-similar` | 知識圖譜 (v2.0.0) |
| `entity_extraction.py` | `/ai/entity/extract`, `batch`, `stats` | NER 實體提取 |
| `embedding_pipeline.py` | `/ai/embedding/stats`, `batch` | Embedding 管線 |
| `synonyms.py` | `/ai/synonyms/list`, `create`, `update`, `delete`, `reload` | 同義詞管理 (v2.0.0) |
| `search_history.py` | `/ai/search-history/*` | 搜尋歷史 |
| `prompts.py` | `/ai/prompts/*` | Prompt 管理 |
| `graph_query.py` | `/ai/graph-query/*` | 圖譜查詢 |
| `ollama_management.py` | `/ai/ollama/status`, `ensure-models`, `warmup` | Ollama 管理 (admin) |
| `ai_stats.py` | `/ai/stats/*` | AI 使用統計 |
| `agent_query.py` | `/ai/agent/query/stream` | Agentic 串流問答 (6工具+SSE) |

### 前端 AI 元件

| 元件 | 位置 | 說明 |
|------|------|------|
| `AIAssistantButton` | `components/ai/` | AI 浮動按鈕 (Portal 渲染) |
| `NaturalSearchPanel` | `components/ai/` | 自然語言搜尋 + `useNaturalSearch` Hook |
| `AISummaryPanel` | `components/ai/` | 摘要生成面板 |
| `AIClassifyPanel` | `components/ai/` | 分類建議面板 |
| `KnowledgeGraph` | `components/ai/` | 知識圖譜互動式視覺化 (react-force-graph-2d) |
| `EntityDetailSidebar` | `components/ai/` | 實體詳情側欄 (`ner_project` → `project` 反向映射) |
| `GraphNodeSettings` | `components/ai/` | 節點自訂設定 (顏色/標籤/可見度, localStorage) |
| `StreamingText` | `components/ai/` | 串流文字輸出元件 |

---

## NER 實體提取

### 支援的實體類型

| 類型 | 說明 | 圖譜節點 |
|------|------|---------|
| `org` | 機關/組織 | CanonicalEntity type=org |
| `person` | 人名 | CanonicalEntity type=person |
| `project` | 專案/案件 | CanonicalEntity type=project |
| `location` | 地點 | CanonicalEntity type=location |
| `date` | 日期 | CanonicalEntity type=date |
| `topic` | 主題 | CanonicalEntity type=topic |

### 支援的關係類型

`issues`, `receives`, `manages`, `located_in`, `belongs_to`, `related_to`, `approves`, `inspects`, `deadline`

### 4 策略 JSON 解析 (fallback chain)

LLM (特別是 Ollama llama3.1:8b) 可能不回傳純 JSON，因此解析器包含 4 層 fallback：

1. **直接 json.loads()** — 純 JSON 回應
2. **Markdown code block 提取** — ````json ... ` `` ` 包裹的回應
3. **最大 JSON 物件搜尋** — 從敘述文字中找到最大的 `{...}` 結構
4. **Regex 散落物件收集** — 從 Markdown 項目符號中收集個別 entity/relation JSON

```python
# 正確的 prompt 設計（英文指令 + 嚴格 JSON-only）
EXTRACTION_SYSTEM_PROMPT = """Output ONLY valid JSON. No markdown, no explanation...
IMPORTANT: Your entire response must be parseable by json.loads(). No other text."""

# User prompt 也用英文避免 Ollama 切換語境
{"role": "user", "content": f"Extract entities and relations from this document. Reply with JSON only.\n\n{text}"}
```

### 批次提取配置

| 參數 | Ollama | Groq |
|------|--------|------|
| 併發度 | 3 | 1 |
| 間隔 | 0.5s | 2.5s |
| Circuit breaker | 連續 50 筆失敗中止 | 同左 |

---

## 知識圖譜建構 (7-Phase)

```
Phase 1: 公文節點 (OfficialDocument → node)
Phase 2: 機關節點 (sender/receiver → org node)
Phase 3: 專案節點 (ContractProject → project node)
Phase 4: NER 實體節點 (DocumentEntity → CanonicalEntity + alias)
Phase 5: 派工連結 (TaoyuanDispatchDocumentLink)
Phase 6: 桃園工程 (TaoyuanProject → node)
Phase 7: 圖譜品質優化
```

### 正規化實體 (CanonicalEntity) 4 階段策略

```
1. 精確匹配 → 完全相同名稱
2. 模糊匹配 → Levenshtein / pg_trgm similarity
3. 語意匹配 → Embedding cosine similarity (pgvector)
4. 新建實體 → 無匹配時建立新 CanonicalEntity
```

---

## Embedding 配置

| 項目 | 值 |
|------|---|
| 模型 | nomic-embed-text (Ollama 本地) |
| 維度 | **768D** |
| DB 擴展 | pgvector 0.8.0 |
| 覆蓋率 | 97.66% (711/728) |
| 快取 | LRU 500 筆, TTL 30 min |
| 並發安全 | asyncio.Lock |

---

## 開發規範

### 1. 所有 AI 端點必須使用 POST (資安規範)

```python
# ✅ 正確 - POST-only
@router.post("/stats")
async def get_ai_stats(...): ...

# ❌ 禁止 - GET 端點暴露查詢參數
@router.get("/stats")
```

### 2. 所有 AI 呼叫必須經過 RateLimiter + Cache

```python
# ✅ 正確 - 使用 _call_ai_with_cache()
async def generate_summary(self, ...):
    return await self._call_ai_with_cache(
        cache_key=self._generate_cache_key("summary", subject, content),
        ttl=self.config.cache_ttl_summary,
        system_prompt=prompts["summary"]["system"],
        user_content=user_content,
    )
```

### 3. 必須實作降級策略

```python
return {
    "summary": "...",
    "confidence": 0.95,
    "source": "ai"  # ai | fallback | rate_limited | disabled | error
}
```

### 4. NER 提取的 prompt 必須用英文指令

Ollama llama3.1:8b 對中文 system prompt 容易產生敘述回應而非 JSON。使用英文指令 + 強調 "json.loads() parseable" 可提高 JSON 輸出率。

### 5. Prompt 修改必須更新 prompts.yaml

NER 提取的 prompt 例外 — 直接定義在 `entity_extraction_service.py` 的 `EXTRACTION_SYSTEM_PROMPT` 常數中，因為需要嚴格控制格式。

### 6. 同義詞管理

- 靜態同義詞：`synonyms.yaml` (53 組)
- 動態同義詞：DB `ai_synonyms` 表 (CRUD API)
- 同義詞熱重載：`POST /ai/synonyms/reload`

---

## 環境變數

```bash
# Groq API (雲端主要)
GROQ_API_KEY=gsk_...
AI_ENABLED=true
AI_DEFAULT_MODEL=llama-3.3-70b-versatile

# Ollama (本地 / Ollama-First)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_CHAT_MODEL=llama3.1:8b
OLLAMA_NER_MODEL=llama3.1:8b
OLLAMA_SUMMARY_MODEL=llama3.1:8b
OLLAMA_CLASSIFY_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text

# pgvector
PGVECTOR_ENABLED=true

# 速率限制
AI_RATE_LIMIT_REQUESTS=30
AI_RATE_LIMIT_WINDOW=60

# 快取
AI_CACHE_ENABLED=true
AI_CACHE_TTL_SUMMARY=3600
AI_CACHE_TTL_CLASSIFY=3600
AI_CACHE_TTL_KEYWORDS=3600
```

---

## 錯誤處理

| 錯誤 | HTTP | 處理方式 |
|------|------|----------|
| API 逾時 | 200 | 自動切換到 Ollama → Fallback |
| 速率限制 | 429 | 返回 `rate_limited` 狀態 |
| 服務不可用 | 200 | 返回降級回應 (source: fallback) |
| 無效輸入 | 422 | Pydantic 驗證錯誤 |
| AI 解析失敗 | 200 | success=false + keywords 備用 |
| NER JSON 解析失敗 | - | 4策略 fallback chain，最終記錄 warning |

---

## 測試要求

### 單元測試

```python
# 必須測試的情境
- AI 正常回應 + 降級備援 (Groq → Ollama → Fallback)
- 速率限制觸發 / 快取命中+未命中
- 同義詞擴展 / 意圖後處理
- NER 4策略JSON解析（純JSON / code block / 最大物件 / regex散落）
- CanonicalEntity 4階段匹配（精確/模糊/語意/新建）
- Embedding 768D 向量生成
- 知識圖譜 7-Phase 建構
```

### 整合測試

```python
# 必須驗證
- Groq API 連接 + Ollama 備援切換
- NER 批次提取 (circuit breaker 機制)
- 知識圖譜圖譜查詢 (/ai/graph-query)
- Embedding 批次管線 (覆蓋率提升)
```

---

## 最佳實踐

1. **Ollama-First**: NER/Embedding/批次使用 `prefer_local=True`，避免消耗 Groq 額度
2. **英文 Prompt**: Ollama 的 NER prompt 使用英文指令，提高 JSON 輸出穩定性
3. **4策略解析**: 永遠假設 LLM 可能不回傳純 JSON，保留 fallback chain
4. **併發安全**: Embedding 用 `asyncio.Lock`，批次提取用 `asyncio.Semaphore`
5. **Circuit Breaker**: 連續失敗 50 筆自動中止，避免浪費資源
6. **資安**: 所有 AI 端點使用 POST + require_auth/require_admin
7. **Prompt 外部化**: 一般 prompt 在 `prompts.yaml`，NER prompt 在 service 常數

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `docs/OLLAMA_SETUP_GUIDE.md` | Ollama 部署指南 |
| `docs/SYSTEM_OPTIMIZATION_REPORT.md` | 系統優化報告 |
| `docs/SERVICE_ARCHITECTURE_STANDARDS.md` | 服務層架構規範 |
| `frontend/src/config/graphNodeConfig.ts` | 知識圖譜節點配色/標籤配置 |
| `.env.example` | 環境變數範例 |
