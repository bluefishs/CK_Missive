# Telegram 個人號永封應急預案 Runbook

> **觸發條件**：Telegram 個人號（Aroan）再次被封禁、或 Bot @Aaron_ckbot 被官方 ban
> **預估恢復時間**：30 分–4 小時（看採用方案）
> **執行權限**：擁有 .env 寫入 + pm2 restart 的人員
> **風險等級**：MEDIUM（用戶體驗暫時降級，不影響核心業務）
> **關聯**：ADR-0027 / `telegram_content_sanitizer.py`

---

## 0. 背景脈絡

2026-04-21 Telegram 個人號 Aroan 被封禁（官方申訴駁回），ADR-0027 已落地：
- `TELEGRAPH_ADMIN_PUSH_ENABLED=false` 關所有主動 push
- LINE 成為主要 admin push 通道
- Telegram bot @Aaron_ckbot 維被動 webhook 備援
- `telegram_content_sanitizer.py` 自動 mask PII

**本 runbook 處理「下一次 Telegram 通道完全失效」場景**，不是當下事故。

---

## 1. 何時觸發

| 場景 | 是否觸發本 runbook |
|---|---|
| Telegram bot webhook 偶發 5xx < 1 hr | ❌ 等候自動恢復 |
| Telegram bot webhook 持續 502/503 ≥ 1 hr | ✅ 啟動 §2 |
| @Aaron_ckbot 被 Telegram 官方 ban（API 401）| ✅ 啟動 §3 |
| 個人號 Aroan 被再次封禁（已關 push，影響低）| ✅ 啟動 §4 監測 |
| LINE 同時也斷 → Telegram 反成單一通道 | ✅ 啟動 §5 緊急恢復 |

---

## 2. Plan A — Webhook 5xx 持續 ≥ 1 hr

### 2.1 確認狀態

```bash
# 看 webhook 訊息
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
# 期望：last_error_date 是近期 + last_error_message 顯示 5xx

# 看 backend log 接收狀況
pm2 logs ck-backend --lines 500 | grep -E "telegram_webhook|TG webhook"

# Prometheus 看 webhook 計數（5min rate）
curl -s http://localhost:8001/metrics | grep "http_requests_total.*telegram"
```

### 2.2 Webhook URL 重設

```bash
# 確認 .env 中的 TELEGRAM_WEBHOOK_URL 正確
grep TELEGRAM_WEBHOOK_URL .env

# 重新註冊 webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${TELEGRAM_WEBHOOK_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

### 2.3 Cloudflare Tunnel 確認

若 Cloudflare Tunnel 同時不通 → 走 `cloudflare_tunnel_outage.md`，本檔不重複。

---

## 3. Plan B — @Aaron_ckbot 被官方 ban（API 401）

### 3.1 確認 ban

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
# 401 + description: "Unauthorized" → 確認 ban
```

### 3.2 暫時切 LINE-only

```bash
# .env 開關（已是 ADR-0027 預設值，這裡確認）
TELEGRAM_ADMIN_PUSH_ENABLED=false
TELEGRAM_WEBHOOK_ENABLED=false  # 新增 — 完全關閉接收

pm2 restart ck-backend --update-env
```

### 3.3 申訴 + 觀察 7 天

- Telegram 官方申訴：https://telegram.org/support
- 如駁回 → 走 §3.4 重建 bot

### 3.4 重建新 bot（last resort）

```bash
# 1. 找 @BotFather 建新 bot（命名避開觸發詞）
#    /newbot → 取得 new_token

# 2. .env 替換
TELEGRAM_BOT_TOKEN=<new_token>
TELEGRAM_BOT_USERNAME=@<new_bot_username>

# 3. 註冊新 webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${TELEGRAM_WEBHOOK_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"

# 4. 通知所有用戶舊 bot 失效，啟用新 bot 帳號
#    用 LINE 通知 + diary 紀錄
```

---

## 4. Plan C — 個人號 Aroan 再次被封禁

ADR-0027 已預防 — 個人號封禁**不影響核心業務**：
- `TELEGRAM_ADMIN_PUSH_ENABLED=false` 主動 push 早就關
- Bot @Aaron_ckbot 為被動接收 webhook，不依賴個人號
- LINE 是主要 admin push 通道

**只需做**：
1. 寫 diary `wiki/memory/diary/<today>.md` 記錄事件
2. 確認 LINE notify 正常（`scripts/checks/line_notify_heartbeat_check.py`）
3. 不重啟系統，不切換通道

---

## 5. Plan D — LINE + Telegram 同時失效（雙通道斷）

**罕見但最痛**：兩條通道都死，admin push 完全 silent。

### 5.1 立即降級

```bash
# 啟用 email fallback（若已配置）
ENABLE_EMAIL_ADMIN_PUSH=true
ADMIN_EMAIL=jujuiacc@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<gmail_account>
SMTP_PASS=<app_password>

pm2 restart ck-backend --update-env
```

### 5.2 確認 Prometheus alert 仍能收到

```bash
# 直接 curl Alertmanager
curl http://localhost:9093/api/v1/alerts | jq '.data[] | select(.labels.severity=="critical")'

# 或開 Grafana dashboard 直觀看
```

### 5.3 緊急恢復至少一條通道（依事故根因走 Plan A/B 或 line-login-setup.md）

---

## 6. PII 衛生檢查（每月）

```bash
# 跑 sanitizer regression
cd backend && python -m pytest tests/unit/test_telegram_content_sanitizer.py -v

# 預期 14 tests passed（身分證/手機/email/長編號 mask）
```

---

## 7. 事後檢討

事故後 24 小時內：
- 寫 `wiki/memory/failures/failure-telegram-<date>.md`
- 補 LESSON 至 `docs/architecture/LESSONS_REGISTRY.md`
- 評估是否要建第三通道（Discord、Slack、Email）

---

## 附：相關資產

- `docs/adr/0027-telegram-personal-ban.md`
- `backend/app/services/integration/telegram_bot.py`
- `backend/app/services/integration/telegram_content_sanitizer.py`
- `backend/app/core/admin_push_metrics.py` — 連續失敗計數器
- `configs/prometheus/alerts.yml` — `AdminPushConsecutiveFailures` rule

> **首要原則**：通道應**多供應**設計（L15 lesson）。任何通道失效應該降級而非中斷服務。
