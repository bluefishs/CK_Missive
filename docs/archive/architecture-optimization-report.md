# 前端架構優化報告

> 生成日期: 2026-01-08
> 版本: 2.0 (優化完成)
> 更新日期: 2026-01-08

## 一、現況分析

### 1.1 資料管理架構概覽

系統目前存在 **三種資料管理模式**：

| 模式 | 特徵 | 問題 |
|------|------|------|
| A. React Query + Zustand 雙重同步 | useEffect 同步資料到 Store | 時間差導致刷新問題 |
| B. React Query 單一來源 (正確) | Hook 直接返回資料 | ✅ 無問題 |
| C. useState + 直接 API 呼叫 (Legacy) | 手動管理狀態 | 缺乏快取、重複請求 |

### 1.2 頁面架構分類

#### ✅ 架構正確的頁面 (模式 B)

| 頁面 | 使用的 Hook | 說明 |
|------|-------------|------|
| `ContractCasePage` | `useProjectsPage` | 直接使用 React Query 資料 |
| `VendorList` | `useVendorsPage` | 直接使用 React Query 資料 |
| `AgenciesPage` | `useAgenciesPage` | 直接使用 React Query 資料 |
| `DocumentPage` | `useDocuments` + mutations | **已優化** (2026-01-08) |
| `UserManagementPage` | `useAdminUsersPage` | **已優化** (2026-01-08) |
| `DashboardPage` | `useDashboardPage` | **已優化** (2026-01-08) |
| `CalendarPage` | `useCalendarPage` | **已優化** (2026-01-08) |

#### ⚠️ 可選優化的詳情頁面 (複雜度高，刷新問題較少)

| 頁面 | 目前模式 | 說明 | 優先級 |
|------|----------|------|--------|
| `ContractCaseDetailPage` | C (Legacy) | 2050+ 行，已有 useProject hooks 可用 | 低 |
| `DocumentDetailPage` | C (Legacy) | 1153 行，已有 useDocument hooks 可用 | 低 |

### 1.3 Store 結構問題 (已解決)

**已清理重複 Store 目錄:**
```
frontend/src/
├── stores/           # 主要使用 (保留)
│   ├── documents.ts
│   └── index.ts
└── store/            # 已清理
    └── index.ts      # 僅保留重導向用途
    # documents.ts    # 已刪除
    # global.ts       # 已刪除
```

---

## 二、問題根因分析

### 2.1 DocumentPage 原始問題 (已修復)

```
原始流程 (有問題):
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ React Query │────►│  useEffect  │────►│   Zustand   │
│ (fetch)     │     │  (sync)     │     │  (render)   │
└─────────────┘     └─────────────┘     └─────────────┘
                         ▲
                         │ 時間差!
                         ▼
              ┌─────────────────────┐
              │ 元件使用 Zustand    │
              │ 資料渲染 (可能過期) │
              └─────────────────────┘

修復後流程:
┌─────────────┐     ┌─────────────┐
│ React Query │────►│   Component │
│ (唯一來源)  │     │  (直接使用) │
└─────────────┘     └─────────────┘
```

### 2.2 Legacy 頁面問題

```typescript
// 問題模式: 直接 API 呼叫 + useState
const [users, setUsers] = useState<User[]>([]);
const [loading, setLoading] = useState(false);

const fetchUsers = async () => {
  setLoading(true);
  const data = await apiClient.get('/users');
  setUsers(data);
  setLoading(false);
};

// 問題:
// 1. 無快取機制，每次進入頁面都重新請求
// 2. 無自動重試
// 3. 無樂觀更新
// 4. 需手動管理 loading/error 狀態
```

---

## 三、優化方案

### 3.1 統一資料架構標準

