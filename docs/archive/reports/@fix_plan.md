# CK_Missive Fix Plan

## 🔴 High Priority (核心功能)
- [x] 公文管理頁面 - DocumentList 排序篩選功能 (Ant Design Table)
- [x] 承攬案件列表 - ContractCasePage 顯示與 CRUD 功能
- [x] 案件詳情頁 - ContractCaseDetailPage 四個 TAB 分頁整合 (承辦同仁、協力廠商 CRUD)
- [x] 廠商管理 - VendorPage 列表與編輯功能 (POST-only API)
- [x] 機關單位 - AgenciesPage 列表與編輯功能 (POST-only API)

## 🟡 Medium Priority (進階功能)
- [ ] 行事曆整合 - CalendarPage 與公文事件連動
- [ ] 發文字號管理 - DocumentNumbersPage 自動編號
- [ ] 公文匯入/匯出 - DocumentImportPage, DocumentExportPage
- [ ] 使用者權限管理 - UserManagementPage, PermissionManagementPage
- [ ] Dashboard 統計圖表優化

## 🟢 Low Priority (優化項目)
- [ ] 前端效能優化 - 減少 API 重複呼叫
- [ ] 錯誤處理強化 - 統一錯誤訊息格式
- [ ] TypeScript 型別完善
- [ ] 響應式設計調整
- [ ] 單元測試覆蓋

## ✅ Completed
- [x] Project initialization
- [x] Ralph 專案初始化
- [x] CodeWiki 文檔建立 (docs/wiki/)
- [x] Docker 容器環境確認
- [x] Dashboard API 驗證 (502 公文資料正常)
- [x] DocumentActions 組件修復 (EyeOutlined 錯誤)
- [x] API CORS 設定修復
- [x] project-vendors API 500 錯誤修復
- [x] DocumentList 欄位排序與篩選機制 (Ant Design Table)
- [x] API 回應格式轉換修復 (documents.ts)
- [x] DocumentList 欄寬最適比例優化 + Tooltip
- [x] ContractCasePage 案件性質 (category) 標籤顯示對應 (01→01委辦案件等)
- [x] Vendors API 認證問題修復 (移除 GET list 認證需求)
- [x] ProjectStaff 角色驗證修復 (擴展 role validator 支援前端選項)
- [x] 422 Pydantic 錯誤處理修復 (ContractCaseDetailPage 錯誤訊息解析)
- [x] 協力廠商業務類別更新 (測量業務、系統業務、查估業務、其他類別)
- [x] 廠商管理營業項目欄位 CRUD 對應完成 (VendorList + schema validation)
- [x] 承辦同仁專案角色更新 (計畫主持、計畫協同、專案PM、職安主管)
- [x] StaffPage 與 ContractCaseDetailPage 角色選項同步
- [x] StaffPage CRUD 功能修復 (users.py 完整 CRUD + schema 對應)
- [x] 公文管理頁面優化 - 刪除重複儀表板、修正收發文統計、篩選區收闔
- [x] API trailing slash 修復 - vendors.py, users.py, project_staff.py, project_vendors.py 路由路徑改為空字串避免 307/404
- [x] ContractCaseDetailPage TAB CRUD 功能恢復正常 (承辦同仁、協力廠商選單載入)
- [x] **API 架構重構 (POST-only 資安機制)** - 統一回應格式與服務層機制

### 🆕 2026-01-05 新增完成項目
- [x] **流水序號 (auto_serial) 格式修復** - 重設為 R0001~R0334, S0001~S0169
- [x] **ORM 模型欄位補齊** - OfficialDocument 新增 auto_serial Column
- [x] **Schema 型別修正** - auto_serial: Optional[int] → Optional[str]
- [x] **收發單位顯示優化** - extractAgencyName() 提取機關名稱 (無代碼)
- [x] **公文-專案關聯** - 智能比對關聯 211 筆公文到承攬案件
- [x] **API 回應擴充** - contract_project_name, assigned_staff 欄位
- [x] **前端欄位新增** - 承攬案件、業務同仁欄位顯示
- [x] **篩選功能修復** - category TAB 篩選正確傳遞後端

