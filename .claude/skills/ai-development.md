# AI 功能開發規範

> **版本**: 2.0.0
> **建立日期**: 2026-02-05
> **最後更新**: 2026-02-06 (v13.0 同義詞擴展、意圖後處理、similarity 排序、POST 資安)
> **觸發關鍵字**: AI, Groq, Ollama, 語意, 摘要, 分類, 同義詞, 意圖解析
> **適用範圍**: AI 相關功能開發與維護

---

## 架構概述

CK_Missive 採用混合 AI 架構：

```
用戶請求
    ↓
┌─────────────────┐
│   RateLimiter   │ ← 30 req/min (Groq 免費方案)
└────────┬────────┘
         ↓
┌─────────────────┐
│   SimpleCache   │ ← 記憶體快取 (TTL 1 小時, LRU 1000 項)
└────────┬────────┘
         ↓
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Groq API      │ ──→ │    Ollama       │ ──→ │   Fallback      │
│   (主要)        │  失敗 │    (本地)        │  失敗 │   (預設回應)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 自然語言搜尋流程 (v2.0.0 新增)

```
用戶查詢 → AI 解析 (Groq/Ollama) → _post_process_intent()
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
        1. 同義詞擴展           2. 縮寫轉全稱          3. 低信心度策略
        keywords 擴展           sender/receiver         confidence < 0.5
                │                       │                       │
                └───────────────────────┼───────────────────────┘
                                        ↓
                            DocumentQueryBuilder
                            with_relevance_order(text)
                            → pg_trgm similarity() 排序
```

---

## 核心元件

### 後端

| 元件 | 位置 | 版本 | 說明 |
|------|------|------|------|
| `AIConfig` | `app/services/ai/ai_config.py` | 1.1.0 | AI 配置管理 (Singleton) |
| `AIConnector` | `app/core/ai_connector.py` | 1.0.0 | 混合 AI 連接器 (Groq + Ollama) |
| `BaseAIService` | `app/services/ai/base_ai_service.py` | 2.1.0 | 基類: 快取 + 限流 + 統計 |
| `DocumentAIService` | `app/services/ai/document_ai_service.py` | 2.2.0 | 公文 AI 服務 + 同義詞 + 意圖 |
| `prompts.yaml` | `app/services/ai/prompts.yaml` | 1.1.0 | 5 組 Prompt 模板 |
| `synonyms.yaml` | `app/services/ai/synonyms.yaml` | 1.0.0 | 53 組同義詞字典 |

### 前端

| 元件 | 位置 | 說明 |
|------|------|------|
| `aiApi` | `src/api/aiApi.ts` | AI API 服務 (全 POST) |
| `AI_CONFIG` | `src/config/aiConfig.ts` | AI 前端配置 + Feature Flag |
| `AIAssistantButton` | `src/components/ai/` | AI 浮動按鈕 (Portal 渲染) |
| `NaturalSearchPanel` | `src/components/ai/` | 自然語言搜尋面板 |
| `AISummaryPanel` | `src/components/ai/` | 摘要生成面板 |
| `AIClassifyPanel` | `src/components/ai/` | 分類建議面板 |

---

## 開發規範

### 1. 所有 AI 端點必須使用 POST (資安規範)

```python
# ✅ 正確 - POST-only (v2.0.0 資安規範)
@router.post("/stats")
async def get_ai_stats(...):
    ...

# ❌ 禁止 - GET 端點暴露查詢參數
@router.get("/stats")
async def get_ai_stats(...):
    ...
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

# ❌ 禁止 - 直接呼叫 connector
async def generate_summary(self, ...):
    return await self.connector.chat_completion(...)
```

### 3. 必須實作降級策略

```python
# AI 回應來源標識
return {
    "summary": "...",
    "confidence": 0.95,
    "source": "ai"  # ai | fallback | rate_limited | disabled | error
}
```

### 4. 新增 AI 功能時必須記錄統計

```python
# 統計自動追蹤（由 _call_ai_with_cache 處理）
# 手動記錄特殊情況:
self._record_stat("feature_name", error=True, latency_ms=elapsed)
```

### 5. Prompt 修改必須更新 prompts.yaml

```yaml
# ✅ 正確 - 外部化 Prompt
search_intent:
  system: |
    你是一個公文搜尋助手。...

# ❌ 禁止 - 硬編碼 Prompt
system_prompt = "你是一個公文搜尋助手。..."
```

### 6. 同義詞管理必須更新 synonyms.yaml

```yaml
# 新增同義詞組，放在對應類別下
agency_synonyms:
  - ["新機關全稱", "簡稱1", "簡稱2"]

business_synonyms:
  - ["業務全稱", "簡稱", "別稱"]
