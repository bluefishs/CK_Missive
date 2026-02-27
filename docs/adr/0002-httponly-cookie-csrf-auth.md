# ADR-0002: httpOnly Cookie + CSRF + Refresh Token Rotation 認證架構

> **狀態**: accepted
> **日期**: 2026-01-10
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.3.0

## 背景

CK_Missive 是一套政府機關公文管理系統，處理具有機密性的公文資料。認證機制必須滿足以下安全需求：

1. **防止 XSS 竊取 Token** — 公文系統涉及多種使用者輸入（主旨、內容、備註），攻擊面較大
2. **防止 CSRF 攻擊** — Cookie-based 認證天然面臨 CSRF 風險
3. **防止 Session 劫持** — 需要有效的 Token 輪換機制，避免 Token 被重複利用
4. **符合政府資安規範** — 需要閒置登出、Token 過期等安全控制

同時，系統需要支援 Google OAuth 登入，且在內網環境下可免認證使用（參見 ADR-0003）。

## 決策

採用**三層防護認證架構**：

1. **httpOnly Cookie 存放 Access Token**
   - Access Token 存放於 httpOnly Cookie，JavaScript 無法讀取，從根本防止 XSS 竊取
   - Cookie 設定 `Secure`（HTTPS）、`SameSite=Lax`

2. **CSRF Double-Submit Cookie 模式**
   - 伺服器生成 CSRF Token 存入非 httpOnly Cookie
   - 前端每次請求在 Header 中附帶 CSRF Token
   - 後端比對 Cookie 與 Header 中的 Token 值
   - `AUTH_DISABLED` 模式下跳過 CSRF 中介軟體

3. **Refresh Token Rotation + 並發鎖**
   - Refresh Token 每次使用後輪換，舊 Token 立即失效
   - 使用 `SELECT FOR UPDATE` 資料庫鎖防止並發競態條件
   - 偵測到 Token 重複使用時，撤銷整個 Token 家族

4. **閒置登出計時器**
   - 前端偵測使用者閒置時間，超時自動登出
   - 符合政府機關資安要求

## 後果

### 正面

- XSS 攻擊無法竊取認證 Token（httpOnly Cookie 無法被 JavaScript 存取）
- CSRF Double-Submit 模式有效防止跨站請求偽造
- Refresh Token Rotation 防止 Token 重放攻擊，`SELECT FOR UPDATE` 確保並發安全
- 閒置登出機制滿足政府資安合規要求
- Google OAuth 整合順暢，Token 由後端統一管理

### 負面

- Cookie-based 認證使 CORS 配置變得複雜（需要 `credentials: include`）
- Refresh Token Rotation 需要資料庫鎖（`SELECT FOR UPDATE`），增加資料庫負擔
- `AUTH_DISABLED` 模式下仍需處理 CSRF 中介軟體的繞過邏輯
- 前後端需同步處理 Token 過期與重新取得的流程

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **JWT 存放 localStorage** | 實作簡單，但 XSS 可直接竊取 Token，不符合政府資安要求 |
| **純 Session-based 認證** | 安全性佳，但 Session 儲存在伺服器端，水平擴展困難 |
| **僅使用 OAuth2** | 標準化程度高，但離線環境無法使用外部 Identity Provider |
| **JWT + Fingerprint** | 可降低 XSS 風險，但實作複雜度高且非主流模式 |

最終選擇 httpOnly Cookie + CSRF + Rotation 的組合，在安全性與實作複雜度之間取得最佳平衡。
