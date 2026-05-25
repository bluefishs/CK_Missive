# 交易污染修復報告

**日期**: 2026-01-09
**版本**: v3.0.1
**修復人員**: Claude Code Assistant
**備份檔案**: `backend/backups/ck_documents_backup_20260109_1355.dump`

---

## 問題描述

### 症狀
- 公文更新/刪除操作返回 500 錯誤
- 錯誤訊息: `InFailedSQLTransactionError: current transaction is aborted, commands ignored until end of transaction block`
- 審計日誌 (`audit_logs`) 在 13:18 後停止寫入
- 系統通知 (`system_notifications`) 完全沒有新記錄

### 根本原因
1. **交易污染 (Transaction Pollution)**: 審計/通知操作與主更新操作共用同一個 DB session
2. 當審計或通知操作失敗時，session 進入錯誤狀態
3. 被污染的 session 返回連接池後，影響後續使用該連接的請求
4. **SQL 語法錯誤**: `notification_service.py` 中 `:data::jsonb` 語法與 asyncpg 衝突

---

## 修復內容

### 1. documents_enhanced.py (行 1110-1156)

**修復前** (錯誤做法):
```python
# 審計和通知共用主 session
await log_document_change(db=db, ...)  # 使用傳入的 db session
await NotificationService.notify_critical_change(db=db, ...)
```

**修復後** (正確做法):
```python
# 使用獨立 session 避免交易污染
from app.db.database import AsyncSessionLocal
async with AsyncSessionLocal() as audit_db:
    try:
        await log_document_change(db=audit_db, ...)
        await NotificationService.notify_critical_change(db=audit_db, ...)
    except Exception as audit_inner_err:
        await audit_db.rollback()
        logger.warning(f"審計日誌記錄失敗: {audit_inner_err}", exc_info=True)
```

**關鍵改動**:
- 主交易 commit 後再執行審計/通知
- 審計/通知使用獨立的 `AsyncSessionLocal()` session
- 完整的異常處理，失敗不影響主操作
- 添加 `[AUDIT]` 和 `[NOTIFY]` 診斷日誌

### 2. notification_service.py (行 176)

**修復前**:
```sql
VALUES (..., :data::jsonb)
```

**修復後**:
```sql
VALUES (..., CAST(:data AS jsonb))
```

**原因**: asyncpg 驅動無法正確解析 `::` 類型轉換語法與 `:` 命名參數的組合

### 3. DEVELOPMENT_GUIDELINES.md

新增「交易污染 (Transaction Pollution)」章節，包含:
- 錯誤訊息範例
- 問題流程圖解
- 正確/錯誤代碼範例
- Session 管理核心原則表

---

## 驗證結果

| 測試項目 | 結果 | 說明 |
|---------|------|------|
| 公文更新 | ✅ 通過 | 返回 200，資料正確更新 |
| 審計日誌 | ✅ 通過 | ID 77-79 成功寫入 |
| 系統通知 | ✅ 通過 | ID 2 成功寫入 |
| 錯誤隔離 | ✅ 通過 | 審計失敗不影響主操作 |

### 資料庫驗證

```sql
-- 審計日誌
SELECT id, created_at, action FROM audit_logs ORDER BY id DESC LIMIT 3;
 id |         created_at         | action
----+----------------------------+--------
 79 | 2026-01-09 13:51:39.780227 | UPDATE
 78 | 2026-01-09 13:50:22.051224 | UPDATE
 77 | 2026-01-09 13:49:25.078943 | UPDATE

-- 系統通知
SELECT id, created_at, title FROM system_notifications ORDER BY id DESC LIMIT 1;
 id |         created_at         |       title
----+----------------------------+--------------------
  2 | 2026-01-09 13:51:39.785442 | 關鍵欄位變更: 主旨
```

---

## 影響範圍

### 修改的檔案
1. `backend/app/api/endpoints/documents_enhanced.py` - 審計日誌隔離
2. `backend/app/services/notification_service.py` - SQL 語法修正
3. `backend/main.py` - 版本號更新至 3.0.1
4. `.claude/DEVELOPMENT_GUIDELINES.md` - 新增交易污染文檔

### 相關功能
- 公文管理 CRUD 操作
- 審計日誌記錄
- 關鍵欄位變更通知

---

## 預防措施

### 開發規範
1. **非核心操作使用獨立 session**: 審計、通知、日誌等操作不應與主交易共用 session
2. **主交易先 commit**: 確保主要業務邏輯完成後，再執行次要操作
3. **完整異常處理**: 非核心操作失敗應該被捕獲，不影響主操作

### 程式碼審查重點
- 檢查 `db` session 是否被傳遞給非核心操作
- 確認使用 `AsyncSessionLocal()` 創建獨立 session
- 驗證 SQL 語句中的參數綁定語法

---

## 附錄: WatchFiles 問題

在修復過程中發現 Windows 環境下 uvicorn 的 WatchFiles 自動重載功能不穩定:
- 檔案變更後未自動重載
- 多個舊進程殘留在記憶體中

**建議**: 在 Windows 開發環境進行重要代碼修改後，建議手動重啟伺服器確保變更生效。

---

*報告生成時間: 2026-01-09 14:06*
