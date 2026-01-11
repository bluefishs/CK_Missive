# AI Architecture Patterns Skill

**技能名稱**：AI 架構模式
**用途**：定義與指導專案中 AI 功能的架構設計，確保 RAG、工具調用等複雜功能的開發一致性與可擴展性。
**適用場景**：開發新的 AI 功能、重構現有 AI 服務、設計 AI 與系統其他部分的互動。
**最後更新**：2026-01-10 (Phase 13 三層意圖識別架構)

---

## 1. 核心原則

1.  **意圖驅動 (Intent-Driven)**：所有 AI 功能的觸發點，都應始於一個明確、可識別的「意圖 (Intent)」。
2.  **三層意圖識別 (Three-Layer Intent Recognition)**：規則引擎 → 向量相似度 → LLM 備援。
3.  **分層抽象 (Layered Abstraction)**：將 AI 邏輯清晰地分為「意圖識別層」、「工具/資料執行層」與「回應生成層」。
4.  **逐步增強 (Progressive Enhancement)**：優先使用確定性的工具或資料庫查詢。只有在無法直接滿足使用者請求時，才將任務交給大型語言模型 (LLM) 進行開放式生成。

---

## 1.5 三層意圖識別架構 (Phase 13 - 2026-01-10)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: 規則引擎 (<5ms)                                     │
│   - INTENT_PATTERNS 字典 (80+ 種模式)                        │
│   - 正則表達式與關鍵詞匹配                                    │
│   - confidence ≥ 0.85 → 直接返回                             │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 向量相似度 (<50ms)                                  │
│   - IntentVectorService (39 種意圖向量)                      │
│   - Cosine similarity 匹配                                   │
│   - similarity ≥ 0.75 → 合併返回                             │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: LLM 分類 (<500ms, 僅備援)                           │
│   - EnhancedIntentService                                    │
│   - Qwen2.5 或 Claude API                                    │
│   - 低信心度或衝突時觸發                                      │
└─────────────────────────────────────────────────────────────┘
```

### 1.5.1 關鍵檔案

| 層級 | 檔案位置 | 說明 |
|------|---------|------|
| Layer 1 | `api/v1/routers/ai_chat_router.py` | INTENT_PATTERNS, detect_intent() |
| Layer 2 | `services/ai/intent_vector_service.py` | INTENT_DESCRIPTIONS, 向量匹配 |
| Layer 3 | `services/ai/enhanced_intent_service.py` | LLM 備援分類 |
| 管線 | `services/ai/intent_pipeline.py` | 執行器註冊與調度 |
| 格式化 | `services/ai/formatters/` | 8 個格式化器模組 |

### 1.5.2 新增意圖規範

新增意圖時，必須同時更新：

1. **INTENT_PATTERNS** (`ai_chat_router.py`)
   ```python
   "new_intent": {
       "patterns": ["關鍵詞1", "關鍵詞2"],
       "description": "意圖描述"
   }
   ```

2. **detect_intent()** 函數 - 新增檢測邏輯段落

3. **INTENT_DESCRIPTIONS** (`intent_vector_service.py`)
   ```python
   "new_intent": [
       "描述變體1 變體2",
       "描述變體3 變體4",
   ],
   ```

4. **執行器** (`intent_executors/`) - 建立對應 Executor 類別

5. **格式化器** (`formatters/`) - 建立對應 Formatter 類別

6. **前端回饋選項** (`AIFeedbackButton.tsx`) - 新增至 INTENT_OPTIONS

---

## 2. RAG (檢索增強生成) 管道設計規範

RAG 是本系統 AI 回答「如何操作」或「這是什麼」等知識型問題的核心。

### 2.1 標準 RAG 流程

```
使用者問題  --> [1. 產生問題的 Embedding] --> [2. 在向量資料庫中進行相似度搜尋] --> [3. 取得相關文件區塊 (Chunks)] --> [4. 建構 Prompt] --> [5. 呼叫 LLM] --> AI 回應
```

### 2.2 Embedding 模型選擇

*   **預設模型**：使用 `text-embedding-3-small` (透過 `app.core.embedding_service`) 作為預設的 Embedding 模型，以在成本與效能間取得平衡。
*   **未來考慮**：當需要處理多語言或更專業的地理資訊術語時，可評估更換為 `text-embedding-3-large` 或其他特定領域的模型。

### 2.3 文字切割 (Chunking) 策略

*   **標準策略**：應採用「遞迴字元切割 (Recursive Character Text Splitting)」。
*   **建議參數**：
    *   `chunk_size`：**1000** 字元 (適合大多數 LLM 的上下文長度)。
    *   `chunk_overlap`：**200** 字元 (確保語意的連續性，避免重要資訊在切割點被斷開)。

### 2.4 元數據 (Metadata) 過濾

*   **必要性**：當 RAG 的知識來源擴展至使用者上傳的私有文件時，Metadata 變得至關重要。
*   **規範**：
    *   每一個向量化後的 `chunk` 都必須附帶一個 `metadata` 物件。
    *   `metadata` 至少應包含 `source` (來源檔名)、`document_id`、以及 `user_id` 或 `project_id`。
    *   在進行向量搜尋前，**必須**先使用 Metadata 進行預過濾，確保 AI 只會檢索到該使用者有權限存取的資訊。

**範例**：
```python
# 進行向量搜尋前的預過濾
results = vector_store.similarity_search(
    query_embedding,
    filter={"user_id": "user-123"} # 確保只搜尋該用戶的文檔
)
```

---

## 3. Agentic Tool-Calling (代理工具調用) 架構

當 AI 需要與系統其他部分互動（如操作地圖、查詢資料庫）時，應採用此架構。

### 3.1 代理運作流程

```
使用者問題 --> [1. 意圖識別] --> [2. 選擇工具] --> [3. 執行工具] --> [4. 處理工具回傳結果] --> [5. 生成最終回應]
```

### 3.2 工具定義規範

所有可供 AI 調用的工具，都必須在一個集中的「工具註冊表」中進行定義，並遵循以下 Schema：

*   **`name`** (str): 工具的唯一識別名稱 (e.g., `flyToCoordinate`, `query_transaction_stats`)。
*   **`description`** (str): 對工具功能的清晰描述，這段描述會被 LLM 用來判斷何時該使用此工具。
*   **`input_schema`** (Pydantic Model): 使用 Pydantic 模型定義工具的輸入參數，包含類型、是否必須等資訊。

**範例** (`tools/map_tools.py`):
```python
from pydantic import BaseModel, Field

