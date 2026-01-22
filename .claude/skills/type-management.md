# 型別管理規範 (Type Management Guide)

> **觸發關鍵字**: 型別, type, schema, Pydantic, TypeScript, BaseModel, interface
> **適用範圍**: 後端 Schema 定義、前端型別定義、型別同步
> **版本**: 1.1.0
> **建立日期**: 2026-01-18
> **最後更新**: 2026-01-21

---

## 核心原則：單一真實來源 (SSOT)

### 架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        型別定義流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  後端 (唯一來源)                前端 (自動生成)                   │
│  ┌─────────────────┐           ┌─────────────────┐             │
│  │ schemas/*.py    │ ──────►   │ types/generated │ ◄── OpenAPI │
│  │ (Pydantic)      │  /openapi │ /api.d.ts       │    自動生成  │
│  └────────┬────────┘   .json   └────────┬────────┘             │
│           │                             │                       │
│           │                             ▼                       │
│           │                    ┌─────────────────┐             │
│           │                    │ types/generated │             │
│           │                    │ /index.ts       │ ◄── 包裝層  │
│           │                    └────────┬────────┘             │
│           │                             │                       │
│           ▼                             ▼                       │
│  ┌─────────────────┐           ┌─────────────────┐             │
│  │ endpoints/*.py  │           │ api/*.ts        │             │
│  │ (匯入 schemas)  │           │ (匯入 types)    │             │
│  └─────────────────┘           └─────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 後端型別定義規範

### 目錄結構

```
backend/app/schemas/
├── common.py              # 通用型別 (PaginationMeta, ErrorResponse...)
├── document.py            # 公文相關 (DocumentCreate, DocumentResponse...)
├── document_calendar.py   # 行事曆相關
├── document_query.py      # 公文查詢參數
├── document_number.py     # 公文字號
├── agency.py              # 機關相關
├── project.py             # 專案相關
├── project_staff.py       # 專案人員
├── project_vendor.py      # 專案廠商
├── project_agency_contact.py  # 機關承辦
├── user.py                # 使用者
├── vendor.py              # 廠商
├── notification.py        # 通知
├── reminder.py            # 提醒
├── backup.py              # 備份
├── case.py                # 案件
├── secure.py              # 安全請求/回應
└── site_management.py     # 網站管理
```

### 命名慣例

| 類型 | 命名模式 | 範例 |
|------|---------|------|
| 基礎模型 | `{Entity}Base` | `DocumentBase`, `UserBase` |
| 建立請求 | `{Entity}Create` | `DocumentCreate`, `UserCreate` |
| 更新請求 | `{Entity}Update` | `DocumentUpdate`, `UserUpdate` |
| 回應模型 | `{Entity}Response` | `DocumentResponse`, `UserResponse` |
| 列表查詢 | `{Entity}ListQuery` | `DocumentListQuery`, `UserListQuery` |
| 列表回應 | `{Entity}ListResponse` | `DocumentListResponse`, `UserListResponse` |

### 禁止事項

```python
# ❌ 禁止：在 endpoints 目錄中定義 BaseModel
# backend/app/api/endpoints/xxx.py
class MyRequest(BaseModel):  # 禁止！
    field: str

# ✅ 正確：從 schemas 匯入
from app.schemas.xxx import MyRequest
```

---

## Schema 與資料庫模型一致性 (v1.1.0 新增)

### ⚠️ 重要：類型不一致會導致 500 錯誤

**典型錯誤場景**:
```
asyncpg.exceptions.DataError: invalid input for query argument $2: 3 (expected str, got int)
[SQL: UPDATE table SET priority=$2::VARCHAR ...]
```

**根本原因**: Pydantic Schema 定義的類型與資料庫欄位類型不一致。

### 常見類型不一致案例

| 欄位 | Schema 定義 | DB 定義 | 問題 | 解法 |
|------|------------|---------|------|------|
| `priority` | `int` | `VARCHAR(50)` | asyncpg 拒絕整數寫入字串欄位 | 改 Schema 為 `str` |
| `status` | `Enum` | `VARCHAR` | Enum 需序列化 | 使用 `status.value` |
| `id` | `str` | `INTEGER` | 類型不符 | 統一使用 `int` |
| `amount` | `float` | `DECIMAL` | 精度問題 | 使用 `Decimal` |

### 解決方案

#### 方案 1：修改 Schema 使其與 DB 一致（推薦）

```python
# backend/app/schemas/document_calendar.py
class DocumentCalendarEventUpdate(BaseModel):
    # 改為 str 與資料庫 VARCHAR 一致
    priority: Optional[str] = None

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        """接受 int 或 str，統一轉為 str"""
        if v is not None:
            return str(v)
        return v
```

#### 方案 2：在 Service 層進行類型轉換

```python
# backend/app/services/xxx_service.py
async def update_entity(self, db, entity_id, update_data):
    for key, value in update_data.items():
        if hasattr(db_entity, key):
            # 特別處理：資料庫欄位是 String，但輸入可能是 int
            if key == 'priority' and value is not None:
                value = str(value)
            setattr(db_entity, key, value)
```

### 檢查清單

- [ ] 新增/修改 Schema 欄位前，先確認資料庫欄位類型
- [ ] 特別注意 `VARCHAR` 欄位，Schema 應定義為 `str`
- [ ] 使用 `field_validator` 處理類型正規化
- [ ] 測試 API 確認無類型錯誤

### Schema 檔案範本

```python
"""
{模組名稱}相關 Pydantic Schema 定義

@version 1.0.0
@date YYYY-MM-DD
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 基礎模型
# ============================================================================

class EntityBase(BaseModel):
    """實體基礎 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="名稱")
    description: Optional[str] = Field(None, description="說明")


class EntityCreate(EntityBase):
    """建立實體 Schema"""
    pass


class EntityUpdate(BaseModel):
    """更新實體 Schema (所有欄位可選)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class EntityResponse(EntityBase):
    """實體回應 Schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class EntityListQuery(BaseModel):
    """實體列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: str = Field(default="desc", description="排序方向")
```

---

## 前端型別定義規範

### 目錄結構

```
frontend/src/types/
├── generated/
│   ├── api.d.ts      # OpenAPI 自動生成 (勿手動編輯)
│   ├── index.ts      # 型別包裝層 (可自訂別名)
│   └── CHANGELOG.md  # 型別變更日誌
├── api.ts            # 舊版手動定義 (逐步遷移至 generated)
└── index.ts          # 主要匯出
```

### 型別包裝層

```typescript
// frontend/src/types/generated/index.ts
import type { components } from './api';

// 業務實體型別 (添加 Api 前綴避免衝突)
export type ApiDocumentResponse = components['schemas']['DocumentResponse'];
export type ApiUserResponse = components['schemas']['UserResponse'];
export type ApiAgency = components['schemas']['Agency'];

// 請求型別
export type ApiDocumentCreate = components['schemas']['DocumentCreate'];
export type ApiDocumentUpdate = components['schemas']['DocumentUpdate'];

// 查詢參數
export type ApiDocumentListQuery = components['schemas']['DocumentListQuery'];

// 回應型別
export type ApiPaginatedResponse<T> = {
  success: boolean;
  items: T[];
  pagination: components['schemas']['PaginationMeta'];
};
```

### 使用方式

```typescript
// 在 API 服務中使用
import type { ApiDocumentResponse, ApiDocumentCreate } from '../types/generated';

export const createDocument = async (data: ApiDocumentCreate): Promise<ApiDocumentResponse> => {
  const response = await apiClient.post('/documents-enhanced', data);
  return response.data;
};
```

---

## OpenAPI 自動生成

### 生成命令

```bash
# 生成 TypeScript 型別定義
cd frontend && npm run api:generate

# 生成並更新變更日誌
cd frontend && npm run api:generate:changelog
```

### package.json 配置

```json
{
  "scripts": {
    "api:generate": "openapi-typescript http://localhost:8001/openapi.json -o src/types/generated/api.d.ts",
    "api:generate:changelog": "node scripts/type-changelog.js generate"
  }
}
```

### Pre-commit 檢查

```bash
# .husky/pre-commit
# TypeScript 編譯檢查
npx tsc --noEmit

# 後端 Schema 變更檢測
SCHEMA_CHANGED=$(git diff --cached --name-only | grep -E "backend/app/schemas/.*\.py$")
if [ -n "$SCHEMA_CHANGED" ]; then
  echo "⚠️ 偵測到後端 Schema 變更，請執行 npm run api:generate"
fi
```

---

## 新增欄位流程

### 步驟

1. **後端 Schema 新增欄位**
   ```python
   # backend/app/schemas/document.py
   class DocumentResponse(DocumentBase):
       new_field: Optional[str] = Field(None, description="新欄位")
   ```

2. **重新生成前端型別**
   ```bash
   cd frontend && npm run api:generate
   ```

3. **驗證 TypeScript 編譯**
   ```bash
   cd frontend && npx tsc --noEmit
   ```

4. **(可選) 更新型別包裝層**
   ```typescript
   // 如需自訂別名
   export type ApiDocumentResponse = components['schemas']['DocumentResponse'];
   ```

### 檢查清單

- [ ] 後端 Schema 欄位定義完整
- [ ] 執行 `npm run api:generate`
- [ ] TypeScript 編譯通過
- [ ] API 回應格式正確

---

## 常見問題排解

### Q1: TypeScript 報型別不存在

```
Property 'XXX' does not exist on type 'components["schemas"]'
```

**原因**: OpenAPI 尚未包含該 Schema

**解法**:
1. 確認後端有定義對應的 Pydantic Schema
2. 確認後端服務正在運行
3. 重新執行 `npm run api:generate`

### Q2: 欄位名稱不一致

```
後端: sender_agency_id
前端: senderAgencyId
```

**解法**: 前端統一使用 snake_case (與後端一致)

### Q3: Optional 型別不匹配

```python
# 後端
field: Optional[int] = None
```

```typescript
// 前端應該是
field?: number;  // 或 field: number | null;
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `/type-sync` | 型別同步檢查命令 |
| `MANDATORY_CHECKLIST.md` 清單 H | 型別管理開發檢查清單 |
| `backend/app/schemas/` | 後端 Schema 定義目錄 |
| `frontend/src/types/generated/` | 前端自動生成型別 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.1.0 | 2026-01-21 | **新增 Schema-DB 類型一致性章節**（類型不一致案例、解決方案、檢查清單） |
| 1.0.0 | 2026-01-18 | 初版建立，包含 SSOT 架構、OpenAPI 自動生成、命名規範 |

---

*維護者: Claude Code Assistant*
