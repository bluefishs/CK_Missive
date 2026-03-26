# 多通道部署指南 — Telegram + LINE via OpenClaw

## 架構

```
Telegram App ←→ OpenClaw ←→ CK_Missive Agent (POST /api/ai/agent/query)
LINE App     ←→ OpenClaw ←→ CK_Missive Agent
```

OpenClaw 作為通道轉發層，將 Telegram/LINE 訊息路由至 CK_Missive 的 AI Agent。

## 前置條件

- Docker Desktop 運行中
- CK_Missive 後端運行中 (PM2 ck-backend, port 8001)
- Redis 運行中 (docker-compose.infra.yml)

## 步驟 1: 取得 Telegram Bot Token

1. 在 Telegram 搜尋 `@BotFather`
2. 發送 `/newbot`
3. 輸入 bot 名稱和 username
4. 記下 Bot Token（格式：`123456:ABC-DEF...`）

## 步驟 2: 配置 OpenClaw

編輯 `C:\Users\User1\.openclaw\openclaw.json`：

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "<你的 Telegram Bot Token>",
      "dmPolicy": "allowlist",
      "allowFrom": ["<你的 Telegram User ID>"],
      "requireMention": true
    },
    "line": {
      "enabled": true,
      "channelSecret": "<已設定>",
      "channelAccessToken": "<已設定>"
    }
  }
}
```

取得 Telegram User ID：搜尋 `@userinfobot`，發送任意訊息即可得到你的 ID。

## 步驟 3: 確認 CK_Missive Skill

已預裝在 OpenClaw workspace：
```
C:\Users\User1\.openclaw\workspace\skills\ck-missive-bridge\SKILL.md
```

此 skill 定義了 Missive Agent 的觸發關鍵字（公文、派工、圖譜等）。

## 步驟 4: 啟動 OpenClaw

### 方案 A: Docker（推薦）

```powershell
docker compose -f docker-compose.infra.yml -f docker-compose.multichannel.yml up -d openclaw
```

### 方案 B: 本地開發

```bash
cd D:\CKProject\CK_OpenClaw
pnpm install
pnpm dev
```

## 步驟 5: 驗證

### Telegram
1. 在 Telegram 搜尋你建立的 Bot
2. 發送 `/start`
3. 發送「今天有哪些公文到期？」
4. Bot 應回覆 CK_Missive Agent 的查詢結果

### LINE
1. LINE webhook URL 設定為 OpenClaw 的公網 URL + `/line/webhook`
2. 在 LINE 對話中發送問題

## 訊息流程

```
1. 使用者在 Telegram/LINE 發送「查詢桃園市的公文」
2. OpenClaw 接收 webhook 事件
3. 訊息經過 Access Control + Mention Gating
4. 觸發 ck-missive-bridge skill（匹配「公文」關鍵字）
5. POST http://host.docker.internal:8001/api/ai/agent/query
   Headers: X-Service-Token: <MCP_SERVICE_TOKEN>
   Body: {"question": "查詢桃園市的公文"}
6. CK_Missive NemoClawAgent 處理查詢（22 工具 + KG + RAG）
7. 回傳結果給 OpenClaw
8. OpenClaw 格式化並回覆至 Telegram/LINE
```

## 環境變數

| 變數 | 位置 | 說明 |
|------|------|------|
| `MCP_SERVICE_TOKEN` | CK_Missive .env + OpenClaw .env | 跨服務認證 Token（必須一致） |
| `OPENCLAW_GATEWAY_PORT` | OpenClaw .env | Gateway 端口 (default 18789) |
| `CONVERSATION_REDIS_HOST` | OpenClaw .env | Redis 主機 |

## 故障排除

| 症狀 | 排查 |
|------|------|
| Bot 無回應 | 確認 OpenClaw 容器運行中 (`docker logs ck_openclaw`) |
| 「查無資料」 | 確認 CK_Missive 後端運行中 + MCP_SERVICE_TOKEN 一致 |
| LINE webhook 失敗 | 確認公網 HTTPS URL 正確設定 |
| Telegram 無法連線 | 確認 botToken 正確 + 網路可達 Telegram API |