```

**同義詞類別**:

| 類別 | 說明 | 用途 |
|------|------|------|
| `agency_synonyms` | 機關名稱同義詞 | sender/receiver 擴展 |
| `doc_type_synonyms` | 公文類型同義詞 | doc_type 匹配 |
| `status_synonyms` | 狀態同義詞 | status 匹配 |
| `business_synonyms` | 業務用語同義詞 | keywords 擴展 |

---

## API 端點規範

### 端點列表 (全部 POST)

| 端點 | 說明 | 快取 | 統計 |
|------|------|------|------|
| `POST /ai/document/summary` | 生成公文摘要 | 1h | ✓ |
| `POST /ai/document/classify` | 分類建議 | 1h | ✓ |
| `POST /ai/document/keywords` | 關鍵字提取 | 1h | ✓ |
| `POST /ai/document/natural-search` | 自然語言搜尋 | - | ✓ |
| `POST /ai/document/parse-intent` | 意圖解析 | 30m | ✓ |
| `POST /ai/agency/match` | 機關匹配 | - | - |
| `POST /ai/health` | 健康檢查 | - | - |
| `POST /ai/config` | 取得配置 | - | - |
| `POST /ai/stats` | AI 使用統計 | - | - |
| `POST /ai/stats/reset` | 重設統計 | - | - |

### 回應格式

```json
{
  "result": "...",
  "confidence": 0.95,
  "source": "ai",
  "error": null
}
```

### 自然語言搜尋回應 (擴展欄位)

```json
{
  "success": true,
  "query": "找桃園市政府的待處理公文",
  "parsed_intent": { "sender": "桃園市政府", "status": "待處理", "confidence": 0.9 },
  "results": [...],
  "total": 15,
  "source": "ai",
  "search_strategy": "similarity",
  "synonym_expanded": false
}
```

| 欄位 | 說明 |
|------|------|
| `search_strategy` | keyword / similarity / hybrid / semantic |
| `synonym_expanded` | 是否經過同義詞擴展 |

---

## 環境變數

```bash
# Groq API (主要)
GROQ_API_KEY=gsk_...          # API 金鑰
AI_ENABLED=true               # 功能開關
AI_DEFAULT_MODEL=llama-3.3-70b-versatile

# Ollama (備援)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# 速率限制
AI_RATE_LIMIT_REQUESTS=30     # 請求數 (Groq 免費: 30/min)
AI_RATE_LIMIT_WINDOW=60       # 時間窗口 (秒)

# 快取
AI_CACHE_ENABLED=true
AI_CACHE_TTL_SUMMARY=3600     # 摘要快取 TTL
AI_CACHE_TTL_CLASSIFY=3600    # 分類快取 TTL
AI_CACHE_TTL_KEYWORDS=3600    # 關鍵字快取 TTL
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

---

## DocumentQueryBuilder 整合 (v1.1.0)

### similarity 排序

```python
# AI 搜尋自動啟用相關性排序
qb = DocumentQueryBuilder(db)
if intent.keywords:
    qb = qb.with_keywords_full(intent.keywords)
    search_text = " ".join(intent.keywords)
    qb = qb.with_relevance_order(search_text)  # pg_trgm similarity

# 內部實作:
# func.greatest(similarity(subject, text), similarity(sender, text)) DESC
```

### 依賴: pg_trgm 擴展

```sql
-- 需確保 PostgreSQL 已啟用
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- GIN 索引覆蓋 11 個欄位
```

---

## Phase 2 預留介面

### 向量語意搜尋 (pgvector)

```python
# AIConnector.generate_embedding() — 已定義介面
async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
    raise NotImplementedError("Phase 2: Ollama nomic-embed-text + pgvector")
```

### 串流回應

```python
# AIConnector.stream_completion() — 已實作但未整合前端
async def stream_completion(...) -> AsyncGenerator[str, None]:
    # 支援 Groq + Ollama 串流
```

---

## 測試要求

### 單元測試

```python
# 必須測試的情境
- AI 正常回應
- 速率限制觸發
- 快取命中 / 未命中
- 服務降級 (Groq → Ollama → Fallback)
- 同義詞擴展 (keywords 擴展結果驗證)
- 意圖後處理 (縮寫轉全稱驗證)
- 統計追蹤 (count / latency / cache_hit)
```

### 整合測試

```python
# 必須驗證
- Groq API 連接 (需要 API key)
- Ollama 備援切換
- 端點回應格式 (全部 POST)
- similarity 排序結果
```

---

## 前端整合

### 使用 AI API (全部 POST)

```typescript
import { aiApi } from '../api/aiApi';

// 生成摘要
const result = await aiApi.generateSummary({ subject: '公文主旨', content: '公文內容' });

// 自然語言搜尋 (含取消機制)
const result = await aiApi.naturalSearch('找桃園市政府的公文');
// result.search_strategy = 'similarity'
// result.synonym_expanded = true/false

// 健康檢查 (POST)
const health = await aiApi.checkHealth();

// 取消搜尋
import { abortNaturalSearch } from '../api/aiApi';
abortNaturalSearch();
```

### 配置同步

```typescript
import { syncAIConfigFromServer, getAIConfig } from '../config/aiConfig';

// 應用程式啟動時同步配置 (Feature Flag)
await syncAIConfigFromServer();
const config = getAIConfig();
```

---

## 最佳實踐

1. **開發環境**: 優先使用 Ollama，避免消耗 Groq 額度
2. **生產環境**: 主要依賴 Groq，Ollama 作為備援
3. **測試**: Mock AI 服務，避免依賴外部 API
4. **監控**: 使用 `POST /ai/stats` 追蹤使用統計
5. **同義詞**: 新業務詞彙立即加入 `synonyms.yaml`
6. **Prompt**: 所有修改在 `prompts.yaml` 中進行，不硬編碼
7. **資安**: 所有端點使用 POST，不暴露查詢參數

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `docs/OLLAMA_SETUP_GUIDE.md` | Ollama 部署指南 |
| `docs/SYSTEM_OPTIMIZATION_REPORT.md` | v13.0 優化報告 |
| `docs/SERVICE_ARCHITECTURE_STANDARDS.md` | 服務層架構規範 |
| `configs/postgresql-tuning.conf` | PostgreSQL 效能調優 |
| `.env.example` | 環境變數範例 |
