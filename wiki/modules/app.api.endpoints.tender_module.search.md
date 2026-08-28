---
title: app.api.endpoints.tender_module.search
kg_entity_id: 38572
type: module
module_lines: 732
module_relations: 33
file_path: /app/app/api/endpoints/tender_module/search.py
created: 2026-08-03
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.search

## 概述
此 Python 模組提供了多個與標案搜尋相關的 API 端點，包括基本的標案搜尋、詳細資訊查詢、公司相關標案搜尋以及實時標案等。

## 公開函數
1. `get_tender_service`
2. `search_tenders`
3. `get_tender_detail`
4. `get_tender_detail_full`
5. `search_by_company`
6. `recommend_tenders`
7. `realtime_tenders`

## 依賴關係
1. `app.core.dependencies`
2. `app.core.redis_client`
3. `app.db.database`
4. `app.schemas.common`
5. `app.extended.models.tender`
6. `app.schemas.tender_admin`
7. `app.services.tender.analytics`
8. `app.services.tender.analytics_battle`
9. `app.services.tender.analytics_price`
10. `app.services.tender.business_recommendation`
