# CK_Missive 安全威脅模型（STRIDE）

> **建立**：2026-04-15
> **方法論**：STRIDE（Spoofing / Tampering / Repudiation / Info Disclosure / DoS / Elevation of Privilege）
> **適用範圍**：CK_Missive 後端 / 前端 / 整合通道 / 部署鏈
> **前置閱讀**：`AUTH_FLOW_DIAGRAM.md`、`ARCHITECTURE_REVIEW_2026-04-15.md`

---

## 1. 系統邊界與資產

### 1.1 信任邊界

```
┌─────────────────────────────────────────────────────────┐
│ T1：網際網路（完全不信任）                                │
│      ↓                                                   │
│ T2：Cloudflare 邊緣（TLS + WAF + Access）                │
│      ↓                                                   │
│ T3：cloudflared tunnel（outbound-only）                  │
│      ↓                                                   │
│ T4：本機 PM2 host（localhost 內部信任）                  │
│      ├─ FastAPI backend                                  │
│      ├─ Postgres / Redis 容器                            │
│      └─ 第三方服務出站（Google / Telegram / Groq / CF）  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 關鍵資產

| 資產 | 機密性 | 完整性 | 可用性 |
|---|---|---|---|
| 公文資料庫（postgres） | **高** | **高** | 高 |
| 使用者帳號 / JWT secret | **高** | **高** | 中 |
| `.env`（MCP_SERVICE_TOKEN、CF_TUNNEL_TOKEN、DB 密碼、API keys） | **極高** | **高** | 中 |
| KG 向量資料（pgvector 768D） | 中 | **高** | 中 |
| 審計日誌（audit_log） | 中 | **極高**（不可篡改） | 中 |
| 通訊通道 token（Telegram / LINE / Discord） | **高** | **高** | 中 |

---

## 2. STRIDE 分析

### S — Spoofing（偽造身份）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| S1 | 偽冒使用者 Google token | Google token signature 驗證 + `GOOGLE_ALLOWED_DOMAINS` | **網域白名單生產未設 → 中** | **高** |
| S2 | JWT 偽造 | HS256 + `SECRET_KEY` 長度足 | `SECRET_KEY` 若為 dev 預設值會被警告但不阻擋 | 中 |
| S3 | Session cookie 竊取 | HttpOnly + Secure + SameSite=Lax | 若客戶端有 XSS 仍可能被惡意擴充套件讀 | 低 |
| S4 | 偽冒機器服務（X-Service-Token） | 常數時間比對 + 雙 token 輪替 | token 若洩漏至 log 仍可被利用 | 中 |
| S5 | Google 帳號被接管後登入 | MFA（TOTP） | **MFA 非強制** | 中 |

### T — Tampering（竄改）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| T1 | SQL injection | SQLAlchemy ORM + parameterized | 任何 raw query 為潛在風險 | 低 |
| T2 | Request 竄改（中間人） | CF 邊緣 TLS | 內部 HTTP 明文（已決策暫不 mTLS） | 低（單機） |
| T3 | JWT payload 竄改 | Signature 驗證 | `alg:none` 攻擊 — 需確認 jwt library 已擋 | 中 |
| T4 | CSRF | `CSRFMiddleware` + double-submit | GET 端點狀態變更（若有）未受 CSRF 保護 | 中 |
| T5 | File upload 竄改 | 檔案類型白名單 | 需確認 MIME 驗證 + 掃毒 | 中 |
| T6 | KG entity 污染 | `CrossDomainLinker` + contribute 驗 token | 來源 worker 被接管可注入 | 中 |

### R — Repudiation（否認）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| R1 | 使用者否認登入 | `audit_log`（login_success/blocked/attempt） | 日誌被篡改 → 建議 append-only 或外送 | 中 |
| R2 | Admin 否認撤銷 session | session 表 revoked_at 記錄 | 同上 | 低 |
| R3 | KG 變更否認 | KG contribute 有來源 domain + commit hash | 合理 | 低 |

### I — Information Disclosure（資訊洩漏）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| I1 | `.env` 誤 commit | `.gitignore` + pre-commit secret-guard | 若 hook 未安裝、強 push 仍可能 | 低 |
| I2 | Secret 入 git 歷史 | 無 | **CK_PileMgmt 已發生** | **高**（跨專案警示） |
| I3 | 錯誤訊息洩漏 internal path | 通用錯誤訊息 | 部分 500 仍回 stack trace — 需審 | 中 |
| I4 | Log 誤印 token | `Redis URL masking` 等部分 | 全面掃描待做 | 中 |
| I5 | `docker inspect` 看到 env | 無（現行 env 模式）| 已決策暫不 Docker Secrets | 低 |
| I6 | 備份外洩 | 備份腳本 pg_dump 至 `/backups` | 備份加密未實作 | 中 |
| I7 | `/api/agents/` `/api/schemas/` 洩漏路由 | ✅ 本日加 `X-Service-Token`（NemoClaw） | 已修 | — |
| I8 | CORS 過寬 | `allowed_origins` 121 個 | 建議審視，移除無用 origin | 中 |

### D — Denial of Service（服務阻斷）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| D1 | 登入 brute force | `@limiter.limit("10/minute")` + CF rate limit | OK | 低 |
| D2 | JSON 大包攻擊 | 需確認 FastAPI max body | 待審 | 中 |
| D3 | AI/LLM 端點爆量（昂貴） | rate_limiter | 需確認 AI 端點 rate 較嚴 | **高**（成本） |
| D4 | Slowloris / 慢連接 | CF 邊緣、uvicorn timeout | OK | 低 |
| D5 | pgvector 慢查詢 | 需 index + LIMIT | 已有，建議加 timeout | 中 |

### E — Elevation of Privilege（權限提升）

| # | 威脅 | 現況防護 | 殘留風險 | 優先 |
|---|---|---|---|---|
| E1 | 帳號 role 欄位篡改 | ORM 欄位 + API 層擋 | 直 DB 存取（若 DB 密碼洩漏）可改 | 中 |
| E2 | MFA 繞過 | `mfa_token` 有 signature | 邏輯漏洞 → 需審 `verify_mfa` flow | 中 |
| E3 | Dev bypass `AUTH_DISABLED=true` 被生產誤啟用 | config 啟動警告 | **警告非阻擋** | **高** |
| E4 | NemoClaw `ALLOW_NO_AUTH=1` 誤啟用 | 本日已加 503 預設 | OK | — |
| E5 | Container escape | Docker 隔離 | 需最新 patch | 低 |
| E6 | IDOR（存他人文件 ID） | endpoint 層需驗 user owns resource | 需逐 endpoint 審 | 中 |

---

## 3. Top 5 最高優先威脅與建議

| 排名 | 威脅 ID | 標題 | 建議行動 |
|---|---|---|---|
| 1 | S1 | Google 網域白名單未設 | 生產 `GOOGLE_ALLOWED_DOMAINS=<允許網域>` 立即設定 |
| 2 | E3 | `AUTH_DISABLED=true` 可能生產誤啟用 | 啟動時硬失敗（非警告）若 DEVELOPMENT_MODE=false 但 AUTH_DISABLED=true |
| 3 | D3 | AI/LLM 端點爆量成本 | 對 `/api/ai/*` 加更嚴 rate limit + 每日配額 |
| 4 | I2 | Git 歷史留密碼（PileMgmt 已發生） | 導入 secret scanning CI（gitleaks / truffleHog） |
| 5 | S5 | MFA 非強制 | 管理員角色強制 MFA；普通 user 建議引導 |

---

## 4. 持續監控指標

| 指標 | 位置 | 告警閾值 |
|---|---|---|
| 登入失敗率 | audit_log | >5/分 同 IP |
| Rate limit 觸發 | Prometheus | 短時間大量 429 |
| `previous_token_used` 計數 | nemoclaw log | 輪換後應降至 0 |
| 503 AUTH_UNCONFIGURED | nemoclaw log | 任一發生即告警 |
| HTTP 5xx | Prometheus | >1% |
| Postgres 慢查詢 | pg_stat_statements | 查詢 > 1s |
| Disk usage（備份） | monitoring | >80% |

---

## 5. 重新評估觸發條件

本威脅模型應**每半年**或以下事件觸發重審：
- 新的通訊通道 / 第三方整合上線
- 登入流程重大變更
- 出現資安事件（即使未造成損害）
- 法規要求變動
- 部署模式改變（host mode → K8s 等）

---

## 6. 變更歷史

| 日期 | 變更 |
|---|---|
| 2026-04-15 | 初版 — STRIDE 首次盤點 |
