# CK_Missive 開發指引與架構維護機制

> **重要**: 本文件為開發流程指引，完整的開發規範請參閱
> [`docs/DEVELOPMENT_STANDARDS.md`](../docs/DEVELOPMENT_STANDARDS.md)

---

## 🛠️ 自動化架構維護機制

### 1. 結構驗證工具

**Skills 同步檢查腳本**:
```powershell
# Windows (PowerShell) - 檢查 42 項配置
powershell -File scripts/checks/skills-sync-check.ps1
```
```bash
# Linux/macOS (Bash)
bash scripts/skills-sync-check.sh
```

**前後端路由一致性**:
```powershell
powershell -File .claude/hooks/route-sync-check.ps1
```

**API 序列化檢查**:
```powershell
powershell -File .claude/hooks/api-serialization-check.ps1
```

### 2. 開發前檢查流程
每次開始開發或添加新文件前：

1. **執行 `/pre-dev-check`**: Claude Code 中輸入此指令
2. **閱讀強制檢查清單**: 查看 `.claude/MANDATORY_CHECKLIST.md`
3. **按規範放置文件**: 新文件必須放在正確位置
4. **提交前再檢查**: 確保沒有違反架構規範

### 3. 文件放置決策樹

```
新增文件時請問自己：
├─ 是後端測試？ → backend/tests/
├─ 是腳本工具？ → scripts/
├─ 是部署相關？ → .github/workflows/ 或 docker-compose
├─ 是文件？ → docs/
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

3. **安全快速檢查** (後端 API)
   - 確認無 `str(e)` 出現在 HTTPException detail 或 JSON response 中
   - 所有端點有 `require_auth()` 或 `require_admin()`

4. **檢測無誤後才提出複查**
   - 編譯通過 → 告知使用者可測試
   - 編譯失敗 → 自行修復後重新檢測

### 提交代碼前：
- [ ] 執行 `scripts/checks/skills-sync-check.ps1` 驗證配置同步
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
**解決**: 測試放 `backend/tests/`，工具放 `scripts/`

### 2. 根目錄雜亂
**問題**: 在專案根目錄添加臨時文件
**解決**: 刪除或移動到適當位置

### 3. 開發工具散落
**問題**: 腳本和工具分散在各處
**解決**: 統一歸類到 `scripts/` 目錄

## 🔧 自動化集成

### CI/CD 集成
專案已整合 GitHub Actions CI 流程（`.github/workflows/ci.yml`），包含：
- Skills 同步檢查、前後端編譯、安全掃描、測試覆蓋率等

## 📚 學習資源

1. **強制檢查清單**: `.claude/MANDATORY_CHECKLIST.md` - 開發前必讀
2. **開發規範**: `docs/DEVELOPMENT_STANDARDS.md` - 統一開發規範
3. **Skills 同步驗證**: `scripts/checks/skills-sync-check.ps1` - 自動化檢查
4. **本指引**: 開發流程和最佳實踐

## ⚡ 快速命令

```bash
# Skills 同步檢查
powershell -File scripts/checks/skills-sync-check.ps1

# 前端 TypeScript 檢查
cd frontend && npx tsc --noEmit

# 後端 Python 語法檢查
cd backend && python -m py_compile app/main.py

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

### 6.1 Excel 匯入 upsert 模式缺失 (v1.84.2 新增)

**問題**: `ExcelImportService` 無 `公文ID` 時遇到重複 `doc_number` 只會跳過，無法更新已存在資料。
**臨時解法**: `backend/scripts/fixes/import_112_documents.py` (支援 `--dry-run`)
**長期建議**: 為 `import_from_file()` 新增 `upsert_mode` 參數。

### 6.2 ProjectMatcher 模糊匹配風險 (v1.84.2 新增)

**問題**: ILIKE 模糊匹配無相似度閾值，短名稱可能誤匹配。
**建議**: 加入最低字元數門檻 (>=8 字) 或 Levenshtein 距離比對。

### 6.3 自動建立機關無來源標記 (v1.84.2 新增)

