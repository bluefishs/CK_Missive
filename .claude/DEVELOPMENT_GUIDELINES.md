# CK_Missive 開發指引與架構維護機制

> **重要**: 本文件為開發流程指引，完整的開發規範請參閱
> [`docs/DEVELOPMENT_STANDARDS.md`](../docs/DEVELOPMENT_STANDARDS.md)

---

## 🛠️ 自動化架構維護機制

### 1. 結構驗證工具
**Python 驗證器**: `claude_plant/development_tools/validation/validate_structure.py`
```bash
# 執行結構檢查
python claude_plant/development_tools/validation/validate_structure.py
```

**PowerShell 驗證器**: `claude_plant/development_tools/scripts/structure_check.ps1`
```powershell
# 僅檢查
.\claude_plant\development_tools\scripts\structure_check.ps1

# 檢查並自動修復
.\claude_plant\development_tools\scripts\structure_check.ps1 -Fix
```

### 2. 開發前檢查流程
每次開始開發或添加新文件前：

1. **閱讀架構規範**: 查看 `STRUCTURE.md`
2. **執行結構檢查**: 運行驗證工具確認當前狀態
3. **按規範放置文件**: 新文件必須放在正確位置
4. **提交前再檢查**: 確保沒有違反架構規範

### 3. 文件放置決策樹

```
新增文件時請問自己：
├─ 是測試文件？ → claude_plant/development_tools/tests/
├─ 是腳本工具？ → claude_plant/development_tools/scripts/
├─ 是部署相關？ → claude_plant/development_tools/deployment/
├─ 是維護工具？ → claude_plant/development_tools/maintenance/
├─ 是備份文件？ → claude_plant/development_tools/backup/
├─ 是開發文檔？ → claude_plant/development_tools/docs/
├─ 是核心後端代碼？ → backend/app/
└─ 是前端代碼？ → frontend/src/
```

## 📋 開發檢查清單

### 新增文件前：
- [ ] 確認文件類型和用途
- [ ] 檢查 STRUCTURE.md 規範
- [ ] 選擇正確的目錄位置
- [ ] 使用描述性文件名

### ⚠️ 程式碼修改後（必要流程）：
**修正後必須先自我檢測，確認無誤後再提出複查要求**

1. **TypeScript 編譯檢查** (前端)
   ```bash
   cd frontend && npx tsc --noEmit
   ```

2. **Python 語法檢查** (後端)
   ```bash
   cd backend && python -m py_compile app/main.py
   ```

3. **檢測無誤後才提出複查**
   - 編譯通過 → 告知使用者可測試
   - 編譯失敗 → 自行修復後重新檢測

### 提交代碼前：
- [ ] 執行 `validate_structure.py` 檢查
- [ ] 確保沒有在禁止位置添加文件
- [ ] 確認 backend/ 目錄保持純淨
- [ ] 檢查是否有臨時或測試文件留在不當位置

### 週期性維護：
- [ ] 每週執行一次結構檢查
- [ ] 清理不需要的臨時文件
- [ ] 整理歸檔舊的開發文件
- [ ] 更新開發工具和腳本

## 🚨 常見違規情況與解決方案

### 1. Backend 目錄污染
**問題**: 在 backend/ 中添加測試或工具文件
**解決**: 移動到 `claude_plant/development_tools/` 對應子目錄

### 2. 根目錄雜亂
**問題**: 在專案根目錄添加臨時文件
**解決**: 刪除或移動到適當位置

### 3. 開發工具散落
**問題**: 腳本和工具分散在各處
**解決**: 統一歸類到 `claude_plant/development_tools/`

## 🔧 自動化集成

### Git Hooks (建議)
在 `.git/hooks/pre-commit` 中添加：
```bash
#!/bin/sh
echo "🔍 檢查專案結構..."
python claude_plant/development_tools/validation/validate_structure.py
if [ $? -ne 0 ]; then
    echo "❌ 專案結構檢查失敗，請修正後再提交"
    exit 1
fi
```

### CI/CD 集成
在 CI 流程中添加結構檢查步驟：
```yaml
- name: Validate Project Structure
  run: python claude_plant/development_tools/validation/validate_structure.py
```

