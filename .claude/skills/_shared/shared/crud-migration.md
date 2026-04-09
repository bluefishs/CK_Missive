---
name: crud-migration
description: 統一 CRUD 層架構，處理棄用 API 遷移
version: 1.0.0
category: shared
triggers:
  - CRUD 遷移
  - crud migration
  - API 遷移
  - 棄用警告
  - deprecation
updated: 2026-01-22
---

# CRUD Migration Skill

> **用途**: 統一 CRUD 層架構，處理棄用 API 遷移
> **觸發**: CRUD 遷移, crud migration, API 遷移
> **版本**: 1.0.0
> **分類**: shared

**適用場景**：新增 CRUD 模組、遷移舊模組、處理棄用警告

---

## 一、CRUD 架構概覽

### 1.1 目錄結構

```
backend/app/
├── api/v1/crud/          # ✅ 新位置（統一 CRUD 層）
│   ├── __init__.py       # 統一匯出
│   ├── base.py           # CRUDBase 基礎類別
│   ├── transaction.py    # 交易 CRUD
│   ├── land_parcel.py    # 地號 CRUD
│   ├── ai_chat_log.py    # AI 對話 CRUD
│   ├── analysis_module.py# 分析模組 CRUD
│   └── generated_report.py# 報表 CRUD
│
├── crud/                  # ⚠️ 舊位置（已棄用）
│   ├── __init__.py       # 含 DeprecationWarning
│   └── ...               # 向後相容匯出
```

### 1.2 匯入路徑

```python
# ✅ 正確：使用新位置
from backend.app.api.v1.crud import (
    transaction_crud,
    land_parcel_crud,
    crud_ai_chat_log,
    analysis_module_crud,
    GeneratedReportCRUD,
)

# ❌ 棄用：舊位置（會產生 DeprecationWarning）
from backend.app.crud import transaction_crud
```

---

## 二、新增 CRUD 模組

### 2.1 基礎類別繼承

```python
# backend/app/api/v1/crud/my_module.py
"""
模組名稱 CRUD 操作
My Module CRUD Operations

Created: YYYY-MM-DD
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.api.v1.crud.base import CRUDBase
from backend.app.models.my_module import MyModel
from backend.app.schemas.my_module import MyModelCreate, MyModelUpdate


class CRUDMyModule(CRUDBase[MyModel, MyModelCreate, MyModelUpdate]):
    """模組 CRUD 操作類"""

    def get_by_custom_field(
        self, db: Session, *, custom_field: str
    ) -> Optional[MyModel]:
        """根據自訂欄位查詢"""
        return (
            db.query(self.model)
            .filter(self.model.custom_field == custom_field)
            .first()
        )

    def get_multi_by_status(
        self, db: Session, *, status: str, skip: int = 0, limit: int = 100
    ) -> List[MyModel]:
        """根據狀態取得多筆記錄"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )


# 單例實例
my_module_crud = CRUDMyModule(MyModel)
```

### 2.2 靜態方法模式（無繼承）

```python
# 適用於特殊 CRUD 邏輯
class GeneratedReportCRUD:
    """生成報表 CRUD 操作類"""

    @staticmethod
    def create(db: Session, **kwargs) -> GeneratedReport:
        """建立記錄"""
        report = GeneratedReport(**kwargs)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_by_id(db: Session, report_id: int) -> Optional[GeneratedReport]:
        """根據 ID 取得記錄"""
        return (
            db.query(GeneratedReport)
            .filter(GeneratedReport.id == report_id)
            .first()
        )

    @staticmethod
    def mark_as_deleted(
        db: Session,
        report_id: int,
        deleted_by: Optional[str] = None,
        physical_delete: bool = False
    ) -> Optional[GeneratedReport]:
        """軟刪除/物理刪除"""
        report = GeneratedReportCRUD.get_by_id(db, report_id)
        if not report:
            return None

        if physical_delete and os.path.exists(report.file_path):
            os.remove(report.file_path)

        report.status = "deleted"
        report.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
        return report


generated_report_crud = GeneratedReportCRUD()
```

### 2.3 更新 __init__.py

```python
# backend/app/api/v1/crud/__init__.py

# 新增模組匯入
from backend.app.api.v1.crud.my_module import (
    CRUDMyModule,
    my_module_crud,
)

__all__ = [
    # ... 現有匯出
    # 新增
    "CRUDMyModule",
    "my_module_crud",
]
```

---

## 三、遷移現有模組

### 3.1 遷移步驟

