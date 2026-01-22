# API 序列化與資料返回規範

> **觸發關鍵字**: 序列化, serialize, API 返回, ORM, 500 錯誤, 資料轉換, 批次處理, 效能
> **適用範圍**: 後端 API 端點、資料返回格式、ORM 模型處理、效能優化
> **版本**: 1.1.0
> **建立日期**: 2026-01-21
> **最後更新**: 2026-01-22

---

## 問題背景

FastAPI + SQLAlchemy + Pydantic 架構中，API 返回資料時常見的序列化問題：

1. **ORM 模型無法序列化**: 直接返回 SQLAlchemy 模型導致 500 錯誤
2. **類型不一致**: Schema 定義與資料庫欄位類型不同
3. **欄位名稱錯誤**: 程式碼存取不存在的模型欄位
4. **datetime 處理**: 未正確轉換為 ISO 格式字串

---

## 核心規範

### 規範 1：禁止直接返回 ORM 模型

**錯誤示例**:
```python
# ❌ 會導致 PydanticSerializationError
@router.post("/items")
async def get_items(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return {"items": items}  # 直接返回 ORM 模型列表
```

**錯誤訊息**:
```
pydantic_core._pydantic_core.PydanticSerializationError:
Unable to serialize unknown type: <class 'app.extended.models.Item'>
```

### 正確做法

#### 方法 A：使用 Pydantic Schema（推薦）

```python
from app.schemas.item import ItemResponse

@router.post("/items", response_model=List[ItemResponse])
async def get_items(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Item))
    items = result.scalars().all()

    # 使用 Schema 序列化
    return [ItemResponse.model_validate(item) for item in items]
```

#### 方法 B：手動轉換為字典

```python
@router.post("/items")
async def get_items(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Item))
    items = result.scalars().all()

    # 手動轉換
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    }
```

#### 方法 C：使用 response_model 自動處理

```python
from app.schemas.item import ItemListResponse

@router.post("/items", response_model=ItemListResponse)
async def get_items(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Item))
    items = result.scalars().all()

    # response_model 會自動處理序列化（需 Schema 設定 from_attributes=True）
    return ItemListResponse(items=items, total=len(items))
```

**Schema 定義**:
```python
class ItemResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # 關鍵設定
```

---

### 規範 2：datetime 欄位處理

**問題**: datetime 對象在某些情況下無法直接序列化。

**解法**:

```python
# ❌ 可能有問題
{"created_at": doc.created_at}

# ✅ 安全做法
{"created_at": doc.created_at.isoformat() if doc.created_at else None}
```

**或使用 Pydantic Schema 自動處理**:
```python
class ItemResponse(BaseModel):
    created_at: Optional[datetime] = None  # Pydantic 會自動序列化為 ISO 格式
```

---

### 規範 3：欄位名稱必須與模型一致

**常見錯誤**:
```python
# ❌ 錯誤：模型沒有 'type' 欄位
{"type": doc.type}

# ✅ 正確：使用實際欄位名稱 'doc_type'
{"doc_type": doc.doc_type}
```

**預防措施**:
1. 在存取欄位前，先確認 ORM 模型定義
2. 使用 IDE 的自動補全功能
3. 使用 `hasattr()` 進行防禦性檢查

```python
# 防禦性寫法
{
    "deadline": doc.deadline.isoformat() if hasattr(doc, 'deadline') and doc.deadline else None,
}
```

---

### 規範 4：Schema 類型與資料庫一致

**問題場景**:
```
asyncpg.exceptions.DataError: invalid input for query argument $2: 3 (expected str, got int)
```

**原因**: Schema 定義 `priority: int`，但資料庫欄位是 `VARCHAR`。

**解法**:

```python
# 方法 A：修改 Schema 類型
class EventUpdate(BaseModel):
    priority: Optional[str] = None  # 與 DB VARCHAR 一致

# 方法 B：使用 validator 轉換
class EventUpdate(BaseModel):
    priority: Optional[int] = None

    @field_validator('priority', mode='before')
    @classmethod
    def to_string(cls, v):
        return str(v) if v is not None else v

# 方法 C：在 Service 層轉換
if key == 'priority' and value is not None:
    value = str(value)
```

---

## 常見欄位類型對照

| 用途 | 資料庫類型 | Schema 類型 | 注意事項 |
|------|-----------|------------|---------|
| 主鍵 | `INTEGER` | `int` | - |
| 狀態 | `VARCHAR(50)` | `str` | 勿用 `Enum` 直接存儲 |
| 優先級 | `VARCHAR(50)` | `str` | 常見錯誤：定義為 `int` |
| 日期時間 | `TIMESTAMP` | `datetime` | 自動處理 |
| 金額 | `DECIMAL` | `Decimal` | 避免 `float` |
| 布林 | `BOOLEAN` | `bool` | - |
| JSON | `JSONB` | `Dict[str, Any]` | - |

---

## 檢測腳本

