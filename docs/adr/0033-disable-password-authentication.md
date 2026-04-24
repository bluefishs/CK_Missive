# ADR-0033: 關閉帳號密碼登入機制

- **Status**: Accepted
- **Date**: 2026-04-24
- **Deciders**: Aaron (jujuiacc@gmail.com)
- **Related**: ADR-0017 Docker Secrets (secrets 管理), 內部資安評估

---

## Context

CK_Missive 公網站 `missive.cksurvey.tw` 提供三種登入方式：
1. **Google OAuth**（IdP 認證，無密碼）
2. **LINE Login**（IdP 認證，無密碼）
3. **帳號密碼**（本地 bcrypt hash + MFA 選配）

帳密登入最初用於：
- 內網環境後備（Google/LINE 平台配置完成前）
- 本地開發測試
- 外部 IdP 不可達時的緊急備援

### 觸發點

公網站面臨的實際風險：
- **暴力破解**：單一端點 POST `/api/auth/login`，rate limit 5/min 擋不住分散式攻擊
- **Credential stuffing**：使用者若在他處 reuse 密碼，帳號全部暴露
- **憑證外洩**：登入表單自動填充 + keylogger / MITM 提高洩漏面
- **bcrypt 比對耗 CPU**：惡意 request 可作為 resource exhaustion 向量

目前 Google OAuth 與 LINE Login 皆已配置完成（2026-04 GCP origin 已加 `missive.cksurvey.tw`），
帳密後備的必要性消失。

---

## Decision

**全面關閉帳號密碼登入機制**，前端 UI 隱藏 + 後端 endpoint 回 410 Gone。

### 實施範圍

| 層 | 變動 |
|---|---|
| **前端 `EntryPage`** | `SHOW_PASSWORD_LOGIN = false`（常數，非運行時 toggle） |
| **前端 `LoginPanel`** | 帳密表單渲染加 `flags.password` 雙層守護 |
| **前端 `LoginPage` (/login)** | 整頁改為 `<Navigate to="/entry" replace />` legacy redirect |
| **後端 `/api/auth/login`** | 無條件回 `410 Gone` + `logger.warning [SECURITY]` + 審計寫入 `LOGIN_BLOCKED_PASSWORD_DISABLED` |
| **rate limit** | 5/min 保留以防暴力嘗試被用作探測手段 |

### 保留項目

- **Google OAuth `/api/auth/google`**：正常運作
- **LINE Login `/api/auth/line`**：正常運作
- **`/api/auth/refresh`、`/api/auth/logout`、`/api/auth/me`**：正常運作（不涉及密碼驗證）
- **MFA 流程**：endpoint 保留，但因 `/login` 已停用而無呼叫路徑；未清除以免影響尚未 migrate 的 user
- **快速進入**（`authDisabled` 模式）：僅限本機 / 內網開發，不受本 ADR 影響

### 審計與監控

後端每次收到 `/api/auth/login` 請求時：
1. `logger.warning [SECURITY] 帳密登入嘗試 (已停用): user=xx ip=yy`
2. 寫入 `auth_audit_log` event_type=`LOGIN_BLOCKED_PASSWORD_DISABLED`
3. 回 `410 Gone` with 明確 detail 訊息

預期正常流量為 0，持續嘗試 → 資安告警訊號。

---

## Consequences

### 正向
- 根除帳密相關攻擊向量（暴力破解、credential stuffing）
- 降低 CPU 消耗（bcrypt 比對成本）
- 簡化認證路徑（SSO only，IdP 處理憑證安全）
- 前端 UI 收斂（移除帳密表單降低頁面複雜度）

### 負向 / 風險
- 外部 IdP（Google / LINE）不可達時**無後備**
  - 緩解：運維 runbook 加「IdP outage → 手動開啟 `/login` endpoint（git revert + redeploy）」
- 舊用戶若未綁定 Google / LINE 帳號可能無法登入
  - 緩解：部署前檢查 `users.google_id` + `users.line_id` 綁定覆蓋率

### 遷移
- 未綁定 SSO 的歷史 user：`SELECT id, email FROM users WHERE google_id IS NULL AND line_id IS NULL`
- 通知：請 user 先以原帳密登入（部署前）綁定 SSO；部署後無法登入者請聯絡管理員

---

## Alternatives Considered

### A. 加強 rate limit + captcha
拒絕。仍留暴力破解理論面，不徹底；使用者體驗下降。

### B. 僅前端隱藏，後端保留
拒絕。後端 endpoint 仍可直接 curl 打，資安評估視為未解決。

### C. 刪除 endpoint（404）
拒絕。無明確訊號給 client；資安監控難以區分「惡意探測」vs「設定錯誤」。

### D. 採用 WebAuthn / Passkey 取代密碼
擱置。屬於下一代方案；當前 SSO 已足夠覆蓋絕大多數使用情境。

---

## Verification

- Regression tests：
  - `backend/tests/unit/test_password_login_disabled.py` — endpoint 必回 410
  - `frontend/src/pages/__tests__/LoginPageRedirect.test.tsx` — 舊 /login 必 redirect 至 /entry
- 手動驗證：
  - `curl -X POST https://missive.cksurvey.tw/api/auth/login -d 'username=x&password=x'` → 410
  - 訪問 `/entry` → 無「帳號密碼登入」按鈕
  - 訪問 `/login` → 自動轉 `/entry`

### 回滾路徑

若 IdP outage 需臨時啟用：
1. `git revert <本 commit>` 不推薦（影響 audit trail）
2. 推薦：在 oauth.py 將 `raise HTTPException(410 Gone)` 改為 feature flag
   `settings.AUTH_PASSWORD_FALLBACK_ENABLED`，且僅限管理員 IP 白名單

---

**關聯資產**：
- `backend/app/api/endpoints/auth/oauth.py:59` `/login` endpoint
- `frontend/src/pages/EntryPage.tsx:48` `SHOW_PASSWORD_LOGIN` flag
- `frontend/src/pages/LoginPage.tsx` (legacy redirect)
- `frontend/src/pages/entry/LoginPanel.tsx:82` 表單 flag 雙守護
- MEMORY `access_urls.md`（登入入口 URL 規範）
