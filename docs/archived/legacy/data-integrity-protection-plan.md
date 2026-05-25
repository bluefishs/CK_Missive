# 資料完整性保護計畫

> 建立日期: 2026-01-08
> 觸發事件: 公文主旨被意外修改為 "Test Update"

## 一、問題根因分析

### 1.1 直接原因

| 層面 | 問題 | 說明 |
|------|------|------|
| 操作層 | 測試/開發操作 | 開發階段透過 UI 編輯時輸入測試值 |
| API 層 | 無修改確認 | 關鍵欄位可直接覆寫，無二次確認 |
| 追蹤層 | 無使用者記錄 | 審計日誌未記錄操作者身份 |

### 1.2 系統缺陷

```
現有架構問題：
┌─────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│  ├── DocumentPage.tsx                                       │
│  │     └── 編輯公文 → 無關鍵欄位保護警示                      │
│  └── DocumentOperations.tsx                                  │
│        └── 保存時無確認對話框                                 │
├─────────────────────────────────────────────────────────────┤
│ Backend                                                      │
│  ├── documents_enhanced.py                                   │
│  │     └── update_document()                                │
│  │           ├── ✅ 有 audit_logger                          │
│  │           ├── ❌ 無 user_id 記錄                          │
│  │           └── ❌ 無關鍵欄位修改限制                        │
│  └── audit_logger.py                                         │
│        └── ⚠️ audit_logs 表不存在                            │
└─────────────────────────────────────────────────────────────┘
```

## 二、優化方案

### P0：審計日誌持久化（立即執行）

**目標：** 確保所有資料變更可追溯

**實作步驟：**
1. 建立 `audit_logs` 資料表 (已建立 migration 檔案)
2. 執行 migration

```bash
# 執行 migration
cd backend
alembic upgrade head
```

**審計表結構：**
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,   -- 被修改的表格
    record_id INTEGER NOT NULL,          -- 被修改的記錄 ID
    action VARCHAR(20) NOT NULL,         -- CREATE/UPDATE/DELETE
    changes TEXT,                         -- 變更內容 JSON
    user_id INTEGER,                      -- 操作者 ID
    user_name VARCHAR(100),               -- 操作者名稱
    source VARCHAR(50) DEFAULT 'API',    -- 來源
    ip_address VARCHAR(50),               -- 操作者 IP
    is_critical BOOLEAN DEFAULT FALSE,   -- 是否為關鍵欄位變更
    created_at TIMESTAMP DEFAULT NOW()
);
```

### P1：關鍵欄位保護機制

**關鍵欄位定義：**
```python
CRITICAL_FIELDS = {
    "documents": ["subject", "doc_number", "sender", "receiver", "status"],
    "contract_projects": ["project_name", "project_code", "status", "budget"],
}
```

**保護策略：**

| 策略 | 說明 | 實作位置 |
|------|------|----------|
| 前端確認對話框 | 修改關鍵欄位時彈出確認視窗 | DocumentOperations.tsx |
| 後端驗證 | 記錄關鍵欄位變更並發送警示 | audit_logger.py |
| 權限控管 | 僅特定角色可修改關鍵欄位 | 待規劃 |

**前端實作範例：**
```typescript
// 關鍵欄位變更確認
const handleSave = async (data: Partial<Document>) => {
  const criticalChanges = detectCriticalChanges(originalDoc, data);

  if (criticalChanges.length > 0) {
    const confirmed = await Modal.confirm({
      title: '確認修改關鍵欄位',
      content: (
        <div>
          <p>您即將修改以下關鍵欄位：</p>
          <ul>
            {criticalChanges.map(change => (
              <li key={change.field}>
                {change.label}: "{change.oldValue}" → "{change.newValue}"
              </li>
            ))}
          </ul>
          <p>此操作將被記錄。確定要繼續嗎？</p>
        </div>
      ),
    });

    if (!confirmed) return;
  }

  await updateMutation.mutateAsync(data);
};
```

### P2：資料品質檢查

**匯入時過濾測試資料：**
```python
# backend/app/services/csv_processor.py (已實作)
TEST_PATTERNS = ['test', 'demo', '測試', '範例']

def validate_subject(subject: str) -> bool:
    """驗證主旨是否為有效資料"""
    if not subject or len(subject.strip()) < 5:
        return False
    if any(pattern in subject.lower() for pattern in TEST_PATTERNS):
        logger.warning(f"[資料品質] 主旨疑似測試資料: {subject}")
        return False
    return True
```

### P3：變更通知機制

**關鍵欄位變更時發送通知：**
```python
async def notify_critical_change(
    document_id: int,
    field: str,
    old_value: str,
    new_value: str,
    user_name: str
):
    """關鍵欄位變更通知"""
    message = f"""
    ⚠️ 公文關鍵欄位變更通知

    公文 ID: {document_id}
    變更欄位: {field}
    原始值: {old_value}
    新值: {new_value}
    操作者: {user_name}
    時間: {datetime.now()}
    """
    # 發送 Email、Slack 或其他通知管道
    await send_notification(message)
```

## 三、實作優先級

| 優先級 | 項目 | 狀態 | 完成日期 |
|--------|------|------|----------|
| P0 | 建立 audit_logs 表 | ✅ 完成 | 2026-01-08 |
| P0 | API 加入 user_id 記錄 | ✅ 完成 | 2026-01-08 |
| P1 | 前端關鍵欄位確認對話框 | ✅ 完成 | 2026-01-08 |
| P1 | 審計日誌查詢 API | ✅ 完成 | 2026-01-08 |
| P2 | 匯入資料品質檢查加強 | ✅ 完成 | 2026-01-08 |
| P3 | 變更通知機制 | ✅ 完成 | 2026-01-08 |

## 四、驗收標準

- [x] 所有公文更新操作都有審計日誌記錄
- [x] 審計日誌包含操作者 ID 和名稱
- [x] 修改關鍵欄位時前端顯示確認對話框
- [x] 可查詢特定公文的歷史變更記錄
- [x] 關鍵欄位變更觸發通知（P3）

## 五、相關檔案

- `backend/app/core/audit_logger.py` - 審計日誌核心
- `backend/alembic/versions/create_audit_logs_table.py` - 審計表 Migration
- `backend/app/api/endpoints/documents_enhanced.py` - 公文更新 API
- `frontend/src/components/document/DocumentOperations.tsx` - 公文編輯元件
- `backend/app/services/notification_service.py` - 通知服務核心
- `backend/app/api/endpoints/system_notifications.py` - 系統通知 API
- `frontend/src/components/common/NotificationCenter.tsx` - 前端通知中心 UI
