# API 回應格式規範

> 版本: 1.0.0
> 建立日期: 2026-01-08
> 用途: 統一前後端 API 回應格式，確保一致性

---

## 一、標準回應結構

### 1.1 成功回應 - 列表

```json
{
  "success": true,
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 10,
  "total_pages": 10
}
```

**TypeScript 定義**:

```typescript
interface ListResponse<T> {
  success: boolean;
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
```

### 1.2 成功回應 - 單筆

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**TypeScript 定義**:

```typescript
interface SingleResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
```

### 1.3 成功回應 - 操作

```json
{
  "success": true,
  "message": "刪除成功",
  "affected_count": 5
}
```

**TypeScript 定義**:

```typescript
interface ActionResponse {
  success: boolean;
  message: string;
  affected_count?: number;
}
```

---

## 二、錯誤回應結構

### 2.1 標準錯誤

```json
{
  "success": false,
  "detail": "錯誤描述訊息",
  "error_code": "VALIDATION_ERROR"
}
```

**TypeScript 定義**:

```typescript
interface ErrorResponse {
  success: false;
  detail: string;
  error_code?: string;
}
```

### 2.2 驗證錯誤 (Pydantic)

```json
{
  "detail": [
    {
      "loc": ["body", "doc_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 2.3 業務錯誤

```json
{
  "success": false,
  "detail": "公文字號已存在",
  "error_code": "DUPLICATE_DOCUMENT",
  "conflict_id": 123
}
```

---

## 三、錯誤代碼對照表

### 3.1 系統錯誤 (5xx)

| 錯誤代碼 | HTTP Status | 說明 |
|---------|-------------|------|
| `INTERNAL_ERROR` | 500 | 內部伺服器錯誤 |
| `DATABASE_ERROR` | 500 | 資料庫連線錯誤 |
| `SERVICE_UNAVAILABLE` | 503 | 服務暫時不可用 |

### 3.2 客戶端錯誤 (4xx)

| 錯誤代碼 | HTTP Status | 說明 |
|---------|-------------|------|
| `VALIDATION_ERROR` | 400 | 請求參數驗證失敗 |
| `UNAUTHORIZED` | 401 | 未授權 (未登入) |
| `FORBIDDEN` | 403 | 權限不足 |
| `NOT_FOUND` | 404 | 資源不存在 |
| `DUPLICATE_ENTRY` | 409 | 重複資料 |

### 3.3 業務錯誤

| 錯誤代碼 | 說明 | 適用場景 |
|---------|------|---------|
| `DUPLICATE_DOCUMENT` | 公文字號重複 | 公文新增/匯入 |
| `INVALID_DATE_FORMAT` | 日期格式錯誤 | 日期解析失敗 |
| `AGENCY_NOT_FOUND` | 機關不存在 | 機關關聯時 |
| `PROJECT_NOT_FOUND` | 案件不存在 | 案件關聯時 |
| `IMPORT_FAILED` | 匯入失敗 | CSV/Excel 匯入 |
| `EXPORT_FAILED` | 匯出失敗 | 資料匯出 |
| `SYNC_FAILED` | 同步失敗 | Google Calendar |

---

## 四、後端實作規範

### 4.1 使用 ServiceResponse

```python
# backend/app/services/base/service_response.py

from dataclasses import dataclass
from typing import Any, Optional, List

@dataclass
class ServiceResponse:
    success: bool
    data: Any = None
    message: str = ""
    error_code: Optional[str] = None
    errors: Optional[List[str]] = None

# 使用範例
def create_document(data: dict) -> ServiceResponse:
    try:
        doc = Document(**data)
        db.add(doc)
        db.commit()
        return ServiceResponse(
            success=True,
            data=doc,
            message="公文建立成功"
        )
    except IntegrityError:
        return ServiceResponse(
            success=False,
            message="公文字號已存在",
            error_code="DUPLICATE_DOCUMENT"
        )
```

### 4.2 API 端點回應

```python
# backend/app/api/endpoints/documents_enhanced.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

@router.post("/create")
async def create_document(data: DocumentCreate):
    result = await document_service.create(data)

    if not result.success:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "detail": result.message,
                "error_code": result.error_code
            }
        )

    return {
        "success": True,
        "data": result.data,
        "message": result.message
    }
```

### 4.3 例外處理器

```python
# backend/app/core/exceptions.py

from fastapi import Request
from fastapi.responses import JSONResponse

async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "內部伺服器錯誤",
            "error_code": "INTERNAL_ERROR"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

# main.py 註冊
app.add_exception_handler(Exception, generic_exception_handler)
```

---

## 五、前端實作規範

### 5.1 統一錯誤處理

```typescript
// frontend/src/api/client.ts

export async function handleApiResponse<T>(
  response: Response
): Promise<T> {
  const data = await response.json();

  if (!response.ok || data.success === false) {
    const error = new ApiError(
      data.detail || data.message || '請求失敗',
      data.error_code
    );
    throw error;
  }

  return data;
}

class ApiError extends Error {
  constructor(
    message: string,
    public errorCode?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
```

### 5.2 錯誤訊息顯示

```typescript
// frontend/src/utils/errorHandler.ts

import { notification } from 'antd';

const ERROR_MESSAGES: Record<string, string> = {
  DUPLICATE_DOCUMENT: '公文字號已存在，請檢查後重試',
  VALIDATION_ERROR: '輸入資料格式錯誤',
  UNAUTHORIZED: '請先登入系統',
  FORBIDDEN: '您沒有執行此操作的權限',
  NOT_FOUND: '找不到請求的資源',
  INTERNAL_ERROR: '系統發生錯誤，請稍後再試',
};

export function showApiError(error: ApiError) {
  const message = ERROR_MESSAGES[error.errorCode || ''] || error.message;

  notification.error({
    message: '操作失敗',
    description: message,
  });
}
```

### 5.3 React Query 錯誤處理

```typescript
// 使用 React Query 時的錯誤處理

const { mutate } = useMutation({
  mutationFn: createDocument,
  onError: (error: ApiError) => {
    showApiError(error);
  },
  onSuccess: (data) => {
    notification.success({ message: data.message });
  },
});
```

---

## 六、遷移指南

### 6.1 現有 API 遷移

對於現有使用 `{detail: "..."}` 格式的 API：

```python
# 舊格式
raise HTTPException(status_code=400, detail="錯誤訊息")

# 新格式
return JSONResponse(
    status_code=400,
    content={
        "success": False,
        "detail": "錯誤訊息",
        "error_code": "VALIDATION_ERROR"
    }
)
```

### 6.2 向後相容

前端應同時支援兩種格式：

```typescript
function extractErrorMessage(error: any): string {
  // 新格式
  if (error.detail && typeof error.detail === 'string') {
    return error.detail;
  }
  // Pydantic 驗證錯誤
  if (Array.isArray(error.detail)) {
    return error.detail.map(e => e.msg).join(', ');
  }
  // 舊格式
  if (error.message) {
    return error.message;
  }
  return '未知錯誤';
}
```

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `docs/ERROR_HANDLING_GUIDE.md` | 錯誤處理指南 |
| `docs/specifications/TYPE_MAPPING.md` | 型別對照表 |
| `backend/app/core/exceptions.py` | 後端例外處理 |
| `frontend/src/api/client.ts` | 前端 API 客戶端 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-08 | 初版建立 |

---

*文件維護: Claude Code Assistant*
