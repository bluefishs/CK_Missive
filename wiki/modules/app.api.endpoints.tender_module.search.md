---
title: app.api.endpoints.tender_module.search
kg_entity_id: 38572
type: module
module_lines: 508
module_relations: 31
file_path: /app/app/api/endpoints/tender_module/search.py
created: 2026-08-03
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.search

## 概述
此 Python 模組包含了多個與標案搜尋相關的 API 函數，用於提供不同層次的標案資訊查詢服務。

## 主要函數
- `get_tender_service`
- `search_tenders`
- `get_tender_detail`
- `get_tender_detail_full`
- `search_by_company`
- `recommend_tenders`
- `realtime_tenders`

## 依賴關係
- `app.services.tender.search`
- `app.schemas.common`
- `app.schemas.tender_admin`
- `app.db.database`
- `app.services.tender.analytics`
- `app.services.tender.analytics_battle`
- `app.services.tender.analytics_price`
- `app.extended.models.tender`
- `app.services.tender.business_recommendation`
- `app.services.tender.ezbid_scraper`
