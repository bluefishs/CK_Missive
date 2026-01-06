# 資料庫備份機制 - 乾坤測繪公文管理系統

## 概述

本目錄包含 PostgreSQL 資料庫的自動備份與還原腳本，支援：
- 每日自動備份
- 備份檔案壓縮 (gzip)
- 自動清理過期備份
- 一鍵還原功能

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `db_backup.ps1` | Windows PowerShell 備份腳本 |
| `db_backup.sh` | Linux/Git Bash 備份腳本 |
| `db_restore.ps1` | 資料庫還原腳本 |
| `setup_scheduled_task.ps1` | Windows 排程設定腳本 |

## 快速開始

### 1. 手動執行備份

**Windows PowerShell:**
```powershell
# 執行備份
.\db_backup.ps1

# 顯示詳細輸出
.\db_backup.ps1 -Verbose

# 指定保留天數
.\db_backup.ps1 -RetentionDays 14
```

**Linux/Git Bash:**
```bash
# 執行備份
bash db_backup.sh

# 顯示詳細輸出
bash db_backup.sh --verbose

# 指定保留天數
bash db_backup.sh --retention-days 14
```

### 2. 設定每日自動備份

**Windows (需要管理員權限):**
```powershell
# 設定每日凌晨 2:00 執行備份
.\setup_scheduled_task.ps1

# 指定時間和保留天數
.\setup_scheduled_task.ps1 -BackupTime "03:00" -RetentionDays 14

# 移除排程
.\setup_scheduled_task.ps1 -Remove
```

**Linux (使用 cron):**
```bash
# 編輯 crontab
crontab -e

# 加入以下行（每日凌晨 2:00 執行）
0 2 * * * /path/to/CK_Missive/scripts/backup/db_backup.sh >> /var/log/ck_backup.log 2>&1
```

### 3. 還原資料庫

```powershell
# 列出可用備份
.\db_restore.ps1 -List

# 還原最新備份
.\db_restore.ps1 -Latest

# 還原指定備份
.\db_restore.ps1 -BackupFile "C:\path\to\backup.sql.gz"

# 跳過確認提示
.\db_restore.ps1 -Latest -Force
```

## 目錄結構

```
CK_Missive/
├── backups/
│   └── database/           # 備份檔案存放位置
│       ├── ck_missive_backup_20241230_020000.sql.gz
│       └── ck_missive_backup_20241231_020000.sql.gz
├── logs/
│   └── backup/             # 備份日誌
│       ├── backup_20241230.log
│       └── restore_20241230.log
└── scripts/
    └── backup/             # 備份腳本
        ├── db_backup.ps1
        ├── db_backup.sh
        ├── db_restore.ps1
        └── setup_scheduled_task.ps1
```

## 設定說明

腳本會自動從專案根目錄的 `.env` 檔案讀取以下設定：

| 環境變數 | 預設值 | 說明 |
|----------|--------|------|
| `POSTGRES_USER` | ck_user | 資料庫使用者 |
| `POSTGRES_PASSWORD` | ck_password_2024 | 資料庫密碼 |
| `POSTGRES_DB` | ck_documents | 資料庫名稱 |
| `COMPOSE_PROJECT_NAME` | ck_missive | Docker 專案名稱 |

## 備份策略

- **備份時間**: 建議凌晨 2:00 (系統負載最低時段)
- **保留天數**: 預設 7 天
- **壓縮**: 使用 gzip 壓縮，節省約 70-90% 空間
- **命名規則**: `ck_missive_backup_YYYYMMDD_HHMMSS.sql.gz`

## 注意事項

1. **Docker 容器必須運行**: 備份腳本透過 `docker exec` 執行 `pg_dump`
2. **磁碟空間**: 請確保備份目錄有足夠空間
3. **還原警告**: 還原操作會覆蓋現有資料，請謹慎操作
4. **測試還原**: 建議定期測試備份還原流程

## 故障排除

### 備份失敗

1. 檢查 Docker 容器是否運行:
   ```powershell
   docker ps | findstr ck_missive_postgres
   ```

2. 檢查日誌檔案:
   ```powershell
   Get-Content .\logs\backup\backup_*.log -Tail 50
   ```

### 還原失敗

1. 確認備份檔案完整性
2. 檢查資料庫連線
3. 查看還原日誌

## 版本記錄

| 日期 | 版本 | 說明 |
|------|------|------|
| 2024-12-30 | 1.0 | 初始版本 |