class FlyToCoordinateInput(BaseModel):
    lat: float = Field(..., description="緯度")
    lon: float = Field(..., description="經度")
    zoom: int = Field(17, description="縮放級別")

# 在工具註冊表中
TOOL_REGISTRY = {
    "flyToCoordinate": {
        "description": "將地圖視圖移動到指定的經緯度座標。",
        "input_schema": FlyToCoordinateInput,
        "execute_function": map_service.fly_to, # 執行的函數
    }
}
```

### 3.3 複雜工具鏈 (Complex Tool Chaining)

當需要執行多個工具來完成一個任務時，應遵循「ReAct (Reason + Act)」模式。

**流程**:
1.  **Reason (思考)**: LLM 分析使用者問題，決定第一個要執行的工具及其參數。
2.  **Act (行動)**: 系統執行該工具。
3.  **Observe (觀察)**: LLM 接收工具的執行結果。
4.  **Reason (再次思考)**: LLM 根據觀察到的結果，判斷任務是否已完成。如果未完成，則規劃下一步的行動（調用下一個工具或生成最終答案）。
5.  重複上述步驟直到任務完成。

---

## 4. 提示工程 (Prompt Engineering) 模板

為確保 LLM 的回覆穩定且符合預期，應使用標準化的 Prompt 模板。

### 4.1 RAG 問答模板

```
你是「乾坤測繪不動產估價系統」的 AI 操作助理。
請根據以下提供的【相關功能說明】，簡潔地回答使用者的問題。
如果說明內容無法回答問題，請誠實地說「根據我目前所知，無法回答這個問題」。

【相關功能說明】
---
{rag_context}
---

使用者問題：{user_question}
你的回答：
```

### 4.2 意圖識別模板

```
你的任務是分析使用者的查詢，並將其分類為最符合的意圖。
可用的意圖有：[data_query, comparison, trend, map_locate, tool_open, help]。

使用者查詢："{user_question}"

請只用 JSON 格式回傳最可能的意圖以及其相關參數。
例如：
{ "intent": "data_query", "data_type": "transactions", "city_name": "台北市" }
```

### 4.3 資料總結模板

```
你是一位專業的數據分析師。請根據以下 JSON 格式的數據，為使用者產生一段簡潔、易懂的摘要，不超過 100 字。

數據：
---
{json_data}
---

分析摘要：
```
---

**建立日期**：2025-12-26
**最後更新**：2026-01-10