### 🆕 2026-01-06 新增完成項目
- [x] **TypeScript 編譯錯誤修復** - DocumentList, DocumentFilter, UnifiedTable 等組件
- [x] **資料對應錯誤修正** - 修復 id=1, id=222 公文主旨對應問題
- [x] **CSV 匯入驗證強化** - csv_processor.py 新增格式驗證、測試資料過濾
- [x] **資料庫每日備份機制** - PowerShell/Bash 自動備份腳本 + 排程設定

---

## 🏗️ API Architecture (POST-only 資安機制)

### 設計原則
1. **POST-only 端點**: 所有資料操作使用 POST 方法，避免 URL 參數洩漏敏感資訊
2. **統一回應格式**: `{ success: true, items: [...], pagination: {...} }`
3. **分頁機制**: page/limit 分頁取代 skip/limit，前端友善
4. **服務層分離**: API → Service → Repository 三層架構

### 後端 API 端點規範 (Backend)

| 資源 | 列表 | 詳情 | 建立 | 更新 | 刪除 |
|------|------|------|------|------|------|
| agencies | POST `/list` | POST `/{id}/detail` | POST `` | POST `/{id}/update` | POST `/{id}/delete` |
| documents | POST `/list` | POST `/{id}/detail` | POST `` | POST `/{id}/update` | POST `/{id}/delete` |
| vendors | POST `/list` | POST `/{id}/detail` | POST `` | POST `/{id}/update` | POST `/{id}/delete` |
| projects | POST `/list` | POST `/{id}/detail` | POST `` | POST `/{id}/update` | POST `/{id}/delete` |
| users | POST `/list` | POST `/{id}/detail` | POST `` | POST `/{id}/update` | POST `/{id}/delete` |

### 前端 API 模組 (Frontend)

```
frontend/src/api/
├── client.ts          # 統一 API Client (ApiClient class)
├── types.ts           # 共用型別定義 (PaginatedResponse, ErrorResponse)
├── agenciesApi.ts     # 機關 API 服務 ✅
├── documentsApi.ts    # 公文 API 服務 ✅
├── projectsApi.ts     # 專案 API 服務 ✅
├── usersApi.ts        # 使用者 API 服務 ✅
├── vendors.ts         # 廠商 API 服務 ✅
├── index.ts           # 統一匯出
│
└── [deprecated]
    ├── config.ts      # 舊版配置 → 已棄用
    ├── documents.ts   # 舊版公文 API → 已棄用
    └── projects.ts    # 舊版專案 API → 已棄用
```

### 統一回應格式

```typescript
// 列表回應
interface PaginatedResponse<T> {
  success: boolean;
  items: T[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// 錯誤回應
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: { field?: string; message: string }[];
  };
}
```

### 使用範例

```typescript
// 前端呼叫
import { agenciesApi } from '@/api';

const { items, pagination } = await agenciesApi.getAgencies({
  page: 1,
  limit: 20,
  search: '關鍵字',
});
```

---

## 📋 相關文件功能設計 (Related Documents Design)

### 現有架構
- **OfficialDocument 模型**: 包含 `contract_project_id` 外鍵指向 ContractProject
- **ContractProject 模型**: 包含 `documents` relationship (一對多)
- **前端 UI**: ContractCaseDetailPage TAB 4 "相關文件" 已有顯示結構

### 資料庫關聯
```
ContractProject (contract_projects)
    │
    └── documents (OfficialDocument[])
          │ contract_project_id (FK)
          │
          └── OfficialDocument (documents)
```

### 需實作 API 端點

1. **GET `/api/projects/{project_id}/documents`**
   - 功能: 取得專案關聯的公文列表
   - 回應: `{ documents: RelatedDocument[], total: number }`

2. **POST `/api/projects/{project_id}/documents/{document_id}`**
   - 功能: 將公文關聯到專案 (設定 contract_project_id)
   - 注意: 一份公文只能關聯一個專案

3. **DELETE `/api/projects/{project_id}/documents/{document_id}`**
   - 功能: 解除公文與專案的關聯 (清除 contract_project_id)

### 前端整合步驟

1. **新增 API 方法** (`frontend/src/api/projects.ts`):
```typescript
// 取得專案關聯文件
getProjectDocuments: async (projectId: number) => {
  const response = await api.get(`/projects/${projectId}/documents`);
  return response.data;
},

// 關聯文件到專案
linkDocument: async (projectId: number, documentId: number) => {
  const response = await api.post(`/projects/${projectId}/documents/${documentId}`);
  return response.data;
},

// 解除文件關聯
unlinkDocument: async (projectId: number, documentId: number) => {
  const response = await api.delete(`/projects/${projectId}/documents/${documentId}`);
  return response.data;
},
```

