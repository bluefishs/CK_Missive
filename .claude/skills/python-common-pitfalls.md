# Python 常見陷阱規範

> **版本**: 1.0.0
> **建立日期**: 2026-01-28
> **觸發關鍵字**: Pydantic, forward reference, async, MissingGreenlet, 預設參數, selectinload

---

## 1. Pydantic 前向引用 (Forward Reference)

### 問題描述

當 Pydantic Schema 使用字串形式的前向引用（如 `List["OtherModel"]`）時，如果被引用的模型在不同檔案中定義，會在運行時發生錯誤。

### 錯誤訊息

```
pydantic.errors.PydanticUserError: `ResponseModel` is not fully defined;
you should define `ReferencedModel`, then call `ResponseModel.model_rebuild()`.
```

### 解決方案

在 `__init__.py` 中，所有相關 Schema 導入後呼叫 `model_rebuild()`：

```python
# schemas/taoyuan/__init__.py

# 1. 先導入所有 Schema
from .project import TaoyuanProjectListResponse  # 使用前向引用
from .links import TaoyuanProjectWithLinks       # 被引用的模型

# 2. 重建前向引用
TaoyuanProjectListResponse.model_rebuild()

# 3. 然後匯出
__all__ = [
    "TaoyuanProjectListResponse",
    "TaoyuanProjectWithLinks",
]
```

### 程式碼範例

```python
# ❌ 錯誤 - 前向引用未解析
# project.py
class TaoyuanProjectListResponse(BaseModel):
    items: List["TaoyuanProjectWithLinks"] = []  # 前向引用

# __init__.py
from .project import TaoyuanProjectListResponse  # 使用時報錯！

# ✅ 正確 - 呼叫 model_rebuild()
# __init__.py
from .project import TaoyuanProjectListResponse
from .links import TaoyuanProjectWithLinks  # 確保被引用模型已導入
TaoyuanProjectListResponse.model_rebuild()   # 解析前向引用
```

### 檢查清單

- [ ] Schema 是否使用字串形式的型別引用？（如 `"ModelName"`）
- [ ] 被引用的模型是否在不同檔案中定義？
- [ ] `__init__.py` 是否在所有導入後呼叫 `model_rebuild()`？

---

## 2. SQLAlchemy 非同步關聯載入 (MissingGreenlet)

### 問題描述

在 async SQLAlchemy 中，直接存取未預載入的 relationship 屬性會觸發同步 IO，導致 `MissingGreenlet` 錯誤。

### 錯誤訊息

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

### 解決方案

使用 `selectinload()` 或 `joinedload()` 在查詢時預載入所有需要的關聯：

```python
from sqlalchemy.orm import selectinload

query = select(TaoyuanDispatchOrder).options(
    selectinload(TaoyuanDispatchOrder.document_links).selectinload(
        TaoyuanDispatchDocumentLink.document
    ),
    selectinload(TaoyuanDispatchOrder.payment),  # 載入一對一關聯
    selectinload(TaoyuanDispatchOrder.attachments),  # 載入一對多關聯
)
```

### 程式碼範例

```python
# ❌ 錯誤 - 未預載入關聯
async def get_dispatch_orders(db: AsyncSession):
    result = await db.execute(select(TaoyuanDispatchOrder))
    orders = result.scalars().all()

    for order in orders:
        # MissingGreenlet 錯誤！嘗試 lazy load
        if order.payment:
            print(order.payment.amount)

# ✅ 正確 - 使用 selectinload 預載入
async def get_dispatch_orders(db: AsyncSession):
    result = await db.execute(
        select(TaoyuanDispatchOrder).options(
            selectinload(TaoyuanDispatchOrder.payment)
        )
    )
    orders = result.scalars().all()

    for order in orders:
        # 安全！已預載入
        if order.payment:
            print(order.payment.amount)
```

### 關聯載入策略選擇

| 策略 | 適用場景 | SQL 查詢數 |
|------|---------|-----------|
| `selectinload()` | 一對多、多對多關聯 | 2 (主查詢 + IN 查詢) |
| `joinedload()` | 一對一、多對一關聯 | 1 (JOIN) |
| `subqueryload()` | 大量資料的一對多 | 2 (主查詢 + 子查詢) |

### 檢查清單

- [ ] 所有在 async context 中存取的 relationship 是否都有預載入？
- [ ] 新增的 relationship 是否已加入現有查詢的 `options()`？
- [ ] 巢狀關聯是否使用鏈式 `selectinload(A.b).selectinload(B.c)`？

---

## 3. Python 預設參數陷阱 (None 覆蓋預設值)

### 問題描述

當函數參數有預設值時，明確傳入 `None` 會覆蓋該預設值，而不是使用預設值。

### 問題範例

```python
def get_next_number(prefix: str = '乾坤測字第'):
    return f"{prefix}001號"

# 呼叫方式
get_next_number()      # 返回 "乾坤測字第001號" ✓
get_next_number(None)  # 返回 "None001號" ✗ (None 覆蓋了預設值)
```

### 解決方案

將預設值改為 `None`，並在函數內部明確處理：

```python
from typing import Optional

def get_next_number(prefix: Optional[str] = None) -> str:
    """
    取得下一個編號

    Args:
        prefix: 前綴（預設：乾坤測字第）
    """
    if prefix is None:
        prefix = '乾坤測字第'
    return f"{prefix}001號"
```

### 程式碼範例

```python
# ❌ 錯誤 - 預設值被 None 覆蓋
async def get_next_send_number(
    self,
    prefix: str = '乾坤測字第',  # 問題：傳入 None 會覆蓋
    year: Optional[int] = None
) -> Dict[str, Any]:
    year_pattern = f"{prefix}{roc_year}%"  # prefix 可能是 None！

# ✅ 正確 - 在函數內部處理 None
async def get_next_send_number(
    self,
    prefix: Optional[str] = None,  # 明確接受 None
    year: Optional[int] = None
) -> Dict[str, Any]:
    if prefix is None:
        prefix = '乾坤測字第'  # 在函數內設定預設值
    year_pattern = f"{prefix}{roc_year}%"  # 安全
```

### 常見情境

此問題常發生在：
1. FastAPI 端點將 Pydantic 模型的 Optional 欄位傳給服務層
2. 服務層方法有預設值但接收到 `None`
3. 測試時明確傳入 `None` 進行邊界測試

### 檢查清單

- [ ] 函數參數是否可能從外部接收 `None`？
- [ ] 預設值是否應該在函數內部而非簽名中設定？
- [ ] 是否有對應的單元測試覆蓋 `None` 輸入情境？

---

## 快速診斷命令

```bash
# 檢查前向引用是否有呼叫 model_rebuild
grep -rn "model_rebuild" backend/app/schemas/ --include="*.py"

# 搜尋可能缺少預載入的查詢
grep -rn "\.scalars()" backend/app/ --include="*.py" -B 10 | grep -v "selectinload"

# 搜尋可能的預設參數問題
grep -rn ": str = " backend/app/services/ --include="*.py"
```

---

## 相關文件

- `.claude/skills/api-serialization.md` - API 序列化規範
- `.claude/skills/database-schema.md` - 資料庫結構說明
- `docs/specifications/TYPE_CONSISTENCY.md` - 型別一致性規範
