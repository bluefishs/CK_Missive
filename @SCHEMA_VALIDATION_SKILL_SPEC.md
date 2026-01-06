# Schema Validation Skill Specification

> 版本: 1.0.0
> 建立日期: 2026-01-06
> 用途: Model-Database Schema 一致性驗證與維護

---

## 一、功能概述

### 核心能力

Schema Validation Skill 提供以下自動化功能：

1. **啟動時驗證** - 應用程式啟動時自動比對 SQLAlchemy Models 與資料庫 Schema
2. **不一致偵測** - 識別缺少的欄位、多餘的欄位、型別差異
3. **審計日誌** - 記錄關鍵資料變更歷史
4. **修復建議** - 產生 Alembic migration 或 SQL 建議

---

## 二、使用方式

### 啟動驗證 (自動)

```python
# backend/main.py - lifespan 事件中自動執行
from app.core.schema_validator import validate_schema
from app.extended.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    is_valid, mismatches = await validate_schema(
        engine=engine,
        base=Base,
        strict=False,  # False: 僅警告, True: 阻止啟動
        tables_to_check=None  # None: 檢查所有表格
    )
    if not is_valid:
        logger.warning(f"發現 {len(mismatches)} 個 Schema 不一致")
    yield
```

### 手動驗證

```bash
# 執行一致性測試
cd backend
pytest tests/test_schema_consistency.py -v
```

### 審計日誌

```python
from app.core.audit_logger import log_document_change, detect_changes

# 記錄公文變更
await log_document_change(
    db=db,
    document_id=564,
    action="UPDATE",
    changes={"subject": {"old": "舊主旨", "new": "新主旨"}},
    user_id=1,
    source="API"
)

# 自動偵測變更
changes = detect_changes(old_data, new_data)
```

---

## 三、核心模組

### schema_validator.py

```python
# 主要函數
async def validate_schema(
    engine: AsyncEngine,
    base: DeclarativeMeta,
    strict: bool = False,
    tables_to_check: Optional[List[str]] = None
) -> Tuple[bool, List[SchemaMismatch]]

# 輔助函數
async def get_database_columns(conn, table_name) -> Dict[str, dict]
async def get_database_tables(conn) -> Set[str]
def get_model_columns(model_class) -> Dict[str, dict]
async def validate_table(conn, table_name, model_columns) -> List[SchemaMismatch]
async def generate_migration_hints(mismatches) -> str
```

### audit_logger.py

```python
# 主要函數
async def log_audit_entry(
    db: AsyncSession,
    table_name: str,
    record_id: int,
    action: str,  # CREATE, UPDATE, DELETE
    changes: Dict[str, Any],
    user_id: Optional[int] = None,
    source: str = "SYSTEM"
)

# 便捷方法
async def log_document_change(db, document_id, action, changes, user_id, source)

# 變更偵測
def detect_changes(old_data: Dict, new_data: Dict) -> Dict[str, Dict]

# 保護器類別
class DocumentUpdateGuard:
    async def load_original() -> Dict
    async def validate_and_log(new_data, user_id, source) -> Dict
```

---

## 四、錯誤類型

| 錯誤類型 | 說明 | 處理建議 |
|---------|------|---------|
| `TABLE_NOT_FOUND` | 模型定義的表格在資料庫中不存在 | 執行 `alembic upgrade head` |
| `COLUMN_MISSING_IN_DB` | 模型欄位在資料庫中不存在 | 新增 migration 或修改模型 |
| `COLUMN_MISSING_IN_MODEL` | 資料庫欄位在模型中未定義 | 在模型中新增對應欄位 |

---

## 五、關鍵欄位定義

審計日誌會特別標記以下欄位的變更：

```python
CRITICAL_FIELDS = {
    "documents": ["subject", "doc_number", "sender", "receiver", "status"],
    "contract_projects": ["project_name", "project_code", "status", "budget"],
}
```

---

## 六、整合範例

### 在 API 端點中使用審計日誌

```python
# backend/app/api/endpoints/documents_enhanced.py

@router.post("/{document_id}/update")
async def update_document(
    document_id: int,
    data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    # 使用保護器
    guard = DocumentUpdateGuard(db, document_id)
    original = await guard.load_original()

    # 執行更新
    updated = await document_service.update(db, document_id, data)

    # 記錄變更
    await guard.validate_and_log(
        new_data=updated.__dict__,
        user_id=current_user.id,
        source="API"
    )

    return updated
```

---

## 七、測試驗證

### 測試案例

```python
# tests/test_schema_consistency.py

class TestSchemaConsistency:
    async def test_critical_tables_exist(self, db_engine):
        """測試關鍵表格是否存在"""

    async def test_model_tables_exist(self, db_engine):
        """測試所有模型表格是否存在"""

    async def test_document_attachments_columns(self, db_engine):
        """測試 document_attachments 欄位一致性"""

    async def test_documents_columns(self, db_engine):
        """測試 documents 欄位一致性"""

def test_model_imports():
    """測試模型可正確導入"""
```

### 執行測試

```bash
# 執行全部測試
pytest tests/test_schema_consistency.py -v

# 僅執行特定測試
pytest tests/test_schema_consistency.py::TestSchemaConsistency::test_critical_tables_exist -v
```

---

## 八、維護指南

### 新增表格時

1. 在 `models.py` 定義新模型
2. 執行 `alembic revision --autogenerate -m "Add new table"`
3. 執行 `alembic upgrade head`
4. 重啟應用驗證 Schema 一致性

### 修改欄位時

1. 修改 `models.py` 中的欄位定義
2. 執行 `alembic revision --autogenerate -m "Modify column"`
3. 確認 migration 內容正確
4. 執行 `alembic upgrade head`
5. 驗證啟動日誌無警告

### 發現不一致時

1. 檢查啟動日誌中的警告訊息
2. 比對 models.py 與資料庫實際結構
3. 決定是修改模型還是新增 migration
4. 執行修正後重新驗證

---

## 九、相關檔案

| 檔案路徑 | 說明 | 強制等級 |
|---------|------|----------|
| **`@DEVELOPMENT_STANDARDS.md`** | **統一開發規範總綱** | 🔴 必讀 |
| `@TYPE_CONSISTENCY_SKILL_SPEC.md` | 型別一致性規範 | 🔴 必須 |
| `backend/app/core/schema_validator.py` | Schema 驗證核心模組 | - |
| `backend/app/core/audit_logger.py` | 審計日誌模組 | - |
| `backend/app/extended/models.py` | ORM 模型定義 | - |
| `backend/tests/test_schema_consistency.py` | 一致性測試 | - |
| `backend/main.py` | 應用程式入口 (含驗證整合) | - |

> ⚠️ **注意**：本規範為 `@DEVELOPMENT_STANDARDS.md` 的子規範，必須配合總綱一同遵守。

---

## 十、版本歷史

| 版本 | 日期 | 變更內容 |
|-----|------|---------|
| 1.0.0 | 2026-01-06 | 初始版本 - 修復 25 個 Schema 不一致 |

---

*文件維護: Claude Code Assistant*
