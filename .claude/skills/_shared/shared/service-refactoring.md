---
name: service-refactoring
description: 拆分大型服務、統一服務架構
version: 1.0.0
category: shared
triggers:
  - 服務重構
  - service refactoring
  - 拆分服務
  - 模組化
  - monolith
updated: 2026-01-22
---

# Service Refactoring Skill

> **用途**: 拆分大型服務、統一服務架構
> **觸發**: 服務重構, service refactoring, 拆分服務, 模組化
> **版本**: 1.0.0
> **分類**: shared

**適用場景**：大型單體服務重構、模組化架構建立

---

## 一、大型服務識別

### 1.1 需要拆分的標準

| 指標       | 閾值     | 說明           |
| ---------- | -------- | -------------- |
| 檔案大小   | > 30KB   | 程式碼過於集中 |
| 程式碼行數 | > 800 行 | 難以維護       |
| 函數數量   | > 20 個  | 職責過多       |
| 相依模組   | > 10 個  | 耦合度過高     |

### 1.2 目前待拆分服務

| 服務                            | 大小 | 問題                           | 優先級 |
| ------------------------------- | ---- | ------------------------------ | ------ |
| `moi_building_query_service.py` | 54KB | 單體過大，包含模型、工具、服務 | P3     |
| `coordinate_service.py`         | 36KB | 驗證、轉換、快取混合           | P3     |
| `land_price_service.py`         | 16KB | 接近閾值                       | P4     |

---

## 二、拆分策略

### 2.1 moi_building_query_service.py 拆分

**現狀**：54KB，包含資料模型、地址解析、API 呼叫、結果處理

**目標結構**：

```
backend/app/services/moi/building/
├── __init__.py           # 統一匯出
├── models.py             # BuildingMarkingSection, BuildingQueryResult
├── address_parser.py     # 地址解析/轉換工具函數
├── api_client.py         # MOI API 呼叫封裝
├── query_service.py      # MOIBuildingQueryService 主服務
└── cache.py              # 查詢快取邏輯
```

**拆分步驟**：

```python
# Step 1: 建立目錄結構
# backend/app/services/moi/building/__init__.py

from backend.app.services.moi.building.models import (
    BuildingMarkingSection,
    BuildingQueryResult,
)
from backend.app.services.moi.building.query_service import (
    MOIBuildingQueryService,
)

__all__ = [
    "BuildingMarkingSection",
    "BuildingQueryResult",
    "MOIBuildingQueryService",
]
```

```python
# Step 2: 抽離資料模型
# backend/app/services/moi/building/models.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BuildingMarkingSection:
    """建物標示部資料"""
    building_number: str
    floor_area: float
    main_use: str
    # ...

@dataclass
class BuildingQueryResult:
    """建物查詢結果"""
    success: bool
    data: Optional[BuildingMarkingSection]
    error: Optional[str]
```

```python
# Step 3: 抽離地址解析
# backend/app/services/moi/building/address_parser.py

def parse_address(address: str) -> dict:
    """解析地址為結構化資料"""
    # 地址解析邏輯
    pass

def normalize_address(address: str) -> str:
    """標準化地址格式"""
    # 地址標準化邏輯
    pass

def extract_building_number(address: str) -> Optional[str]:
    """從地址提取建號"""
    pass
```

```python
# Step 4: 抽離 API 客戶端
# backend/app/services/moi/building/api_client.py

import httpx
from typing import Optional

class MOIApiClient:
    """MOI 建物 API 客戶端"""

    BASE_URL = "https://api.moi.gov.tw"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def query_building(self, building_number: str) -> dict:
        """查詢建物資料"""
        response = await self.client.get(
            f"{self.BASE_URL}/building/{building_number}",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()
```

```python
# Step 5: 重構主服務
# backend/app/services/moi/building/query_service.py

from backend.app.services.moi.building.models import (
    BuildingMarkingSection,
    BuildingQueryResult,
)
from backend.app.services.moi.building.address_parser import (
    parse_address,
    normalize_address,
)
from backend.app.services.moi.building.api_client import MOIApiClient

class MOIBuildingQueryService:
    """MOI 建物查詢服務"""

    def __init__(self):
        self.api_client = MOIApiClient()

    async def query_by_address(self, address: str) -> BuildingQueryResult:
        """透過地址查詢建物"""
        normalized = normalize_address(address)
        parsed = parse_address(normalized)
        # 查詢邏輯
        pass
```

### 2.2 coordinate_service.py 拆分

**現狀**：36KB，混合驗證、轉換、快取邏輯

**目標結構**：

```
backend/app/services/coordinate/
├── __init__.py           # 統一匯出
├── validators.py         # 座標驗證邏輯
├── converters.py         # 座標轉換邏輯（TWD97 <-> WGS84）
├── cache.py              # 座標快取邏輯
└── service.py            # 統一服務入口
```

