# CK_Missive 服務層架構規範

> **版本**: 1.0.0
> **建立日期**: 2026-02-06
> **適用範圍**: 後端服務層、前端狀態管理層

---

## 目錄

1. [後端服務層規範](#1-後端服務層規範)
2. [Repository 層規範](#2-repository-層規範)
3. [前端 Hook 分層規範](#3-前端-hook-分層規範)
4. [前端 API 服務層規範](#4-前端-api-服務層規範)
5. [遷移指南](#5-遷移指南)

---

## 1. 後端服務層規範

### 1.1 服務初始化模式

**推薦模式：工廠模式 (Factory Pattern)**

```python
# ✅ 推薦：工廠模式
class DocumentService:
    """
    公文服務

    使用工廠模式，db session 在建構時注入
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)

    async def get_list(self, params: DocumentListQuery) -> List[Document]:
        return await self.repository.get_paginated(params)

# 依賴注入
from app.core.dependencies import get_service_with_db

@router.get("/documents")
async def list_documents(
    service: DocumentService = Depends(get_service_with_db(DocumentService))
):
    return await service.get_list()
```

**棄用模式：Singleton 模式**

```python
# ❌ 棄用：Singleton 模式
# 此模式將在 v2.0 移除
class VendorService(BaseService):
    """
    @deprecated 使用工廠模式替代
    """
    def __init__(self):
        super().__init__(PartnerVendor, "廠商")

    # db 在每個方法中傳入，增加複雜度
    async def get_vendors(self, db: AsyncSession, skip: int, limit: int):
        ...

# 依賴注入（舊版）
@router.get("/vendors")
async def list_vendors(
    service: VendorService = Depends(get_vendor_service),
    db: AsyncSession = Depends(get_async_db)
):
    return await service.get_vendors(db, skip, limit)
```

### 1.2 服務分類

| 類型 | 適用場景 | 範例 |
|------|----------|------|
| **領域服務** | 複雜業務邏輯 | DocumentService, DispatchOrderService |
| **CRUD 服務** | 簡單實體操作 | VendorService, AgencyService |
| **整合服務** | 跨系統整合 | CalendarIntegrationService |
| **AI 服務** | AI 功能封裝 | DocumentAIService |

### 1.3 服務職責原則

- **單一職責**：每個服務只負責一個領域
- **無狀態**：服務不保存請求間的狀態
- **依賴注入**：所有依賴通過建構函數注入
- **錯誤處理**：統一使用 ApiException

```python
# ✅ 正確：單一職責
class DocumentService:
    async def create(self, data: DocumentCreate) -> Document: ...
    async def update(self, id: int, data: DocumentUpdate) -> Document: ...
    async def delete(self, id: int) -> bool: ...

# ❌ 錯誤：職責過多
class DocumentService:
    async def create(self, data): ...
    async def send_notification(self): ...  # 應該在 NotificationService
    async def sync_calendar(self): ...      # 應該在 CalendarService
```

---

## 2. Repository 層規範

### 2.1 基礎結構

```python
from app.repositories.base_repository import BaseRepository

class DocumentRepository(BaseRepository[OfficialDocument]):
    """
    公文 Repository

    繼承 BaseRepository 獲得標準 CRUD 操作
    """
    def __init__(self, db: AsyncSession):
        super().__init__(db, OfficialDocument)

    # 領域特定查詢
    async def get_by_doc_number(self, doc_number: str) -> Optional[OfficialDocument]:
        ...
```

### 2.2 查詢方法分類

| 類型 | 命名規則 | 範例 |
|------|----------|------|
| 單筆查詢 | `get_by_{field}` | `get_by_id()`, `get_by_doc_number()` |
| 列表查詢 | `get_all()`, `get_paginated()` | `get_all()`, `get_paginated(params)` |
| 條件查詢 | `find_by_{condition}` | `find_by_status()`, `find_by_date_range()` |
| 統計查詢 | `count_{what}`, `get_{what}_statistics` | `count_by_status()`, `get_monthly_statistics()` |

### 2.3 Query Builder 模式 (推薦)

```python
# ✅ 推薦：使用 Query Builder
class DocumentQueryBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._query = select(OfficialDocument)

    def with_status(self, status: str) -> 'DocumentQueryBuilder':
        self._query = self._query.where(OfficialDocument.status == status)
        return self

    def with_date_range(self, start: date, end: date) -> 'DocumentQueryBuilder':
        self._query = self._query.where(
            OfficialDocument.doc_date.between(start, end)
        )
        return self

    def with_keyword(self, keyword: str) -> 'DocumentQueryBuilder':
        self._query = self._query.where(
            OfficialDocument.subject.ilike(f"%{keyword}%")
        )
        return self

    async def execute(self) -> List[OfficialDocument]:
        result = await self.db.execute(self._query)
        return result.scalars().all()

# 使用範例
documents = await (
    DocumentQueryBuilder(db)
    .with_status("待處理")
    .with_date_range(start_date, end_date)
    .with_keyword("桃園")
    .execute()
)
```

---

## 3. 前端 Hook 分層規範

### 3.1 分層架構

```
hooks/
├── queries/          # 層 1：原始 React Query
│   ├── useDocumentsQuery.ts
│   └── useProjectsQuery.ts
├── state/            # 層 2：整合 Zustand Store
│   ├── useDocumentsState.ts
│   └── useProjectsState.ts
└── business/         # 層 3：業務邏輯 Hook
    ├── useDocumentForm.ts
    ├── useDocumentRelations.ts
    └── useDispatchWorkflow.ts
```

### 3.2 各層職責

**層 1：Queries (原始查詢)**

```typescript
// hooks/queries/useDocumentsQuery.ts
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

**層 2：State (整合 Store)**

```typescript
// hooks/state/useDocumentsState.ts
export function useDocumentsState() {
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

**層 3：Business (業務邏輯)**

```typescript
// hooks/business/useDocumentForm.ts
export function useDocumentForm(documentId?: number) {
  const [form] = Form.useForm();
  const { create, update, isCreating, isUpdating } = useDocumentsState();
  const { data: detail } = useDocumentDetailQuery(documentId);

  // 表單初始化
  useEffect(() => {
    if (detail) {
      form.setFieldsValue(detail);
    }
  }, [detail, form]);

  // 提交處理
  const handleSubmit = async (values: DocumentFormValues) => {
    if (documentId) {
      await update({ id: documentId, ...values });
    } else {
      await create(values);
    }
  };

  return {
    form,
    isLoading: isCreating || isUpdating,
    handleSubmit,
  };
}
```

### 3.3 命名規則

| 層級 | 命名模式 | 範例 |
|------|----------|------|
| Queries | `use{Entity}Query`, `use{Entity}ListQuery` | `useDocumentQuery`, `useDocumentsQuery` |
| State | `use{Entity}State`, `use{Entity}Store` | `useDocumentsState` |
| Business | `use{Entity}{Action}` | `useDocumentForm`, `useDocumentRelations` |

---

## 4. 前端 API 服務層規範

### 4.1 目錄結構

```
api/
├── core/                    # 核心模組
│   ├── client.ts           # API Client
│   ├── endpoints.ts        # 端點定義
│   └── types.ts            # 通用型別
├── document/               # 公文模組
│   ├── index.ts
│   ├── documentsApi.ts
│   └── attachmentsApi.ts
├── project/                # 專案模組
│   └── projectsApi.ts
├── agency/                 # 機關模組
│   └── agenciesApi.ts
├── taoyuan/                # 桃園派工模組
│   ├── dispatchApi.ts
│   ├── projectsApi.ts
│   └── paymentsApi.ts
└── system/                 # 系統模組
    ├── authApi.ts
    ├── configApi.ts
    └── backupApi.ts
```

### 4.2 API 服務命名規則

| 類型 | 命名規則 | 範例 |
|------|----------|------|
| 模組檔案 | `{entity}Api.ts` (複數) | `documentsApi.ts`, `projectsApi.ts` |
| 匯出物件 | `{entity}Api` | `documentsApi`, `projectsApi` |
| 方法命名 | `{action}{Entity}` | `getList()`, `create()`, `update()`, `delete()` |

### 4.3 API 方法標準化

```typescript
// ✅ 標準 API 服務結構
export const documentsApi = {
  // 列表
  async getList(params?: DocumentListQuery): Promise<PaginatedResponse<Document>> {
    return apiClient.post(ENDPOINTS.LIST, params ?? {});
  },

  // 詳情
  async getDetail(id: number): Promise<Document> {
    return apiClient.post(ENDPOINTS.DETAIL(id), {});
  },

  // 建立
  async create(data: DocumentCreate): Promise<Document> {
    return apiClient.post(ENDPOINTS.CREATE, data);
  },

  // 更新
  async update(id: number, data: DocumentUpdate): Promise<Document> {
    return apiClient.post(ENDPOINTS.UPDATE(id), data);
  },

  // 刪除
  async delete(id: number): Promise<DeleteResponse> {
    return apiClient.post(ENDPOINTS.DELETE(id), {});
  },
};
```

---

## 5. 遷移指南

### 5.1 後端服務遷移 (Singleton → 工廠)

**Step 1**: 標記現有 Singleton 服務為 deprecated

```python
class VendorService(BaseService):
    """
    廠商服務

    .. deprecated:: 1.42.0
       使用 VendorServiceV2 替代，將在 2.0 版移除
    """
```

**Step 2**: 建立新版工廠模式服務

```python
class VendorServiceV2:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = VendorRepository(db)
```

**Step 3**: 逐步遷移 API 端點

### 5.2 前端 Hook 遷移

**Step 1**: 建立新的分層目錄結構
**Step 2**: 將現有 Hook 分類到對應層級
**Step 3**: 更新 import 路徑
**Step 4**: 移除舊的混合式 Hook

---

## 附錄

### A. 檢查清單

**新增後端服務時**：
- [ ] 使用工廠模式初始化
- [ ] 依賴注入所有外部依賴
- [ ] 單一職責原則
- [ ] 統一錯誤處理

**新增前端 Hook 時**：
- [ ] 確定所屬層級 (Query/State/Business)
- [ ] 遵循命名規則
- [ ] 正確整合 React Query
- [ ] 處理錯誤狀態

### B. 相關文件

- `backend/app/core/dependencies.py` - 依賴注入模組
- `backend/app/repositories/base_repository.py` - Repository 基類
- `frontend/src/hooks/createEntityHookWithStore.ts` - Hook 工廠
- `.claude/skills/type-management.md` - 型別管理規範