**問題**: `AgencyMatcher._create_agency()` 自動建立的機關無法區分來源。93 個機關中 83 個缺 `agency_code`。
**建議**: 新增 `source` 欄位 (`manual` / `import_auto` / `api_auto`)。

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

**⚠️ 另一種觸發方式 — React Query queryFn 中呼叫 setFieldsValue (v1.61.0 新增)**:

```tsx
// ❌ 錯誤：queryFn 可能在 Form DOM 掛載前執行
const { data } = useQuery({
  queryKey: ['config'],
  queryFn: async () => {
    const result = await api.getConfig();
    form.setFieldsValue(result);  // Form 尚未 mount → 警告
    return result;
  },
});

// ✅ 正確：用 useEffect 等 data 就緒後才 setFieldsValue
const { data } = useQuery({ queryKey: ['config'], queryFn: api.getConfig });
useEffect(() => {
  if (data) form.setFieldsValue(data);
}, [data, form]);
```

**已修復**: `BackupManagementPage.tsx` (v1.61.0)

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

### 8. 🔴 錯誤時清空列表 (Error Clears List) - 嚴重 (2026-02-04 新增)

**錯誤訊息**: 用戶反映「紀錄儲存後消失」、「列表突然清空」

**原因**: 在 `catch` 區塊中呼叫 `setXxx([])` 清空列表，當 API 暫時失敗時，已載入的資料會消失。

**問題流程**:
```
1. 用戶看到列表（資料已載入）
2. 用戶執行操作（新增/編輯）
3. 操作成功後自動重新載入列表
4. 重新載入 API 暫時失敗
5. catch 區塊執行 setItems([])
6. 用戶看到列表消失 ❌
```

**❌ 錯誤做法**:
```typescript
const loadItems = useCallback(async () => {
  setLoading(true);
  try {
    const result = await api.getItems();
    setItems(result.items);
  } catch (error) {
    logger.error('載入失敗:', error);
    setItems([]);  // ❌ 危險：清空已存在的資料
  } finally {
    setLoading(false);
  }
}, []);
```

**✅ 正確做法**:
```typescript
const loadItems = useCallback(async () => {
  setLoading(true);
  try {
    const result = await api.getItems();
    setItems(result.items);
  } catch (error) {
    logger.error('載入失敗:', error);
    // ✅ 不清空列表，保留現有資料
    // setItems([]);
    message.error('載入失敗，請重新整理頁面');
  } finally {
    setLoading(false);
  }
}, [message]);
```

**適用場景**:
| 場景 | 是否清空 | 說明 |
|------|----------|------|
| **詳情頁局部刷新** | ❌ 不清空 | 用戶已看到資料，清空會導致「消失」 |
| **操作後重新載入** | ❌ 不清空 | 操作成功但刷新失敗，應保留資料 |
| **頁面初始載入** | ⚠️ 視情況 | 新頁面無舊資料，可清空 |
| **切換實體（如換專案）** | ✅ 可清空 | 避免顯示舊實體的資料 |

**已修復的檔案** (v1.35.0):
- `DocumentDetailPage.tsx` - loadDispatchLinks, loadProjectLinks
- `useDocumentRelations.ts` - useDispatchLinks, useProjectLinks
- `StaffDetailPage.tsx` - loadCertifications
- `ReminderSettingsModal.tsx` - loadReminders

**測試要求**:
所有新增的載入函數必須包含「錯誤時保留資料」的測試：
```typescript
it('API 錯誤時應該保留現有資料，不清空列表', async () => {
  // 1. 首次成功載入
  mockApi.mockResolvedValueOnce({ items: [mockItem] });
  await act(() => result.current.refresh());
  expect(result.current.items).toHaveLength(1);

  // 2. 第二次 API 錯誤
  mockApi.mockRejectedValueOnce(new Error('Network Error'));
  await act(() => result.current.refresh());

  // 3. 關鍵斷言：資料仍然保留
  expect(result.current.items).toHaveLength(1);
});
```

### 9. 🔴 交易污染 (Transaction Pollution) - 嚴重

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
- `backend/app/api/endpoints/documents/crud.py` - update_document, delete_document
- `backend/app/services/audit_service.py` - AuditService.log_document_change
- `backend/app/services/notification_service.py` - notify_critical_change

