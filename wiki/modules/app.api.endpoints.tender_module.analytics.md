---
title: app.api.endpoints.tender_module.analytics
kg_entity_id: 38543
type: module
module_lines: 221
module_relations: 25
file_path: /app/app/api/endpoints/tender_module/analytics.py
created: 2026-08-04
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.analytics

## 概述
該模組提供了多個與標案分析相關的 API 端點，用於展示和處理各種標案數據，包括統計信息、待審核標案刷新、跨標案參考、分析儀表板、戰鬥室、組織生態系統、公司概況、標案價格分析以及價格趨勢。

## 公開函數
- `cache_stats`
- `refresh_pending`
- `cross_reference`
- `analytics_dashboard`
- `analytics_battle_room`
- `analytics_org_ecosystem`
- `analytics_company_profile`
- `tender_price_analysis`
- `tender_price_trends`

## 依賴關係
- `app.core.dependencies`
- `app.db.database`
- `app.schemas.common`
- `app.services.tender.analytics`
- `app.services.tender.business_recommendation`
- `app.services.tender.cache`
- `app.services.tender.metrics`