**拆分範例**：

```python
# backend/app/services/coordinate/validators.py

from typing import Tuple

def validate_wgs84(lat: float, lon: float) -> bool:
    """驗證 WGS84 座標"""
    return -90 <= lat <= 90 and -180 <= lon <= 180

def validate_twd97(x: float, y: float) -> bool:
    """驗證 TWD97 座標"""
    # TWD97 範圍檢查
    return 100000 <= x <= 400000 and 2400000 <= y <= 2900000

def validate_coordinate_pair(coord: Tuple[float, float], system: str) -> bool:
    """驗證座標對"""
    if system == "WGS84":
        return validate_wgs84(coord[0], coord[1])
    elif system == "TWD97":
        return validate_twd97(coord[0], coord[1])
    return False
```

```python
# backend/app/services/coordinate/converters.py

from typing import Tuple
import pyproj

# 座標系統定義
WGS84 = pyproj.CRS("EPSG:4326")
TWD97 = pyproj.CRS("EPSG:3826")

def wgs84_to_twd97(lat: float, lon: float) -> Tuple[float, float]:
    """WGS84 轉 TWD97"""
    transformer = pyproj.Transformer.from_crs(WGS84, TWD97, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return (x, y)

def twd97_to_wgs84(x: float, y: float) -> Tuple[float, float]:
    """TWD97 轉 WGS84"""
    transformer = pyproj.Transformer.from_crs(TWD97, WGS84, always_xy=True)
    lon, lat = transformer.transform(x, y)
    return (lat, lon)
```

---

## 三、向後相容處理

### 3.1 保留舊路徑匯出

```python
# backend/app/services/moi_building_query_service.py
"""
⚠️ DEPRECATED: 此模組已遷移至 services/moi/building/

請使用：
from backend.app.services.moi.building import MOIBuildingQueryService

Deprecated since: 2025-12-24
"""

import warnings

warnings.warn(
    "moi_building_query_service is deprecated. "
    "Use backend.app.services.moi.building instead.",
    DeprecationWarning,
    stacklevel=2
)

# 向後相容匯出
from backend.app.services.moi.building import (
    MOIBuildingQueryService,
    BuildingMarkingSection,
    BuildingQueryResult,
)
```

---

## 四、服務目錄結構規範

### 4.1 標準結構

```
backend/app/services/
├── __init__.py
├── unified/              # 統一服務層（已存在）
│   ├── land.py
│   ├── gis.py
│   └── ...
├── moi/                  # MOI 相關服務
│   ├── building/
│   └── land/
├── coordinate/           # 座標服務
│   ├── validators.py
│   ├── converters.py
│   └── service.py
├── reports/              # 報表服務
│   ├── generator.py
│   └── templates/
└── external/             # 外部 API 整合
    ├── nlsc/
    ├── tgos/
    └── ors/
```

### 4.2 模組命名規範

| 類型 | 命名        | 範例                      |
| ---- | ----------- | ------------------------- |
| 目錄 | snake_case  | `moi/building/`           |
| 模組 | snake_case  | `query_service.py`        |
| 類別 | PascalCase  | `MOIBuildingQueryService` |
| 函數 | snake_case  | `parse_address`           |
| 常數 | UPPER_SNAKE | `MAX_RETRY_COUNT`         |

---

## 五、重構驗證清單

### 拆分完成檢查

```bash
# 1. 確認新模組可正確匯入
python -c "from backend.app.services.moi.building import MOIBuildingQueryService"

# 2. 確認舊路徑產生棄用警告
python -c "from backend.app.services.moi_building_query_service import MOIBuildingQueryService"
# 應該顯示 DeprecationWarning

# 3. 執行相關測試
pytest backend/tests/services/moi/ -v

# 4. 檢查無循環匯入
python -c "from backend.app.services import *"
```

### 效能驗證

| 指標         | 重構前 | 重構後目標 |
| ------------ | ------ | ---------- |
| 模組載入時間 | 基準   | <= 基準    |
| 記憶體使用   | 基準   | <= 基準    |
| API 響應時間 | 基準   | <= 基準    |

---

## 六、時程建議

| 階段    | 工作項目                        | 預估工作量 |
| ------- | ------------------------------- | ---------- |
| Phase 1 | moi_building_query_service 拆分 | 2-3 天     |
| Phase 2 | coordinate_service 拆分         | 1-2 天     |
| Phase 3 | 測試與驗證                      | 1 天       |
| Phase 4 | 文件更新                        | 0.5 天     |

**總計**：約 5-7 個工作天

---

**建立日期**：2025-12-24
**最後更新**：2025-12-24
