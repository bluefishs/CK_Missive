# Runbook: Google OAuth 啟用 — missive.cksurvey.tw

**用途**：配合 ADR-0033（關閉帳密登入）後，Google OAuth 成為公網主要登入
路徑之一。此 runbook 指引 GCP Console 設定、env 配置與驗證流程。

**前置**：
- 可存取 Google Cloud Console 管理權限
- 已完成 ADR-0033 部署（v5.9.4+，`/api/auth/login` 回 410 Gone）
- 已可 SSH / RDP 到 prod 主機編輯 `.env`

**關聯**：
- ADR-0033 關閉帳密登入
- `memory/line_login_domain.md` — LINE Login 設定（本 runbook 姊妹篇）
- `frontend/src/pages/EntryPage.tsx:36-38` `GOOGLE_LOGIN_ENABLED` 旗標
- `backend/app/api/endpoints/auth/oauth.py:109` `/api/auth/google` endpoint

---

## 1. GCP Console 設定（5-10 分）

### 1.1 進入 OAuth 設定
1. 開啟 https://console.cloud.google.com/apis/credentials
2. 選專案（或新建 "CK-Missive" 專案）
3. 左側「OAuth 同意畫面」→ 若尚未設定：
   - User Type：**External**（允許所有 Google 帳號）或 Internal（限 Workspace）
   - 應用程式名稱：`CK Missive 公文管理系統`
   - 使用者支援電子郵件：admin@example.com
   - 授權網域：`cksurvey.tw`
   - 保存

### 1.2 建立 OAuth 2.0 Client ID
1. 上方「+ 建立憑證」→「OAuth 用戶端 ID」
2. 應用程式類型：**Web application**
3. 名稱：`CK Missive Production`
4. **授權的 JavaScript 來源**（Authorized origins）：
   ```
   https://missive.cksurvey.tw
   http://localhost:3000      （開發機，可選）
   http://localhost:8001      （backend-served dist，可選）
   ```
5. **授權的重新導向 URI**（Authorized redirect URIs）：
   ```
   https://missive.cksurvey.tw/auth/callback
   http://localhost:3000/auth/callback    （開發機，可選）
   ```
6. 點「建立」

### 1.3 複製憑證
彈出視窗顯示：
- **Client ID**: `xxxxxxxxx-xxxxxxx.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxxxxxxxxxxxx`

**立刻複製到安全的密碼管理器**（關閉後要重看需進 edit 才看得到 secret）。

---

## 2. 本機 `.env` 配置

### 2.1 編輯 `.env`

```bash
cd D:\CKProject\CK_Missive
nano .env   # 或任何編輯器
```

找到 Google OAuth 段並填入：

```bash
# Google OAuth
GOOGLE_CLIENT_ID=xxxxxxxxx-xxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://missive.cksurvey.tw/auth/callback

# 網域白名單（空 = 允許任何 Google 帳號；建議限公司 domain）
GOOGLE_ALLOWED_DOMAINS=cksurvey.tw,cktech.net.tw

# 新用戶控制
AUTO_ACTIVATE_NEW_USER=false    # 建議 false：管理員手動啟用
DEFAULT_USER_ROLE=user

# 前端專用（Vite build-time 注入）
VITE_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
```

### 2.2 重建前端 dist + restart backend

```bash
# 重 build frontend（VITE_GOOGLE_CLIENT_ID 是 build-time 變數）
cd frontend && npm run build && cd ..

# restart backend 讀新 env
pm2 restart ck-backend --update-env

# 等 health OK
sleep 15 && curl -sf http://localhost:8001/health | head -c 100
```

---

## 3. 驗證測試

### 3.1 本機驗證（開發）

```bash
# check client id 進 bundle
grep -o "VITE_GOOGLE_CLIENT_ID:\"[^\"]*\"" frontend/dist/assets/main-*.js | head -1
# 應顯示你的 client id（非 "your_google_client_id"）
```

### 3.2 公網驗證（實測登入流程）

1. 瀏覽器開 `https://missive.cksurvey.tw/entry`（無痕視窗避免快取）
2. 點「使用 Google 帳號登入」按鈕
3. 若跳出 Google 帳號選擇器 → **OAuth 已生效**
4. 若跳 400 / `redirect_uri_mismatch` → 檢查 GCP Console 授權 URI 是否正確（見 4.1 FAQ）
5. 選帳號、授權後應自動跳回 `/dashboard`
6. 檢查 user DB 是否有新紀錄：
   ```bash
   docker exec ck_missive_postgres_dev psql -U ck_user -d ck_documents \
     -c "SELECT id, email, is_active, created_at FROM users WHERE google_id IS NOT NULL ORDER BY created_at DESC LIMIT 5;"
   ```

### 3.3 後端 log 檢查

```bash
pm2 logs ck-backend --lines 50 --nostream | grep -E "Google.*登入|AUTH|google_oauth"
```