**目標架構:**
```
┌─────────────────────────────────────────────────────────┐
│                      Component                          │
│  ┌─────────────────┐      ┌─────────────────┐          │
│  │   Zustand       │      │   React Query   │          │
│  │ (UI State Only) │      │ (Server State)  │          │
│  │ - filters       │      │ - lists         │          │
│  │ - pagination    │      │ - details       │          │
│  │ - sort order    │      │ - mutations     │          │
│  └─────────────────┘      └─────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Hook 設計模式

```typescript
// 標準頁面 Hook 範本
export const useXxxPage = (params?: XxxListParams) => {
  // 查詢
  const listQuery = useXxxList(params);
  const statsQuery = useXxxStatistics();

  // Mutations
  const createMutation = useCreateXxx();
  const updateMutation = useUpdateXxx();
  const deleteMutation = useDeleteXxx();

  return {
    // 資料 (直接從 React Query)
    items: listQuery.data?.items ?? [],
    pagination: listQuery.data?.pagination,
    statistics: statsQuery.data,

    // 狀態
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,

    // 操作
    refetch: listQuery.refetch,
    create: createMutation.mutateAsync,
    update: updateMutation.mutateAsync,
    delete: deleteMutation.mutateAsync,

    // Mutation 狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
```

### 3.3 Zustand Store 職責限定

```typescript
// stores/documents.ts - 只存 UI 狀態
interface DocumentsUIState {
  // 篩選條件
  filters: DocumentFilter;
  setFilters: (filters: Partial<DocumentFilter>) => void;
  resetFilters: () => void;

  // 分頁設定
  pagination: { page: number; limit: number };
  setPagination: (pagination: Partial<{ page: number; limit: number }>) => void;

  // 不再存放 documents 資料!
}
```

---

## 四、優化作業清單

### 4.1 高優先級 (P0) - ✅ 已完成

- [x] `DocumentPage.tsx` - 移除 Zustand 資料同步，改用 React Query 直接渲染

### 4.2 中優先級 (P1) - ✅ 已完成

| 作業項目 | 檔案路徑 | 狀態 | 完成日期 |
|----------|----------|------|----------|
| 建立 useAdminUsers Hook | `hooks/useAdminUsers.ts` | ✅ 完成 | 2026-01-08 |
| 建立 adminUsersApi | `api/adminUsersApi.ts` | ✅ 完成 | 2026-01-08 |
| 優化 UserManagementPage | `pages/UserManagementPage.tsx` | ✅ 完成 | 2026-01-08 |
| 建立 useDashboard Hook | `hooks/useDashboard.ts` | ✅ 完成 | 2026-01-08 |
| 建立 dashboardApi | `api/dashboardApi.ts` | ✅ 完成 | 2026-01-08 |
| 優化 DashboardPage | `pages/DashboardPage.tsx` | ✅ 完成 | 2026-01-08 |
| 建立 useCalendar Hook | `hooks/useCalendar.ts` | ✅ 完成 | 2026-01-08 |
| 建立 calendarApi | `api/calendarApi.ts` | ✅ 完成 | 2026-01-08 |
| 優化 CalendarPage | `pages/CalendarPage.tsx` | ✅ 完成 | 2026-01-08 |
| 統一 Store 目錄 | `store/` + `stores/` → `store/` | ✅ 完成 | 2026-01-08 |
| 刪除損壞/備份檔案 | `.broken`, `.bak` | ✅ 完成 | 2026-01-08 |
| 清理 JSX 遺留目錄 | `Documents/`, `pages/Documents/` | ✅ 完成 | 2026-01-08 |
| 修復公文資料 | id=524, doc_number=1140000001 | ✅ 完成 | 2026-01-08 |

### 4.3 低優先級 (P2) - 可選優化 (暫緩)

| 作業項目 | 檔案路徑 | 說明 |
|----------|----------|------|
| 優化 ContractCaseDetailPage | `pages/ContractCaseDetailPage.tsx` | 複雜度高 (2050 行)，已有 useProject hooks |
| 優化 DocumentDetailPage | `pages/DocumentDetailPage.tsx` | 複雜度高 (1153 行)，已有 useDocument hooks |
| 統一 API Client | 全域 | 確保所有頁面使用統一 apiClient |

---

## 五、實作指南

### 5.1 新增 React Query Hook 範本

```typescript
// hooks/useXxx.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { xxxApi, XxxListParams } from '../api/xxxApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';

// 列表查詢
export const useXxxList = (params?: XxxListParams) => {
  return useQuery({
    queryKey: queryKeys.xxx.list(params || {}),
    queryFn: () => xxxApi.getList(params),
    ...defaultQueryOptions.list,
  });
};

// 建立 Mutation
export const useCreateXxx = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: XxxCreate) => xxxApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.xxx.all });
    },
  });
};
```

### 5.2 頁面改造步驟

1. **檢查現有 Hook** - 確認 `hooks/` 目錄是否已有對應的 React Query hook
2. **建立缺少的 Hook** - 參考 `useDocuments.ts` 或 `useProjects.ts`
3. **修改頁面** - 移除 useState 資料管理，改用 Hook
4. **移除 useEffect 同步** - 確保不再有資料同步邏輯
5. **測試即時刷新** - 驗證 CRUD 操作後列表立即更新

---

## 六、驗收標準

### 6.1 功能驗收

- [x] 主要 CRUD 頁面在操作後立即刷新列表
- [x] 頁面切換時不會重複發送相同請求 (快取生效)
- [x] Loading 狀態正確顯示
- [x] Error 狀態正確處理

### 6.2 程式碼規範

- [x] 主要列表頁面使用統一的 Hook 模式
- [x] Zustand Store 只存放 UI 狀態
- [x] 主要頁面不存在 useEffect 資料同步邏輯
- [x] API 呼叫統一使用 `apiClient`

### 6.3 已優化頁面清單

| 頁面 | Hook | API | 完成日期 |
|------|------|-----|----------|
| DocumentPage | useDocuments | documentsApi | 2026-01-08 |
| UserManagementPage | useAdminUsersPage | adminUsersApi | 2026-01-08 |
| DashboardPage | useDashboardPage | dashboardApi | 2026-01-08 |
| CalendarPage | useCalendarPage | calendarApi | 2026-01-08 |

---

## 附錄: 已優化頁面對照

### DocumentPage.tsx 優化對照

**Before (問題版本):**
```typescript
// 從 Zustand 取資料
const { documents } = useDocumentsStore();

// useEffect 同步
useEffect(() => {
  if (documentsData) {
    useDocumentsStore.getState().setDocuments(documentsData.items);
  }
}, [documentsData]);

// 手動刷新
const handleSave = async () => {
  await documentsApi.updateDocument(...);
  await forceRefreshDocuments(); // 可能無效
};
```

**After (優化版本):**
```typescript
// 直接從 React Query 取資料
const documents = documentsData?.items ?? [];

// 使用 Mutation Hook (自動失效快取)
const updateMutation = useUpdateDocument();

const handleSave = async () => {
  await updateMutation.mutateAsync({...}); // 自動刷新
};
```
