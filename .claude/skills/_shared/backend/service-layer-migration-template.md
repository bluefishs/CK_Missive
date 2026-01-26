# 服務層遷移範本

**技能名稱**：服務層遷移 (Service Layer Migration)
**用途**：將端點層的 DB 操作遷移至服務層
**適用場景**：三層式架構合規、P3-001-B 技術債清理
**建立日期**：2026-01-18

---

## 一、遷移原則

### 1.1 三層式架構

```
端點層 (Endpoint)     →  HTTP I/O、參數驗證
        ↓
服務層 (Service)      →  業務邏輯、交易管理
        ↓
倉儲層 (Repository)   →  資料存取、SQL 封裝
```

### 1.2 遷移優先級

| 優先級 | 條件 | 範例 |
|-------|------|------|
| **高** | 核心業務邏輯、頻繁使用 | compensation/cases |
| **中** | 多端點共用邏輯 | spatial/analysis |
| **低** | deprecated 端點、低使用率 | GET 端點（已有 POST 版本）|
| **跳過** | 純代理、無邏輯 | tile-proxy, wms-proxy |

---

## 二、服務類別範本

### 2.1 基本結構

```python
"""
{模組名稱} 服務層
{Module Name} Service Layer

封裝 {模組描述} 的業務邏輯。

Created: YYYY-MM-DD
Architecture: Three-Layer Architecture (三層式架構)
"""

from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


class {ModuleName}Service:
    """
    {模組描述} 服務

    負責封裝業務邏輯，供端點層調用。
    """

    def __init__(self, db: Session):
        """
        初始化服務

        Args:
            db: SQLAlchemy 資料庫會話
        """
        self.db = db

    def get_items(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        查詢項目列表

        Args:
            filters: 查詢過濾條件

        Returns:
            項目列表
        """
        try:
            conditions = ["1=1"]
            params = {}

            if filters:
                if filters.get("status"):
                    conditions.append("status = :status")
                    params["status"] = filters["status"]

            where_clause = " AND ".join(conditions)

            result = self.db.execute(
                text(f"""
                    SELECT id, name, status, created_at
                    FROM items
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """),
                params
            )

            return [dict(row._mapping) for row in result.fetchall()]

        except Exception as e:
            logger.error("Failed to get items", error=str(e))
            raise

    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        根據 ID 查詢項目

        Args:
            item_id: 項目 ID

        Returns:
            項目資訊，若不存在則返回 None
        """
        try:
            result = self.db.execute(
                text("SELECT * FROM items WHERE id = :id"),
                {"id": item_id}
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

        except Exception as e:
            logger.error("Failed to get item", item_id=item_id, error=str(e))
            raise

    def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        建立項目

        Args:
            data: 項目資料

        Returns:
            建立的項目資訊
        """
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO items (name, status)
                    VALUES (:name, :status)
                    RETURNING id, name, status, created_at
                """),
                data
            )
            self.db.commit()
            row = result.fetchone()
            return dict(row._mapping)

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create item", error=str(e))
            raise


# 工廠函數 (可選)
def get_service(db: Session) -> {ModuleName}Service:
    """獲取服務實例"""
    return {ModuleName}Service(db)
```

### 2.2 命名規範

| 類型 | 命名模式 | 範例 |
|------|---------|------|
| 服務類別 | `{Domain}Service` | `LandSectionService`, `PathAnalysisService` |
| 檔案名稱 | `{domain}_service.py` | `land_section_service.py` |
| 方法名稱 | `動詞_名詞` | `get_cities`, `create_task`, `search_sections` |

---

## 三、端點層更新範本

### 3.1 遷移前

```python
# ❌ 直接在端點操作資料庫
@router.post("/items")
def get_items(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM items"))
    items = result.fetchall()
    return success_response(data=[dict(row._mapping) for row in items])
```

### 3.2 遷移後

