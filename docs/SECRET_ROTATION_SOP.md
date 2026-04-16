# CK_Missive 密碼 / Token 輪換 SOP

> **建立**：2026-04-15
> **適用**：CK_Missive 所有 `.env` 密碼與 token
> **關聯決策**：`CK_AaaP/evaluations/docker-secrets.md`（Docker Secrets 暫不導入，配套 SOP）

---

## 1. 何時需要輪換

| 觸發 | 頻率 / 條件 |
|---|---|
| 定期輪換 | **每 90 天**（建議） |
| 疑似洩漏 | 立即 |
| 人員異動 | 離職後 7 天內 |
| 密碼被 commit 入 git | 立即 + git 歷史審視 |

---

## 2. 需輪換的項目盤點

CK_Missive `.env` 敏感項（以實際檔案為準）：

| 變數 | 類型 | 輪換對象 | 備註 |
|---|---|---|---|
| `POSTGRES_PASSWORD` | DB | PostgreSQL `postgres` user | `ALTER USER` |
| `REDIS_PASSWORD` | Cache | Redis `requirepass` | `CONFIG SET requirepass` |
| `MCP_SERVICE_TOKEN` | Internal auth | 內部 bearer | 雙 token 緩衝（見 §4） |
| `MCP_SERVICE_TOKEN_PREV` | Internal auth（舊 token 緩衝） | 24h 後移除 | |
| `CF_TUNNEL_TOKEN` | Cloudflare | CF Dashboard 重建 tunnel | |
| `TELEGRAM_BOT_TOKEN` | 3rd party | BotFather 產新 token | |
| `TELEGRAM_ADMIN_CHAT_ID` | 非密碼 | 不需輪換 | |
| `OPENAI_API_KEY` | 3rd party | OpenAI Dashboard | |
| `GROQ_API_KEY` | 3rd party | Groq Console | |
| `HF_TOKEN` | 3rd party | Hugging Face | |

---

## 3. 一般輪換流程（非 `MCP_SERVICE_TOKEN`）

### 3.1 POSTGRES_PASSWORD

```bash
# 1. 生成新密碼（32 字元強隨機）
NEW_PW=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

# 2. 連入 DB 改密碼
docker exec -it ck_missive_postgres_dev psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$NEW_PW';"

# 3. 更新 .env
# 手動編輯 CK_Missive/backend/.env：POSTGRES_PASSWORD=<新值>
# 或：
sed -i.bak "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PW/" d:/CKProject/CK_Missive/backend/.env

# 4. 重啟依賴該密碼的服務
pm2 restart ck-backend

# 5. 驗證連線
curl -s http://127.0.0.1:8001/health | jq .database
# 預期: {"status":"connected", ...}
```

### 3.2 REDIS_PASSWORD

```bash
NEW_PW=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

# 線上改（不停機）
docker exec -it ck_missive_redis_dev redis-cli CONFIG SET requirepass "$NEW_PW"

# 更新 .env
sed -i.bak "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_PW/" d:/CKProject/CK_Missive/backend/.env

# 持久化到 redis.conf（避免容器重啟後回舊值）
docker exec -it ck_missive_redis_dev redis-cli -a "$NEW_PW" CONFIG REWRITE

# 重啟 backend 讓新連線帶新密碼
pm2 restart ck-backend
```

### 3.3 CF_TUNNEL_TOKEN

```bash
# 1. CF Dashboard → Zero Trust → Networks → Tunnels → ck-missive → Delete
# 2. Create a tunnel → 同名 ck-missive → 複製新 token
# 3. 更新 .env: CF_TUNNEL_TOKEN=<新 token>
# 4. PM2 重啟 cloudflared
pm2 restart cloudflared
pm2 logs cloudflared --lines 10
# 預期見 "Registered tunnel connection"

# 5. 驗證公網
curl -s https://missive.cksurvey.tw/api/health | jq .status
```

