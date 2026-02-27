# 系統全景架構圖

CK_Missive 公文管理系統的完整技術架構。前端 React SPA 透過 Axios 與 FastAPI 後端通訊，
後端連接 PostgreSQL（含 pgvector）、Redis 快取、以及 AI 推論服務（Groq 雲端 + Ollama 本地）。

> 最後更新：2026-02-27 | 關聯：[ADR-0001](../adr/0001-groq-primary-ollama-fallback.md), [ADR-0005](../adr/0005-mixed-mode-deployment.md)

```mermaid
graph TB
    subgraph Frontend["前端 (React 18 + TypeScript + Ant Design)"]
        UI[頁面元件]
        RQ[React Query<br/>伺服器狀態快取]
        ZS[Zustand Store<br/>UI 狀態]
        AX[Axios Client<br/>攔截器 + CSRF]
        EB[ApiErrorBus<br/>全域錯誤通知]
    end

    subgraph Backend["後端 (FastAPI + Python 3.12)"]
        API[API 端點層<br/>46+ AI 端點]
        MW[中介軟體<br/>Auth / CORS / CSRF / Rate Limit]
        SVC[Service 層<br/>業務邏輯]
        REPO[Repository 層<br/>資料存取]
        AI_SVC[AI 服務群<br/>19 個模組]
    end

    subgraph AI["AI 推論層"]
        GROQ[Groq Cloud API<br/>主要 · 快速]
        OLLAMA[Ollama Local<br/>fallback · GPU]
    end

    subgraph Infra["基礎設施 (Docker Compose)"]
        PG[(PostgreSQL 16<br/>+ pgvector 0.8.0)]
        REDIS[(Redis<br/>快取 + 限流)]
    end

    UI --> RQ
    UI --> ZS
    RQ --> AX
    AX -->|HTTP/SSE| MW
    AX -.->|錯誤| EB
    MW --> API
    API --> SVC
    SVC --> REPO
    SVC --> AI_SVC
    REPO --> PG
    AI_SVC -->|主要路徑| GROQ
    AI_SVC -->|fallback| OLLAMA
    AI_SVC -->|向量搜尋| PG
    AI_SVC -->|快取| REDIS
    SVC -->|快取| REDIS

    classDef frontend fill:#e6f7ff,stroke:#1890ff
    classDef backend fill:#f6ffed,stroke:#52c41a
    classDef ai fill:#fff7e6,stroke:#faad14
    classDef infra fill:#f9f0ff,stroke:#722ed1

    class UI,RQ,ZS,AX,EB frontend
    class API,MW,SVC,REPO,AI_SVC backend
    class GROQ,OLLAMA ai
    class PG,REDIS infra
```

## 元件說明

| 層級 | 元件 | 技術 | 說明 |
|------|------|------|------|
| 前端 | React Query | `@tanstack/react-query` | 伺服器狀態快取與自動同步 |
| 前端 | Zustand | `zustand` | 輕量 UI 狀態管理 |
| 前端 | ApiErrorBus | 自建 | 全域錯誤事件匯流排（403/5xx/網路） |
| 後端 | API 端點 | FastAPI | 46+ AI 端點 + 業務端點 |
| 後端 | AI 服務群 | 19 個模組 | 見 [ai-pipeline.md](ai-pipeline.md) |
| AI | Groq | 雲端 API | 主要推論（免費額度，sub-second） |
| AI | Ollama | 本地 GPU | RTX 4060 8GB，qwen3:4b + nomic-embed-text |
| 基礎設施 | PostgreSQL | Docker | 含 pgvector 768D 向量搜尋 |
| 基礎設施 | Redis | Docker | 快取 + Rate Limit 計數器 |
