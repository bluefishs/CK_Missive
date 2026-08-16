---
title: app.core.exceptions
kg_entity_id: 11477
type: module
module_lines: 483
module_relations: 22
file_path: /app/app/core/exceptions.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.exceptions

## 概述
此模組定義了系統中使用的自定義異常類別和統一的異常處理器，確保所有 API 異常回應格式一致。

## 主要類別
- `AppException`
- `ValidationException`
- `NotFoundException`
- `UnauthorizedException`
- `ForbiddenException`
- `ConflictException`
- `DuplicateException`
- `ResourceInUseException`
- `InvalidOperationException`
- `DatabaseException`
- `InternalException`

## 公開函數
- `format_error_response`
- `app_exception_handler`
- `http_exception_handler`
- `validation_exception_handler`
- `generic_exception_handler`
- `register_exception_handlers`
- `value_error_handler`
- `db_constraint_exception_handler`

## 依賴關係
- `app.core.cors`
- `app.schemas.common`