應看到：
- `[AUTH] Google 登入嘗試: user@example.com`
- `[AUTH] Google 登入成功 user_id=N`

**紅旗訊號**：
- `[AUTH] 網域被拒: xxx@gmail.com` → 改 `GOOGLE_ALLOWED_DOMAINS` 或設為空
- `invalid_token / aud mismatch` → GCP client ID 與 .env 不一致
- `redirect_uri_mismatch` → Console 授權 URI 漏了

---

## 4. 常見問題（FAQ）

### Q1: `redirect_uri_mismatch`
**解法**：GCP Console 「授權的重新導向 URI」必須**完全匹配**前端實際送出的 callback（含 protocol、host、port、path）。
- 公網：`https://missive.cksurvey.tw/auth/callback`（必 https）
- 本機：`http://localhost:3000/auth/callback`（無 S）
- 逗號分隔多個

### Q2: `origin_mismatch` / CORS 錯
**解法**：GCP Console 「授權的 JavaScript 來源」必須加 `https://missive.cksurvey.tw`。

### Q3: 能登入但帳號 `is_active=false` 無法進系統
**解法**：`AUTO_ACTIVATE_NEW_USER=false` 時新帳號預設停用，管理員需手動啟用：
```sql
UPDATE users SET is_active=true WHERE email='xxx@cksurvey.tw';
```
或暫時設 `AUTO_ACTIVATE_NEW_USER=true` 讓自動啟用（生產不建議）。

### Q4: 「網域被拒」
**解法**：檢查 `GOOGLE_ALLOWED_DOMAINS`：
- 空（`GOOGLE_ALLOWED_DOMAINS=`）→ 允許所有 Google 帳號
- `cksurvey.tw` → 僅 `@cksurvey.tw` 可登入
- 多 domain 用逗號：`cksurvey.tw,gmail.com`

### Q5: Google Sign-In 按鈕沒顯示
**解法**：
1. 檢查前端 build 是否含 `VITE_GOOGLE_CLIENT_ID`（不是預設 `your-actual-google-client-id...`）
2. 公網需 https（Google API 強制）
3. 檢查 browser console 是否有 CSP / 防火牆錯誤
4. Google API 中國區不可達 → EntryPage 會 5 秒自動降級隱藏按鈕（`useGoogleSignIn.ts:initializeGoogleSignIn`）

### Q6: 生產站 `VITE_GOOGLE_CLIENT_ID` 不生效
**解法**：Vite 將 env 注入**build 時**的常數。改 `.env` 後必須：
```bash
cd frontend && npm run build
# 不用 restart PM2（static 檔案自動生效），但瀏覽器需 hard refresh (Ctrl+Shift+R)
```

---

## 5. 安全檢查清單

- [ ] `GOOGLE_ALLOWED_DOMAINS` 設為公司 domain（非空字串）
- [ ] `AUTO_ACTIVATE_NEW_USER=false` 避免未授權用戶自動取得存取
- [ ] `.env` 權限 600（`chmod 600 .env`，非 world-readable）
- [ ] GCP Console OAuth 同意畫面「已發佈」（Publishing status=In production，非 Testing）
- [ ] Client Secret 非硬 code 進 repo（只在 prod .env）
- [ ] 定期（每季）檢查 GCP Console「使用的帳號」看是否有異常

---

## 6. 回滾路徑（緊急）

若 Google OAuth 出嚴重問題：

```bash
# Option A: 改 .env 清空 CLIENT_ID → 前端隱藏按鈕
sed -i 's/^GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=/' .env
cd frontend && npm run build && cd ..
pm2 restart ck-backend --update-env

# Option B: ADR-0033 reverse 路徑（極端情況）
# 參照 docs/adr/0033-disable-password-authentication.md 第 6 節
#「回滾路徑（IdP outage 緊急）」的 feature flag 方案
```

---

## 7. LINE Login 並行設定（延伸）

Google 設好後，LINE Login 同理：
- Provider：https://developers.line.biz/console/
- 授權 URI：`https://missive.cksurvey.tw/auth/line/callback`
- 配置 env：`LINE_LOGIN_CHANNEL_ID` / `LINE_LOGIN_CHANNEL_SECRET`
- 詳見 `memory/line_login_domain.md`（已知 LINE 公網 domain 阻塞中，2026-04-10 暫緩）

---

## 關聯資產

- `backend/app/api/endpoints/auth/oauth.py:109` Google OAuth endpoint
- `backend/app/core/config.py:96-97` `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `frontend/src/hooks/utility/useGoogleSignIn.ts` Sign-In 初始化
- `frontend/src/pages/EntryPage.tsx:36-38` `GOOGLE_LOGIN_ENABLED` 旗標
- `frontend/src/pages/EntryPage.tsx:110-124` `handleGoogleCallback`
- `backend/app/services/auth_service.py` `verify_google_token` / `check_email_domain`
- `docs/adr/0033-disable-password-authentication.md` 帳密登入關閉決策
