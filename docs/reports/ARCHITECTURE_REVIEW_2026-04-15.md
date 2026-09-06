# CK_Missive 架構覆盤與建議（2026-04-15）

> **建立**：2026-04-15
> **範圍**：本次對 CK_Missive 主專案的架構健檢、登入/防護機制評估、bug 修復紀錄、整體優化建議
> **前次覆盤**：NemoClaw 2026-03-25 架構覆盤 7.8/10

---

## 一、本次發現 / 修復

### 1.1 公文系統「API 無回應」bug（已修復）
- 症狀：Telegram 管理員每 5 分鐘告警「Expecting value: line 1 column 1 (char 0)」
- 根因：`main.py` SPA catch-all `@app.get("/{spa_path:path}")` 搶先匹配 `/health`，後方重複定義永不生效
- 修法：`/health` 路由搬到 SPA mount 前；刪後方重複；`health.py` 12 個 POST→GET 修正（原皆誤設 POST）
- 驗證：`curl /health` 回 JSON 200 ✅

### 1.2 Google 登入 403 bug（已修復）
- 症狀：`POST /api/auth/google` 403
- 根因：`TunnelGuardMiddleware` 當 `TUNNEL_GUARD_ENABLED=true` + 請求帶 `CF-Connecting-IP` header 時，若路徑不在 `ALLOWED_EXTERNAL_PATHS` 一律 403。`/api/auth/google` 不在白名單
- 修法：
  - `tunnel_guard.py:ALLOWED_EXTERNAL_PATHS` 加入 `/api/auth/`（涵蓋 google/line/login/logout/refresh/mfa 等）
  - `docs/CLOUDFLARE_ACCESS_BYPASS.md` Bypass Policy 補 `/api/auth/` Path 規則
  - `CK_AaaP/CK_AaaP_Cloudflare_Setup_Guide.md` 同步更新
- **仍須您操作**：CF Dashboard → Zero Trust → Access → Applications → CK Platform → Policies → `Machine Traffic Bypass` → 新增 Path `/api/auth/`

---

## 二、登入流程與防護機制評估

### 2.1 組件清單

**後端 `backend/app/api/endpoints/auth/`**：
- `oauth.py` — Google OAuth login
- `line_login.py` — LINE Login OAuth
- `mfa.py` — TOTP 雙因素
- `password_reset.py` — 忘記密碼
- `email_verify.py` — Email 驗證
- `session.py` / `sessions.py` — Session 管理
- `login_history.py` — 登入歷史
- `common.py` — 共用登入（帳密）
- `profile.py` — 個人資料

**後端核心模組**：
- `auth_service.py` — 核心認證
- `mfa_service.py` — MFA 產生/驗證
- `csrf.py` — CSRF 防護（ADR-0002 HttpOnly Cookie）
- `rate_limiter.py` — 頻率限制
- `security_headers.py` — 安全 HTTP headers
- `security_utils.py` — 加密工具
- `domain_whitelist.py` — Google 網域白名單
- `tunnel_guard.py` — 外網路徑白名單守衛

**Middleware 棧（由外到內）**：
```
RequestIdMiddleware
  ↓
TunnelGuardMiddleware   ← 擋非白名單外部路徑
  ↓
CSRFMiddleware           ← CSRF token 驗證
  ↓
SecurityHeadersMiddleware ← X-Frame-Options / CSP 等
  ↓
LoggingMiddleware        ← 結構化日誌
  ↓
GZipMiddleware
  ↓
CORSMiddleware
  ↓
Endpoint
```

### 2.2 防護評估