### 3.4 第三方 API Key（OpenAI / Groq / HF / Telegram）

標準流程：
1. 在對應平台 Dashboard 產生新 key
2. 更新 `.env`
3. **舊 key 保留 24h**（讓 in-flight request 完成）
4. `pm2 restart ck-backend`
5. 觀察 1 小時，無錯誤後回對應 Dashboard 撤銷舊 key

---

## 4. MCP_SERVICE_TOKEN 雙 Token 緩衝輪換

此 token 供 NemoClaw / OpenClaw / 外部插件使用，**不能同步切換**（會 race）。

`auth.lua` 已實作雙 token 驗證（`MCP_SERVICE_TOKEN` 為 current、`MCP_SERVICE_TOKEN_PREV` 為舊）。

### 流程

```
T0    生成新 token
      .env: MCP_SERVICE_TOKEN_PREV=<舊>
            MCP_SERVICE_TOKEN=<新>
      重啟 nemoclaw_tower / openclaw / missive backend

T+24h 觀察日誌：grep "previous_token_used" — 應歸零
      .env: 移除 MCP_SERVICE_TOKEN_PREV
      再次重啟

T+48h 所有插件都用新 token 後，舊 token 完全失效
```

### 具體步驟

```bash
# T0
NEW_TOKEN=$(openssl rand -hex 32)
OLD_TOKEN=$(grep "^MCP_SERVICE_TOKEN=" d:/CKProject/CK_Missive/backend/.env | cut -d= -f2)

# 更新 .env（backend/.env 與 nemoclaw_tower 所讀的 .env，若不同步需皆改）
cat >> d:/CKProject/CK_Missive/backend/.env <<EOF

# Token rotation $(date +%Y-%m-%d)
MCP_SERVICE_TOKEN_PREV=$OLD_TOKEN
EOF
sed -i "s/^MCP_SERVICE_TOKEN=.*/MCP_SERVICE_TOKEN=$NEW_TOKEN/" d:/CKProject/CK_Missive/backend/.env

# 重啟相關服務
pm2 restart ck-backend
MSYS_NO_PATHCONV=1 docker restart nemoclaw_tower openclaw_engine

# 驗證：舊 token 仍可用
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-Service-Token: $OLD_TOKEN" http://127.0.0.1:9000/api/registry
# 預期: 200（並在 nemoclaw 日誌出現 "previous_token_used"）

# T+24h：移除舊 token
sed -i '/^MCP_SERVICE_TOKEN_PREV=/d' d:/CKProject/CK_Missive/backend/.env
pm2 restart ck-backend
MSYS_NO_PATHCONV=1 docker restart nemoclaw_tower

# 確認舊 token 失效
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-Service-Token: $OLD_TOKEN" http://127.0.0.1:9000/api/registry
# 預期: 401
```

---

## 5. 防誤 commit 保護

已部署 pre-commit hook：`scripts/hooks/pre-commit-secret-guard.sh`

安裝（每個開發者 clone 後執行一次）：
```bash
bash scripts/hooks/install-hooks.sh
```

擋下的檔案模式：
- `.env`、`.env.*`（除 `.env.example` / `.env.template` / `.env.sample`）
- `credentials.json`
- `*.pem`、`*.key`
- `secrets/*.{txt,yml,yaml}`

額外警告（不阻擋）：staged diff 含疑似密碼關鍵字。

---

## 6. 檢查清單（每次輪換後）

- [ ] `.env` 新值已寫入
- [ ] 對應服務已重啟
- [ ] 連線 / 健康檢查通過
- [ ] 舊 token（若適用）24h 後移除
- [ ] 若密碼曾被 commit，執行 git 歷史審視
- [ ] 本次輪換記錄於變更日誌（日期 / 項目 / 執行人）

---

## 7. 變更歷史

| 日期 | 項目 | 執行人 |
|---|---|---|
| 2026-04-15 | 本 SOP 建立 | — |
