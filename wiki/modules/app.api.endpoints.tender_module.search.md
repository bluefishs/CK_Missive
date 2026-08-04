---
title: app.api.endpoints.tender_module.search
kg_entity_id: 38572
type: module
module_lines: 480
module_relations: 31
file_path: /app/app/api/endpoints/tender_module/search.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.search

## 概述
此 Python 模組提供了多種與標案搜尋相關的功能，包括基本的標案搜索、詳細信息獲取、公司相關標案搜索以及實時標案等。

## 主要函數
- `get_tender_service`
- `search_tenders`
- `get_tender_detail`
- `get_tender_detail_full`
- `search_by_company`
- `recommend_tenders`
- `realtime_tenders`

## 依賴關係
- `app.core.redis_client`
- `app.db.database`
- `app.schemas.common`
- `app.extended.models.tender`
- `app.schemas.tender_admin`
- `app.services.tender.analytics`
- `app.services.tender.analytics_battle`
- `app.services.tender.analytics_price`
- `app.services.tender.business_recommendation`
- `app.services.tender.cache`