| 項目 | 現況 | 評等 |
|---|---|---|
| 密碼學 | JWT + HttpOnly Cookie（ADR-0002） | ✅ 優 |
| CSRF | 專用 middleware + double-submit token | ✅ 優 |
| Session | 可撤銷、有歷史 | ✅ 優 |
| MFA | TOTP 已實作 | ✅ 優 |
| 網域白名單 | `GOOGLE_ALLOWED_DOMAINS` | ⚠️ 生產未設 |
| Rate limit | `@limiter.limit("10/minute")` at endpoint | ✅ 良 |
| Tunnel guard | 白名單 + 可開關 | ✅ 良（本次修補完整） |
| Audit log | `AuditService.log_auth_event` 覆蓋 login / block | ✅ 優 |
| 登入失敗計數 / 鎖定 | 需確認 | ⚠️ 待驗 |
| 密碼複雜度規則 | 需確認 | ⚠️ 待驗 |
| Session fixation | JWT 模式免疫 | ✅ |
| OAuth state/nonce（CSRF） | Google Credential 模式帶 nonce | ✅ |
| 明文傳輸 | 公網走 CF TLS；內網 HTTP | ⚠️ 已決策暫不 mTLS |
| Secret 管理 | `.env` + gitignore + pre-commit hook（剛增強） | ✅ 中 |

### 2.3 風險清單（優先級）

| # | 風險 | 嚴重度 | 建議 |
|---|---|---|---|
| R1 | `DEVELOPMENT_MODE=true` 當前為 true（本機 .env） | 中 | 生產 .env 確認為 false（CF Tunnel 設定指南已標註） |
| R2 | `GOOGLE_ALLOWED_DOMAINS` 空 → 允許任意 Google 帳號 | 高（公網上線後） | 上線前設定允許網域列表（如 `cksurvey.tw,partner.com`） |
| R3 | `AUTH_DISABLED=true` 曾見於 log 警告訊息 | 高（若生產也如此） | 生產 .env 驗證 `AUTH_DISABLED=false` |
| R4 | 登入頁 `/` 若未走 CF Access SSO，登入端點暴露廣 | 中 | 已有 rate limit，但建議加 failed-attempt lockout |
| R5 | MFA 是否預設啟用未確認 | 中 | 建議新用戶強制啟用或高權角色強制 |
| R6 | CSRF token 取得路徑本身是否受保護 | 中 | 驗證 CSRF endpoint 在 tunnel_guard 白名單 |

---

## 三、系統文件盤點

### 3.1 文件覆蓋度（CK_Missive/docs/）

| 類別 | 文件 | 狀態 |
|---|---|---|
| 架構 | `Architecture_Optimization_Recommendations.md`、`CALENDAR_ARCHITECTURE.md`、`DOCUMENT_AI_ARCHITECTURE.md` | ✅ |
| ADR | `adr/0001` ~ `0016`（16 份，完整決策紀錄） | ✅ 優 |
| 部署 | `DEPLOYMENT_GUIDE.md`、`DEPLOYMENT_CHECKLIST.md`、`DEPLOYMENT_GAP_ANALYSIS.md`、`MANUAL_DEPLOYMENT_GUIDE.md`、`NAS_DEPLOYMENT_GUIDE.md` | ✅ 優 |
| Cloudflare | 本次整併至 `CK_AaaP/CK_AaaP_Cloudflare_Setup_Guide.md`；原文保留 | ✅ |
| Secret rotation | 本次新增 `SECRET_ROTATION_SOP.md` | ✅ |
| KG | `KG_FEDERATION_TOKEN_ROTATION_SOP.md` 等 | ✅ |
| 開發 | `DEVELOPMENT_GUIDE.md`、`DEVELOPMENT_STANDARDS.md`、`CONTRIBUTING.md` | ✅ |
| 錯誤處理 | `ERROR_HANDLING_GUIDE.md` | ✅ |
| Env | `ENV_MANAGEMENT_GUIDE.md` | ✅ |

**文件成熟度結論**：**高**。CK_Missive 是 CK 平台文件最完整的專案，ADR 累積到 16 份，可作為**其他子專案借鏡範本**。

### 3.2 文件缺口