2. **更新 loadData()** (`ContractCaseDetailPage.tsx`):
```typescript
const [projectResponse, staffResponse, vendorsResponse, documentsResponse] = await Promise.all([
  projectsApi.getProject(projectId),
  projectStaffApi.getProjectStaff(projectId).catch(...),
  projectVendorsApi.getProjectVendors(projectId).catch(...),
  projectsApi.getProjectDocuments(projectId).catch(() => ({ documents: [], total: 0 })),
]);
setRelatedDocs(documentsResponse.documents);
```

3. **新增關聯對話框**: 使用 Modal + 公文搜尋/選擇功能

### 附件功能設計

- 現有 `DocumentAttachment` 模型已存在
- 需考慮是否新增 `ProjectAttachment` 模型或使用現有附件機制
- 建議: 直接使用公文附件，透過公文關聯專案間接顯示

---

## 📝 Notes
- **前端開發伺服器**: http://localhost:3000
- **後端 API 文檔**: http://localhost:8001/api/docs
- **主要 API 端點**: `/api/documents-enhanced`, `/api/projects`, `/api/vendors`, `/api/agencies`
- 每次修改後端代碼需重啟 Docker: `docker restart ck_missive_backend`

## 🔗 Reference
- 詳細 API 文檔: `docs/wiki/Backend-API-Overview.md`
- 組件文檔: `docs/wiki/Frontend-Components.md`
- 資料模型: `docs/wiki/Database-Models.md`

---

## 🏛️ 架構優化建議 (Architecture Optimization)

### 1. API 回應格式統一化

**現況問題**:
- 不同 API 使用不同回應格式 (`items/documents`, `total/count`, `page/current`)
- 前端需針對每個 API 寫不同的轉換邏輯

**建議方案**:
```python
# 統一分頁回應格式
class UnifiedPaginatedResponse(BaseModel):
    success: bool = True
    items: List[Any]
    pagination: PaginationMeta

class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool
```

### 2. 關聯查詢效能優化

**現況問題**:
- 公文列表需額外查詢 contract_projects + project_user_assignments
- 可能產生 N+1 查詢問題

**建議方案**:
```python
# Option A: SQLAlchemy joined load
query = select(OfficialDocument).options(
    joinedload(OfficialDocument.contract_project).joinedload(ContractProject.staff)
)

# Option B: 批次查詢 (已實作)
project_ids = [doc.contract_project_id for doc in items]
projects = await db.execute(select(...).where(ContractProject.id.in_(project_ids)))

# Option C: 資料庫 VIEW
CREATE VIEW document_with_project AS
SELECT d.*, cp.project_name, ...
FROM documents d
LEFT JOIN contract_projects cp ON d.contract_project_id = cp.id;
```

### 3. 快取策略建議

**適合快取的資料**:
| 資料類型 | TTL | 快取層 |
|---------|-----|--------|
| 機關下拉選單 | 10 min | Redis |
| 廠商下拉選單 | 10 min | Redis |
| 承攬案件下拉 | 5 min | Redis |
| 年度選單 | 1 day | Redis |
| 公文列表 | 30 sec | React Query |

**實作建議**:
```python
# Backend Redis 快取
from redis import asyncio as aioredis

@router.get("/agencies-dropdown")
async def get_agencies_dropdown(redis: aioredis.Redis = Depends(get_redis)):
    cached = await redis.get("agencies_dropdown")
    if cached:
        return json.loads(cached)
    data = await query_agencies()
    await redis.set("agencies_dropdown", json.dumps(data), ex=600)
    return data
```

```typescript
// Frontend React Query
const { data } = useQuery({
  queryKey: ['agencies'],
  queryFn: fetchAgencies,
  staleTime: 10 * 60 * 1000, // 10 minutes
});
```

### 4. 錯誤處理統一化

**建議格式**:
```python
class ApiError(BaseModel):
    code: str           # 錯誤代碼 (ERR_NOT_FOUND, ERR_VALIDATION)
    message: str        # 使用者可讀訊息
    details: List[Dict] # 詳細資訊 (欄位錯誤等)

# 範例
{
    "success": false,
    "error": {
        "code": "ERR_VALIDATION",
        "message": "資料驗證失敗",
        "details": [
            {"field": "doc_number", "message": "公文文號不可為空"}
        ]
    }
}
```