## 📚 學習資源

1. **架構規範**: `STRUCTURE.md` - 完整的目錄結構說明
2. **驗證工具**: `validate_structure.py` - 自動化檢查腳本
3. **修復腳本**: `structure_check.ps1` - PowerShell 自動修復工具
4. **本指引**: 開發流程和最佳實踐

## ⚡ 快速命令

```bash
# 結構檢查
python claude_plant/development_tools/validation/validate_structure.py

# PowerShell 檢查和修復
.\claude_plant\development_tools\scripts\structure_check.ps1 -Fix

# 查看架構規範
cat STRUCTURE.md

# 查看本指引
cat .claude/DEVELOPMENT_GUIDELINES.md
```

---

## 🛡️ 資料品質管理 Skills

本專案提供以下 Claude Code Skills 來管理資料品質：

### 可用 Skills

| Skill | 說明 | 指令 |
|-------|------|------|
| `/data-quality-check` | 資料品質檢查 | 執行公文資料完整性檢查 |
| `/db-backup` | 資料庫備份管理 | 備份、還原、排程設定 |
| `/csv-import-validate` | CSV 匯入驗證 | 驗證並匯入公文 CSV |

### 快速使用

```bash
# 資料品質檢查
在 Claude Code 中輸入: /data-quality-check

# 資料庫備份
在 Claude Code 中輸入: /db-backup

# CSV 匯入驗證
在 Claude Code 中輸入: /csv-import-validate
```

### Skill 檔案位置

```
.claude/commands/
├── data-quality-check.md   # 資料品質檢查
├── db-backup.md            # 資料庫備份管理
└── csv-import-validate.md  # CSV 匯入驗證
```

---

## 📊 資料驗證規範

### 公文類型 (doc_type) 白名單

```python
VALID_DOC_TYPES = ['函', '開會通知單', '會勘通知單', '書函', '公告', '令', '通知']
```

### 公文類別 (category) 規範

```python
VALID_CATEGORIES = ['收文', '發文']

# 類別與欄位連動規則
if category == '收文':
    required_fields = ['receiver', 'receive_date']
    default_receiver = '本公司'
elif category == '發文':
    required_fields = ['sender', 'send_date']
    default_sender = '本公司'
```

### 字串清理規範

**重要**: 避免 `str(None)` 產生 "None" 字串

```python
def clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in ('none', 'null', ''):
        return None
    return text
```

---

## 🚨 常見錯誤與修復

### 1. 批次匯入流水號重複
**錯誤**: `duplicate key value violates unique constraint "documents_auto_serial_key"`
**解法**: 使用記憶體計數器追蹤已生成的流水號

### 2. 字串欄位存在 "None"
**原因**: `str(None)` 產生 "None" 字串
**解法**: 使用 `_clean_string()` 方法過濾

### 3. DOM 巢狀警告
**錯誤**: `<div> cannot appear as descendant of <p>`
**解法**: 將 `<p>` 改為 `<div>` 容器

### 4. 導覽列與網站管理不一致
**原因**: 修改了錯誤的佈局元件（DynamicLayout.tsx 而非 Layout.tsx）
**解法**:
- AppRouter 使用 `Layout.tsx`，**非** `DynamicLayout.tsx`
- 修改導覽相關功能時，必須修改 `Layout.tsx`
- 確保 `Layout.tsx` 監聽 `navigation-updated` 事件

### 5. 導覽更新後頁面未即時反映
**原因**: 缺少事件監聽器
**解法**: 在 Layout.tsx 加入事件監聽：
```typescript
useEffect(() => {
  const handleNavigationUpdate = () => {
    loadNavigationData(); // 重新載入導覽資料
  };
  window.addEventListener('navigation-updated', handleNavigationUpdate);
  return () => {
    window.removeEventListener('navigation-updated', handleNavigationUpdate);
  };
}, []);
```

### 6. 機關關聯遺失
**原因**: 匯入時未使用智慧匹配
**解法**: 整合 `AgencyMatcher` / `ProjectMatcher`

