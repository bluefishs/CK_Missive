# 資料庫備份管理 (Database Backup Management)

管理 CK_Missive PostgreSQL 資料庫的備份與還原操作。

## 快速指令

### 執行備份
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_backup.ps1" -Verbose
```

### 查看可用備份
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_restore.ps1" -List
```

### 還原最新備份
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_restore.ps1" -Latest
```

### 設定每日自動備份
需要以管理員身分執行：
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\setup_scheduled_task.ps1"
```

## 備份位置

- **備份檔案**: `C:\GeminiCli\CK_Missive\backups\database\`
- **備份日誌**: `C:\GeminiCli\CK_Missive\logs\backup\`

## 備份策略

| 項目 | 設定值 |
|------|--------|
| 備份時間 | 每日 02:00 |
| 保留天數 | 7 天 |
| 檔案格式 | SQL (未壓縮) |
| 命名規則 | `ck_missive_backup_YYYYMMDD_HHMMSS.sql` |

## 手動備份 (Docker 直接執行)

如果腳本無法執行，可以直接使用 Docker 命令：

```bash
# 備份
docker exec ck_missive_postgres_dev pg_dump -U ck_user -d ck_documents > backup.sql

# 還原
cat backup.sql | docker exec -i ck_missive_postgres_dev psql -U ck_user -d ck_documents
```

## 驗證備份完整性

```bash
# 檢查備份檔案大小
dir "C:\GeminiCli\CK_Missive\backups\database"

# 檢視備份內容前 50 行
head -50 "C:\GeminiCli\CK_Missive\backups\database\<backup_file>.sql"
```

## 故障排除

### 備份失敗
1. 確認 Docker 容器運行中：
   ```bash
   docker ps | findstr postgres
   ```
2. 檢查日誌：
   ```powershell
   Get-Content "C:\GeminiCli\CK_Missive\logs\backup\backup_*.log" -Tail 50
   ```

### 還原失敗
1. 確認備份檔案存在且完整
2. 檢查資料庫連線
3. 查看還原日誌

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `scripts/backup/db_backup.ps1` | 主要備份腳本 |
| `scripts/backup/db_backup.sh` | Linux 版備份腳本 |
| `scripts/backup/db_restore.ps1` | 還原腳本 |
| `scripts/backup/setup_scheduled_task.ps1` | 排程設定 |
| `scripts/backup/README.md` | 完整使用說明 |
