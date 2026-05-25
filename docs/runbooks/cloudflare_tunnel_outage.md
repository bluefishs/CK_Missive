# Cloudflare Tunnel 故障排查 Runbook

> **觸發條件**：`missive.cksurvey.tw` 公網不可達、cloudflared 容器/PM2 service 異常
> **預估恢復時間**：5–60 分鐘
> **執行權限**：擁有 server SSH + cloudflared 配置寫入 + Cloudflare Dashboard 管理權限
> **風險等級**：HIGH（影響所有公網用戶 + LINE/Telegram webhook + Hermes 串接）
> **關聯**：ADR-0015 / ADR-0016 / `configs/cloudflare-tunnel.yml`

---

## 0. 何時觸發

| 場景 | 是否觸發本 runbook |
|---|---|
| `missive.cksurvey.tw` 用戶報「打不開」| ✅ 立即啟動 |
| 內網 `localhost:8001` 正常但公網不通 | ✅ 啟動 §2 |
| LINE webhook 收不到（Telegram 用戶反映 bot 無回）| ✅ 啟動 §3 |
| `missive.cksurvey.tw` 502 Bad Gateway | ✅ 啟動 §4（後端死了不是 tunnel 問題）|
| cloudflared service 一直 restart | ✅ 啟動 §5 |
| Cloudflare 全球性故障（status.cloudflare.com）| ❌ 等候，或臨時切其他 tunnel |

---

## 1. 第一步：定位是 Tunnel 還是 Backend 問題

```bash
# 1.1 內網直接打 backend
curl -s http://localhost:8001/api/health
# 期望：{"status":"healthy"} → backend 正常 → 問題在 tunnel
# 若失敗 → backend 死，走 backend_restart.md，本檔不處理

# 1.2 公網打看
curl -sI https://missive.cksurvey.tw/api/health
# 期望：HTTP 200
# 502 → tunnel 連得到 backend 但 backend 5xx（看 backend log）
# 530/521/522 → tunnel 自身有問題（本 runbook 範圍）
# 連線拒絕 → DNS 或 Cloudflare 邊緣有問題

# 1.3 cloudflared 服務狀態
pm2 list | grep cloudflared
# 期望：online
# 若 errored / stopped → 走 §5

# 1.4 cloudflared logs
pm2 logs cloudflared --lines 100
# 找 "Connection registered" / "ERR" / "Unauthorized"
```

---

## 2. Plan A — Tunnel 連線丟失（530/521/522）

### 2.1 重啟 cloudflared

```bash
pm2 restart cloudflared
sleep 5
pm2 logs cloudflared --lines 30 | grep -E "Connection registered|ERR"
# 期望看到 "Connection registered connIndex=0" 等多筆
```

### 2.2 重啟仍失敗 → token 過期

```bash
# 確認 token 是否還有效（去 Cloudflare Zero Trust dashboard 看）
# Settings → Access → Tunnels → <tunnel_name> → connectors

# 若 token revoked → 重產
cloudflared tunnel token <tunnel_id>  # 需登入過 cloudflared

# .env 替換 TUNNEL_TOKEN，pm2 restart cloudflared --update-env
```

### 2.3 仍失敗 → 重建 tunnel

```bash
# Cloudflare Dashboard → Zero Trust → Networks → Tunnels
# 1. Delete 舊 tunnel
# 2. Create new tunnel "missive"
# 3. 複製新 token + 設定 routing：
#    - Public hostnames: missive.cksurvey.tw → http://localhost:8001
#    - Bypass policy（必須第一順位）：cookie ck_csrf=set 等
# 4. .env 更新 TUNNEL_TOKEN
# 5. pm2 restart cloudflared --update-env
```

---

## 3. Plan B — LINE/Telegram webhook 收不到

### 3.1 確認 webhook URL 仍指向 missive.cksurvey.tw

```bash
# LINE
curl -s -X GET "https://api.line.me/v2/bot/channel/webhook/endpoint" \
  -H "Authorization: Bearer ${LINE_CHANNEL_ACCESS_TOKEN}" | jq

# Telegram
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | jq
# 重點：last_error_date / last_error_message
```

### 3.2 公網 webhook 路徑測試

