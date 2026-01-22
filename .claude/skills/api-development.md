# API 開發規範 (API Development Guide)

> **觸發關鍵字**: API, endpoint, 端點, route, 路由, FastAPI
> **適用範圍**: API 設計、端點定義、前後端整合
> **版本**: 1.1.0
> **最後更新**: 2026-01-22

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

### ⚠️ 端點常數強制規範 (v1.1.0 新增)

**核心規範：所有 API 路徑必須使用 `API_ENDPOINTS` 常數，禁止硬編碼**

```typescript
// ❌ 禁止：硬編碼 API 路徑
async uploadFiles(dispatchOrderId: number) {
  return apiClient.post(
    `/taoyuan-dispatch/dispatch/${dispatchOrderId}/attachments/upload`,  // 違規！
    ...
  );
}

// ✅ 正確：使用端點常數
async uploadFiles(dispatchOrderId: number) {
  return apiClient.post(
    API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_UPLOAD(dispatchOrderId),
    ...
  );
}
```

### 新增端點流程

1. **後端新增 API**
   ```python
   @router.post("/dispatch/{id}/attachments/upload")
   async def upload_attachments(...):
       ...
   ```

2. **前端補充端點常數**
   ```typescript
   // frontend/src/api/endpoints.ts
   DISPATCH_ATTACHMENTS_UPLOAD: (id: number) => `/taoyuan-dispatch/dispatch/${id}/attachments/upload`,
   ```

3. **API 服務使用常數**
   ```typescript
   // frontend/src/api/taoyuanDispatchApi.ts
   return apiClient.post(
     API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_UPLOAD(id),
     ...
   );
   ```

### 常見遺漏場景

| 場景 | 容易遺漏原因 | 檢查方式 |
|------|-------------|----------|
| 檔案上傳 | 使用 FormData 時容易直接寫路徑 | grep 檢查 `apiClient.upload` |
| 檔案下載 | 使用 blob 下載時容易直接寫路徑 | grep 檢查 `downloadPost` |
| 動態 ID 路徑 | 覺得用模板字串較方便 | grep 檢查 `\`/` 模式 |

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

### ⚠️ SSOT 架構 (Single Source of Truth)

**核心規範：所有 Pydantic Schema 必須定義在 `schemas/` 目錄**

```
backend/app/schemas/     ← 唯一的型別定義來源
backend/app/api/endpoints/  ← 只匯入，禁止本地定義
```

```python
# ❌ 禁止：在 endpoints 中定義 BaseModel
# backend/app/api/endpoints/xxx.py
class LocalRequest(BaseModel):  # 違規！
    field: str

# ✅ 正確：從 schemas 匯入
from app.schemas.xxx import XxxRequest
```

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

# 查詢參數也必須定義在 schemas 中
class DocumentListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
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
| 422 | Unprocessable Entity | Schema 驗證失敗 |
| 500 | Internal Server Error | 後端邏輯錯誤 |

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
| `.claude/skills/type-management.md` | 型別管理規範 (SSOT) |
| `.claude/commands/type-sync.md` | 型別同步檢查命令 |
| `frontend/src/api/endpoints.ts` | 前端端點定義 |
| `backend/app/api/routes.py` | 後端路由註冊 |
| `backend/app/schemas/` | 後端 Schema 定義目錄 |
