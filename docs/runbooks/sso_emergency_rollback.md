# SSO 緊急回滾 Runbook

> **觸發條件**：Google + LINE 同時不可達，或 ADR-0033 後發現大量用戶被永久鎖死
> **預估恢復時間**：5–15 分鐘（含 deploy）
> **執行權限**：擁有 server SSH + git push + pm2 restart 的人員
> **風險等級**：HIGH（暫時開啟密碼登入 = 重新引入 ADR-0033 規避的風險）

---

## 0. 何時觸發

| 場景 | 是否觸發本 runbook |
|---|---|
| Google OAuth 服務中斷 < 30 分 | ❌ 等候即可（Google SLA 通常自動恢復）|
| LINE OAuth 中斷 < 30 分 | ❌ 等候 |
| Google + LINE 同時中斷 > 30 分 | ✅ 啟動 |
| Cloudflare Tunnel 中斷（用戶連不到 missive） | ❌ 走 ADR-0015 runbook，非本檔範圍 |
| 用戶報「我登入不了，但其他人可以」 | ❌ 走「個人 SSO 解綁」流程，非本檔範圍 |
| Owner 自己也鎖在外面（id=1 SuperUser 無 SSO） | ✅ 啟動（Plan B：直接 DB 補綁） |

## 1. 觸發前先確認（5 分鐘）

```bash
# 1. 跑 IdP connectivity check
python scripts/checks/idp_connectivity_check.py
# 期望：2/2 OK；若兩個都 FAIL → 確認觸發

# 2. 跑 SSO coverage check
python scripts/checks/sso_coverage_check.py
# 看 admin 級鎖死帳號清單

# 3. 確認自己有 server access
ssh <server> 'pm2 list | grep ck-backend'
```

## 2. Plan A — 暫時恢復密碼登入（建議首選）

### 2.1 reverse ADR-0033 的 endpoint
```bash
cd /path/to/CK_Missive
git log --oneline backend/app/api/endpoints/auth/oauth.py | head -5
# 找到 ADR-0033 commit hash（commit 8537ba95 之前）

# 暫時 revert 該 commit 的 oauth.py 部分（只動 login endpoint，不動 google/line）
git show <ADR-0033-commit>:backend/app/api/endpoints/auth/oauth.py > /tmp/oauth_old.py
# 手動把 login 段落從舊版貼回，保留新增的 SSO 邏輯
```

### 2.2 部署 + 監控
```bash
# Restart backend
pm2 restart ck-backend --update-env

# 監看 login 嘗試
pm2 logs ck-backend | grep -E "LOGIN_|password"

# 鎖定範圍 — 加 IP whitelist（僅辦公室 IP 可用密碼）
# 在 backend/app/core/rate_limiter.py 加：
#   if request.path == '/api/auth/login' and not is_office_ip(request.client.host):
#       raise HTTPException(403)
```

### 2.3 通知
- LINE notify 推送：「SSO 暫時不可用，已開啟臨時密碼登入；待 IdP 恢復後關閉」
- 寫 wiki/memory/diary/<today>.md 記錄事件

### 2.4 IdP 恢復後關閉密碼登入
```bash
git revert <暫時 reverter 的 commit>
pm2 restart ck-backend
# 跑驗證
python scripts/checks/idp_connectivity_check.py --ci
```

## 3. Plan B — DB 直接補綁 SSO（適用單一 admin 鎖死）

當問題只是「id=1 SuperUser 無 SSO」而非 IdP 整體中斷：

```bash
# Step 1：在另一個有 SSO 的 admin 帳號上 google login，記下 google_id
# 取自 backend log: "[AUTH] Google 登入嘗試: <email>"
# 或從 oauth callback 解 token

# Step 2：DB 直接寫入
psql $DATABASE_URL -c "
  UPDATE users
  SET google_id = '<google_sub_from_token>', auth_provider = 'google'
  WHERE id = 1;
"

# Step 3：用該 Google 帳號登入測試
```

**警告**：直接寫入 DB 跳過審計與正常綁定流程，事後務必補 audit log：
```sql
INSERT INTO audit_logs (event_type, user_id, details, success, created_at)
VALUES ('EMERGENCY_SSO_BIND', 1, '{"reason": "ADR-0033 lockout recovery"}', TRUE, NOW());
```

## 4. Plan C — Break-glass 帳號（建議常設）

> 建議**事先**保留 1 個緊急帳號 + 強保護，而非事到臨頭才建。

### 建立步驟
```sql
INSERT INTO users (
  email, username, full_name, password_hash, role,
  is_admin, is_superuser, is_active, auth_provider, mfa_enabled
) VALUES (
  'breakglass@cksurvey.tw',
  'breakglass',
  'Break-Glass Emergency Admin',
  '<bcrypt hash of strong password>',
  'superuser', TRUE, TRUE, FALSE,  -- ⚠ is_active=FALSE 平時關閉
  'email', TRUE  -- MFA 強制
);
```

### 啟用條件（嚴格）
- IP whitelist：僅辦公室固定 IP 可登入
- MFA 強制：TOTP 必填
- 平時 `is_active=FALSE`，只在啟動 runbook 時 `UPDATE is_active=TRUE`
- 每次啟用必發 LINE notify 給所有 admin
- 用畢立刻 `is_active=FALSE` + 改密碼

## 5. 事後檢討（24 小時內）

- 寫 `wiki/memory/failures/failure-sso-outage-<date>.md`
- 跑 `python scripts/checks/sso_coverage_check.py` 確認鎖死帳號數 → 0
- 補 LESSON 到 `docs/architecture/LESSONS_REGISTRY.md`
- 評估是否要永久建立 Plan C 帳號

## 6. 預防措施（治理）

| 措施 | 頻率 | 工具 |
|---|---|---|
| SSO 覆蓋率檢查 | 月 | `scripts/checks/sso_coverage_check.py` |
| IdP connectivity 監控 | 日（cron）| `scripts/checks/idp_connectivity_check.py` |
| Admin 帳號 SSO 綁定強制 | 部署前 | `--ci` 模式接 deployment gate |
| Break-glass 帳號審計 | 季 | 手動 DB query |

---

## 附：相關 ADR 與資產

- `docs/adr/0033-disable-password-authentication.md`
- `docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md`
- `wiki/memory/failures/failure-adr-0025-rls-half-wired.md`（同類事故參考）

> **首要原則**：無論採哪 Plan，**先恢復服務再追根因**。事故時用戶痛感優先。
