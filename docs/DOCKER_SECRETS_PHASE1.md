# Docker Secrets Phase 1 盤點

> **狀態**：Phase 1 規劃（盤點完成，未實作）
> **建立**：2026-04-16
> **依據**：`CK_AaaP_Docker_Secrets_Evaluation.md`、`D:/CKProject/CLAUDE.md` P0 議題
> **範圍**：僅 CK_Missive；backend 非容器化時僅覆蓋 infra containers（Postgres/Redis）

---

## 盤點：`.env` 76 個變數分三類

### 🔴 Tier 1 — 必須轉 Secret（7 項）

| 變數 | 性質 | 用量 | 建議機制 |
|---|---|---|---|
| `POSTGRES_PASSWORD` | DB 主密碼 | infra compose | Docker Secret ✅ |
| `SECRET_KEY` | JWT/session 簽章金鑰 | backend | Docker Secret（backend 容器化後）/ 現階段檔案權限 600 |
| `GOOGLE_CLIENT_SECRET` | OAuth | backend | Docker Secret |
| `GROQ_API_KEY` | LLM API | backend | Docker Secret |
| `NVIDIA_API_KEY` | LLM API | backend | Docker Secret |
| `LINE_CHANNEL_SECRET` / `LINE_LOGIN_CHANNEL_SECRET` | LINE API | backend | Docker Secret |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_WEBHOOK_SECRET` | Telegram API | backend | Docker Secret |
| `CLOUDFLARE_TUNNEL_TOKEN` | Tunnel 授權 | cloudflared | Docker Secret ✅ |
| `MCP_SERVICE_TOKEN` | 服務間驗證 | backend | Docker Secret |

### 🟡 Tier 2 — 敏感但可環境變數（8 項）

| 變數 | 備註 |
|---|---|
| `DATABASE_URL` | 含密碼，建議改由 `POSTGRES_*` 組合 |
| `REDIS_URL` | 若無密碼可留 env |
| `VLLM_API_KEY` | 本機 vLLM 可留 env |
| `TELEGRAM_ADMIN_CHAT_ID` | PII，建議 secret |
| `GOOGLE_CALENDAR_ID` | 內部資源 ID |
| `WEBHOOK_BASE_URL` | 公網域名 |
| `LINE_LOGIN_REDIRECT_URI` | 公網域名 |
| `GOOGLE_REDIRECT_URI` | 公網域名 |

### 🟢 Tier 3 — 非敏感（61 項）

埠號、開關 flag、路徑、日誌等級、NEMOCLAW_* URL（ADR-0015 已廢止可刪除）等。

---

## 關鍵限制

1. **Backend 非容器化**：`ecosystem.config.js` 用 PM2 host mode，Docker Secrets 僅覆蓋 Postgres/Redis/cloudflared
2. **Phase 1 ROI**：
   - ✅ 高：`POSTGRES_PASSWORD` + `CLOUDFLARE_TUNNEL_TOKEN`（compose 直接用）
   - ⚠️ 中：Backend secrets 需等 Phase 2 容器化 backend 才有 Secret 介面
3. **Windows 限制**：Docker Desktop Secrets 僅支援 Swarm mode，Compose 需 file-based secret（`file: ./secrets/xxx.txt`）

---

## Phase 1 實作範本（compose override）

### `secrets/` 目錄（加入 `.gitignore`）
```
secrets/
├── postgres_password.txt         # 600 perm
├── cloudflare_tunnel_token.txt
└── README.md                     # 提醒勿 commit
```

### `docker-compose.infra.secrets.yml`（override，不改原 compose）
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_pw
    secrets:
      - pg_pw

  cloudflared:
    command: tunnel --no-autoupdate run --token-file /run/secrets/cf_token
    secrets:
      - cf_token

secrets:
  pg_pw:
    file: ./secrets/postgres_password.txt
  cf_token:
    file: ./secrets/cloudflare_tunnel_token.txt
```

### 啟動指令
```bash
docker compose \
  -f docker-compose.infra.yml \
  -f docker-compose.infra.secrets.yml \
  up -d
```

### Backend（過渡期）
在容器化前，建議：
- `.env` 檔案權限 `chmod 600`（Windows: 移除 Everyone/Users 讀取權限）
- 使用 `backend/app/core/secrets.py` 提供統一讀取介面，之後切 Secret 只改一處

---

## 遷移檢查清單

- [ ] 建立 `secrets/` 目錄並加入 `.gitignore`
- [ ] 從 `.env` 拷貝 `POSTGRES_PASSWORD` → `secrets/postgres_password.txt`
- [ ] 從 `.env` 拷貝 `CLOUDFLARE_TUNNEL_TOKEN` → `secrets/cloudflare_tunnel_token.txt`
- [ ] 建立 `docker-compose.infra.secrets.yml`
- [ ] 驗證 `docker compose config` 無錯
- [ ] 停止舊 infra，改用新命令啟動
- [ ] 確認 `docker exec postgres psql` 連線正常
- [ ] 確認 CF Tunnel 健康（`scripts/ops/verify-cloudflare-tunnel.ps1`）
- [ ] 從 `.env` 移除 `POSTGRES_PASSWORD` 與 `CLOUDFLARE_TUNNEL_TOKEN`（改由 secrets 供應）
- [ ] 更新 `.env.example` 註明改由 secret 檔提供
- [ ] ADR 記錄（編號接續 ADR-0017）

---

## Phase 2 前置（暫緩）

- Backend 容器化（Dockerfile + healthcheck）
- Secrets 統一介面 `backend/app/core/secrets.py`（檔案優先、env fallback）
- CI/CD 密鑰輪換自動化

---

## 清理機會（順便處理）

ADR-0015 廢止 NemoClaw 後，以下 3 個變數建議從 `.env.example` 移除：
- `NEMOCLAW_TOWER_URL`
- `NEMOCLAW_GATEWAY_URL`
- `NEMOCLAW_REGISTRY_URL`
