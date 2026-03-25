# KG Federation Token Rotation SOP

> 跨專案 KG 聯邦 Service Token 輪替標準作業程序

## 概述

KG Federation 使用 `MCP_SERVICE_TOKEN` 進行 service-to-service 認證。Hub (CK_Missive) 支援**雙令牌機制** — 同時接受 current 與 previous token，確保輪替期間零停機。

## 涉及專案與服務

| 專案 | .env 變數 | 容器 |
|------|----------|------|
| CK_Missive (Hub) | `MCP_SERVICE_TOKEN`, `MCP_SERVICE_TOKEN_PREV` | backend |
| CK_lvrland_Webmap | `MCP_SERVICE_TOKEN` | backend, celery-worker, celery-beat |
| CK_DigitalTunnel | `MCP_SERVICE_TOKEN` | api, worker, celery-beat |

## 輪替步驟

### Step 1: 產生新 Token

```bash
# 產生 32 位元組 URL-safe base64 token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

記下產出的新 token（以下以 `NEW_TOKEN` 代稱）。

### Step 2: 更新 Hub (CK_Missive)

編輯 `CK_Missive/.env`：

```env
# 將舊 token 移至 PREV
MCP_SERVICE_TOKEN_PREV=<舊的 MCP_SERVICE_TOKEN 值>
# 設定新 token
MCP_SERVICE_TOKEN=NEW_TOKEN
```

重啟 Hub backend：

```bash
cd CK_Missive
pm2 restart ck-missive-backend
# 或 Docker:
docker compose -f docker-compose.infra.yml restart backend
```

> 此時 Hub 同時接受新舊兩個 token — contributor 用舊 token 仍可正常呼叫。

### Step 3: 更新 Contributors

**CK_lvrland_Webmap:**

```bash
# 編輯 .env
MCP_SERVICE_TOKEN=NEW_TOKEN

# 重啟服務
docker compose restart backend celery-worker celery-beat
```

**CK_DigitalTunnel:**

```bash
# 編輯 .env
MCP_SERVICE_TOKEN=NEW_TOKEN

# 重啟服務
docker compose restart api worker celery-beat
```

### Step 4: 驗證

```bash
# 從 LvrLand 測試
curl -X POST http://ck_missive_app:8001/api/ai/graph/federation-health \
  -H "Authorization: Bearer <admin_jwt>"

# 從 Tunnel 測試 kg_sync 任務
docker exec ck_tunnel_worker python -c "
from src.tasks.kg_sync import sync_kg_entities
sync_kg_entities.delay()
"
```

確認回應正常後，進入下一步。

### Step 5: 清除舊 Token (選用)

確認所有 contributor 已切換至新 token 後，可移除 Hub 的 `MCP_SERVICE_TOKEN_PREV`：

```env
# CK_Missive/.env
MCP_SERVICE_TOKEN_PREV=
```

重啟 Hub backend。

## 安全要求

- Token 長度至少 32 bytes (建議 `secrets.token_urlsafe(32)`)
- Token 僅存於 `.env` 檔案，**禁止 hardcode**
- `.env` 檔案已列入 `.gitignore`
- 建議每 90 天輪替一次
- 使用 `hmac.compare_digest()` 防止 timing attack（Hub 已實作）

## 故障排除

| 症狀 | 原因 | 修復 |
|------|------|------|
| 401 Invalid service token | Contributor 的 token 不匹配 Hub | 確認 contributor `.env` 中的 `MCP_SERVICE_TOKEN` 與 Hub 的 current 或 prev 一致 |
| 403 Service token required | Hub 未配置 `MCP_SERVICE_TOKEN` | 確認 Hub `.env` 與 docker-compose 都有傳遞此變數 |
| Celery task 靜默失敗 | Container 未接收到環境變數 | 確認 docker-compose.yml 中對應 service 的 environment 區段有 `MCP_SERVICE_TOKEN=${MCP_SERVICE_TOKEN:-}` |

## 時序圖

```
Timeline:   T0          T1           T2           T3
            |           |            |            |
Hub:        OLD         OLD+NEW      OLD+NEW      NEW only
LvrLand:    OLD         OLD          NEW          NEW
Tunnel:     OLD         OLD          NEW          NEW
            |           |            |            |
Action:     [normal]    [update Hub] [update      [remove
                                      contributors] PREV]
```

> T1~T2 期間為**雙令牌共存期**，所有服務可無中斷切換。
