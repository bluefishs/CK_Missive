# Frontend Hooks 分層架構

> **版本**: 1.0.0
> **建立日期**: 2026-02-06
> **參考**: docs/SERVICE_ARCHITECTURE_STANDARDS.md

---

## 目錄結構

```
hooks/
├── business/         # 業務邏輯 Hooks (混合三層)
│   ├── use{Entity}.ts           # 層 1: 原始 React Query
│   ├── use{Entity}WithStore.ts  # 層 2: 整合 Zustand Store
│   └── use{Entity}{Action}.ts   # 層 3: 業務邏輯
├── system/           # 系統功能 Hooks
│   ├── useCalendar.ts
│   ├── useDashboard.ts
│   └── useNotifications.ts
├── utility/          # 工具類 Hooks
│   ├── useAuthGuard.ts
│   ├── useNavigation.ts
│   └── useResponsive.ts
└── index.ts          # 統一匯出
```

---

## Hook 分層規範

### 層 1: Queries (原始查詢)

**命名規則**: `use{Entity}Query` 或 `use{Entity}` (單複數)

```typescript
// hooks/business/useDocuments.ts
export function useDocumentsQuery(params: DocumentListQuery) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentsApi.list(params),
  });
}

export function useDocumentDetailQuery(id: number) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.getDetail(id),
    enabled: !!id,
  });
}
```

**特性**:
- 只負責 API 呼叫和快取
- 不包含 UI 狀態
- 可直接在元件中使用

### 層 2: State (整合 Store)

**命名規則**: `use{Entity}WithStore` 或 `use{Entity}State`

```typescript
// hooks/business/useDocumentsWithStore.ts
export function useDocumentsWithStore() {
  const store = useDocumentStore();
  const listQuery = useDocumentsQuery(store.filters);

  const createMutation = useMutation({
    mutationFn: documentsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  return {
    // 資料
    documents: listQuery.data?.items ?? [],
    total: listQuery.data?.total ?? 0,
    isLoading: listQuery.isLoading,

    // Store 狀態
    filters: store.filters,
    setFilters: store.setFilters,

    // 操作
    create: createMutation.mutate,
    isCreating: createMutation.isPending,
  };
}
```

**特性**:
- 整合 React Query 和 Zustand
- 提供統一的資料存取介面
- 處理快取失效策略

### 層 3: Business (業務邏輯)

**命名規則**: `use{Entity}{Action}`

```typescript
// hooks/business/useDocumentCreateForm.ts
export function useDocumentCreateForm() {
  const [form] = Form.useForm();
  const { create, isCreating } = useDocumentsWithStore();
  const navigate = useNavigate();

  const handleSubmit = async (values: DocumentFormValues) => {
    await create(values);
    message.success('公文建立成功');
    navigate('/documents');
  };

  return {
    form,
    isLoading: isCreating,
    handleSubmit,
  };
}
```

**特性**:
- 封裝完整業務流程
- 處理導航、訊息、驗證
- 可重用於多個頁面

---

## 命名規則總表

| 層級 | 命名模式 | 範例 |
|------|----------|------|
| 層 1 Queries | `use{Entity}Query`, `use{Entity}s` | `useDocumentQuery`, `useDocuments` |
| 層 2 State | `use{Entity}WithStore`, `use{Entity}State` | `useDocumentsWithStore` |
| 層 3 Business | `use{Entity}{Action}` | `useDocumentCreateForm`, `useDocumentRelations` |

---

## 現有 Hooks 對照表

### business/ 目錄

| 檔案 | 層級 | 說明 |
|------|------|------|
| `useDocuments.ts` | 層 1 | 公文查詢 |
| `useDocumentsWithStore.ts` | 層 2 | 公文狀態管理 |
| `useDocumentCreateForm.ts` | 層 3 | 公文表單邏輯 |
| `useProjects.ts` | 層 1 | 專案查詢 |
| `useProjectsWithStore.ts` | 層 2 | 專案狀態管理 |
| `useVendors.ts` | 層 1 | 廠商查詢 |
| `useVendorsWithStore.ts` | 層 2 | 廠商狀態管理 |
| `useAgencies.ts` | 層 1 | 機關查詢 |
| `useAgenciesWithStore.ts` | 層 2 | 機關狀態管理 |
| `useTaoyuanProjects.ts` | 層 1+2 | 桃園工程 |
| `useTaoyuanDispatch.ts` | 層 1+2 | 桃園派工 |
| `useTaoyuanPayments.ts` | 層 1+2 | 桃園契金 |
| `createEntityHookWithStore.ts` | 工廠 | Hook 生成工廠 |

### system/ 目錄

| 檔案 | 說明 |
|------|------|
| `useCalendar.ts` | 行事曆功能 |
| `useCalendarIntegration.ts` | Google Calendar 整合 |
| `useDashboard.ts` | 儀表板資料 |
| `useDashboardCalendar.ts` | 儀表板行事曆 |
| `useDocumentStats.ts` | 公文統計 |
| `useDocumentRelations.ts` | 公文關聯管理 |
| `useNotifications.ts` | 系統通知 |
| `useAdminUsers.ts` | 管理者用戶管理 |

### utility/ 目錄

| 檔案 | 說明 |
|------|------|
| `useAuthGuard.ts` | 認證守衛 |
| `usePermissions.ts` | 權限檢查 |
| `useAppNavigation.ts` | 應用導航 |
| `useResponsive.ts` | 響應式斷點 |
| `usePerformance.ts` | 效能監控 |
| `useApiErrorHandler.ts` | API 錯誤處理 |

---

## 未來規劃

### Phase 1: 當前狀態維護
- 維持現有 business/ 混合結構
- 新增 Hook 遵循命名規範

### Phase 2: 結構重組 (可選)
```
hooks/
├── queries/          # 層 1: 純 React Query
│   ├── useDocumentsQuery.ts
│   └── useProjectsQuery.ts
├── state/            # 層 2: Store 整合
│   ├── useDocumentsState.ts
│   └── useProjectsState.ts
├── business/         # 層 3: 業務邏輯
│   ├── useDocumentForm.ts
│   └── useDocumentRelations.ts
├── system/           # 系統功能 (不變)
├── utility/          # 工具類 (不變)
└── index.ts
```

---

## 最佳實踐

### 1. 依賴方向

```
業務邏輯 Hook → 狀態 Hook → 查詢 Hook → API 服務
     ↓              ↓           ↓
   Form.useForm  Zustand    React Query
```

### 2. 錯誤處理

```typescript
// ✅ 正確：保留現有資料
catch (error) {
  message.error('載入失敗');
  // 不要 setItems([])
}

// ❌ 錯誤：清空列表
catch (error) {
  setItems([]); // 會導致資料消失
}
```

### 3. 快取失效

```typescript
// ✅ 使用 queryClient 統一管理
const queryClient = useQueryClient();

const mutation = useMutation({
  mutationFn: api.create,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
  },
});
```

---

## 相關文件

- `docs/SERVICE_ARCHITECTURE_STANDARDS.md` - 服務層架構規範
- `frontend/src/store/README.md` - Zustand Store 規範
- `frontend/src/api/README.md` - API 服務規範
