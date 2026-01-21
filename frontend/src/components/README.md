# 前端組件架構規範

> **版本**: 1.0.0
> **日期**: 2026-01-21
> **維護**: Claude Code Assistant

---

## 目錄結構

```
components/
├── admin/                  # 管理員專用組件
│   ├── EnhancedDatabaseViewer.tsx   # 增強版資料庫檢視器
│   ├── SimpleDatabaseViewer.tsx     # 簡易版資料庫檢視器
│   ├── PermissionManager.tsx        # 權限管理面板
│   ├── UserEditModal.tsx            # 使用者編輯彈窗
│   └── UserPermissionModal.tsx      # 使用者權限彈窗
│
├── calendar/               # 行事曆相關組件
│   ├── EnhancedCalendarView.tsx     # 增強版行事曆檢視
│   ├── EventFormModal.tsx           # 事件表單彈窗
│   ├── IntegratedEventModal.tsx     # 整合事件彈窗
│   └── ReminderSettingsModal.tsx    # 提醒設定彈窗
│
├── common/                 # 共用組件
│   ├── DetailPage/                  # 詳細頁面組件群
│   │   ├── DetailPageHeader.tsx     # 頁面標題
│   │   ├── DetailPageLayout.tsx     # 頁面版面
│   │   └── utils.tsx                # 工具函數
│   ├── ErrorBoundary.tsx            # 錯誤邊界
│   ├── NotificationCenter.tsx       # 通知中心
│   ├── PageLoading.tsx              # 頁面載入中
│   ├── RemarksField.tsx             # 備註欄位
│   ├── ResponsiveContainer.tsx      # 響應式容器
│   ├── SequenceNumberGenerator.tsx  # 序號產生器
│   └── UnifiedTable.tsx             # 統一表格
│
├── document/               # 公文相關組件
│   ├── DocumentActions.tsx          # 公文操作按鈕
│   ├── DocumentCard.tsx             # 公文卡片
│   ├── DocumentFilter.tsx           # 公文篩選器
│   ├── DocumentImport.tsx           # 公文匯入
│   ├── DocumentList.tsx             # 公文列表
│   ├── DocumentOperations.tsx       # 公文操作面板
│   ├── DocumentPagination.tsx       # 公文分頁
│   ├── DocumentTabs.tsx             # 公文頁籤
│   └── operations/                  # 操作相關子組件
│       ├── CriticalChangeConfirmModal.tsx
│       ├── DuplicateFileModal.tsx
│       ├── ExistingAttachmentsList.tsx
│       └── FileUploadSection.tsx
│
├── extended/               # 擴充管理面板 (頁面內嵌組件)
│   ├── AgencyManagement.tsx         # 機關管理面板
│   ├── ContractProjects.tsx         # 承攬案件面板
│   ├── DocumentManagement.tsx       # 公文管理面板
│   └── VendorManagement.tsx         # 廠商管理面板
│
├── hoc/                    # 高階組件
│   ├── withAuth.tsx                 # 認證包裝器
│   └── withLoading.tsx              # 載入包裝器
│
├── project/                # 專案相關組件
│   └── ProjectVendorManagement.tsx  # 專案廠商管理
│
├── site-management/        # 網站管理組件
│   ├── NavigationItemForm.tsx       # 導覽項目表單
│   └── SiteConfigManagement.tsx     # 網站設定管理
│
├── vendor/                 # 廠商相關組件
│   └── VendorList.tsx               # 廠商列表
│
├── index.ts                # 統一匯出
└── Layout.tsx              # 主版面
```

---

## 命名規範

### 檔案命名

| 類型 | 規則 | 範例 |
|------|------|------|
| 頁面組件 | `*Page.tsx` | `DocumentPage.tsx`, `LoginPage.tsx` |
| 功能組件 | `*[功能].tsx` | `DocumentCard.tsx`, `UserEditModal.tsx` |
| 彈窗組件 | `*Modal.tsx` | `EventFormModal.tsx` |
| 表單組件 | `*Form.tsx` | `NavigationItemForm.tsx` |
| 列表組件 | `*List.tsx` | `DocumentList.tsx`, `VendorList.tsx` |
| 管理面板 | `*Management.tsx` | `AgencyManagement.tsx` |
| 增強版本 | `Enhanced*.tsx` | `EnhancedCalendarView.tsx` |
| 高階組件 | `with*.tsx` | `withAuth.tsx`, `withLoading.tsx` |

### 命名原則

1. **PascalCase**: 所有組件使用 PascalCase 命名
2. **描述性**: 名稱應清楚描述組件用途
3. **後綴一致**: 相同類型的組件使用相同後綴
4. **避免冗餘**: 不要重複目錄名稱 (如 `document/Document` 是可以的)

### 位置規則

| 組件類型 | 位置 | 說明 |
|----------|------|------|
| 頁面 | `pages/` | 對應路由的完整頁面 |
| 共用組件 | `components/common/` | 跨功能使用的基礎組件 |
| 領域組件 | `components/{domain}/` | 特定功能領域的組件 |
| 高階組件 | `components/hoc/` | 功能增強包裝器 |

---

## 新增組件指南

### 判斷組件位置

```
新組件 → 是否為完整頁面?
         ├─ 是 → pages/{PageName}Page.tsx
         └─ 否 → 是否跨功能共用?
                  ├─ 是 → components/common/{ComponentName}.tsx
                  └─ 否 → 屬於哪個領域?
                           └─ components/{domain}/{ComponentName}.tsx
```

### 範例

```typescript
// 新增公文附件預覽組件
// 判斷: 不是頁面, 不是共用, 屬於公文領域
// 位置: components/document/AttachmentPreview.tsx

// 新增通用確認彈窗
// 判斷: 不是頁面, 是共用組件
// 位置: components/common/ConfirmModal.tsx

// 新增廠商詳情頁
// 判斷: 是完整頁面
// 位置: pages/VendorDetailPage.tsx
```

---

## 匯出規範

### 統一入口

```typescript
// components/index.ts
export * from './common';
export * from './document';
// ...

// 使用時
import { ErrorBoundary, DocumentCard } from '@/components';
```

### 子目錄匯出

每個子目錄應有 `index.ts` 統一匯出：

```typescript
// components/common/index.ts
export { ErrorBoundary } from './ErrorBoundary';
export { NotificationCenter } from './NotificationCenter';
export { PageLoading } from './PageLoading';
// ...
```

---

*最後更新: 2026-01-21*
