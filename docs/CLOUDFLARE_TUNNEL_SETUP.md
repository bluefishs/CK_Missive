# Cloudflare Tunnel 部署指南（ADR-0015）

> **用途**: 取代 NemoClaw 反向代理，讓 Missive backend 安全暴露至公網。
> **依據**: ADR-0015
> **建立**: 2026-04-15

---

## 前置條件

- Cloudflare 帳號（免費方案即可）
- 已註冊網域並加入 Cloudflare DNS（例：`missive.example.com`）
- Missive backend 運行於 `localhost:8001`（PM2 託管）

---

## 安裝 cloudflared

### Windows
```powershell
winget install --id Cloudflare.cloudflared
# 或
choco install cloudflared
```

### Linux/macOS
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

---

## 步驟一：登入與建立 Tunnel

```bash
cloudflared tunnel login               # 瀏覽器開啟 CF 授權頁
cloudflared tunnel create ck-missive   # 建立 tunnel，取得 UUID
```

完成後 `~/.cloudflared/<UUID>.json` 存有憑證。

---

## 步驟二：配置檔 `~/.cloudflared/config.yml`

```yaml
tunnel: <UUID>
credentials-file: C:\Users\User1\.cloudflared\<UUID>.json

ingress:
  # Missive REST API（Telegram / Discord webhook + Hermes ACP）
  - hostname: api.missive.example.com
    service: http://localhost:8001
    originRequest:
      connectTimeout: 10s
      noHappyEyeballs: true
      httpHostHeader: api.missive.example.com

  # Missive Web UI（選用，僅開給特定團隊）
  - hostname: app.missive.example.com
    service: http://localhost:3000

  # Fallback：拒絕所有未知路由
  - service: http_status:404
```

---

## 步驟三：DNS 路由

```bash
cloudflared tunnel route dns ck-missive api.missive.example.com
cloudflared tunnel route dns ck-missive app.missive.example.com
```

---

## 步驟四：服務化啟動

### Windows（PM2）

`ecosystem.config.js` 新增：

```javascript
{
  name: 'cloudflared',
  script: 'cloudflared',
  args: 'tunnel run ck-missive',
  interpreter: 'none',
  autorestart: true,
  max_restarts: 10,
  min_uptime: '30s',
  error_file: './logs/cloudflared-error.log',
  out_file: './logs/cloudflared-out.log',
}
```

### Linux（systemd）
```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

---

## 步驟五：驗證

```bash
curl https://api.missive.example.com/api/health
# 預期: {"status":"ok", ...}

curl -X POST https://api.missive.example.com/api/ai/agent/tools \
  -H "X-Service-Token: ${MCP_SERVICE_TOKEN}"
# 預期: manifest v1.2 JSON
```

---

## 安全強化（ADR-0015 必備）

### 1. 關閉 localhost bypass

`backend/.env` 或 `ecosystem.config.js`：
```
DEVELOPMENT_MODE=false   # 不允許 MCP_SERVICE_TOKEN 缺席時的 localhost 豁免
```

### 2. Cloudflare WAF 規則

Dashboard → Security → WAF → Custom Rules：

```
# 只允許 Telegram Bot API 段（webhook 來源）
(http.host eq "api.missive.example.com" and http.request.uri.path contains "/api/telegram/webhook") 
and not (ip.src in {149.154.160.0/20 91.108.4.0/22})
→ Block

# 管理介面僅允許自家 IP
(http.host eq "app.missive.example.com") and not (ip.src in {<YOUR_OFFICE_IP>/32})
→ Block
```

### 3. Rate Limit（CF 層）

```
(http.host eq "api.missive.example.com")
→ Rate Limit: 600 req/min/IP
```

### 4. Cloudflare Access（可選，Zero-Trust）

```
管理介面 app.missive.* → Access Policy: Email OTP + Google Workspace
```

---

## Hermes Gateway 配置對齊

Hermes 若跑在本機/NAS，讀的是 `http://localhost:8001`（無需走 CF Tunnel）。
若 Hermes 跑在雲端（Modal/Daytona），才指向 `https://api.missive.example.com`：

```bash
hermes config set tools.missive.base_url https://api.missive.example.com
hermes config set tools.missive.service_token $MCP_SERVICE_TOKEN
```

---

## 回滾計畫

1. PM2 停 cloudflared：`pm2 delete cloudflared`
2. CF Dashboard 暫停 tunnel
3. Telegram/Discord webhook 回切至 ngrok 或既有 NemoClaw Nginx
4. LINE 已下線（ADR-0014），不可回滾

---

## 觀測

| 指標 | 位置 |
|---|---|
| Tunnel 健康 | `cloudflared tunnel info ck-missive` |
| 流量分析 | Cloudflare Dashboard → Analytics |
| 4xx/5xx | Missive `/api/health/detailed` + CF Security Events |
| 延遲 | Shadow Logger p50/p95（`scripts/checks/shadow-baseline-report.cjs`） |
