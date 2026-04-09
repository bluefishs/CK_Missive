---
name: multi-channel
description: 多通道整合開發規範 — LINE/Telegram/Discord 統一架構
version: 1.0.0
category: domain
triggers:
  - LINE
  - Telegram
  - Discord
  - 多通道
  - channel
  - webhook
  - 推播
  - bot
updated: '2026-04-09'
---

# 多通道整合開發規範


## 三通道架構

```
LINE 小花貓Aroan
    ↓ (webhook)
  OpenClaw (Claude Haiku)
    ↓ (bash curl)
  Missive Agent API ←─── Telegram @Aaron_ckbot (direct webhook)
        ↑
  Discord (Interactions Endpoint, 直連)
```

**關鍵差異**:
- LINE: 經由 OpenClaw 轉發，非直連
- Telegram: 直接 webhook 到 Missive，智慧回覆
- Discord: Interactions Endpoint 直連 Agent API

---

## 統一抽象層

| 檔案 | 職責 |
|------|------|
| `channel_adapter.py` | 通道抽象介面 (LINE/Discord/Telegram 統一) |
| `sender_context.py` | 發送者上下文 (頻道感知，識別訊息來源) |
| `agent_stream_helper.py` | SSE 串流輔助 (跨通道統一 streaming + typing status) |

所有通道的 Agent 問答最終匯入同一個 `agent_orchestrator`，差異僅在輸入解析與輸出格式化。

---

## 服務層

### LINE (`backend/app/services/`)

| 檔案 | 說明 |
|------|------|
| `line_bot_service.py` | LINE Bot 主服務 (362L, 直連模式) |
| `line_flex_builder.py` | Flex Message 建構器 |
| `line_image_handler.py` | 圖片處理 (接收+辨識) |
| `line_push_scheduler.py` | 推播排程器 |

### Telegram

| 檔案 | 說明 |
|------|------|
| `telegram_bot_service.py` | Bot 智慧回覆整合 (reactions + reply thread) |

### Discord

| 檔案 | 說明 |
|------|------|
| `discord_bot_service.py` | Discord Bot (430L) |
| `discord_helpers.py` | 格式化工具 (Markdown → Discord 格式) |

### 通知統一

| 檔案 | 說明 |
|------|------|
| `notification_dispatcher.py` | 通知派發 (路由到對應通道) |
| `morning_report_service.py` | 每日晨報 7 模組 (08:00 推送) |

---

## API 端點

| 端點 | 說明 |
|------|------|
| `line_webhook.py` | LINE Webhook 接收端點 |
| `telegram_webhook.py` | Telegram Bot Webhook 端點 |
| Agent SSE (`agent_query.py`) | 通用 Agent 問答 (所有通道共用) |

---

## SSE 串流統一

所有通道使用相同的 SSE 串流機制：

1. 收到用戶訊息後，呼叫 `agent_orchestrator` 開始 ReAct 迴圈
2. `agent_streaming_helpers.py` 產生 SSE 事件
3. `agent_stream_helper.py` 將 SSE 事件轉換為通道特定格式
4. 每個通道在串流期間顯示 typing status (LINE: loading animation, Telegram: typing action, Discord: typing indicator)

---

## Morning Report 多通道推送

`morning_report_service.py` 每日 08:00 自動產生 7 模組晨報：

1. 公文摘要 (未處理/逾期)
2. 行事曆提醒 (今日事件)
3. 專案進度 (里程碑到期)
4. 標案通知 (新標案/截止)
5. 財務摘要 (待審費用)
6. 系統健康 (異常偵測)
7. Agent 進化 (學習成果)

推送順序: Telegram → LINE → Discord (依可用性)

---

## 頻道配置重點

### LINE

- Webhook 需公網 HTTPS，使用 ngrok 暴露本地端口
- ngrok URL 變更時需至 LINE Developers Console 重設
- OpenClaw container 內 API URL 必須用 `host.docker.internal:8001`
- Container 重建後需重新寫入 `IDENTITY.md` 和 `SKILL.md`

### Telegram

- Bot token 透過 `.env` 的 `TELEGRAM_BOT_TOKEN` 設定
- Webhook 透過 `setWebhook` API 註冊
- 支援 reactions (表情回應) 和 reply thread (串連對話)
- 智慧回覆: 根據訊息內容自動判斷是否需要 Agent 處理

### Discord

- Interactions Endpoint 直連 Missive Agent API，不經 OpenClaw
- 使用 Discord Bot 權限系統管理存取
- Markdown 格式需轉換 (discord_helpers.py 處理)

---

## OpenClaw 依賴關係

| 通道 | 依賴 OpenClaw | 說明 |
|------|:---:|------|
| LINE | 是 | 經 OpenClaw (Claude Haiku) 轉發 |
| Telegram | 否 | 直接 webhook 到 Missive |
| Discord | 否 | Interactions Endpoint 直連 |

OpenClaw 離線時：LINE 通道不可用，Telegram 和 Discord 不受影響。

---

## 常見陷阱

1. **ngrok URL 過期**: 免費版每次重啟 URL 變更，需同步更新 LINE webhook
2. **OpenClaw container 重建**: Docker volume 不同步 host，需手動重寫 SKILL.md
3. **Discord 格式**: 超過 2000 字元需分段發送
4. **Telegram 智慧回覆**: 群組中需 @mention 或 reply 才觸發 Agent
5. **串流超時**: 長時間 Agent 處理需定期發送心跳，避免通道端斷線
