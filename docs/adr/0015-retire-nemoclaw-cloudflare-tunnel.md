# ADR-0015: 廢止 CK_NemoClaw，採 Cloudflare Tunnel 公網暴露

> **狀態**: accepted
> **日期**: 2026-04-15
> **決策者**: 專案 Owner
> **關聯**: ADR-0014（Hermes 取代 OpenClaw）, docs/CLOUDFLARE_TUNNEL_SETUP.md

## 背景

ADR-0014 通過後，OpenClaw 下線、Hermes 接管通道。此時 CK_NemoClaw 原有三項職責只剩：

1. **Docker Compose 編排** — 主要為 openclaw 服務，下線後僅剩監控
2. **Nginx 反向代理** — 供外網暴露 Missive webhook（LINE/Telegram/Discord）
3. **監控塔 :9000** — 與 Missive 自身 `/api/health/detailed` + PM2 monit 功能重疊

同時，決策採用 **Cloudflare Tunnel** 對外暴露 Missive：
- 免費 TLS 憑證（自動續期）
- 無需開 port、無公網 IP 要求
- 內建 DDoS 防護
- Zero-Trust 存取規則（可做 token 驗證）

Cloudflare Tunnel 完全覆蓋 NemoClaw 的反向代理功能，且零維運成本。

## 決策

**廢止 CK_NemoClaw repo，所有對外暴露改走 Cloudflare Tunnel**。

### 遷移範圍

| 原 NemoClaw 職責 | 替換方案 |
|---|---|
| Nginx 反向代理 | Cloudflare Tunnel (`cloudflared`) |
| Docker 編排 | 既有 `docker-compose.infra.yml`（PostgreSQL + Redis）+ PM2 |
| 監控塔 :9000 | Missive `/api/health/detailed` + PM2 monit + Cloudflare Analytics |
| openclaw 容器 | 已於 ADR-0014 下線 |

### 對外暴露清單（Cloudflare Tunnel hostname 規劃）

| Hostname | 背後 | 用途 |
|---|---|---|
| `api.missive.example.com` | `localhost:8001` | Missive REST API（Telegram/Discord webhook + Hermes ACP + 管理後台） |
| `app.missive.example.com` | `localhost:3000` | Missive Web UI（選用，僅當需要外網存取管理介面） |

> 公網暴露僅限通道 webhook 與 ACP 端點；管理介面預設僅內網。

## 後果

### 正面

- **零反向代理維運**：Cloudflare 代管 TLS + DDoS
- **零 NemoClaw repo drift**：一個 repo 移除 = 一個漂移源頭消失
- **Zero-Trust 層**：可加 Cloudflare Access 做第二層 auth
- **免費**：Cloudflare Tunnel + 自訂 subdomain 免費方案足夠
- **架構收斂**：Missive 成為唯一對外 service，命名混亂（見 `identity_clarity.md`）結束

### 負面

- **依賴 Cloudflare**：若 CF 宕機則外網不可用（但對方 SLA 高於自建）
- **失去集中監控儀表板**：需自行使用 Grafana 或 Cloudflare Analytics
- **Webhook 必須走 CF**：LINE 公網域名問題（見 `line_login_domain.md`）在 LINE 下線後自動消除，但若日後恢復需重設 webhook URL

## 替代方案

| 方案 | 排除原因 |
|---|---|
| **保留 NemoClaw 瘦身版**（方案 B） | 半活 repo 會變技術債倉；功能被 CF Tunnel 完全覆蓋 |
| **自建 Nginx + Let's Encrypt** | 維運憑證更新 + DDoS 風險，CF Tunnel 免費替代 |
| **ngrok** | 商業付費限流、URL 不穩定 |
| **Hermes 完全 serverless (Modal/Daytona)** | 本地 GPU (Gemma 4) 無法利用；成本優勢有限 |

## 實施順序（依賴 ADR-0014）

```
Day  0 (2026-04-15) ────── ADR-0015 accepted（今日）
Day  3 (2026-04-17) ────── Shadow baseline 評估通過 → Phase 1 start
Day  4 (2026-04-18) ────── Cloudflare Tunnel 安裝 + 測試 hostname 指向 Missive
Day  5 ~ 10           ────── Hermes gateway 安裝（host 直跑，不進容器）
Day 11 (2026-04-25) ────── Telegram webhook 切至 CF Tunnel URL + Hermes 處理
Day 14 ~ 17           ────── 灰度觀察
Day 18 ~ 22           ────── Discord 切換 + LINE 下線
Day 25 (2026-05-09) ────── OpenClaw 容器下線（NemoClaw 剩空殼）
Day 28 (2026-05-12) ────── 原定歸檔日 → 延展至 2026-05-26（Phase 1 軟切緩衝）
Day 42 (2026-05-26) ────── CK_NemoClaw repo 歸檔（README 指向本 ADR）

## 2026-04-17 時程修訂記錄

原 Day 28 (2026-05-12) 歸檔時程偏緊 — Phase 1 軟切（LINE bot AGENT_PRIMARY routing flag）
尚未啟動，25 天壓力窗口不足以穩定灰度。延展兩週至 2026-05-26，Phase 1 獲得
4/24–5/01 完整軟切窗口 + 5/01–5/26 灰度觀察期。
```

## 驗收標準

- [ ] Cloudflare Tunnel `api.missive.*` 能 200 回應 `/api/health`
- [ ] Telegram bot 經 CF Tunnel 成功收發訊息
- [ ] Hermes gateway 本地直跑、無需 NemoClaw
- [ ] `CK_NemoClaw/README.md` 更新為「已歸檔」標示
- [ ] Missive CLAUDE.md 移除 NemoClaw 依賴說明
- [ ] 公網暴露端點經 **POST-only + service token** 守門（延用 ADR-0014 政策）

## 安全考量

Cloudflare Tunnel 公網暴露後：
1. **強制 `MCP_SERVICE_TOKEN`** — 不再允許 localhost bypass（即使 `DEVELOPMENT_MODE=true` 也不行）
2. **WAF 規則**：Cloudflare 設定 IP allowlist（如只允許 Telegram/Discord IP 段）
3. **Rate Limit**：SlowAPIMiddleware 保持啟用；CF 層加 per-minute 規則
4. **CORS**：僅允許 Hermes gateway domain + 必要 webhook 來源
