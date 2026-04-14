# Cloudflare Tunnel — cksurvey.tw 部署步驟

> **專案實例**: ADR-0015 落地配置
> **域名**: `cksurvey.tw`（Gandi 註冊）
> **公網入口**: `https://api.cksurvey.tw` → `localhost:8001`
> **建立**: 2026-04-15

---

## 階段一：DNS 遷移至 Cloudflare（一次性，約 10 分鐘）

1. 登入 https://dash.cloudflare.com → **Add a Site**
2. 輸入 `cksurvey.tw` → Free plan → Continue
3. Cloudflare 會給兩組 nameserver，例：
   ```
   sam.ns.cloudflare.com
   lara.ns.cloudflare.com
   ```
4. 登入 https://admin.gandi.net → Domain → `cksurvey.tw` → Nameservers
5. 移除 Gandi 預設 NS，改填 CF 兩組 NS，儲存
6. 回 Cloudflare Dashboard → Check Nameservers（等 Active 狀態，通常 10–30 分鐘）

## 階段二：Tunnel 建立（Dashboard 模式）

1. Cloudflare Dashboard → **Zero Trust** → Networks → **Tunnels** → Create a tunnel
2. Tunnel type: `Cloudflared`
3. Name: `ck-missive`
4. 完成後取得 **Tunnel Token**（32 hex 字串，**絕不入版控**）
5. Public Hostname 設定：
   | Subdomain | Domain | Service |
   |---|---|---|
   | `api` | `cksurvey.tw` | `http://localhost:8001` |

## 階段三：本機安裝與啟動

### 1. 安裝 cloudflared（Windows）

```powershell
winget install --id Cloudflare.cloudflared
cloudflared --version
```

### 2. Token 寫入 `.env`（僅本機、已 gitignore）

在專案根目錄 `.env` **末尾追加**（不要貼到任何 commit）：

```
CF_TUNNEL_TOKEN=<從 Dashboard 複製的 32 hex token>
```

### 3. PM2 啟動

```powershell
pm2 reload ecosystem.config.js  # 會自動偵測 CF_TUNNEL_TOKEN 並啟 cloudflared
pm2 list                         # 應見 cloudflared online
pm2 logs cloudflared --lines 30  # 應見 "Registered tunnel connection"
```

## 階段四：驗證（smoke test）

### 瀏覽器
```
https://api.cksurvey.tw/api/health
→ {"status":"ok", ...}
```

### 終端機（帶 token）
```powershell
$env:MISSIVE_PUBLIC_URL = "https://api.cksurvey.tw"
$env:MCP_SERVICE_TOKEN  = "<your service token>"
cd backend
python -m pytest tests/integration/test_public_exposure_smoke.py -v
```

預期 6 個 smoke tests 全 PASSED。

## 階段五：資安強化

### 1. 關閉 localhost bypass

`.env`：
```
DEVELOPMENT_MODE=false
```

### 2. Cloudflare WAF 規則

Dashboard → `cksurvey.tw` → Security → WAF → Custom Rules：

**規則 1：管理介面 IP allowlist（若開 app.cksurvey.tw）**
```
(http.host eq "app.cksurvey.tw") and not (ip.src in {<您的辦公室 IP>/32})
→ Block
```

**規則 2：API rate limit**
```
(http.host eq "api.cksurvey.tw")
→ Rate Limit: 600 req/min/IP
```

**規則 3：Telegram webhook IP 限制（Phase 2 切換後）**
```
(http.request.uri.path contains "/api/telegram/webhook") 
  and not (ip.src in {149.154.160.0/20 91.108.4.0/22})
→ Block
```

## 階段六：Webhook 切換（Phase 2，Day 11 起）

### Telegram
```powershell
$env:TG_TOKEN = "<your bot token>"
curl -X POST "https://api.telegram.org/bot$($env:TG_TOKEN)/setWebhook" `
  --data "url=https://api.cksurvey.tw/api/telegram/webhook"
```

### Discord
Discord Developer Portal → Application → General Information → **Interactions Endpoint URL**：
```
https://api.cksurvey.tw/api/discord/interactions
```

## 回滾

```powershell
pm2 delete cloudflared
# Webhook 回切至 ngrok 或既有 NemoClaw URL（過渡期）
```

---

## 常見問題

**Q: DNS 遷移後原本 Gandi 的 email 還能用？**
A: Gandi 提供的 email 仍正常（MX record 可保留）。DNS 遷至 CF 時記得把 Gandi 的 MX record 一併複製到 CF DNS。

**Q: Tunnel token 外洩怎辦？**
A: Dashboard → Networks → Tunnels → `ck-missive` → **Delete tunnel** → 重建新的 tunnel，用新 token 更新 `.env`。

**Q: 為什麼用 Token 模式而非 Config 模式？**
A: Token 模式由 Dashboard 管理，路由設定可視化；Config 模式需手動維護 yml 與 credentials 檔。Token 模式對少量 service 更簡單。

---

## 觀測

| 指標 | 位置 |
|---|---|
| Tunnel 狀態 | CF Dashboard → Zero Trust → Networks → Tunnels |
| 流量/延遲/錯誤 | CF Dashboard → Analytics → `cksurvey.tw` |
| 本機 cloudflared 日誌 | `backend/logs/cloudflared-*.log` |
| 後端回應延遲 | Shadow Logger（`scripts/checks/shadow-baseline-report.cjs`） |
