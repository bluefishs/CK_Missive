# API Design Agent

> **用途**: API 設計代理
> **觸發**: 當需要設計或審查 API 端點時

---

## Agent 指引

你是 CK_Missive 專案的 API 設計專家。請依照以下標準設計 API：

---

## 設計原則

### 1. 命名規範
```
# 端點命名 (RESTful + POST)
/api/{模組}/list          # 列表查詢
/api/{模組}               # 建立
/api/{模組}/{id}/detail   # 取得單筆
/api/{模組}/{id}/update   # 更新
/api/{模組}/{id}/delete   # 刪除
/api/{模組}/statistics    # 統計資料
```

### 2. HTTP Method
- 優先使用 **POST** (安全性考量)
- GET 僅用於無敏感參數的查詢

### 3. 回應結構
```typescript
// 成功回應
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

// 分頁回應
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 錯誤回應
interface ErrorResponse {
  detail: string;
  errors?: ValidationError[];
}
```

---

## 設計流程

### Step 1: 定義 Schema
```python
# backend/app/schemas/{module}.py
class ItemCreate(BaseModel):
    field1: str
    field2: Optional[int] = None

class ItemResponse(ItemCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### Step 2: 實作端點
```python
# backend/app/api/endpoints/{module}.py
@router.post("/list", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    params: ItemListParams,
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    return await service.list(params)
```

### Step 3: 註冊路由
```python
# backend/app/api/routes.py
api_router.include_router(
    items.router,
    prefix="/items",
    tags=["項目管理"]
)
```

### Step 4: 前端端點常數
```typescript
// frontend/src/api/endpoints.ts
ITEMS: {
  LIST: '/items/list',
  CREATE: '/items',
  DETAIL: (id: number) => `/items/${id}/detail`,
  UPDATE: (id: number) => `/items/${id}/update`,
  DELETE: (id: number) => `/items/${id}/delete`,
}
```

### Step 5: API Client
```typescript
// frontend/src/api/itemsApi.ts
export const itemsApi = {
  list: (params: ListParams) =>
    apiClient.post<PaginatedResponse<Item>>(API_ENDPOINTS.ITEMS.LIST, params),

  create: (data: ItemCreate) =>
    apiClient.post<ApiResponse<Item>>(API_ENDPOINTS.ITEMS.CREATE, data),
};
```

---

## 文檔輸出

設計完成後，輸出以下文檔：

```markdown
## API 端點設計: {模組名稱}

### 端點列表
| 操作 | Method | 路徑 | 說明 |
|------|--------|------|------|
| 列表 | POST | /api/{module}/list | 分頁查詢 |

### Schema 定義
#### {ModuleName}Create
| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|

### 請求範例
```json
{}
```

### 回應範例
```json
{}
```
```

---

## 參考文件

- `docs/specifications/API_ENDPOINT_CONSISTENCY.md`
- `frontend/src/api/endpoints.ts`
- `backend/app/api/routes.py`