詳細說明請參考: `docs/ERROR_HANDLING_GUIDE.md`

### 10. 🔴 useEffect 中直接呼叫 API 造成無限迴圈 - 嚴重

**錯誤訊息**: 無明確前端錯誤，但後端日誌出現同一端點每秒 5-10 次請求，最終 OOM 導致 ERR_EMPTY_RESPONSE

**原因**: useEffect 依賴陣列中包含會因 API 回應而改變的值（如 `total`, `data.length`），形成無限觸發迴圈。

**問題流程**:
```
1. useEffect 觸發 → 呼叫 API
2. API 回應 → setState (e.g., setFilteredStats)
3. 元件 re-render → 依賴值改變 (e.g., total prop)
4. useEffect 再次觸發 → 回到步驟 1
5. ~10 req/sec → 後端 OOM → 全系統 ERR_EMPTY_RESPONSE
```

**❌ 錯誤做法**:
```typescript
useEffect(() => {
  const fetchStats = async () => {
    const stats = await api.getFilteredStatistics(params);
    setFilteredStats(stats);
  };
  fetchStats();
}, [filters.search, filters.doc_type, total]);  // ← total 會因 API 回應而變！
```

**✅ 正確做法**:
```typescript
useEffect(() => {
  const fetchStats = async () => {
    const stats = await api.getFilteredStatistics(params);
    setFilteredStats(stats);
  };
  fetchStats();
}, [filters.search, filters.doc_type]);
// 只依賴「使用者主動變更」的篩選條件，不依賴 API 回應值
```

**判斷規則**:

| 可以放入依賴陣列 | 禁止放入依賴陣列 |
|------------------|------------------|
| 使用者輸入的篩選條件 | API 回應的 total / count |
| URL 參數 (id, page) | 從 API 回應衍生的 state |
| 使用者選擇的 tab | data.length |
| 表單值 | loading 狀態 |

**相關事故**: 2026-02-06 DocumentTabs.tsx 無限迴圈導致後端 OOM，全系統連鎖崩潰

### 11. 🟡 重構或刪除模組時遺漏引用

**錯誤訊息**: `ImportError: cannot import name 'xxx' from 'yyy'`

**原因**: 重命名/刪除/移動 Python 模組或函數後，未全域搜尋並更新所有引用點。

**❌ 錯誤做法**: 直接刪除 `get_vendor_service` 函數，未檢查其他檔案的 import。

**✅ 正確做法**:
```bash
# 刪除或移動前，先全域搜尋所有引用
grep -r "get_vendor_service" backend/
# 確認每個引用點都已更新後，才刪除原始定義
```

**相關事故**: 2026-02-06 vendors.py ImportError 導致後端啟動失敗

### 12. 🔴 slowapi @limiter.limit 參數命名衝突 (v1.61.0 新增)

**錯誤訊息**: `parameter 'request' must be an instance of starlette.requests.Request`

**原因**: slowapi 的 `@limiter.limit` 裝飾器會在端點參數中搜尋名為 `request` 且型別為 `Request` 的參數。若 Pydantic body 參數也命名為 `request`，slowapi 會找到錯誤的參數。

**❌ 錯誤做法**:
```python
@limiter.limit("5/minute")
async def create_backup(
    http_request: Request,           # ← slowapi 找不到（名字不是 request）
    response: Response,
    request: CreateBackupRequest,    # ← slowapi 找到了但型別錯誤 → 500
):
```

**✅ 正確做法**:
```python
@limiter.limit("5/minute")
async def create_backup(
    request: Request,               # ← slowapi 正確找到
    response: Response,
    body: CreateBackupRequest,      # ← body 參數不命名為 request
):
```

**強制規則**:
- 所有 `@limiter.limit` 裝飾的端點必須有 `request: Request` 參數
- 所有 `@limiter.limit` 裝飾的端點必須有 `response: Response` 參數
- Pydantic body 參數命名為 `body`，**不可**命名為 `request`

**相關事故**: 2026-02-24 備份管理頁面 5 個端點全部 500

### 13. 🟡 硬編碼 API 路徑 (v1.79.0 新增)