### 6.5 Antd Modal useForm 警告 (2026-01-29 新增)
**錯誤**: `Warning: Instance created by useForm is not connected to any Form element`
**原因**: 在 Modal 組件中使用 `Form.useForm()`，當 `open=false` 時 Modal 內容不渲染，但 hook 已執行

**❌ 錯誤做法**:
```tsx
const MyModal = ({ visible }) => {
  const [form] = Form.useForm();  // Hook 立即執行

  return (
    <Modal open={visible}>  {/* visible=false 時內容不渲染 */}
      <Form form={form}>...</Form>
    </Modal>
  );
};
```

**✅ 正確做法 - 使用 forceRender**:
```tsx
const MyModal = ({ visible }) => {
  const [form] = Form.useForm();

  return (
    <Modal open={visible} forceRender>  {/* 強制渲染內容 */}
      <Form form={form}>...</Form>
    </Modal>
  );
};
```

**已修復的組件** (v1.14.0):
- `UserPermissionModal.tsx`
- `UserEditModal.tsx`
- `DocumentOperations.tsx`
- `DocumentSendModal.tsx`
- `SequenceNumberGenerator.tsx`
- `ProjectVendorManagement.tsx`
- `SiteConfigManagement.tsx`
- `NavigationItemForm.tsx`

### 7. 導覽路徑不一致 (2026-01-12 新增)
**錯誤**: 導覽選單點擊後顯示 404 或空白頁面
**原因**: 資料庫中的導覽路徑與前端 ROUTES 定義不一致
**解法**:
- 使用 `/route-sync-check` 指令檢查路徑一致性
- 修正資料庫中的導覽路徑
- 使用 `init_navigation_data.py --force-update` 強制同步

**預防機制**:
- 後端 API 內建路徑白名單驗證（`navigation_validator.py`）
- 前端 SiteManagementPage 使用下拉選單選擇路徑
- 新增前端路由時，同步更新 `navigation_validator.py` 白名單

### 8. 🔴 交易污染 (Transaction Pollution) - 嚴重

**錯誤訊息**: `InFailedSQLTransactionError: current transaction is aborted, commands ignored until end of transaction block`

**原因**: 在 `db.commit()` 後繼續使用同一個 session 執行其他操作（如審計日誌、通知），若這些操作失敗，session 狀態變為 "aborted"，被歸還連接池後污染後續請求。

**流程圖解**:
```
1. update_document() 使用 db session
2. await db.commit()  ← 主交易成功
3. await log_audit(db, ...)  ← 使用同一個 session
4. 如果步驟 3 失敗 → session 狀態 = "aborted"
5. session 歸還連接池（帶著錯誤狀態）
6. 下一個請求拿到這個 session → 所有 SQL 都失敗
```

**❌ 錯誤做法**:
```python
async def update_document(db: AsyncSession, ...):
    await db.execute(update_stmt)
    await db.commit()  # 交易結束

    # 危險！使用同一個 session
    await log_document_change(db, ...)  # 失敗會污染 session
```

**✅ 正確做法 - 使用統一服務 (2026-01-09 更新)**:
```python
async def update_document(db: AsyncSession, ...):
    await db.execute(update_stmt)
    await db.commit()  # 主交易結束

    # ✅ 使用 AuditService（自動使用獨立 session）
    from app.services.audit_service import AuditService
    await AuditService.log_document_change(
        document_id=doc_id,
        action="UPDATE",
        changes=changes,
        user_id=user_id,
        user_name=user_name
    )

    # ✅ 使用 safe_* 方法（自動使用獨立 session）
    from app.services.notification_service import NotificationService
    await NotificationService.safe_notify_critical_change(
        document_id=doc_id,
        field="subject",
        old_value=old_val,
        new_value=new_val
    )
```

**可用的安全服務**:

| 服務 | 方法 | 說明 |
|------|------|------|
| `AuditService` | `log_change()` | 通用審計日誌 |
| `AuditService` | `log_document_change()` | 公文審計日誌 |
| `NotificationService` | `safe_notify_critical_change()` | 關鍵欄位變更通知 |
| `NotificationService` | `safe_notify_document_deleted()` | 公文刪除通知 |

