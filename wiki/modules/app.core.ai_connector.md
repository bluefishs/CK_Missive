---
title: app.core.ai_connector
kg_entity_id: 11309
type: module
module_lines: 1251
module_relations: 19
file_path: /app/app/core/ai_connector.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.ai_connector

## 概述
`app.core.ai_connector` 是一個混合 AI 連接器模組，支援多種 AI 服務提供者，並根據預定義的優先順序進行選擇。此版本整合了 NVIDIA Cloud API 的支持，以提高性能和品質。

## 主要類別
- **AIConnector**: 管理和調用不同 AI 服務提供者的連接器。

## 公開函數
- **get_ai_connector**: 同步獲取並初始化 AI 連接器。
- **get_ai_connector_async**: 异步獲取並初始化 AI 連接器。

## 依賴關係
- `app.core.ai_connector_management`
- `app.services.ai.core.ai_config`
- `app.services.ai.core.token_usage_tracker`
- `app.core.inference_provider_context`
- `app.core.inference_provider_metrics`
- `app.core.inference_semaphore`
- `app.core.provider_circuit_breaker`

### 支援的 AI 服務優先順序
1. Groq API (免費，超快 ~100-500ms，llama3-70b)
2. NVIDIA Cloud API (Nemotron-49B，高品質)
3. 本地 Ollama (離線備援)
4. 智慧預設回應 (最終備援)

### NVIDIA Cloud API
- 使用 OpenAI-compatible 介面 (integra