**錯誤**: API 端點定義存在但呼叫處直接寫死字串路徑，或用字串拼接構建動態路徑。

**原因**: 新增 API 呼叫時未查閱 `endpoints.ts`，直接硬編碼路徑。

**❌ 錯誤做法**:
```typescript
// 硬編碼靜態路徑
apiClient.post('/projects/list', params);
this.axios.post('/auth/login', formData);

// 字串拼接動態路徑（端點定義為靜態字串）
apiClient.post(`${AI_ENDPOINTS.ANALYSIS}/${documentId}`);
```

**✅ 正確做法**:
```typescript
// 使用端點常數
apiClient.post(PROJECTS_ENDPOINTS.LIST, params);
this.axios.post(AUTH_ENDPOINTS.LOGIN, formData);

// 使用函數型端點
apiClient.post(AI_ENDPOINTS.ANALYSIS_GET(documentId));
```

**防護機制**:
- `endpoints.test.ts` 端點唯一性測試：自動偵測重複靜態值
- `endpoints.test.ts` 服務匯入測試：驗證 12 個 API 服務檔案正確匯入
- 清單 L (`MANDATORY_CHECKLIST.md`)：開發前必須確認端點已定義

**相關事故**: 2026-03-06 發現 21 處硬編碼路徑，v1.79.0 全部消除

### 15. 🟡 Endpoint 本地 BaseModel 違反 SSOT (v1.83.5 新增)

**錯誤**: 在 `api/endpoints/` 檔案中定義本地 Pydantic BaseModel，而非從 `schemas/` 匯入。

**原因**: 新增 API 端點時直接就地定義回應型別，未遵循 Schema SSOT 架構。

**已知違規位置**:

| 檔案 | 本地 BaseModel | 應移至 |
|------|---------------|--------|
| `ai/ai_stats.py` | `ToolSuccessRateItem`, `ToolSuccessRatesResponse`, `DailyTrendItem`, `DailyTrendResponse` | `schemas/ai/stats.py` (新建) |
| `line_webhook.py` | `WebhookResponse` | `schemas/line.py` (已存在) |
| `taoyuan_dispatch/dispatch_document_links.py` | `ConfirmCorrespondenceRequest` | `schemas/taoyuan/` |

**❌ 錯誤做法**:
```python
# 在 endpoints/ 中直接定義
class ToolSuccessRateItem(BaseModel):
    tool_name: str
    success_rate: float
```

**✅ 正確做法**:
```python
# schemas/ai/stats.py
class ToolSuccessRateItem(BaseModel):
    tool_name: str
    success_rate: float

# endpoints/ai/ai_stats.py
from app.schemas.ai.stats import ToolSuccessRateItem
```

**自動化檢查**:
```bash
# 搜尋 endpoints/ 中的本地 BaseModel 定義
grep -rn "class.*BaseModel" backend/app/api/endpoints/ --include="*.py" | grep -v __pycache__
```

---

### 13.5. 🟡 服務層遷移檢查清單 (v1.60.0)

將端點業務邏輯遷移至 Service 層時，必須按以下順序執行：

**遷移步驟**:
1. 建立/擴充 Service 類別方法（業務邏輯）
2. 建立/擴充 Repository 方法（DB 操作）
3. 更新端點：呼叫 Service 取代直接 db 操作
4. 移除端點中的 `db: AsyncSession = Depends(get_async_db)` 依賴
5. 清理 unused imports（`AsyncSession`, `select`, `func` 等）
6. 執行 `grep -r "舊函數名" backend/` 確認無遺漏引用

**檢查清單**:
- [ ] Service 方法是否封裝了完整業務邏輯？
- [ ] 端點是否改用 `Depends(get_service(ServiceClass))`？
- [ ] 端點是否已移除直接 `db.execute()` 呼叫？
- [ ] Repository 方法是否處理 `db.commit()` 和 `db.refresh()`？
- [ ] 前端 API 型別是否只做 re-export（無本地 interface）？
- [ ] deprecated 路由是否已清除？

### 14. 🟡 前端型別遷移注意事項 (v1.60.0)

