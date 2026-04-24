# Runbook: LINE Login 啟用 — missive.cksurvey.tw

**用途**：配合 ADR-0033 後，LINE Login 作為 Google OAuth 之外的 SSO
替代路徑。`missive.cksurvey.tw` 公網已部署，前端已配置
`VITE_LINE_LOGIN_CHANNEL_ID=2009560922` +
`VITE_LINE_LOGIN_REDIRECT_URI=https://missive.cksurvey.tw/auth/line/callback`，
本 runbook 補齊 LINE Developers Console 端設定 + 實測流程。

**前置**：
- 可存取 LINE Developers Console (https://developers.line.biz/)
- 已部署 v5.9.4+ 公網（本站 missive.cksurvey.tw）
- 已讀 `memory/line_login_domain.md`（歷史阻塞紀錄，公網域名上線後解除）

**關聯**：
- ADR-0033 關閉帳密登入
- `docs/runbooks/google-oauth-setup.md`（姊妹篇，優先設 Google）
- `frontend/.env.production:14-18` 已有 Channel ID / Redirect URI
- `backend/app/api/endpoints/auth/line_login.py` LINE OAuth callback handler

---

## 1. LINE Developers Console 確認（5-10 分）

### 1.1 開啟 Channel 設定
1. 進入 https://developers.line.biz/console/
2. 找到既有 Provider 下的 **Login Channel**（Channel ID = `2009560922`）
   - 若不存在：建立 new Provider → LINE Login Channel
   - Channel type：LINE Login（非 Messaging API）

### 1.2 授權網域（Callback URL）
點「Basic settings」→ **Callback URL** 列必須含：
```
https://missive.cksurvey.tw/auth/line/callback
http://localhost:3000/auth/line/callback   （開發機，可選）
```

LINE OAuth 2.1 規則：
- 公網必須 **https**（無例外）
- **不接受私有 IP**（192.168.x.x、10.x.x.x），這是 2026-04-10 `line_login_domain.md` 所記的阻塞點
- 可混合 localhost + 公網

### 1.3 檢查 Channel 狀態
- Channel status 必須 **Published**（非 Developing）
- OAuth scope 勾選：**profile**、**openid**、**email**（若要取得 email）
- Login button 樣式可保預設

### 1.4 複製 Channel Secret
「Basic settings」最下方 **Channel Secret** — 複製填入 `.env`。
Channel ID 已公開（`2009560922`）可入 frontend build。

---

## 2. `.env` 配置（backend）

### 2.1 編輯 `.env`
```bash
cd D:\CKProject\CK_Missive
nano .env
```

新增或確認：
```bash
# LINE Login（OAuth 2.1）
LINE_LOGIN_CHANNEL_ID=2009560922
LINE_LOGIN_CHANNEL_SECRET=<上一步複製的 Channel Secret>
LINE_LOGIN_REDIRECT_URI=https://missive.cksurvey.tw/auth/line/callback

# 前端專用（Vite build-time 注入，已在 frontend/.env.production）
VITE_LINE_LOGIN_CHANNEL_ID=2009560922
VITE_LINE_LOGIN_REDIRECT_URI=https://missive.cksurvey.tw/auth/line/callback
```

⚠️ `LINE_LOGIN_CHANNEL_ID` 必須與 `VITE_LINE_LOGIN_CHANNEL_ID`
完全一致（前後端同一 channel）。

### 2.2 Restart backend（讀新 secret）
```bash
pm2 restart ck-backend --update-env
sleep 15 && curl -sf http://localhost:8001/health | head -c 100
```

前端已在 `.env.production` 配置過，**若 frontend/dist 已 build 且 VITE 變數未變則不需重 build**。
檢查 bundle：
```bash
grep -o "VITE_LINE_LOGIN_CHANNEL_ID:\"[0-9]*\"" frontend/dist/assets/main-*.js | head -1
# 預期：VITE_LINE_LOGIN_CHANNEL_ID:"2009560922"
```

若為舊值或空，重 build：
```bash
cd frontend && npm run build && cd ..
```

---

## 3. 驗證測試

### 3.1 登入流程實測
1. 瀏覽器（無痕）開 `https://missive.cksurvey.tw/entry`
2. 應看到綠色 LINE 按鈕「使用 LINE 帳號登入」
3. 點擊 → 跳至 LINE auth page
4. 登入 + 同意授權 → 跳回 `/auth/line/callback?code=xxx&state=xxx`
5. 後端處理完轉 `/dashboard`

### 3.2 後端 log 檢查
```bash
pm2 logs ck-backend --lines 80 --nostream | grep -iE "line.*login|line.*oauth|LineLogin"
```

預期：
- `[AUTH] LINE 登入嘗試: user_name=XXX`
- `[AUTH] LINE 登入成功 user_id=N`

**紅旗訊號**：
- `LINE Login 尚未設定` → .env 的 `LINE_LOGIN_CHANNEL_ID/SECRET` 為空
- `invalid_request / redirect_uri_mismatch` → Console 的 Callback URL 未加
- `invalid_grant` → Channel Secret 過期或錯誤

### 3.3 DB 檢查新用戶
```bash
docker exec ck_missive_postgres_dev psql -U ck_user -d ck_documents \
  -c "SELECT id, email, line_id, is_active, created_at FROM users WHERE line_id IS NOT NULL ORDER BY created_at DESC LIMIT 5;"
```

---

## 4. 常見問題（FAQ）

### Q1: 「LINE Login 尚未設定」錯誤
**解法**：`.env` 的 `LINE_LOGIN_CHANNEL_ID` 和 `LINE_LOGIN_CHANNEL_SECRET`
必須同時非空；`pm2 restart --update-env` 後才讀新值。

### Q2: `redirect_uri_mismatch`
**解法**：LINE Console 的 Callback URL 列必須完全匹配前端送出的
redirect。特別留意：
- 末尾斜線有/無（`/callback` vs `/callback/`）
- https vs http
- port（公網無 port、本機要 :3000）

### Q3: 按鈕不顯示在前端
**解法**：檢查 `frontend/dist/assets/main-*.js` 是否含
`VITE_LINE_LOGIN_CHANNEL_ID:"2009560922"`；若為空或預設值，
前端 `EntryPage.tsx:50` 的 `SHOW_LINE_LOGIN = Boolean(LINE_LOGIN_CHANNEL_ID)`
會隱藏按鈕。需重 build。

### Q4: 登入後 email 取不到
**解法**：LINE Console 的 OAuth scopes 必須勾 **openid + email**
（不勾 email 時只能拿到 user_id 和 displayName）。後端
`line_login.py:_get_line_profile` 支援 id_token + Verify API 雙路徑，
但前端 scope 也要跟著改。

### Q5: 同個 LINE 帳號能重複登入
**解法**：LINE user_id 是永久的。後端 `users.line_id` 為 UNIQUE，
第二次以後自動 login（不新建 user）。若出現 UniqueViolation，檢查
遷移是否正確建 index。

### Q6: Callback 收到 code 但 token 交換失敗
**解法**：通常是 `LINE_LOGIN_REDIRECT_URI` 前後端不一致。
authorize 階段傳的 redirect_uri 必須與 token 階段傳的**完全相同**。

---

## 5. 安全檢查清單

- [ ] `LINE_LOGIN_CHANNEL_SECRET` 僅存在 prod `.env`，不入 git
- [ ] `.env` chmod 600
- [ ] Channel status = **Published**（非 Developing 測試模式）
- [ ] Callback URL 僅列正式公網域名 + 開發機（不放任何測試/暫用 URL）
- [ ] 定期（每季）到 LINE Console 檢查「登入記錄」是否有異常
- [ ] LINE user_id 是 UNIQUE，禁止 null（防空值 JOIN 錯位）

---

## 6. 回滾路徑（5 分鐘）

LINE Login 出問題時：

```bash
# Option A: 清空 Channel ID → 前端隱藏按鈕
sed -i 's/^LINE_LOGIN_CHANNEL_ID=.*/LINE_LOGIN_CHANNEL_ID=/' .env
sed -i 's/^VITE_LINE_LOGIN_CHANNEL_ID=.*/VITE_LINE_LOGIN_CHANNEL_ID=/' frontend/.env.production
cd frontend && npm run build && cd ..
pm2 restart ck-backend --update-env

# Option B: 保留 Google OAuth 作為唯一 SSO 路徑（若 Google 仍可用）
# 不需動 LINE config；user 自然會用 Google 按鈕
```

---

## 7. 與 Google OAuth 比較

| 項目 | Google OAuth | LINE Login |
|---|---|---|
| 註冊成本 | 需 GCP 帳號 + Console 設定 | 需 LINE Developer 帳號 |
| 台灣用戶覆蓋 | 約 70-80%（Android 為主） | **95%+**（市占率最高） |
| Email 取得 | 預設含 | 需勾 email scope |
| 企業帳號整合 | Workspace Domain 限制 | 個人帳號為主 |
| 推播整合 | 需額外設定 Gmail | **同 Messaging API 可推播** |
| 中國可達性 | 不可（GFW） | 可（LINE 海外） |

**建議**：兩者並存，依使用者習慣選擇；LINE 在台灣市場有絕對優勢。

---

## 關聯資產

- `backend/app/api/endpoints/auth/line_login.py` LINE OAuth callback
- `backend/app/core/config.py` `LINE_LOGIN_CHANNEL_ID/SECRET/REDIRECT_URI`
- `frontend/src/hooks/utility/useLineLogin.ts` 前端 hook
- `frontend/src/pages/EntryPage.tsx:50` `SHOW_LINE_LOGIN` 旗標
- `frontend/.env.production:14-18` 公網 build-time 配置
- `memory/line_login_domain.md` 歷史阻塞紀錄（已解除）
- `docs/adr/0033-disable-password-authentication.md` 帳密登入關閉
- `docs/LINE_BOT_SETUP_GUIDE.md` LINE Bot（不同 channel）設定
