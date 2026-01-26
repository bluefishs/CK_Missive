# Schema 設計規範

**技能名稱**：型別包裝層設計 (Type Wrapper Layer)
**用途**：確保後端 Pydantic Schema 與前端 TypeScript 型別的一致性
**適用場景**：API 開發、型別定義、前後端整合
**建立日期**：2026-01-18

---

## 一、型別包裝層架構

### 1.1 概念說明

型別包裝層 (Type Wrapper Layer) 是將 Pydantic 模型從端點層抽離，統一管理在 `schemas/` 目錄的架構模式。

```
┌─────────────────────────────────────────────────────────────────┐
│                      型別包裝層架構圖                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Backend                              Frontend                   │
│  ┌──────────────────┐                ┌──────────────────┐       │
│  │ schemas/         │  ←──對應──→    │ types/           │       │
│  │ ├── base.py      │                │ ├── api.ts       │       │
│  │ ├── spatial/     │                │ ├── spatial.ts   │       │
│  │ ├── real_estate/ │                │ ├── realEstate.ts│       │
│  │ └── compensation/│                │ └── compensation/│       │
│  └──────────────────┘                └──────────────────┘       │
│           │                                   │                  │
│           ▼                                   ▼                  │
│  ┌──────────────────┐                ┌──────────────────┐       │
│  │ endpoints/       │                │ components/      │       │
│  │ (使用 schema)     │                │ (使用 types)     │       │
│  └──────────────────┘                └──────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心原則

| 原則 | 說明 | 範例 |
|------|------|------|
| **關注點分離** | 型別定義與業務邏輯分離 | Schema 不含 DB 操作 |
| **單一來源** | 每個模型只定義一次 | 從 `schemas/` 導入，不在端點重複定義 |
| **領域組織** | 按業務領域分目錄 | `spatial/`, `real_estate/`, `compensation/` |
| **前後端對應** | Backend Schema ↔ Frontend Types | `BufferRequest` ↔ `BufferRequest` |

---

## 二、目錄結構

### 2.1 Backend Schema 結構

```
backend/app/schemas/
├── __init__.py           # 主入口，匯出常用模型
├── base.py               # 基礎模型 (StandardResponse, PaginationMeta)
│
├── spatial/              # 空間分析領域
│   ├── __init__.py       # 領域入口
│   ├── analysis.py       # 分析請求模型
│   ├── layer.py          # 圖層相關模型
│   └── query.py          # 查詢參數模型
│
├── real_estate/          # 不動產領域
│   ├── __init__.py
│   ├── query.py          # 查詢請求
│   ├── coordinates.py    # 座標相關
│   ├── statistics.py     # 統計回應
│   └── transcripts.py    # 謄本資料
│
├── compensation/         # 補償估價領域
│   ├── __init__.py
│   ├── case.py           # 案件模型
│   └── project.py        # 專案模型
│
└── basemap/              # 底圖相關
    ├── __init__.py
    └── layer_source.py   # 圖層來源
```

### 2.2 Frontend Types 結構

```
frontend/src/types/
├── index.ts              # 主入口
├── api.ts                # API 通用型別
├── spatial.ts            # 空間分析型別
├── realEstate.ts         # 不動產型別
└── compensation/         # 補償估價型別
    ├── index.ts
    ├── case.ts
    └── project.ts
