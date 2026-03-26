# LINE + OpenClaw 運維指南

> 最後更新: 2026-03-25 | 狀態: 運行中

## 現行架構

```
LINE 使用者 → 小花貓 Aroan (LINE Official Account)
    ↓ webhook (HTTPS via ngrok)
OpenClaw Gateway (Docker: openclaw_engine, port 18789)
    ↓ Claude Haiku 理解意圖 → bash curl
CK_Missive Agent API (PM2: ck-backend, port 8001)
    ↓ NemoClawAgent + 22 工具
回覆 → OpenClaw → LINE
```

## 啟動順序（重開機後）

```powershell
# 1. 基礎設施
docker compose -f docker-compose.infra.yml up -d

# 2. 後端
pm2 start ecosystem.config.js      # ck-backend (8001) + ck-frontend (3000)

# 3. OpenClaw
cd D:\CKProject\CK_NemoClaw
docker compose up -d openclaw       # openclaw_engine (18789)

# 4. 確認 Ollama 在同一個 network（每次 container 重建後需要）
docker network connect nemoclaw_network openclaw-ollama-1

# 5. 確認 skill 存在
docker exec openclaw_engine sh -c "cat /home/node/.openclaw/workspace/skills/ck-missive-bridge/SKILL.md | head -3"

# 6. 啟動 ngrok（LINE webhook 需要公網 HTTPS）
ngrok http 18789

# 7. 設定 LINE webhook URL（每次 ngrok URL 變更時）
#    方法 A: 用 LINE Developers Console 手動設定
#    方法 B: 用 API:
curl -X PUT "https://api.line.me/v2/bot/channel/webhook/endpoint" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <LINE_CHANNEL_ACCESS_TOKEN>" \
  -d '{"endpoint": "https://<ngrok-url>/line/webhook"}'
```

## 重要配置檔案

| 檔案 | 位置 | 說明 |
|------|------|------|
| OpenClaw config | `C:\Users\User1\.openclaw\openclaw.json` | LINE/Telegram channel 設定 |
| OpenClaw .env | `D:\CKProject\CK_OpenClaw\.env` | ANTHROPIC_API_KEY, MCP_SERVICE_TOKEN |
| Missive .env | `D:\CKProject\CK_Missive\.env` | LINE_BOT_ENABLED, DB, Redis |
| Docker Compose | `D:\CKProject\CK_NemoClaw\docker-compose.yml` | OpenClaw container 定義 |
| IDENTITY.md | container 內 `/home/node/.openclaw/workspace/IDENTITY.md` | Agent 身份 + API 指示 |
| Skill | container 內 `/home/node/.openclaw/workspace/skills/ck-missive-bridge/SKILL.md` | Missive API 呼叫指示 |

## 常見問題

### LINE 無反應
1. 確認 ngrok 在跑：`curl http://localhost:4040/api/tunnels`
2. 確認 webhook URL 正確：LINE Developers Console → Messaging API → Webhook URL
3. 確認 OpenClaw 在跑：`docker ps | grep openclaw`

### Agent 說「API 連不上」
1. 確認 Missive 後端在跑：`curl -X POST http://localhost:8001/api/health`
2. 確認 container 內可連：`docker exec openclaw_engine sh -c "curl -s http://host.docker.internal:8001/api/health"`
3. 確認 skill 有 `host.docker.internal`（不是 `localhost`）

### 查詢結果不完整
- 派工單搜尋預設 50 筆、上限 100 筆
- 公文搜尋預設 20 筆、上限 50 筆

### Telegram 409 Conflict
- 同一個 Bot Token 只能有一個 getUpdates 連線
- 停止其他使用同 Token 的程式，等 30 秒後重啟

## Credentials（不要外洩）

| 項目 | 存放位置 |
|------|---------|
| LINE Channel Secret | `openclaw.json` → channels.line.channelSecret |
| LINE Channel Access Token | `openclaw.json` → channels.line.channelAccessToken |
| Telegram Bot Token | `openclaw.json` → channels.telegram.botToken |
| Anthropic API Key | `CK_OpenClaw/.env` → ANTHROPIC_API_KEY |
| MCP Service Token | 兩邊 `.env` 共用 |