```python
# ✅ 委派給服務層
from backend.app.services.item_service import ItemService

@router.post("/items")
def get_items(db: Session = Depends(get_db)):
    service = ItemService(db)
    items = service.get_items()
    return success_response(data=items)
```

### 3.3 端點檔案頭部註解

```python
"""
{模組名稱} API 端點
{Module Name} API Endpoints

Updated: YYYY-MM-DD - 服務層遷移 (P3-001-B)

Architecture: 三層式架構
- 端點層: 本檔案 (HTTP I/O)
- 服務層: backend/app/services/{service_file}.py
"""
```

---

## 四、遷移步驟

### 4.1 準備階段

1. **分析端點**：識別所有 DB 操作 (`db.query`, `db.execute`, `db.add`, etc.)
2. **分組邏輯**：將相關功能分組（CRUD、查詢、統計等）
3. **設計介面**：定義服務方法簽名

### 4.2 實作階段

1. **建立服務檔案**：`backend/app/services/{domain}_service.py`
2. **遷移 DB 操作**：將 SQL 邏輯移至服務方法
3. **更新端點**：改為調用服務方法
4. **添加註解**：更新檔案頭部說明

### 4.3 驗證階段

1. **語法檢查**：`python -m py_compile backend/app/services/{file}.py`
2. **架構驗證**：`python backend/verify_architecture.py`
3. **功能測試**：確保 API 行為不變

---

## 五、特殊情況處理

### 5.1 共用輔助函數

```python
# 保留在端點層的輔助函數（純計算、無 DB 操作）
def calculate_zoom_level(west: float, east: float, south: float, north: float) -> int:
    """純計算函數，不涉及 DB，可保留在端點"""
    ...

# 移至服務層的輔助函數（涉及 DB 操作）
class SpatialService:
    def get_layer_info(self, layer_id: int) -> Dict:
        """涉及 DB 查詢，應在服務層"""
        ...
```

### 5.2 外部服務調用

```python
class LandSectionService:
    def __init__(self, db: Session):
        self.db = db
        # 外部服務相關配置由服務層管理
        self.circuit_breaker = circuit_breaker_registry.get_or_create("moi_cadastral")

    def locate_section_from_moi(self, lot_code: str) -> Optional[Dict]:
        """調用外部 MOI 服務，封裝在服務層"""
        ...
```

### 5.3 deprecated 端點處理

```python
# deprecated GET 端點不需要遷移服務層
# 只需確保對應的 POST 端點已遷移即可
@router.get("/items", deprecated=True)
def get_items_deprecated(...):
    """[已棄用] 請使用 POST /items"""
    # 可直接委派給 POST 版本或保持原樣
    ...
```

---

## 六、驗證清單

### 6.1 遷移完成檢查

- [ ] 服務檔案已建立並通過語法檢查
- [ ] 端點已更新為調用服務方法
- [ ] 檔案頭部註解已更新（日期、架構說明）
- [ ] `verify_architecture.py` 警告數減少
- [ ] 功能測試通過

### 6.2 文件更新

- [ ] `known-issues-registry.md` 記錄遷移項目
- [ ] `CLAUDE.md` 更新遷移進度

---

## 七、已遷移模組參考

| 模組 | 服務檔案 | 遷移日期 |
|------|---------|---------|
| compensation/cases | `case_service.py` | 2026-01-10 |
| compensation/projects | `project_service.py` | 2026-01-10 |
| spatial/admin_districts | `admin_district_service.py` | 2026-01-18 |
| system/database_info | `database_info_service.py` | 2026-01-18 |
| spatial/analysis | `spatial_analysis_service.py` | 2026-01-18 |
| spatial/land_sections | `land_section_service.py` | 2026-01-10 (POST) |

---

## 八、相關文件

- `docs/ARCHITECTURE.md` - 三層式架構設計
- `.claude/skills/schema-design-patterns.md` - Schema 設計規範
- `backend/verify_architecture.py` - 架構驗證腳本

---

**最後更新**：2026-01-18