```

---

## 三、Pydantic 模型規範

### 3.1 基本結構

```python
"""
領域名稱 Schema
Domain Name Schemas

說明文字。

Created: YYYY-MM-DD
Architecture: Type Wrapper Layer (型別包裝層)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequestModel(BaseModel):
    """請求模型說明"""

    required_field: int = Field(..., description="必填欄位說明")
    optional_field: Optional[str] = Field(None, description="選填欄位說明")
    default_field: str = Field(default="value", description="有預設值的欄位")

    class Config:
        json_schema_extra = {
            "example": {
                "required_field": 1,
                "optional_field": "example",
                "default_field": "value"
            }
        }
```

### 3.2 命名規範

| 類型 | 命名模式 | 範例 |
|------|---------|------|
| 請求模型 | `{Action}Request` | `BufferRequest`, `QueryRequest` |
| 回應模型 | `{Entity}Response` | `LayerInfoResponse`, `StatisticsResponse` |
| 建立模型 | `{Entity}Create` | `SpatialLayerCreate`, `CaseCreate` |
| 更新模型 | `{Entity}Update` | `SpatialLayerUpdate`, `CaseUpdate` |
| 列表項目 | `{Entity}Item` | `TransactionItem`, `ParcelItem` |
| 查詢參數 | `{Entity}Query` | `BBoxQuery`, `FilterQuery` |

### 3.3 欄位定義規範

```python
# ✅ 正確：使用 Field 並提供 description
layer_id: int = Field(..., description="圖層 ID")

# ✅ 正確：數值欄位加驗證
distance: float = Field(..., gt=0, description="緩衝距離")
limit: int = Field(default=10, ge=1, le=100, description="返回數量限制")

# ✅ 正確：選項欄位說明可用值
unit: str = Field(default="meters", description="單位: meters, kilometers, feet, miles")

# ❌ 錯誤：缺少 description
layer_id: int

# ❌ 錯誤：沒有驗證的數值
limit: int = 10
```

### 3.4 Config 設定

```python
class Config:
    # Pydantic v2 語法
    json_schema_extra = {
        "example": { ... }
    }

    # 忽略額外欄位 (重構相容性)
    extra = "ignore"
```

---

## 四、導入與使用

### 4.1 端點層導入

```python
# ✅ 正確：從 schemas 模組導入
from backend.app.schemas.spatial import (
    BufferRequest,
    DistanceRequest,
    LayerInfoResponse,
)

# ❌ 錯誤：在端點內定義模型
class BufferRequest(BaseModel):
    ...
```

### 4.2 模組 __init__.py 範例

```python
"""
空間分析 Schema 模組
Spatial Analysis Schema Module
"""

from backend.app.schemas.spatial.analysis import (
    BufferRequest,
    DistanceRequest,
    IntersectRequest,
)
from backend.app.schemas.spatial.layer import (
    LayerInfoResponse,
    SpatialLayerCreate,
    SpatialLayerUpdate,
)
from backend.app.schemas.spatial.query import (
    BBoxQuery,
    CoordinatePoint,
    SpatialQueryRequest,
)

__all__ = [
    # Analysis
    "BufferRequest",
    "DistanceRequest",
    "IntersectRequest",
    # Layer
    "LayerInfoResponse",
    "SpatialLayerCreate",
    "SpatialLayerUpdate",
    # Query
    "BBoxQuery",
    "CoordinatePoint",
    "SpatialQueryRequest",
]
```

---

## 五、前後端型別對應

### 5.1 型別映射表

| Python (Pydantic) | TypeScript | 說明 |
|-------------------|------------|------|
| `int` | `number` | 整數 |
| `float` | `number` | 浮點數 |
| `str` | `string` | 字串 |
| `bool` | `boolean` | 布林值 |
| `Optional[T]` | `T \| null` | 可選型別 |
| `List[T]` | `T[]` | 陣列 |
| `Dict[str, T]` | `Record<string, T>` | 字典 |
| `datetime` | `string` (ISO 8601) | 日期時間 |
| `Literal["a", "b"]` | `"a" \| "b"` | 字面量聯合型別 |

### 5.2 Frontend 型別定義範例

```typescript
// frontend/src/types/spatial.ts

export interface BufferRequest {
  layer_id: number;
  distance: number;
  unit?: 'meters' | 'kilometers' | 'feet' | 'miles';
  segments?: number;
  dissolve?: boolean;
}

export interface LayerInfoResponse {
  id: number;
  name: string;
  table_name: string;
  geometry_type: 'Point' | 'LineString' | 'Polygon' | 'MultiPolygon';
  srid: number;
  feature_count: number;
  extent?: {
    minx: number;
    miny: number;
    maxx: number;
    maxy: number;
  };
  properties?: string[];
}
```

---

## 六、遷移指南

### 6.1 將端點內模型遷移至 schemas/

1. **識別模型**：找出端點檔案中的 Pydantic 模型定義
2. **建立 Schema 檔案**：在對應領域目錄建立檔案
3. **複製並優化**：移動模型定義，加入 `json_schema_extra`
4. **更新 __init__.py**：在領域 `__init__.py` 匯出模型
5. **更新端點**：移除端點內定義，改為導入
6. **驗證**：執行語法檢查確認導入正確

### 6.2 遷移範例

```python
# 遷移前 - endpoints/spatial/analysis.py
from pydantic import BaseModel, Field

class BufferRequest(BaseModel):
    layer_id: int = Field(...)
    distance: float = Field(...)

@router.post("/buffer")
async def create_buffer(request: BufferRequest):
    ...

# 遷移後 - endpoints/spatial/analysis.py
from backend.app.schemas.spatial import BufferRequest

@router.post("/buffer")
async def create_buffer(request: BufferRequest):
    ...
```

---

## 七、驗證工具

### 7.1 語法檢查

```bash
# 編譯檢查所有 schema 檔案
python -m py_compile backend/app/schemas/spatial/*.py

# 導入驗證
python -c "from backend.app.schemas.spatial import BufferRequest; print('OK')"
```

### 7.2 架構驗證

```bash
# 確認端點不再內定義模型
grep -r "class.*Request.*BaseModel" backend/app/api/v1/endpoints/
```

---

## 八、相關文件

- `docs/ARCHITECTURE.md` - 三層式架構設計
- `.claude/skills/codewiki-procedures.md` - 文件管理規範
- `backend/app/schemas/base.py` - 基礎回應模型

---

**最後更新**：2026-01-18