### 5. 前端型別安全強化

**建議**:
- 使用 Zod 進行執行期驗證
- API Client 自動產生 TypeScript 型別

```typescript
// 使用 zodios 或 orval 自動產生
import { createApiClient } from './generated/api';

const api = createApiClient({
  baseUrl: 'http://localhost:8001/api'
});

// 型別安全的 API 呼叫
const { items } = await api.documents.list({ page: 1, limit: 10 });
```

### 6. 資料庫索引優化建議

```sql
-- 建議新增索引
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_contract_project ON documents(contract_project_id);
CREATE INDEX idx_documents_auto_serial ON documents(auto_serial);
CREATE INDEX idx_documents_doc_date ON documents(doc_date);

-- 複合索引 (常用查詢)
CREATE INDEX idx_documents_category_date ON documents(category, doc_date DESC);
```

### 7. 測試覆蓋建議

| 測試類型 | 工具 | 優先級 |
|---------|------|--------|
| 單元測試 (後端) | pytest | 🔴 高 |
| 單元測試 (前端) | Vitest | 🟡 中 |
| API 整合測試 | pytest + httpx | 🔴 高 |
| E2E 測試 | Playwright | 🟢 低 |

---

---

## 🛡️ 資料品質管理機制 (Data Quality Management)

### 1. CSV 匯入驗證規則

**驗證層級** (`backend/app/services/csv_processor.py`):

| 規則 | 說明 | 處理方式 |
|------|------|----------|
| 公文字號格式 | 必須包含「字第」且前有機關字首 | 跳過該筆 |
| 主旨內容檢查 | 不可為空、test、testing、測試 | 跳過該筆 |
| 主旨長度警告 | 少於 5 字元 | 記錄警告 |
| 必要欄位 | doc_number 為必填 | 跳過該筆 |

**驗證程式碼示例**:
```python
# 公文字號格式驗證
if '字第' in doc_number:
    prefix = doc_number.split('字第')[0]
    if not prefix or len(prefix) < 2:
        logger.warning(f"[資料品質] 公文字號格式不完整: {doc_number}")
        return None

# 測試資料過濾
if subject.lower() in ['test', 'testing', '測試', '']:
    logger.warning(f"[資料品質] 主旨為測試資料或空白，跳過此筆")
    return None
```

### 2. 資料庫備份機制

**備份腳本** (`scripts/backup/`):

| 檔案 | 功能 |
|------|------|
| `db_backup.ps1` | Windows PowerShell 備份腳本 |
| `db_backup.sh` | Linux/Git Bash 備份腳本 |
| `db_restore.ps1` | 資料庫還原腳本 |
| `setup_scheduled_task.ps1` | Windows 排程設定 |

**備份策略**:
- 時間: 每日 02:00
- 保留: 7 天 (可調整)
- 位置: `backups/database/`
- 格式: `ck_missive_backup_YYYYMMDD_HHMMSS.sql`

**快速指令**:
```powershell
# 手動備份
.\scripts\backup\db_backup.ps1 -Verbose

# 查看可用備份
.\scripts\backup\db_restore.ps1 -List

# 還原最新備份
.\scripts\backup\db_restore.ps1 -Latest

# 設定每日自動備份 (需管理員)
.\scripts\backup\setup_scheduled_task.ps1 -BackupTime "02:00"
```

### 3. 資料完整性檢查

**定期檢查項目**:
- [ ] 公文字號格式一致性
- [ ] 主旨內容非空值
- [ ] 收發單位對應正確
- [ ] 專案關聯有效性

**SQL 檢查範例**:
```sql
-- 檢查空主旨
SELECT id, doc_number FROM documents WHERE subject IS NULL OR subject = '';

-- 檢查格式異常的公文字號
SELECT id, doc_number FROM documents WHERE doc_number NOT LIKE '%字第%';

-- 檢查孤立的專案關聯
SELECT id, contract_project_id FROM documents
WHERE contract_project_id IS NOT NULL
AND contract_project_id NOT IN (SELECT id FROM contract_projects);
```

---

*最後更新: 2026-01-06 - 新增資料品質管理機制與備份策略*
