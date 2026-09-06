---
title: app.services.integration.line_bot
kg_entity_id: 798900
type: module
module_lines: 539
module_relations: 19
file_path: /app/app/services/integration/line_bot.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.integration.line_bot

## 概述
`LineBotService` 是一個整合 LINE Messaging API 的服務模組，負責處理來自 LINE 的各種訊息類型（文字、語音、圖片等），並根據不同的訊息內容進行相應的處理和回覆。

## 主要類別
- **LineBotService**: 網路請求處理與業務邏輯整合的主要類別

## 公開函數
- **get_line_bot_service()**: 初始化 LINE Bot 服務實例

## 依賴關係
- **app.core.redis_client**: 資料暫存及同步的 Redis 客戶端
- **app.db.database**: 資料庫操作相關的模組
- **app.services.erp.invoice_recognizer**: 發票辨識服務，用於處理圖片訊息
- **app.services.common.line_admin_commands**: 管理員命令處理功能
- **app.services.ai.misc.voice_transcriber**: 語音轉文字服務
- **app.services.ai.agent.agent_conversation_memory**: 代理對話記憶模組
- **app.services.ai.agent.agent_orchestrator**: 代理 orchestrator 模組，負責協調和管理代理對話流程
- **app.core.admin_push_metrics**: 管理員推送度量資訊的模組

此 LINE Bot Service 版本為 1.2.0，於 2026 年 3 月 15 日創建，並在 2026 年 3 月 23 日更新至 v1。
