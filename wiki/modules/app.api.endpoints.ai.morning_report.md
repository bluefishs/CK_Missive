---
title: app.api.endpoints.ai.morning_report
kg_entity_id: 800549
type: module
module_lines: 244
module_relations: 19
file_path: /app/app/api/endpoints/ai/morning_report.py
created: 2026-08-24
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.morning_report

## 概述
此模組提供了晨報操作的 API 端點，包括晨報的預覽、推送、歷史快照和狀態查詢。

## 主要函數
- `preview_morning_report`: 生成並返回晨報的預覽版本。
- `push_morning_report`: 手動推送晨報，包含 Delivery Log 和字數截斷保護。
- `morning_report_history`: 提供近 14 天內晨報快照列表。
- `morning_report_status`: 查詢晨報的狀態。

## 依賴關係
- `app.core.dependencies`
- `app.core.redis_client`
- `app.services.integration.line_bot`
- `app.services.integration.telegram_bot`
- `app.services.ai.domain.morning_report_delivery`
- `app.services.ai.domain.morning_report_service`

## 端點
1. **POST /ai/stats/morning-report/preview** - 晨報預覽（不推送）
2. **POST /ai/stats/morning-report/push** - 手動推送晨報（含 Delivery Log + 字數截斷保護）
3. **POST /ai/stats/morning-report/history** - 近 14 天內晨報快照列表
```

此 Markdown 文檔概括了 `app.api.endpoints.ai.morning_report` 模組的主要內容，包括其功能、依賴關係和端點。
