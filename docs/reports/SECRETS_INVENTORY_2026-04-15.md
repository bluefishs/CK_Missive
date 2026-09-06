# Secrets Inventory Snapshot — 2026-04-15

> P0 安全盤點（對應 CLAUDE.md 頂層未決項）
> 狀態：**僅盤點，未執行 rotation**。後續依此清單排序處理。

## 現況速覽

| 項目 | 狀態 | 備註 |
|------|------|------|
| `.env` 存在於 git | ❌ 不存在 | `.gitignore` 涵蓋 `.env` / `.env.*` |
| `.env` 檔案權限 | ⚠️ **644** | 建議改 **600**（其他 user 目前可讀） |
| `docker-compose.*.yml` hardcoded 密碼 | ✅ 無 | 全部使用 `${VAR}` 替換 |
| `.env.example` | ✅ 乾淨 | 全部為 placeholder（如 `YOUR_SECURE_PASSWORD_HERE`） |

## 需 rotation 追蹤的 secrets

按風險等級排序：

### 🔴 高優先（對外 / 財務 / 公網）

| 鍵 | 用途 | 外洩影響 | Rotation 建議 |
|----|------|----------|---------------|
| `SECRET_KEY` | JWT 簽章 | Session 偽造 | 90 天；輪換會使既有 token 全失效 |
| `GOOGLE_CLIENT_SECRET` | OAuth 登入 | 身份冒用 | Google Cloud Console 重新產生 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 推播 | 偽造推播 | LINE Developers Console 重產 |
| `LINE_CHANNEL_SECRET` / `LINE_LOGIN_CHANNEL_SECRET` | Webhook 簽章 / 登入 | 假 webhook | 同上 |
| `CLOUDFLARE_TUNNEL_TOKEN` | 公網入口 | 流量劫持 | CF Zero Trust → Tunnels → Refresh |
| `MCP_SERVICE_TOKEN` | 跨服務認證 | 內部 API 擅用 | 使用 `MCP_SERVICE_TOKEN_PREV` 雙 token 無縫輪換 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_WEBHOOK_SECRET` | Telegram Bot | 偽造推播 | @BotFather /revoke |

### 🟠 中優先（內部憑證 / 第三方 API）

| 鍵 | 用途 | Rotation 建議 |
|----|------|---------------|
| `POSTGRES_PASSWORD` | DB 連線 | 先建 readonly 帳號分離；主帳號 rotation 需停機 |
| `GROQ_API_KEY` | Groq LLM | Groq Console 重產 |
| `NVIDIA_API_KEY` | NVIDIA NIM | NVIDIA Console 重產 |
| `VLLM_API_KEY` | 本地 vLLM | 僅內網，低風險 |

### 🟢 低優先（低風險 / 純配置）

| 鍵 | 備註 |
|----|------|
| `GOOGLE_CLIENT_ID` / `LINE_LOGIN_CHANNEL_ID` / `GOOGLE_CALENDAR_ID` | 非 secret（公開識別） |
| `GOOGLE_REDIRECT_URI` | URL 設定 |
| `DATABASE_URL` | 組合自 POSTGRES_* 變數 |

## 已到位的安全機制

- ✅ `docker-compose.*.yml` 零 hardcoded 密碼
- ✅ `.env.example` 不含真實值（`test_env_example_no_real_secrets` CI 守門）
- ✅ `config.py` validator：生產模式強制 `AUTH_DISABLED=false`、`SECRET_KEY != dev_only_`（test 6/6 通過）
- ✅ `MCP_SERVICE_TOKEN_PREV` 支援雙 token 輪換（已在 `docker-compose.dev.yml` 接線）
- ✅ `docs/SECRET_ROTATION_SOP.md` 已有完整 SOP
- ✅ `.git/hooks/pre-commit` 偵測敏感檔案（`.env`、`credentials.json`、`.pem`、`.key`）
- ✅ CF Tunnel 每日驗證排程（06:15，本次新增）

## 建議執行順序（Phase 1 rotation）

1. **立即（零風險）**：`.env` 權限 `644 → 600`
2. **下次部署窗口（分鐘級停機）**：`SECRET_KEY` 輪換（全 token 失效，需通知用戶重登）
3. **下次維護窗口（秒級）**：`MCP_SERVICE_TOKEN` 雙 token 輪換
4. **非同步（無停機）**：Google / LINE / Telegram / Groq / NVIDIA / CF Tunnel 六項 API key（分批、驗證、刪舊）
5. **重大維護**：`POSTGRES_PASSWORD`（需建 readonly + 應用重連）

## 不執行的原因（本次僅盤點）

- 根本變更（密碼輪換）需業務窗口配合，避免踩到正在進行的公網流量
- `.env` 權限調整雖零風險，仍建議用戶於下次 host 維護時執行（避免 PM2/Docker 讀取時機）
- 建議接 `docs/SECRET_ROTATION_SOP.md` 的逐項步驟，每完成一項 commit 一次
