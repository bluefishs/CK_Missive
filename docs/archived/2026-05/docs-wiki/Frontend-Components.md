# 前端組件文檔

## 頁面組件 (Pages)

### 核心業務頁面

| 組件 | 檔案 | 路徑 | 說明 |
|------|------|------|------|
| `DashboardPage` | `DashboardPage.tsx` | `/dashboard` | 系統儀表板 |
| `DocumentPage` | `DocumentPage.tsx` | `/documents` | 公文管理主頁 |
| `ContractCasePage` | `ContractCasePage.tsx` | `/contract-cases` | 承攬案件列表 |
| `ContractCaseDetailPage` | `ContractCaseDetailPage.tsx` | `/contract-cases/:id` | 案件詳情 |
| `VendorPage` | `VendorPage.tsx` | `/vendors` | 廠商管理 |
| `AgenciesPage` | `AgenciesPage.tsx` | `/agencies` | 機關單位 |
| `CalendarPage` | `CalendarPage.tsx` | `/calendar` | 行事曆 |

### 公文相關頁面

| 組件 | 檔案 | 說明 |
|------|------|------|
| `DocumentCreatePage` | `DocumentCreatePage.tsx` | 新增公文 |
| `DocumentEditPage` | `DocumentEditPage.tsx` | 編輯公文 |
| `DocumentDetailPage` | `DocumentDetailPage.tsx` | 公文詳情 |
| `DocumentImportPage` | `DocumentImportPage.tsx` | 匯入公文 |
| `DocumentExportPage` | `DocumentExportPage.tsx` | 匯出公文 |
| `DocumentNumbersPage` | `DocumentNumbersPage.tsx` | 發文字號管理 |

### 系統管理頁面

| 組件 | 檔案 | 路徑 |
|------|------|------|
| `UserManagementPage` | `UserManagementPage.tsx` | `/admin/user-management` |
| `PermissionManagementPage` | `PermissionManagementPage.tsx` | `/admin/permissions` |
| `SiteManagementPage` | `SiteManagementPage.tsx` | `/admin/site-management` |
| `DatabaseManagementPage` | `DatabaseManagementPage.tsx` | `/admin/database` |
| `SystemPage` | `SystemPage.tsx` | `/system` |

### 認證頁面

| 組件 | 檔案 | 路徑 |
|------|------|------|
| `LoginPage` | `LoginPage.tsx` | `/login` |
| `RegisterPage` | `RegisterPage.tsx` | `/register` |
| `ForgotPasswordPage` | `ForgotPasswordPage.tsx` | `/forgot-password` |
| `ProfilePage` | `ProfilePage.tsx` | `/profile` |

---

## 共用組件 (Components)

### 文件操作組件 (`/components/document/`)

| 組件 | 說明 | 主要 Props |
|------|------|-----------|
| `DocumentList` | 公文列表表格 | `documents`, `onEdit`, `onDelete` |
| `DocumentActions` | 操作按鈕/下拉選單 | `document`, `onView`, `onEdit` |
| `DocumentFilter` | 篩選條件面板 | `onFilter`, `filters` |
| `DocumentTabs` | 分頁標籤 | `activeTab`, `onChange` |
| `DocumentOperations` | 批次操作工具列 | `selectedIds`, `onBatchAction` |
| `DocumentPagination` | 分頁控制 | `total`, `current`, `onChange` |

### 管理組件 (`/components/admin/`)

| 組件 | 說明 |
|------|------|
| `PermissionManager` | 權限管理介面 |
| `UserEditModal` | 使用者編輯彈窗 |
| `UserPermissionModal` | 權限設定彈窗 |
| `EnhancedDatabaseViewer` | 資料庫檢視器 |

### 行事曆組件 (`/components/calendar/`)

| 組件 | 說明 |
|------|------|
| `EnhancedCalendarView` | 增強型日曆檢視 |

### 共用工具組件 (`/components/common/`)

| 組件 | 說明 |
|------|------|
| `ErrorBoundary` | 錯誤邊界處理 |
| `PageLoading` | 頁面載入動畫 |
| `UnifiedTable` | 統一表格組件 |
| `RemarksField` | 備註欄位 |
| `SequenceNumberGenerator` | 流水號生成器 |

### 版面配置 (`/components/layout/`)

| 組件 | 說明 |
|------|------|
| `Layout` | 主要版面配置 |
| `DynamicLayout` | 動態版面 |

---

## 組件使用範例

### DocumentList 使用
```tsx
import { DocumentList } from '@/components/document/DocumentList';

<DocumentList
  documents={documents}
  loading={isLoading}
  total={total}
  pagination={{ current: 1, pageSize: 10 }}
  onEdit={(doc) => handleEdit(doc)}
  onDelete={(doc) => handleDelete(doc)}
  onView={(doc) => handleView(doc)}
/>
```

### DocumentActions 使用
```tsx
import { DocumentActions } from '@/components/document/DocumentActions';

<DocumentActions
  document={record}
  onView={handleView}
  onEdit={handleEdit}
  onDelete={handleDelete}
  mode="buttons"  // 'buttons' | 'dropdown' | 'inline'
/>
```

---
*檔案位置: `frontend/src/components/`*