- ❌ 缺 `AUTH_FLOW_DIAGRAM.md`（登入流程圖 + middleware 順序）
- ❌ 缺 `SECURITY_THREAT_MODEL.md`（STRIDE 或類似威脅模型）
- ❌ 缺 `INCIDENT_RESPONSE_PLAYBOOK.md`（密碼洩漏、token 外洩、帳號被盜的應變）
- ⚠️ `ARCHITECTURE_REVIEW_*.md` 僅有 NemoClaw 版（2026-03-25 7.8/10），Missive 本身無

---

## 四、整體建議事項（優先序）

### P0（立即，本次已處理）
- ✅ `/health` SPA 覆蓋 bug
- ✅ Google 登入 403（tunnel_guard 白名單）
- ✅ pre-commit secret guard + install-hooks 共享化
- ✅ Secret rotation SOP

### P1（近期，建議 1~2 週內）
1. **生產 `.env` 驗證**：`DEVELOPMENT_MODE=false`、`AUTH_DISABLED=false`、`TUNNEL_GUARD_ENABLED=true`、`GOOGLE_ALLOWED_DOMAINS` 已設
2. **CF Access Bypass Policy 加 `/api/auth/`**（否則本次修復在生產仍會 302）
3. **補登入安全**：
   - 失敗計數 + 鎖定策略（若未內建）
   - 密碼規則強化（若採帳密）
   - MFA 強制策略（高權角色）
4. **補 3 份缺文件**：`AUTH_FLOW_DIAGRAM.md`、`SECURITY_THREAT_MODEL.md`、`INCIDENT_RESPONSE_PLAYBOOK.md`

### P2（2~4 週）
1. **N-7 Missive backend 容器化**：解鎖 Docker Secrets Phase 1（見 evaluation doc）、統一部署模式
2. **KG 各缺口補測**（實際已有基礎，可拓展 edge case）
3. **Observability 閉環**：確認 Loki 真有收到 Missive 日誌、Grafana Dashboard 可視化

### P3（條件觸發再議）
1. Service Mesh / mTLS（已決策暫不導入）
2. Docker Secrets 全面化（等 N-7 後）
3. 跨專案集中化 secret 管理（Vault 等）

---

## 五、整體健康度評分（Missive 本體）

| 維度 | 分 | 說明 |
|---|---|---|
| 架構設計 | 9 / 10 | 4 層 AI 架構（ADR-0007）、SSOT type（ADR-0004）、CF Tunnel 公網（ADR-0015） |
| 文件 | 9 / 10 | ADR 16 份 + 完整部署/開發文件，缺威脅模型與 IR playbook |
| 安全 | 7.5 / 10 | JWT + CSRF + MFA + audit 齊全，但需生產 env 與 CF Access 配置驗證 |
| 可觀測性 | 7 / 10 | PM2/日誌/Prometheus/Loki 棧到位；但 Loki 收 Missive 日誌端到端未驗 |
| 測試 | 7.5 / 10 | KG/agent/frontend 測試齊備；benchmark/fuzzing 較弱 |
| 部署自動化 | 8 / 10 | PM2 + ecosystem + CF Tunnel；但仍 host mode |
| **綜合** | **8.0 / 10** | — |

---

## 六、決策事項（本次已落地）

| 項目 | 決策 | 文件位置 |
|---|---|---|
| Service Mesh / mTLS | 暫不導入（A） | `CK_AaaP/CK_AaaP_Service_Mesh_Evaluation.md` |
| Docker Secrets | 暫不導入（A），補 pre-commit + SOP | `CK_AaaP/CK_AaaP_Docker_Secrets_Evaluation.md` |
| PileMgmt 洩漏密碼 | 另案處理（非 Missive 範疇） | — |
| Missive 為主體原則 | 其他專案僅借鏡優點 | 記憶 `feedback_missive_first.md` |

---

## 七、變更歷史

| 日期 | 變更 | 影響檔案 |
|---|---|---|
| 2026-04-15 | 初版 — 架構覆盤 + 登入防護評估 + 403 修復 | 本文件 |
