---
title: app.api.endpoints.backup
kg_entity_id: 10789
type: module
module_lines: 373
module_relations: 27
file_path: /app/app/api/endpoints/backup.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.backup

## 概述
此模組提供了資料庫備份管理 API 端點，支援備份、還原、列表與管理功能。此外，還支持異地備份設定與備份日誌查詢。

## 主要類別
- 無

## 公開函數
1. `create_backup`: 創建資料庫備份。
2. `list_backups`: 列出所有備份。
3. `delete_backup`: 刪除指定的備份。
4. `restore_database`: 從備份還原資料庫。
5. `get_backup_config`: 获取备份配置信息。
6. `get_environment_status`: 获取环境状态信息。
7. `cleanup_orphan_files`: 清理孤儿文件。
8. `get_backup_status`: 获取备份状态。
9. `get_remote_backup_config`: 获取异地备份配置。
10. `update_remote_backup_config`: 更新异地备份配置。

## 依賴關係
- `app.api.endpoints.auth`
- `app.core.dependencies`
- `app.core.rate_limiter`
- `app.schemas.backup`
- `app.services.backup`
- `app.services.backup.auto_scheduler`
