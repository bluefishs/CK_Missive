# AI 搜尋與問答管線架構圖

CK_Missive 的 AI 子系統包含三條主要管線：四層搜尋意圖解析、Agent 工具編排、RAG 問答。

> 最後更新：2026-02-27 | 關聯：[ADR-0007](../adr/0007-four-layer-ai-architecture.md), [ADR-0009](../adr/0009-agent-rule-based-self-correction.md)

## 1. 四層搜尋意圖解析

```mermaid
graph LR
    Q[使用者查詢] --> RE[Layer 1<br/>規則引擎<br/>sync · 0ms]
    Q --> VS[Layer 2<br/>向量匹配<br/>async · <1s]
    Q --> LLM[Layer 3<br/>LLM 解析<br/>async · 1-3s]
    RE --> MG[Layer 4<br/>合併層]
    VS --> MG
    LLM --> MG
    MG --> R[IntentParsedResult<br/>+ confidence]

    style RE fill:#f6ffed,stroke:#52c41a
    style VS fill:#e6f7ff,stroke:#1890ff
    style LLM fill:#fff7e6,stroke:#faad14
    style MG fill:#f9f0ff,stroke:#722ed1
```

| Layer | 元件 | 處理 | 延遲 |
|-------|------|------|------|
| 1 | `rule_engine.py` | 正則：文號、日期、狀態碼 | 0ms |
| 2 | `search_entity_expander.py` | pgvector 餘弦距離 + 同義詞 | <1s |
| 3 | `search_intent_parser.py` | Groq/Ollama JSON 結構化輸出 | 1-3s |
| 4 | 合併邏輯 | 衝突解決 + 信心度計算 | <1ms |

## 2. Agent 工具編排

```mermaid
graph TB
    Q2[使用者問題] --> CHK{閒聊偵測}
    CHK -->|閒聊| CHAT[直接回覆<br/>3 步完成]
    CHK -->|業務| PLAN[LLM 規劃<br/>tool_calls]

    PLAN --> CORR{自動修正<br/>5 策略}
    CORR --> EXEC[工具執行迴圈<br/>max 3 輪]

    EXEC --> T1[search_documents]
    EXEC --> T2[search_dispatch_orders]
    EXEC --> T3[search_entities]
    EXEC --> T4[get_entity_detail]
    EXEC --> T5[find_similar]
    EXEC --> T6[analyze_document]

    T1 --> SYN[合成答案<br/>LLM 串流]
    T2 --> SYN
    T3 --> SYN
    T4 --> SYN
    T5 --> SYN
    T6 --> SYN

    SYN -->|SSE| FE[前端逐字顯示]

    style CHK fill:#fff7e6,stroke:#faad14
    style CORR fill:#fff1f0,stroke:#ff4d4f
    style EXEC fill:#e6f7ff,stroke:#1890ff
```

### Agent 自動修正策略

| # | 策略 | 觸發條件 | 動作 |
|---|------|---------|------|
| 1 | 空計劃恢復 | LLM 回傳無效 JSON | 用 SearchIntentParser hints 建構 tool_calls |
| 2 | 派工單偵測 | 正則匹配派工單號 | 強制加入 `search_dispatch_orders` |
| 2.5 | 零結果重試 | search_documents 0 結果 + 派工關鍵字 | 自動加 `search_dispatch_orders` |
| 4 | 實體展開 | search_entities 有結果 | 自動展開 `get_entity_detail` |
| 5 | 實體類型映射 | LLM 自然語言類型 | 映射到 DB 縮寫 |

## 3. RAG 問答管線

```mermaid
graph LR
    Q3[使用者問題] --> EMB[Embedding<br/>nomic-embed-text]
    EMB --> VEC[pgvector<br/>餘弦距離搜尋]
    VEC --> RR[Reranker<br/>TF-IDF + 關鍵字]
    RR --> CTX[上下文組裝<br/>Top-K 公文]
    CTX --> GEN[LLM 生成<br/>Groq 串流]
    GEN -->|SSE| FE2[前端逐字顯示]

    style EMB fill:#e6f7ff,stroke:#1890ff
    style VEC fill:#f9f0ff,stroke:#722ed1
    style GEN fill:#fff7e6,stroke:#faad14
```

### SSE 串流協議

```
Event 1:  {"type": "sources", "data": [...]}     ← 來源公文
Event 2+: {"type": "token", "data": "字"}        ← 逐字回答
Event N:  {"type": "done", "data": {...}}         ← 完成
Event E:  {"type": "error", "data": "message"}    ← 錯誤
```
