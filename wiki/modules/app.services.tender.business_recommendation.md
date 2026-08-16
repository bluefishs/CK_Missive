---
title: app.services.tender.business_recommendation
kg_entity_id: 798673
type: module
module_lines: 725
module_relations: 22
file_path: /app/app/services/tender/business_recommendation.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.tender.business_recommendation

## 概述
該模組負責根據特定篩選原則，自動找出符合條件的標案並通過 LINE 通知方式推送給管理員。主要用於「近 N 日新增 + 預算大 + 機關曾合作」的標案。

## 主要函數
1. `find_business_recommendations`: 根據篩選原則找到符合條件的標案。
2. `push_daily_recommendations`: 將每日篩選出的推薦標案通過 LINE 通知推送給管理員。
3. `count_complete_tenders`: 計算已完成標案數量。
4. `fetch_complete_tenders`: 提取已完成標案信息。
5. `load_keyword_rules`: 加載關鍵字規則。
6. `save_keyword_rules`: 儲存關鍵字規則。
7. `suggest_keyword_terms`: 提出關鍵字建議。

## 依賴關係
1. `app.core.redis_client`: 使用 Redis 客戶端進行數據存儲和讀取操作。
2. `app.services.tender.metrics`: 標案度量服務，用於獲取標案相關的統計信息。
3. `app.services.contracts.facades`: 合同Facade服務，用於合同相關的操作。
