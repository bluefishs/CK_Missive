# LINE Bot 串接啟用指南

## 前置條件

- LINE Developers Console 帳號
- 公網 HTTPS URL（ngrok 或 NAS 反向代理）
- CK_Missive 後端運行中 (port 8001)

## 步驟 1: 建立 LINE Messaging API Channel

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 選擇或建立 Provider
3. Create a **Messaging API** channel（注意：不是 LINE Login channel，那個已有）
4. 記下：
   - **Channel Secret** (Basic settings > Channel secret)
   - **Channel Access Token** (Messaging API > Channel access token > Issue)

## 步驟 2: 設定環境變數

編輯 `.env`：

```env
# LINE Bot Messaging API (新增)
LINE_BOT_ENABLED=true
LINE_CHANNEL_SECRET=<你的 Channel Secret>
LINE_CHANNEL_ACCESS_TOKEN=<你的 Channel Access Token>
```

## 步驟 3: 設定 Webhook URL

### 方案 A: ngrok（開發測試）

```bash
ngrok http 8001
# 取得 https://xxxx.ngrok-free.app
```

LINE Developers Console > Messaging API > Webhook URL:
```
https://xxxx.ngrok-free.app/api/line/webhook
```

### 方案 B: NAS 反向代理（正式環境）

```
https://your-nas-domain.com/api/line/webhook
```

### 驗證 Webhook

1. 在 LINE Developers Console 點擊 **Verify**
2. 應回傳 200 OK
3. 確認 **Use webhook** 開關已啟用

## 步驟 4: 重啟後端

```powershell
pm2 restart ck-backend
```

## 步驟 5: 測試

### 5.1 驗證服務狀態

```bash
curl -X POST http://localhost:8001/api/line/webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: invalid" \
  -d '{"events":[]}'
# 預期: 400 Invalid signature（表示服務已啟用）
```

### 5.2 加 Bot 為好友

掃描 LINE Developers Console > Messaging API 的 QR Code

### 5.3 發送測試訊息

在 LINE 對話中輸入：
- `今天有哪些公文到期？` → Agent 問答回覆
- 傳送發票照片 → OCR 辨識 + 自動建立費用紀錄
- 語音訊息 → Whisper 轉文字 + Agent 回覆

## 功能清單

| 訊息類型 | 處理流程 | 說明 |
|---------|---------|------|
| 文字 | → AgentOrchestrator → 回覆 | 全功能 AI 問答（含對話記憶） |
| 語音 | → Whisper 轉文字 → Agent → 回覆 | 需 Groq API key |
| 圖片 | → OCR 辨識 → 建立費用紀錄 → 回覆 | 需 Tesseract + LINE 帳號綁定 |
| Push | 系統主動推播 → LINE | 截止日提醒、異常警報 |

## 架構圖

```
LINE App (使用者)
    ↓ (Messaging API webhook)
POST /api/line/webhook
    ↓ (HMAC-SHA256 驗證)
LineBotService.handle_*_message()
    ├─ text  → _query_agent() → AgentOrchestrator → 回覆
    ├─ audio → VoiceTranscriber → _query_agent() → 回覆
    └─ image → OCR → ExpenseInvoiceService → 回覆
```

## 環境變數完整清單

| 變數 | 說明 | 必要 |
|------|------|:---:|
| `LINE_BOT_ENABLED` | 啟用 LINE Bot | ✓ |
| `LINE_CHANNEL_SECRET` | Messaging API Channel Secret | ✓ |
| `LINE_CHANNEL_ACCESS_TOKEN` | Messaging API Access Token | ✓ |
| `LINE_LOGIN_CHANNEL_ID` | LINE Login Channel ID | ✓ (已有) |
| `LINE_LOGIN_CHANNEL_SECRET` | LINE Login Channel Secret | ✓ (已有) |
| `LINE_LOGIN_REDIRECT_URI` | LINE Login 回調 URL | ✓ (已有) |
| `GROQ_API_KEY` | Whisper 語音轉文字 | 語音功能需要 |
