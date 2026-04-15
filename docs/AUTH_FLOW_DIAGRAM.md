# CK_Missive 登入流程圖（AUTH_FLOW）

> **建立**：2026-04-15
> **對應代碼**：`backend/app/api/endpoints/auth/` + `backend/app/core/{auth_service,csrf,tunnel_guard,rate_limiter,mfa_service}.py`
> **對應決策**：ADR-0002（HttpOnly Cookie + CSRF）、ADR-0014（Hermes）、ADR-0015（CF Tunnel）

---

## 1. 中介軟體順序（由外到內）

```
Client 請求
    │
    ▼
┌──────────────────────────────────────┐
│ Cloudflare 邊緣（外網才經過）         │
│  • TLS + WAF                          │
│  • Access SSO（Bypass /api/* 機器流量 │
│    + /api/auth/ 登入路徑）            │
│  • Rate limit (CF 層 600/min)         │
└──────────────────────────────────────┘
    │
    ▼ via cloudflared → http://localhost:8001
┌──────────────────────────────────────┐
│ FastAPI middleware stack              │
│  1. RequestIdMiddleware               │
│  2. TunnelGuardMiddleware             │← 403 若 TUNNEL_GUARD_ENABLED
│     (check CF-Connecting-IP + path)   │  且路徑不在 ALLOWED_EXTERNAL_PATHS
│  3. CSRFMiddleware                    │← 非 GET 需 CSRF token
│  4. SecurityHeadersMiddleware         │
│  5. LoggingMiddleware                 │
│  6. GZipMiddleware                    │
│  7. CORSMiddleware                    │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Route dispatcher                      │
│  @router.post("/api/auth/google")     │
│  + @limiter.limit("10/minute")        │← 超限 429
└──────────────────────────────────────┘
    │
    ▼
Endpoint handler（見下方分流）
```

---

## 2. Google OAuth 登入流程

```
Frontend                    Backend                   Google
────────                    ───────                   ──────
LoginPage
  │
  ├─ window.google.accounts.id 載入 GIS SDK
  │
  └─ User 點擊「使用 Google 登入」
           │
           ├──► GIS 彈窗 / One-tap ─────────────────► Google
           │                                              │
           │◄─────────── credential (ID Token) ───────────┤
           │
           ▼
      authService.googleLogin(credential)
           │
           ├──► POST /api/auth/google ─────────► [TunnelGuard]
           │    Body: { credential }                │  pass（已 whitelist）
           │    Headers: X-CSRF-Token                ▼
           │                                    [CSRFMiddleware]
           │                                         │  pass（Cookie+header double-submit）
           │                                         ▼
           │                                    [rate_limiter]
           │                                         │  10/min check
           │                                         ▼
           │                                    oauth.py:google_oauth_login
           │                                         │
           │                                         ├─ verify_google_token()
           │                                         │    └─► Google tokeninfo
           │                                         │
           │                                         ├─ check_email_domain()
           │                                         │    └─ 不符 → 403 LOGIN_BLOCKED
           │                                         │
           │                                         ├─ 查 user / 建立 oauth_user
           │                                         │
           │                                         ├─ is_active? 否 → 403 ACCOUNT_INACTIVE
           │                                         │
           │                                         ├─ MFA 啟用？
           │                                         │   是 → 回 { mfa_required: true, mfa_token }
           │                                         │        → 前端轉 MFA 頁
           │                                         │
           │                                         └─ 簽 JWT → 寫 HttpOnly Cookie
           │                                                  回 { access_token, user }
           │
           │◄──── 200 { token, user }（Set-Cookie: session=...）
           │
           └─ saveAuthData() → Redux store → 導向 Dashboard
```

---

## 3. 其他登入路徑

### 3.1 LINE Login
```
前端 → LINE OAuth 彈窗 → 取得 code
    → POST /api/auth/line/callback { code, redirect_uri }
    → line_login.py:line_callback
         ├─ 交換 access_token
         ├─ 取得 profile
         ├─ 查 user / 建立
         └─ MFA 分流同 Google
```

### 3.2 帳密登入（若啟用）
```
POST /api/auth/login { email, password }
    → common.py:login
         ├─ verify_password(bcrypt)
         ├─ 失敗計數（建議加 lockout）
         ├─ MFA 分流
         └─ 簽 JWT
```

### 3.3 MFA 驗證（續 Google/LINE/帳密 mfa_required）
```
POST /api/auth/mfa/verify { mfa_token, totp_code }
    → mfa.py:verify_mfa
         ├─ 解密 mfa_token 取 user_id
         ├─ pyotp 驗證 totp_code（30 秒視窗）
         ├─ 寫 audit log
         └─ 簽 JWT
```

### 3.4 Session refresh
```
POST /api/auth/refresh（帶 HttpOnly refresh cookie）
    → session.py:refresh
         ├─ 驗 refresh_token
         ├─ rotate token（舊作廢）
         └─ 簽新 JWT
```

### 3.5 Logout
```
POST /api/auth/logout
    → 撤銷 session（DB）
    → 清 HttpOnly cookie
```

---

## 4. Session 生命週期

```
建立            → JWT + Refresh Cookie
                  audit_log: LOGIN_SUCCESS

使用            → JWT 帶 Authorization header 或 cookie
                  每 request 驗 signature + expiry

Refresh         → /api/auth/refresh (rotate)

過期            → 401 → 前端重新登入

主動登出        → /api/auth/logout → session 表 revoked=true

Admin 撤銷      → POST /api/auth/sessions/{id}/revoke

異常偵測        → login_history 比對 IP/UA，異常告警
```

---

## 5. 驗證與授權

### 5.1 Authentication（你是誰）
- JWT signature 驗證（`SECRET_KEY`）
- HttpOnly Cookie（不可被 JS 讀）

### 5.2 Authorization（你能做什麼）
- `user.role` 欄位（`user` / `admin` / `viewer`…）
- `user.permissions` JSON 陣列
- Endpoint level：`Depends(get_current_user)` + `require_role(...)`
- 跨域機器流量：`X-Service-Token`（MCP_SERVICE_TOKEN）

---

## 6. 錯誤碼速查

| 狀態碼 | 情境 | 處理 |
|---|---|---|
| 400 | Google token 無效 | 重新登入 |
| 401 | JWT 過期 / refresh 失敗 | 重新登入 |
| 403（tunnel_guard） | 外網路徑未白名單 | 加入 `ALLOWED_EXTERNAL_PATHS` |
| 403（domain_whitelist） | 網域不在允許清單 | 聯絡管理員加網域 |
| 403（is_active=false） | 帳號未啟用 | 聯絡管理員啟用 |
| 429 | Rate limit（10/min） | 稍候 |
| 500 | 服務內部錯誤 | 查 backend log |

---

## 7. 關聯 ADR

- ADR-0002：HttpOnly Cookie + CSRF 認證模式
- ADR-0003：內網 Auth Bypass（dev 便利）
- ADR-0014：Hermes 取代 OpenClaw（ACP 路徑）
- ADR-0015：CF Tunnel 取代 NemoClaw
- ADR-0016：多專案平坦分域