將 `api/*.ts` 中的本地型別遷移至 `types/*.ts` 時：

**注意事項**:
- `export *` 的 re-export **不會**在同檔案內建立可引用的名稱
- 同檔案引用其他 types 模組的型別時，使用 inline import：
  ```typescript
  // types/api.ts 內需引用 types/admin-system.ts 的型別
  export interface ContactListResponse {
    items: import('./admin-system').ProjectAgencyContact[];  // ✅
  }
  ```
- 確保消費端可從原路徑（`api/*.ts`）或新路徑（`types/*.ts`）匯入
- 元件應直接從 `types/` 匯入型別，從 `api/` 匯入 API 函數

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

## 🔒 錯誤訊息安全規範 (v1.76.1 新增)

### 核心規則：禁止 `str(e)` 暴露至客戶端

所有後端 API 端點的錯誤處理，**禁止**將例外訊息 `str(e)` 傳遞給客戶端。

**❌ 禁止做法**:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"操作失敗: {str(e)}")

except Exception as e:
    return {"success": False, "message": f"失敗: {str(e)}"}
```

**✅ 正確做法**:
```python
except Exception as e:
    logger.error(f"操作失敗: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="操作失敗，請稍後再試")

except Exception as e:
    logger.error(f"操作失敗: {e}", exc_info=True)
    return {"success": False, "message": "操作失敗，請稍後再試"}
```

**規則摘要**:

| 項目 | 規範 |
|------|------|
| `HTTPException(detail=...)` | 使用通用中文錯誤訊息，不含 `str(e)` |
| JSON response error | 使用 `"message": "通用描述"` |
| 伺服器端記錄 | `logger.error(f"描述: {e}", exc_info=True)` |
| ValueError 等業務錯誤 | 可使用預定義的業務錯誤訊息，不暴露堆疊 |

**自動化檢查**:
```bash
# 掃描殘留的 str(e) 洩漏
grep -rn "str(e)" backend/app/api/endpoints/ --include="*.py" | grep -v __pycache__ | grep -v "logger"
```

**相關事故**: 2026-03-03 安全審計發現 54+ 處 str(e) 洩漏，v1.76.1 全面修復

---

## 🤖 Agent 開發前置檢查清單 (2026-02-26 新增)

新增或修改 Agent 工具、SSE 事件、合成邏輯前，須逐項確認：

### 新增工具
- [ ] 後端 `agent_tools.py` 的 `TOOL_DEFINITIONS` 已新增工具描述
- [ ] 後端 `agent_tools.py` 的 `AgentToolExecutor` 已新增實作方法 `_tool_name`
- [ ] 前端 `RAGChatPanel.tsx` 的 `TOOL_ICONS` 已加入工具圖示
- [ ] 前端 `RAGChatPanel.tsx` 的 `TOOL_LABELS` 已加入中文標籤
- [ ] 工具描述足夠讓 LLM 正確選擇（含使用時機說明）

### 修改 SSE 事件
- [ ] 所有推理事件（thinking/tool_call/tool_result）包含 `step_index`
- [ ] error 事件包含 `code` 分類碼（RATE_LIMITED/SERVICE_ERROR/TIMEOUT/VALIDATION_ERROR）
- [ ] 前端 `adminManagement.ts` 的 callback 簽章與後端事件欄位一致
- [ ] 前端 `RAGChatPanel.tsx` 的 `AgentStepInfo` 型別同步更新

### 合成品質
- [ ] `_strip_thinking_from_synthesis()` 能正確處理新工具的輸出格式
- [ ] 閒聊偵測邏輯不會攔截新工具對應的業務查詢
- [ ] 測試至少包含：正常回答、含 [公文N] 引用、含 [派工單N] 引用、大量思考鏈

---

## ✅ Code Review Checklist (2026-02-04 更新)

### 🆕 前端錯誤處理檢查 (2026-02-04 新增)
- [ ] **catch 區塊是否清空列表？** - 禁止在 catch 中 `setXxx([])`
- [ ] 錯誤時是否保留現有資料？
- [ ] 是否顯示錯誤訊息通知用戶？
- [ ] 是否有對應的「錯誤時保留資料」測試？

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
| `app/services/system_health_service.py` | 系統健康檢查服務 (v1.0.0, 2026-02-24) |
| `app/services/ai/relation_graph_service.py` | 知識圖譜建構服務 (v1.0.0, 2026-02-24) |
| `app/services/backup_scheduler.py` | 備份排程器 + 異地自動同步 (v2.0.0, 2026-02-24) |
| `app/services/backup/` | 備份服務套件 (utils/db/attachment/scheduler Mixin) |
| `app/core/decorators.py` | 通用裝飾器 (@non_critical, @retry_on_failure) |
| `app/core/background_tasks.py` | 背景任務管理器 |
| `app/core/db_monitor.py` | 連接池監控器 |
| `app/core/navigation_validator.py` | 導覽路徑白名單驗證器 (2026-01-12) |

### 健康檢查端點

> **BREAKING CHANGE (v1.60.0)**: `/health/detailed`, `/health/pool`, `/health/tasks`, `/health/audit`, `/health/backup`, `/health/summary` 已從 `require_auth` 提升為 `require_admin` 權限。僅 `/health` 基本端點維持公開。

| 端點 | 說明 | 權限 |
|------|------|------|
| `GET /health` | 基本健康檢查 | 公開 |
| `GET /health/detailed` | 詳細健康報告 | **admin** |
| `GET /health/pool` | 連接池狀態 | **admin** |
| `GET /health/tasks` | 背景任務狀態 | **admin** |
| `GET /health/audit` | 審計服務狀態 | **admin** |
| `GET /health/backup` | 備份系統狀態 (排程器/連續失敗/異地同步) | **admin** |
| `GET /health/summary` | 系統健康摘要 (含備份狀態) | **admin** |

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

---

## Git Commit 粒度規範

### 原則：一個 commit 做一件事

每個 commit 應聚焦於單一邏輯變更。避免將多個不相關功能打包進同一 commit。

### 良好範例

```
feat: PM 案件附件上傳功能
fix: LINE OAuth state mismatch
refactor: document_service 拆分 dispatch_linker
perf: knowledge graph staleTime 5min + limit 150
```

### 應避免

```
# 不良：多個不相關變更混在一起
feat: PM重定位 + 統一模板 + 委託單位 + 行事曆批次 + Code-graph
```

### 拆分策略

| 情境 | 建議 |
|------|------|
| 新功能 + 相關測試 | 同一 commit (feat: xxx) |
| 新功能 + 無關重構 | 分開 commit |
| DB 遷移 + 對應 ORM | 同一 commit |
| 前端頁面 + 後端 API | 可同一 commit (如果是同一功能) |
| Bug 修復 + 順手重構 | 分開 commit |

### 好處

- `git bisect` 可精確定位 regression
- Code review 更容易理解
- Cherry-pick / revert 更安全
- CHANGELOG 自動生成更精準

---

## 服務行數監控

後端服務檔案行數閾值 **600L**，超過時 CI 會發出警告。

```bash
# 手動執行行數檢查
python scripts/checks/service-line-count-check.py --threshold 600

# CI 模式（超過閾值時失敗）
python scripts/checks/service-line-count-check.py --threshold 600 --fail-on-warn
```

當服務超過 600L 時，考慮拆分策略：
- 提取 helper/utility 到獨立模組
- 將子功能拆分為 sub-service
- 使用策略模式分離不同邏輯分支

---

## AuditableServiceMixin 使用規範

新增/修改 Service 層 CRUD 操作時，應使用 `AuditableServiceMixin` 自動記錄審計日誌。

```python
from app.services.audit_mixin import AuditableServiceMixin

class VendorService(AuditableServiceMixin):
    AUDIT_TABLE = "partner_vendors"

    async def create_vendor(self, data, user_id=None):
        vendor = await self.repository.create(data)
        await self.audit_create(vendor.id, data, user_id=user_id)
        return vendor
```

已套用服務 (10 個): agency, vendor, case_code, document, project, billing, invoice, quotation, vendor_payable, expense_invoice, finance_ledger

---

💡 **記住**: 保持架構規範不僅讓專案更整潔，也讓團隊協作更順暢！