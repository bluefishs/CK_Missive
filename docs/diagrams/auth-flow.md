# 認證與授權流程圖

四種環境的認證策略、Token 生命週期、以及 Refresh Token Rotation 機制。

> 最後更新：2026-02-27 | 關聯：[ADR-0002](../adr/0002-httponly-cookie-csrf-auth.md), [ADR-0003](../adr/0003-internal-network-auth-bypass.md)

## 環境偵測與認證分流

```mermaid
graph TB
    REQ[使用者請求] --> DET{環境偵測<br/>config/env.ts}

    DET -->|localhost<br/>127.0.0.1| OAUTH[Google OAuth]
    DET -->|internal<br/>10.x / 172.16-31.x / 192.168.x| BYPASS[免認證<br/>直接存取]
    DET -->|ngrok<br/>*.ngrok-free.app| OAUTH
    DET -->|public<br/>其他| OAUTH

    OAUTH --> GOOG[Google 登入頁面]
    GOOG --> CB[OAuth Callback]
    CB --> TOKEN[核發 Token<br/>httpOnly Cookie]
    TOKEN --> APP[進入應用]
    BYPASS --> APP

    style BYPASS fill:#f6ffed,stroke:#52c41a
    style OAUTH fill:#e6f7ff,stroke:#1890ff
```

## Token 生命週期

```mermaid
sequenceDiagram
    participant U as 使用者
    participant FE as 前端
    participant BE as 後端
    participant DB as PostgreSQL

    Note over FE,BE: 登入成功後

    BE->>FE: Set-Cookie: access_token (httpOnly)<br/>Set-Cookie: csrf_token (readable)
    Note over FE: access_token: 30 分鐘<br/>refresh_token: 7 天<br/>idle timeout: 30 分鐘

    loop 每次 API 請求
        FE->>BE: Cookie: access_token<br/>X-CSRF-Token: csrf_token
        BE->>BE: 驗證 access_token<br/>驗證 CSRF token
    end

    Note over FE: access_token 過期

    FE->>BE: POST /auth/refresh<br/>Cookie: refresh_token
    BE->>DB: SELECT FOR UPDATE<br/>鎖定 refresh token
    Note over DB: 防止並發競態
    DB-->>BE: token 紀錄
    BE->>DB: 標記舊 token 已使用<br/>建立新 token pair
    BE->>FE: Set-Cookie: 新 access_token<br/>Set-Cookie: 新 refresh_token

    Note over FE: 閒置 30 分鐘

    FE->>FE: idle timeout 觸發
    FE->>BE: POST /auth/logout
    BE->>FE: Clear-Cookie
```

## 安全機制摘要

| 威脅 | 防護 | 實作 |
|------|------|------|
| XSS Token 竊取 | httpOnly Cookie | access_token 不可被 JS 讀取 |
| CSRF 攻擊 | Double-Submit Cookie | `csrf_token` 可讀 + `X-CSRF-Token` header |
| Token 重放 | Refresh Token Rotation | 每次 refresh 產生新 pair，舊的標記已用 |
| 並發競態 | `SELECT FOR UPDATE` | 資料庫鎖防止同時 refresh |
| Session 劫持 | Idle Timeout | 30 分鐘無操作自動登出 |
| 內網攻擊 | IP 白名單 | 僅 RFC 1918 私有 IP 範圍免認證 |
