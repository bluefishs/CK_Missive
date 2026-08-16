---
title: app.api.endpoints.backup
kg_entity_id: 10789
type: module
module_lines: 378
module_relations: 29
file_path: /app/app/api/endpoints/backup.py
created: 2026-08-04
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.backup

## 概述
此 Python 模塊提供了一套完整的資料庫備份管理 API 端點，包括創建備份、列出備份、刪除備份、還原資料庫、獲取備份配置、檢查環境狀態、清理遺留文件以及查詢和更新異地備份設定等功能。

## 公開函數
- `create_backup`: 創建新的資料庫備份。
- `list_backups`: 列出所有存在的備份。
- `delete_backup`: 刪除指定的備份。
- `restore_database`: 依照指定的備份還原資料庫。
- `get_backup_config`: 獲取當前的備份配置信息。
- `get_environment_status`: 檢查並返回環境狀態。
- `cleanup_orphan_files`: 清理遺留文件，確保系統清潔。
- `get_backup_status`: 查詢指定備份的狀態。
- `get_remote_backup_config`: 獲取異地備份配置信息。
- `update_remote_backup_config`: 更新異地備份配置。

## 依賴關係
- `app.core.rate_limiter`
- `app.api.endpoints.auth`
- `app.core.dependencies`
- `app.services.backup`
- `app.services.backup.auto_scheduler`
- `app.schemas.backup`
