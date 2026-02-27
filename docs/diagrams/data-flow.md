# 請求生命週期資料流圖

從前端元件到資料庫的完整請求路徑，標示每層的職責與錯誤處理機制。

> 最後更新：2026-02-27 | 關聯：[ADR-0004](../adr/0004-ssot-type-architecture.md), [ADR-0008](../adr/0008-repository-flush-only-strategy.md)

## 正常請求流程

```mermaid
sequenceDiagram
    participant C as React 元件
    participant RQ as React Query
    participant AX as Axios Client
    participant MW as FastAPI 中介軟體
    participant EP as API 端點
    participant SVC as Service 層
    participant REPO as Repository 層
    participant DB as PostgreSQL

    C->>RQ: useQuery / useMutation
    RQ->>AX: apiClient.post()
    Note over AX: 自動附加 CSRF Token<br/>自動附加 Cookie

    AX->>MW: HTTP Request
    Note over MW: 1. CORS 檢查<br/>2. Auth 驗證 (Cookie)<br/>3. Rate Limit 檢查

    MW->>EP: 路由分發
    Note over EP: 參數驗證<br/>Pydantic Schema

    EP->>SVC: 業務邏輯委派
    SVC->>REPO: 資料存取
    REPO->>DB: SQL Query
    Note over REPO: flush() only<br/>不 commit

    DB-->>REPO: 查詢結果
    REPO-->>SVC: ORM 物件
    SVC-->>EP: 處理結果
    Note over EP: commit()<br/>交易確認

    EP-->>AX: JSON Response
    Note over AX: 攔截器檢查狀態碼

    AX-->>RQ: 更新快取
    RQ-->>C: 重新渲染
```

## 錯誤處理分流

```mermaid
graph TB
    ERR[API 回應錯誤] --> CHK{狀態碼}

    CHK -->|400/409/422| BIZ[業務錯誤<br/>元件自行 catch]
    CHK -->|401| AUTH[Token 過期<br/>自動 refresh]
    CHK -->|403| GLOB1[GlobalApiErrorNotifier<br/>權限不足通知]
    CHK -->|5xx| GLOB2[GlobalApiErrorNotifier<br/>伺服器錯誤通知]
    CHK -->|網路錯誤| GLOB3[GlobalApiErrorNotifier<br/>網路異常通知]

    AUTH -->|refresh 成功| RETRY[自動重試原請求]
    AUTH -->|refresh 失敗| LOGOUT[強制登出]

    style BIZ fill:#fff7e6,stroke:#faad14
    style GLOB1 fill:#fff1f0,stroke:#ff4d4f
    style GLOB2 fill:#fff1f0,stroke:#ff4d4f
    style GLOB3 fill:#fff1f0,stroke:#ff4d4f
```

| 錯誤類型 | 處理者 | 行為 |
|---------|--------|------|
| 400/409/422 | 元件 `catch` | 顯示業務錯誤訊息 |
| 401 | Axios 攔截器 | 自動 refresh token → 重試 |
| 403 | `GlobalApiErrorNotifier` | 全域通知「權限不足」 |
| 5xx | `GlobalApiErrorNotifier` | 全域通知「伺服器錯誤」（3 秒去重） |
| 網路錯誤 | `GlobalApiErrorNotifier` | 全域通知「網路異常」 |

## 關鍵路徑檔案

| 層級 | 檔案 | 職責 |
|------|------|------|
| 前端 Hook | `src/hooks/use*.ts` | React Query 封裝 |
| API Client | `src/api/client.ts` | Axios 實例 + 攔截器 |
| 錯誤匯流排 | `src/api/errors.ts` | `ApiErrorBus` 事件發射 |
| 全域通知 | `src/components/common/GlobalApiErrorNotifier.tsx` | 訂閱 + 顯示 |
| 後端端點 | `backend/app/api/endpoints/` | 參數驗證 + commit |
| Service | `backend/app/services/` | 業務邏輯 |
| Repository | `backend/app/repositories/` | ORM 查詢 + flush |
