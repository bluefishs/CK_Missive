# 資料庫備份管理 (Database Backup Management)

管理 CK_Missive PostgreSQL 資料庫與附件檔案的備份與還原操作。

## API 端點 (POST-only)

系統提供 RESTful API 進行備份管理：

| 端點 | 說明 |
|------|------|
| `POST /api/backup/create` | 建立備份 |
| `POST /api/backup/list` | 列出備份 |
| `POST /api/backup/delete` | 刪除備份 |
| `POST /api/backup/restore` | 還原資料庫 |
| `POST /api/backup/config` | 取得設定 |
| `POST /api/backup/status` | 取得狀態 |

### API 範例

```bash
# 建立備份
curl -X POST http://localhost:8001/api/backup/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_database": true, "include_attachments": true, "retention_days": 7}'

# 查看備份列表
curl -X POST http://localhost:8001/api/backup/list \
  -H "Authorization: Bearer $TOKEN"
```

## 自動排程

系統啟動時自動啟用每日備份排程器：
- **執行時間**: 每日凌晨 02:00
- **備份內容**: 資料庫 + 附件
- **保留天數**: 7 天

## 快速指令

### 執行完整備份（資料庫 + 附件）
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_backup.ps1" -Verbose
```

### 僅備份資料庫
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_backup.ps1" -DatabaseOnly -Verbose
```

### 僅備份附件
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_backup.ps1" -AttachmentsOnly -Verbose
```

### 備份到指定路徑（NAS/外接硬碟）
```powershell
powershell -ExecutionPolicy Bypass -File "C:\GeminiCli\CK_Missive\scripts\backup\db_backup.ps1" -TargetPath "D:\Backup\CK_Missive" -Verbose
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

| 類型 | 預設路徑 |
|------|---------|
| 資料庫備份 | `C:\GeminiCli\CK_Missive\backups\database\` |
| 附件備份 | `C:\GeminiCli\CK_Missive\backups\attachments\` |
| 備份日誌 | `C:\GeminiCli\CK_Missive\logs\backup\` |

## 備份策略

| 項目 | 設定值 |
|------|--------|
| 備份時間 | 每日 02:00 (排程) |
| 保留天數 | 7 天 |
| 資料庫格式 | SQL (未壓縮) |
| 附件格式 | **增量備份** (v1.16.0+) |
| 命名規則 | `ck_missive_backup_YYYYMMDD_HHMMSS.sql` |
| 附件目錄 | `attachments_latest/` (增量) |

## 增量備份機制 (v1.16.0)

自 v1.16.0 起，附件備份採用增量備份機制，大幅減少備份時間與空間使用。

### 運作原理

```
attachments_latest/          # 增量備份主目錄（始終保持最新狀態）
├── documents/               # 公文附件
├── projects/                # 專案附件
└── ...

manifest_20260129_120000.json  # 變更記錄
```

### 增量備份流程

1. **檢查差異**: 比對 `st_mtime`（修改時間）和 `st_size`（檔案大小）
2. **複製新增/修改的檔案**: 僅複製有變更的檔案
3. **刪除已移除的檔案**: 同步刪除來源不存在的檔案
4. **記錄 Manifest**: 保存本次備份統計資訊

### Manifest 檔案格式

```json
{
  "timestamp": "2026-01-29T12:00:00",
  "copied_count": 5,
  "skipped_count": 120,
  "removed_count": 2,
  "copied_size_mb": 15.5,
  "total_files": 125
}
```

### 空間效益比較

| 備份模式 | 首次備份 | 後續備份 (假設 5% 變更) |
|----------|----------|-------------------------|
| 完整備份 | 100% | 100% |
| 增量備份 | 100% | ~5% |

### 異地備份同步

增量備份支援同步到異地備份路徑（如 NAS）：

```
本地: C:\GeminiCli\CK_Missive\backups\attachments\attachments_latest\
異地: Z:\backup\attachments_latest\
```

同步時會使用相同的增量機制，僅傳輸有變更的檔案。

## 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `-RetentionDays` | 保留天數 | 7 |
| `-Verbose` | 顯示詳細輸出 | false |
| `-DatabaseOnly` | 僅備份資料庫 | false |
| `-AttachmentsOnly` | 僅備份附件 | false |
| `-TargetPath` | 自訂備份路徑 | 專案目錄 |

## 手動備份 (Docker 直接執行)

如果腳本無法執行，可以直接使用 Docker 命令：

```bash
# 資料庫備份
docker exec ck_missive_postgres_dev pg_dump -U ck_user -d ck_documents > backup.sql

# 資料庫還原
cat backup.sql | docker exec -i ck_missive_postgres_dev psql -U ck_user -d ck_documents

# 附件備份 (手動複製)
xcopy /E /I "C:\GeminiCli\CK_Missive\backend\uploads" "D:\Backup\attachments"
```

## 驗證備份完整性

```powershell
# 檢查資料庫備份
dir "C:\GeminiCli\CK_Missive\backups\database"

# 檢查附件備份
dir "C:\GeminiCli\CK_Missive\backups\attachments"

# 檢視備份日誌
Get-Content "C:\GeminiCli\CK_Missive\logs\backup\backup_*.log" -Tail 50
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

### 磁碟空間不足
1. 減少保留天數：
   ```powershell
   .\db_backup.ps1 -RetentionDays 3
   ```
2. 備份到外接硬碟：
   ```powershell
   .\db_backup.ps1 -TargetPath "E:\Backup"
   ```

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/services/backup_service.py` | 備份服務核心 |
| `backend/app/services/backup_scheduler.py` | 自動排程器 |
| `backend/app/api/endpoints/backup.py` | API 端點 |
| `scripts/backup/db_backup.ps1` | PowerShell 備份腳本 |
| `scripts/backup/db_restore.ps1` | PowerShell 還原腳本 |
| `scripts/backup/setup_scheduled_task.ps1` | Windows 排程設定 |
