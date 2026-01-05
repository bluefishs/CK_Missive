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
*最後更新: 2026-01-05 - API 架構重構完成 (POST-only 資安機制、統一回應格式、服務層分離)*