### 檢測直接返回 ORM 模型的程式碼

```bash
# 找出可能有問題的程式碼
grep -rn "\.scalars()\.all()" backend/app/api/endpoints/ --include="*.py"

# 檢查返回語句
grep -A5 "scalars().all()" backend/app/api/endpoints/*.py | grep "return"
```

### 檢測序列化錯誤

```bash
# 查看後端日誌
pm2 logs ck-backend --lines 100 | grep -i "serialize\|serialization"

# 測試 API
curl -X POST http://localhost:8001/api/{endpoint} \
  -H "Content-Type: application/json" \
  -d '{}' 2>&1 | grep -i "error"
```

---

## 快速修復範本

### 範本 1：列表查詢端點

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_async_db
from app.extended.models import MyEntity
from app.schemas.my_entity import MyEntityResponse

router = APIRouter()

@router.post("/entities")
async def get_entities(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(MyEntity).limit(100))
    entities = result.scalars().all()

    # ✅ 正確：轉換為可序列化格式
    return {
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entities
        ],
        "total": len(entities)
    }
```

### 範本 2：更新操作端點

```python
@router.post("/entities/update")
async def update_entity(
    update_data: EntityUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    entity = await get_entity_by_id(db, update_data.entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")

    # 取得更新資料
    data = update_data.model_dump(exclude_unset=True, exclude={'entity_id'})

    for key, value in data.items():
        if hasattr(entity, key):
            # ✅ 類型轉換處理
            if key in ('priority', 'status') and value is not None:
                value = str(value)
            setattr(entity, key, value)

    await db.commit()
    await db.refresh(entity)

    # ✅ 返回序列化後的資料
    return {
        "success": True,
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "updated_at": entity.updated_at.isoformat()
        }
    }
```

---

## 規範 5：批次處理效能優化 (v1.1.0 新增)

### 問題背景

在列表查詢 API 中，若需要計算衍生欄位（如累進金額），常見的錯誤做法是在迴圈內逐筆 commit：

```python
# ❌ 錯誤：每筆都 commit，造成效能問題
for item in items:
    if item.needs_recalculation:
        item.calculated_field = await calculate(item)
        await db.commit()  # N 次 commit！
```

### 正確做法：批次收集後一次 commit

```python
# ✅ 正確：批次處理
items_to_update = []

for item in items:
    if item.needs_recalculation:
        item.calculated_field = await calculate(item)
        items_to_update.append(item)

# 一次 commit
if items_to_update:
    await db.commit()
```

### 實際案例：契金累進金額計算

```python
@router.post("/payments/list")
async def list_payments(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(stmt)
    items = result.scalars().all()

    # 收集需要更新的項目
    items_to_update = []

    response_items = []
    for item in items:
        cumulative = item.cumulative_amount

        if cumulative is None or cumulative == 0:
            # 重新計算，但不立即 commit
            cumulative, remaining = await _calculate_cumulative(...)
            item.cumulative_amount = cumulative
            item.remaining_amount = remaining
            items_to_update.append(item)

        response_items.append(serialize(item))

    # 批次更新（一次 commit）
    if items_to_update:
        await db.commit()

    return {"items": response_items}
```

---

## 規範 6：避免硬編碼設定值 (v1.1.0 新增)

### 問題背景

常見錯誤是將業務設定值硬編碼在程式碼中：

```python
# ❌ 錯誤：硬編碼預算金額
total_budget = 6035000  # 如果金額變更，需要改程式碼
```

### 正確做法：從資料庫或設定檔動態取得

```python
# ✅ 正確：從承攬案件動態取得
from app.extended.models import ContractProject

budget_result = await db.execute(
    select(ContractProject.winning_amount, ContractProject.contract_amount)
    .where(ContractProject.id == contract_project_id)
)
budget_row = budget_result.first()
total_budget = float(budget_row[0] or budget_row[1] or 0) if budget_row else 0
```

### 適用場景

| 設定類型 | 硬編碼問題 | 動態來源 |
|----------|-----------|----------|
| 預算金額 | 合約變更需改程式碼 | `ContractProject.winning_amount` |
| 分頁預設值 | 需求變更需改程式碼 | 環境變數或設定表 |
| 狀態選項 | 新增狀態需改程式碼 | 資料庫 enum 或選項表 |
| API 路徑 | 路徑變更需改多處 | `API_ENDPOINTS` 常數 |

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `MANDATORY_CHECKLIST.md` 清單 K | API 序列化開發檢查清單 |
| `type-management.md` | 型別管理規範 |
| `docs/FIX_REPORT_2026-01-21_API_SERIALIZATION.md` | 序列化問題修復案例 |

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.1.0 | 2026-01-22 | **新增批次處理效能優化、避免硬編碼設定值章節** |
| 1.0.0 | 2026-01-21 | 初版建立，包含 ORM 序列化、類型一致性、檢測腳本 |

---

*維護者: Claude Code Assistant*
