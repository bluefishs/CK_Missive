# API 開發規範 (API Development Guide)

> **觸發關鍵字**: API, endpoint, 端點, route, 路由, FastAPI
> **適用範圍**: API 設計、端點定義、前後端整合

---

## 架構概述

### 技術棧
- **後端**: FastAPI + Pydantic v2 + SQLAlchemy 2.0
- **前端**: React + TypeScript + Axios
- **API 風格**: RESTful (POST 優先)

---

## 端點命名規範

### 後端路由結構
```python
# backend/app/api/routes.py - 唯一的路由定義來源
api_router.include_router(documents.router, prefix="/documents-enhanced", tags=["公文管理"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["行事曆"])
api_router.include_router(agencies.router, prefix="/agencies", tags=["機關管理"])
api_router.include_router(projects.router, prefix="/projects", tags=["專案管理"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["廠商管理"])
```

### 前端集中式端點管理
```typescript
// frontend/src/api/endpoints.ts
export const API_ENDPOINTS = {
  DOCUMENTS: {
    LIST: '/documents-enhanced/list',
    CREATE: '/documents-enhanced',
    DETAIL: (id: number) => `/documents-enhanced/${id}/detail`,
    UPDATE: (id: number) => `/documents-enhanced/${id}/update`,
    DELETE: (id: number) => `/documents-enhanced/${id}/delete`,
  },
  // ... 其他模組
};
```

---

## HTTP Method 規範

### 為何優先使用 POST

1. **安全性**: 請求參數在 body 中，不暴露於 URL
2. **彈性**: 支援複雜的篩選條件
3. **一致性**: 統一的請求處理模式

### Method 對應
| 操作 | Method | 端點範例 |
|------|--------|----------|
| 列表/查詢 | POST | `/documents-enhanced/list` |
| 建立 | POST | `/documents-enhanced` |
| 更新 | POST | `/documents-enhanced/{id}/update` |
| 刪除 | POST | `/documents-enhanced/{id}/delete` |
| 取得單筆 | POST | `/documents-enhanced/{id}/detail` |

---

## Schema 設計

### 後端 Pydantic Schema
```python
# backend/app/schemas/document.py

class DocumentBase(BaseModel):
    doc_number: str
    subject: str
    doc_type: Optional[str] = None
    # ...

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    doc_number: Optional[str] = None
    subject: Optional[str] = None
    # 所有欄位都是 Optional

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 虛擬欄位
    sender_agency_name: Optional[str] = None
    receiver_agency_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
```

### 前端 TypeScript 型別
```typescript
// frontend/src/types/api.ts

interface OfficialDocument {
  id: number;
  doc_number: string;
  subject: string;
  doc_type?: string;
  // ...
  sender_agency_name?: string;    // 虛擬欄位
  receiver_agency_name?: string;  // 虛擬欄位
  created_at: string;
  updated_at: string;
}
```

---

## 回應結構

### 標準成功回應
```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
```

### 分頁回應
```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
```

### 錯誤回應
```typescript
interface ErrorResponse {
  detail: string;
  // 或
  message: string;
  errors?: ValidationError[];
}
```

---

## 常見錯誤代碼

| 代碼 | 說明 | 常見原因 |
|------|------|---------|
| 404 | Not Found | 路由前綴錯誤 |
| 405 | Method Not Allowed | HTTP Method 錯誤 (GET vs POST) |
| 422 | Unprocessable Entity | Schema 驗證失敗、**undefined 值被序列化為 null** |
| 500 | Internal Server Error | 後端邏輯錯誤 |

---

## 前端 API 請求參數處理規範 (v1.1.0)

> **重要**: 此規範解決 POST 請求 422 錯誤的常見問題

### 問題描述

前端傳送 API 請求時，若將 `undefined` 值直接放入請求物件：
1. `JSON.stringify()` 會將 `undefined` 轉換為 `null`
2. 後端 Pydantic 收到 `null` 但 Schema 定義為 `Optional[str]`
3. Pydantic 驗證失敗，回傳 422 Unprocessable Entity

### 錯誤模式

```typescript
// ❌ 錯誤：直接賦值可能為 undefined 的值
const queryParams = {
  page: params?.page ?? 1,
  limit: params?.limit ?? 20,
  search: params?.search,        // undefined → JSON null → 422
  status: params?.status,        // undefined → JSON null → 422
  business_type: params?.business_type,  // undefined → JSON null → 422
};
```

### 正確模式

```typescript
// ✅ 正確：先建立必要參數，再條件式添加可選參數
const queryParams: Record<string, unknown> = {
  page: params?.page ?? 1,
  limit: params?.limit ?? 20,
  sort_by: params?.sort_by ?? 'name',
  sort_order: params?.sort_order ?? 'asc',
};

// 只在有值時添加可選參數
if (params?.search) queryParams.search = params.search;
if (params?.status) queryParams.status = params.status;
if (params?.business_type) queryParams.business_type = params.business_type;
// 布林值需特別處理（false 是有效值）
if (params?.is_active !== undefined) queryParams.is_active = params.is_active;
// 數值 0 可能是有效值
if (params?.year !== undefined) queryParams.year = params.year;
```

### 注意事項

| 參數類型 | 判斷條件 | 說明 |
|---------|---------|------|
| 字串 | `if (params?.field)` | 空字串視為無效 |
| 數值 | `if (params?.field !== undefined)` | 0 是有效值 |
| 布林 | `if (params?.field !== undefined)` | false 是有效值 |
| 陣列 | `if (params?.field?.length)` | 空陣列視為無效 |

### 受影響的 API 檔案

已修復的檔案（可作為參考範本）：
- `frontend/src/api/vendorsApi.ts`
- `frontend/src/api/projectsApi.ts`
- `frontend/src/api/agenciesApi.ts`
- `frontend/src/api/usersApi.ts`

---

## 開發流程

### 新增 API 端點

1. **後端定義路由**
```python
# backend/app/api/endpoints/xxx.py
@router.post("/action")
async def some_action(...):
    ...
```

2. **確認路由前綴**
```python
# backend/app/api/routes.py
api_router.include_router(xxx.router, prefix="/xxx", tags=["模組名"])
```

3. **前端新增端點常數**
```typescript
// frontend/src/api/endpoints.ts
XXX: {
  ACTION: '/xxx/action',
}
```

4. **API Client 使用**
```typescript
// frontend/src/api/xxxApi.ts
import { API_ENDPOINTS } from './endpoints';
const result = await apiClient.post(API_ENDPOINTS.XXX.ACTION, data);
```

---

## 參考文件

| 文件 | 說明 |
|------|------|
| `docs/specifications/API_ENDPOINT_CONSISTENCY.md` | API 端點一致性 v2.0.0 |
| `frontend/src/api/endpoints.ts` | 前端端點定義 |
| `backend/app/api/routes.py` | 後端路由註冊 |