```bash
# 1. 複製並重構模組
cp backend/app/crud/old_module.py backend/app/api/v1/crud/new_module.py

# 2. 更新模組內的匯入路徑
# 將 from app.crud.base 改為 from backend.app.api.v1.crud.base

# 3. 更新 __init__.py 匯出

# 4. 搜尋所有使用舊路徑的檔案
grep -r "from app.crud" backend/app/services/
grep -r "from backend.app.crud" backend/app/api/

# 5. 逐一更新匯入路徑

# 6. 執行測試確認
pytest backend/tests/ -v
```

### 3.2 匯入更新範例

```python
# ❌ 修改前
from app.crud import transaction_crud
from backend.app.crud.generated_report import GeneratedReportCRUD

# ✅ 修改後
from backend.app.api.v1.crud import transaction_crud
from backend.app.api.v1.crud import GeneratedReportCRUD
```

---

## 四、棄用處理

### 4.1 舊模組棄用警告

```python
# backend/app/crud/__init__.py
"""
⚠️ DEPRECATED: 此模組已棄用
請使用 backend.app.api.v1.crud

Deprecated since: 2025-12-24
Will be removed: 2025-06-01
"""

import warnings

warnings.warn(
    "backend.app.crud is deprecated. "
    "Use backend.app.api.v1.crud instead.",
    DeprecationWarning,
    stacklevel=2
)

# 向後相容匯出
from backend.app.api.v1.crud import (
    transaction_crud,
    land_parcel_crud,
    # ...
)
```

### 4.2 API 端點棄用

```python
@router.post(
    "/old-endpoint",
    deprecated=True,
    summary="[已廢棄] 舊端點",
    description="⚠️ **此端點已廢棄，將於 2025-06-01 移除**。請使用 `/api/v1/new-endpoint`",
)
def old_endpoint():
    """棄用端點實作"""
    pass
```

---

## 五、已遷移模組清單

| 模組 | 舊位置 | 新位置 | 狀態 |
|------|--------|--------|------|
| transaction | `crud/transaction.py` | `api/v1/crud/transaction.py` | ✅ |
| land_parcel | `crud/land_parcel.py` | `api/v1/crud/land_parcel.py` | ✅ |
| ai_chat_log | `crud/crud_ai_chat_log.py` | `api/v1/crud/ai_chat_log.py` | ✅ |
| analysis_module | `crud/analysis_module.py` | `api/v1/crud/analysis_module.py` | ✅ |
| generated_report | `crud/crud_generated_report.py` | `api/v1/crud/generated_report.py` | ✅ |

---

## 六、驗證清單

### 遷移完成檢查

```bash
# 1. 確認無舊路徑使用
grep -r "from app.crud" backend/app/api/ backend/app/services/
# 應該無輸出

# 2. 確認新路徑正確
python -c "from backend.app.api.v1.crud import transaction_crud; print('OK')"

# 3. 執行後端測試
pytest backend/tests/ -v

# 4. 啟動服務確認
cd backend && python -m uvicorn backend.app.main:app --reload
```

---

## 七、HTTP 方法遷移 (2025-12-26)

### 7.1 資安規範

根據 `.speckit/api-standards.md` Section 0：
- DELETE 方法 → POST + `/delete` 端點
- PUT 方法 → POST + `/update` 端點

### 7.2 後端遷移範例

```python
# ❌ 舊寫法 (已棄用)
@router.delete("/{id}")
async def delete_item(id: int):
    ...

@router.put("/{id}")
async def update_item(id: int, data: ItemUpdate):
    ...

# ✅ 新寫法 (資安合規)
@router.post("/{id}/delete")
async def delete_item_v2(id: int):
    """使用 POST 方法刪除資源"""
    ...

@router.post("/{id}/update")
async def update_item_v2(id: int, data: ItemUpdate):
    """使用 POST 方法更新資源"""
    ...

# 保留舊端點向後相容 (標記棄用)
@router.delete("/{id}", deprecated=True)
async def delete_item_deprecated(id: int):
    """[已棄用] 請使用 POST /{id}/delete"""
    return await delete_item_v2(id)
```

### 7.3 前端遷移範例

```typescript
// ❌ 舊寫法
export async function deleteItem(id: number) {
  return apiClient.delete(`/items/${id}`);
}

export async function updateItem(id: number, data: ItemData) {
  return apiClient.put(`/items/${id}`, data);
}

// ✅ 新寫法
export async function deleteItem(id: number) {
  return apiClient.post(`/items/${id}/delete`);
}

export async function updateItem(id: number, data: ItemData) {
  return apiClient.post(`/items/${id}/update`, data);
}
```

### 7.4 自動化檢查

```bash
# 執行 HTTP 方法安全檢查
python backend/scripts/check_http_methods.py

# Pre-commit 會自動執行此檢查
git commit  # 若有違規會被攔截
```

---

**建立日期**：2025-12-24
**最後更新**：2025-12-26
