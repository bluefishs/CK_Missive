---
title: app.api.endpoints.tender_module.analytics
kg_entity_id: 38543
type: module
module_lines: 213
module_relations: 23
file_path: /app/app/api/endpoints/tender_module/analytics.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.analytics

## 概述
該模塊提供了與標案分析相關的各種 API 端點，包括 dashboard、battle-room、org-ecosystem、company-profile、price-analysis 和 price-trends。

## 主要類別
無

## 公開函數
1. `cache_stats`
2. `refresh_pending`
3. `cross_reference`
4. `analytics_dashboard`
5. `analytics_battle_room`
6. `analytics_org_ecosystem`
7. `analytics_company_profile`
8. `tender_price_analysis`
9. `tender_price_trends`

## 依賴關係
1. `app.db.database`
2. `app.schemas.common`
3. `app.services.tender.analytics`
4. `app.services.tender.business_recommendation`
5. `app.services.tender.cache`
6. `app.services.tender.metrics`