**核心原則**:
| 原則 | 說明 |
|------|------|
| Session 生命週期 | 一個 request = 一個 session，用完即還 |
| 非關鍵操作隔離 | 審計、通知等使用獨立 session |
| 不重用 committed session | commit 後不要再用同一個 session 做新操作 |
| 錯誤邊界清晰 | 每個 session 有自己的 try-except-rollback |

**相關檔案**:
- `backend/app/api/endpoints/documents_enhanced.py` - update_document, delete_document
- `backend/app/core/audit_logger.py` - log_document_change
- `backend/app/services/notification_service.py` - notify_critical_change

詳細說明請參考: `docs/ERROR_HANDLING_GUIDE.md`

---

## 📁 相關文件

| 文件 | 說明 |
|------|------|
| `docs/TODO.md` | 待辦事項與規劃 |
| `docs/ERROR_HANDLING_GUIDE.md` | 錯誤處理指南 |
| `docs/reports/SYSTEM_SPECIFICATION_UPDATE_20260108.md` | 系統規範更新 |
| `docs/wiki/Service-Layer-Architecture.md` | 服務層架構 |
| `docs/DATABASE_SCHEMA.md` | 資料庫結構 |

---

---

## ✅ Code Review Checklist (2026-01-09)

### 交易安全檢查
- [ ] 審計/通知操作是否使用 `AuditService` 或 `safe_*` 方法？
- [ ] 是否有在 `db.commit()` 後繼續使用同一個 session？
- [ ] 非核心操作是否有完整異常處理？

### SQL 安全檢查
- [ ] 參數綁定是否使用 `:param` 格式？
- [ ] JSON 轉型是否使用 `CAST(:data AS jsonb)` 而非 `:data::jsonb`？
- [ ] 是否有 SQL 注入風險？

### 錯誤處理檢查
- [ ] 是否使用 `@non_critical` 裝飾器包裝非關鍵操作？
- [ ] 失敗時是否有適當的日誌記錄？
- [ ] 錯誤訊息是否足夠清晰以便排查？

### 效能檢查
- [ ] 是否有 N+1 查詢問題？
- [ ] 是否有不必要的資料庫往返？
- [ ] 背景任務是否適當使用？

### 測試檢查
- [ ] 是否有對應的單元測試？
- [ ] 是否測試了異常情境？
- [ ] 測試是否涵蓋邊界條件？

---

## 🆕 新增服務與工具 (2026-01-12 更新)

### 核心服務

| 檔案 | 說明 |
|------|------|
| `app/services/audit_service.py` | 統一審計服務（獨立 session） |
| `app/core/decorators.py` | 通用裝飾器 (@non_critical, @retry_on_failure) |
| `app/core/background_tasks.py` | 背景任務管理器 |
| `app/core/db_monitor.py` | 連接池監控器 |
| `app/core/navigation_validator.py` | 導覽路徑白名單驗證器 (2026-01-12) |

### 健康檢查端點

| 端點 | 說明 |
|------|------|
| `GET /health` | 基本健康檢查 |
| `GET /health/detailed` | 詳細健康報告 |
| `GET /health/pool` | 連接池狀態 |
| `GET /health/tasks` | 背景任務狀態 |
| `GET /health/audit` | 審計服務狀態 |
| `GET /health/summary` | 系統健康摘要 |

### 使用範例

```python
# 非關鍵操作裝飾器
from app.core.decorators import non_critical, retry_on_failure

@non_critical(default_return=False)
async def send_email_notification():
    # 失敗不影響主流程
    ...

@retry_on_failure(max_retries=3, delay=1.0)
async def call_external_api():
    # 自動重試
    ...

# 背景任務
from app.core.background_tasks import BackgroundTaskManager

BackgroundTaskManager.add_audit_task(
    background_tasks,
    table_name="documents",
    record_id=doc_id,
    action="UPDATE",
    changes=changes
)
```

---

💡 **記住**: 保持架構規範不僅讓專案更整潔，也讓團隊協作更順暢！