```bash
# 模擬一個 POST（不會觸發業務，只測通路）
curl -X POST https://missive.cksurvey.tw/api/line-webhook \
  -H "Content-Type: application/json" \
  -d '{"events":[]}'
# 期望：200 + {"status":"ok"} 或具體業務回應
# 5xx → backend 異常
# 530/521 → tunnel 異常
# 403 → CF Access policy 阻擋（**Bypass policy 順位錯誤** — 走 §3.3）
```

### 3.3 CF Access Bypass policy 順位

**ADR-0016 關鍵**：Bypass policy 必須在第一順位，否則 LINE/Telegram webhook 會被擋。

```
Cloudflare Zero Trust → Access → Applications → missive.cksurvey.tw → Policies
順位（從上至下）：
  1. Bypass: webhook 路徑（path matches /api/line-webhook 等）  ← 必須最頂
  2. Allow: SSO 用戶
  3. Block: 其他
```

順位錯了 → 把 Bypass 拖到第一順位 → save → 等 30s 生效 → 重新測 webhook。

---

## 4. Plan C — 502 Bad Gateway（Tunnel OK 但 backend 5xx）

```bash
# Backend 是否真活？
pm2 list | grep ck-backend
curl http://localhost:8001/api/health

# 若 backend 死或 hung → 走 backend_restart.md
# 若 backend 活但回 5xx → 看 logs
pm2 logs ck-backend --lines 200 | grep -E "ERROR|exception"
```

---

## 5. Plan D — cloudflared 一直 restart（crashloop）

### 5.1 看 ecosystem.config.js 配置

```bash
cat ecosystem.config.js | grep -A 10 cloudflared
```

### 5.2 token 模式 vs config 模式

```bash
# token 模式：env TUNNEL_TOKEN
# config 模式：configs/cloudflare-tunnel.yml + credentials json

# 若兩者混用 → 必混亂；統一用 token 模式（推薦）
```

### 5.3 跑 cloudflared 在 foreground 看 stderr

```bash
# 暫停 PM2，手動跑
pm2 stop cloudflared
cloudflared tunnel run --token ${TUNNEL_TOKEN}
# 看完整 startup error
```

---

## 6. 監控與預防

### 6.1 加常駐 watchdog

```bash
# scripts/health/cf_tunnel_watchdog.sh （建議建立）
while true; do
  if ! curl -sf -o /dev/null https://missive.cksurvey.tw/api/health; then
    echo "$(date): missive.cksurvey.tw unhealthy" | tee -a logs/cf-tunnel-watchdog.log
    # 觸發 LINE notify
    curl -X POST "${LINE_NOTIFY_URL}" -H "Authorization: Bearer ${LINE_NOTIFY_TOKEN}" \
      -d "message=⚠ missive.cksurvey.tw 不可達"
  fi
  sleep 60
done
```

### 6.2 Prometheus 監控（建議補）

```yaml
# 加 cloudflared blackbox exporter 監控
# configs/prometheus/cf_tunnel_alert.yml
- alert: CloudflareeTunnelDown
  expr: probe_success{job="cf_tunnel_health"} == 0
  for: 5m
  labels:
    severity: critical
```

### 6.3 月度演練

每月手動執行一次 `pm2 stop cloudflared` 30 秒 → 確認：
- Watchdog 有觸發告警
- 用戶端不會卡死（前端應有 retry / fallback UX）
- LINE webhook backlog 自動補送（或紀錄遺失）

---

## 7. 事故後檢討

24 小時內：
- 寫 `wiki/memory/failures/failure-cf-tunnel-<date>.md`
- 補 LESSON 至 `docs/architecture/LESSONS_REGISTRY.md`
- 量化 MTTR（從 alert 觸發 → 服務恢復）
- 若 MTTR > 30min → 評估 §6.1 watchdog 是否需更激進

---

## 附：相關資產

- `docs/adr/0015-retire-nemoclaw-cloudflare-tunnel.md`
- `docs/adr/0016-multi-project-platform-subdomain.md`
- `configs/cloudflare-tunnel.yml`
- `ecosystem.config.js` cloudflared 配置區塊
- `CK_AaaP/runbooks/cloudflare-setup.md`（部署側）
- `docs/runbooks/backend_restart.md`（backend 死的後續流程）

> **首要原則**：Tunnel 死的時候，**先確認是 tunnel 還是 backend**（§1）。混判會多花 20 分鐘。
