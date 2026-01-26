---
name: code-standards
description: 程式碼標準規範，確保品質、一致性與最佳實踐
version: 1.1.0
category: shared
triggers:
  - 程式碼規範
  - coding style
  - ESLint
  - code review
  - 程式碼品質
updated: 2026-01-22
---

# Code Standards Skill

> **用途**: 確保程式碼品質、一致性與最佳實踐
> **觸發**: 程式碼規範, coding style, ESLint, code review
> **版本**: 1.1.0
> **分類**: shared
> **更新日期**: 2026-01-22

**適用場景**：開發新功能、程式碼審查、重構

---

## 一、ESLint 最佳實踐

### 1.1 React Hook 定義順序 (重要)

**問題**：`Block-scoped variable used before its declaration` 錯誤

**原因**：useCallback/useMemo 必須在使用它們的 useEffect 之前定義

**正確做法**：
```typescript
// ✅ 正確：useCallback 在 useEffect 之前定義
const loadData = useCallback(async () => {
  const result = await fetchData();
  setData(result);
}, [dependencies]);

useEffect(() => {
  loadData(); // 此時 loadData 已定義
}, [loadData]);

// ❌ 錯誤：useEffect 在 useCallback 之前
useEffect(() => {
  loadData(); // 錯誤！loadData 尚未定義
}, [loadData]);

const loadData = useCallback(async () => {
  // ...
}, []);
```

### 1.2 Ref Cleanup 模式 (2026-01-03 新增)

**問題**：`The ref value will likely have changed by the time this effect cleanup function runs`

**原因**：useEffect 的清理函數執行時，ref.current 可能已變更

**正確做法**：
```typescript
// ✅ 正確：複製 ref 值到本地變數
useEffect(() => {
  // 複製 ref 值以確保清理函數可安全存取
  const element = imgRef.current;
  const intervals = refreshIntervalsRef.current;

  if (element) {
    observer.observe(element);
  }

  return () => {
    // 使用本地變數，而非 ref.current
    if (element) {
      observer.unobserve(element);
    }
    intervals.forEach(interval => clearInterval(interval));
  };
}, [dependency]);

// ❌ 錯誤：直接在清理函數中存取 ref.current
useEffect(() => {
  observer.observe(imgRef.current);

  return () => {
    // 錯誤！ref.current 可能已變更
    observer.unobserve(imgRef.current);
  };
}, []);
```

**適用情境**：
- IntersectionObserver
- ResizeObserver
- MutationObserver
- 定時器清理 (setInterval/setTimeout)
- DOM 事件監聽器清理

### 1.3 Context 檔案 ESLint 處理 (2026-01-03 新增)

**問題**：`Fast refresh only works when a file only exports components`

**原因**：Context 檔案需要匯出 Provider 組件和 Hook，但 react-refresh 要求檔案只匯出組件

**正確做法**：
```typescript
// ✅ 正確：在 hook 匯出前添加 eslint-disable
/**
 * 使用統一圖層 Context
 */
// Context 檔案需要匯出 Provider 組件和 Hook，這是 React 的標準模式
// eslint-disable-next-line react-refresh/only-export-components
export function useUnifiedLayer(): UnifiedLayerContextValue {
  const context = useContext(UnifiedLayerContext);
  if (!context) {
    throw new Error('useUnifiedLayer must be used within a UnifiedLayerProvider');
  }
  return context;
}

// ❌ 錯誤：在檔案頂部添加 (不會作用到正確位置)
// eslint-disable-next-line react-refresh/only-export-components
import { createContext, useContext } from 'react';
```

**適用情境**：
- 所有 `*Context.tsx` 檔案
- 同時匯出 Provider 和 Hook 的模組

### 1.4 exhaustive-deps 規則處理

**問題**：React Hook 的依賴陣列警告

**正確做法**：
```typescript
// ✅ 正確：註解放在依賴陣列的正上方
useEffect(() => {
  // 效果邏輯
  fetchData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);

// ❌ 錯誤：註解放在 Hook 開頭
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => {
  fetchData();
}, []);
```

**適用情境**：
- 初始化時執行一次的效果
- 回調函數已穩定化（useCallback 包裝）
- 明確不需要依賴變更觸發的場景

### 1.3 未使用變數處理

**處理方式**：
```typescript
// ✅ 使用底線前綴標記有意忽略的變數
const [_unused, setUsed] = useState<string>('');

// ✅ 解構時忽略不需要的屬性
const { needed, ...rest } = props;
void rest; // 明確標記 rest 為有意忽略

// ❌ 不要保留完全未使用的 import
import { useCallback } from 'react'; // 如果未使用則刪除
```

### 1.4 any 類型處理

**處理方式**：
```typescript
// ✅ 使用 unknown 並進行類型斷言
function handleResponse(data: unknown): void {
  if (isValidResponse(data)) {
    processData(data as ResponseType);
  }
}

// ✅ 使用泛型保持類型安全
function parseJSON<T>(json: string): T {
  return JSON.parse(json) as T;
}

// ⚠️ 需要時使用行內禁用
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const legacy: any = getLegacyData();
```

---

## 二、HTTP 客戶端規範 (重要)

### 2.1 統一使用 apiClient

**核心原則**：所有 API 請求必須使用統一的 `apiClient`，禁止直接 import axios。

**原因**：
- `apiClient` 已內建 Cookie 認證 (withCredentials)
- 自動處理 CSRF Token
- 支援 Token 自動刷新
- 統一錯誤處理
- **直接使用 axios 在無痕模式/清除快取後會失效**

**正確做法**：
```typescript
// ✅ 正確：使用統一 apiClient
import apiClient from '@/api/client';

const fetchData = async () => {
  const response = await apiClient.post('/basemap/layers/list', {
    enabled_only: true
  });
  return response.data;
};
```

**錯誤做法**：
```typescript
// ❌ 錯誤：直接 import axios（會觸發 ESLint 錯誤）
import axios from 'axios';

const fetchData = async () => {
  // 缺少 Cookie 認證、CSRF Token
  const response = await axios.post('/api/v1/basemap/layers/list');
  return response.data;
};
```

### 2.2 例外情況

僅以下檔案允許直接使用 axios：
- `api/client.ts` - apiClient 定義檔
- `api/axiosInstance.ts` - 底層實例（如需保留）

### 2.3 ESLint 規則

已配置 `no-restricted-imports` 規則自動檢測：
```javascript
// .eslintrc.cjs
'no-restricted-imports': ['error', {
  paths: [{
    name: 'axios',
    message: '請使用 @/api/client 的統一 apiClient'
  }]
}]
```

### 2.4 遷移指南

將現有 axios 改為 apiClient：

```typescript
// 舊代碼
import axios from 'axios';
const response = await axios.post(`${API_BASE}/endpoint`, data);

// 新代碼
import apiClient from '@/api/client';
const response = await apiClient.post('/endpoint', data);
// 注意：apiClient 已有 baseURL，不需要再加 /api/v1
```

### 2.5 ⚠️ P0 警告：API 路徑重複問題 (2026-01-08)

**問題描述**：使用 `apiClient` 時又加上 `API_BASE_URL` 前綴，導致請求路徑變成 `/api/v1/api/v1/...`

**症狀**：所有 API 請求返回 404 Not Found

**錯誤模式**：
```typescript
// ❌ 錯誤：apiClient 已有 baseURL='/api/v1'，又加了前綴
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
apiClient.post(`${API_BASE_URL}/analytics/trends`, data);
// 實際請求: /api/v1/api/v1/analytics/trends → 404!

// ❌ 錯誤：在服務檔案中定義 API_BASE_URL
const API_BASE_URL = '/api/v1';
apiClient.get(`${API_BASE_URL}/gislayers/identify`);
// 實際請求: /api/v1/api/v1/gislayers/identify → 404!
```

**正確做法**：
```typescript
// ✅ 正確：直接使用相對路徑
apiClient.post('/analytics/trends', data);
// 實際請求: /api/v1/analytics/trends ✓

// ✅ 正確：若需保留 API_BASE_URL 變數，設為空字串
const API_BASE_URL = '';  // 或直接移除此常數
apiClient.get(`${API_BASE_URL}/gislayers/identify`);
```

**受影響的檔案範例**：
- `pages/DashboardPage.tsx`
- `pages/ModuleManagementPage.tsx`
- `pages/SiteManagementPageImproved.tsx`
- `components/RealEstate/CoordinateSupplementTab.tsx`
- `services/esriIdentifyService.ts`

**檢查指令**：
```bash
# 搜尋可能的錯誤模式
grep -rn "apiClient.*API_BASE_URL" frontend/src/
grep -rn "apiClient.*/api/v1" frontend/src/
```

---

## 三、API 路徑配置規範

### 2.1 axios baseURL 與路徑規則

**配置位置**：`frontend/src/api/client.ts`

```typescript
// baseURL 設定
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
```

**正確做法**：
```typescript
// ✅ 正確：使用相對路徑（不含 /api/v1）
await apiClient.post('/code-categories/engineering');
// 實際請求: /api/v1/code-categories/engineering

// ❌ 錯誤：使用完整路徑（會造成重複）
await apiClient.post('/api/v1/code-categories/engineering');
// 實際請求: /api/v1/api/v1/code-categories/engineering (錯誤！)
```

### 2.2 API 端點定義模式

```typescript
// ✅ 正確：端點常數不含 baseURL 前綴
const ENDPOINTS = {
  ENGINEERING: '/code-categories/engineering',
  TASK: '/code-categories/task',
};

// ❌ 錯誤：端點常數含完整路徑
const ENDPOINTS = {
  ENGINEERING: '/api/v1/code-categories/engineering', // 會導致雙重前綴
};
```

### 2.3 後端路由註冊

**正確做法**（`router_registry.py`）：
```python
# ✅ 路由前綴包含完整路徑
app.include_router(
    code_categories_router,
    prefix="/api/v1/code-categories",  # 後端完整路徑
    tags=["系統-統一編碼類別"]
)
```

---

## 三、React Query 快取配置

### 3.1 快取類型分級

**位置**：`frontend/src/api/utils/cacheConfig.ts`

| 類型 | staleTime | gcTime | 適用場景 |
|------|-----------|--------|----------|
| SLOW | 30 分鐘 | 2 小時 | 導航、系統配置、參考資料 |
| MEDIUM | 5 分鐘 | 30 分鐘 | 地價資料、案件列表 |
| FAST | 1 分鐘 | 5 分鐘 | 即時資料、交易紀錄 |
| REALTIME | 0 | 1 分鐘 | 地圖資料、即時狀態 |

### 3.2 使用範例

```typescript
import { getCacheConfig } from '@/api/utils/cacheConfig';

// ✅ 正確：根據資料類型選擇快取配置
export const useNavigationItems = () => {
  return useQuery({
    queryKey: ['navigation-items'],
    queryFn: fetchNavigationItems,
    ...getCacheConfig('navigation'), // 自動映射到 SLOW
  });
};

// ✅ 正確：高頻變動資料使用 REALTIME
export const useMapLayers = () => {
  return useQuery({
    queryKey: ['map-layers'],
    queryFn: fetchMapLayers,
    ...getCacheConfig('map'), // 自動映射到 REALTIME
  });
};
```

### 3.3 資料類型映射

```typescript
const DATA_TYPE_CACHE_MAP = {
  // SLOW (30分鐘)
  navigation: 'SLOW',
  system: 'SLOW',
  reference: 'SLOW',

  // MEDIUM (5分鐘)
  landPrice: 'MEDIUM',
  cases: 'MEDIUM',
  parcels: 'MEDIUM',

  // FAST (1分鐘)
  transactions: 'FAST',
  users: 'FAST',

  // REALTIME (0秒)
  map: 'REALTIME',
  realtime: 'REALTIME',
};
```

---

## 四、TypeScript 最佳實踐

### 4.1 嚴格模式檢查

**tsconfig.json 必要配置**：
```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### 4.2 類型定義位置

```
frontend/src/
├── types/              # 全域共享類型
│   ├── api.ts          # API 響應類型
│   ├── models.ts       # 資料模型類型
│   └── common.ts       # 通用類型
├── modules/
│   └── gis/
│       └── types/      # 模組專用類型
│           └── layer.ts
```

### 4.3 類型匯出模式

```typescript
// ✅ 正確：使用 type 關鍵字匯出純類型
export type { UserProfile, UserSettings };

// ✅ 正確：介面使用 interface
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

// ❌ 避免：使用 enum（改用 const 物件）
// enum Status { Active, Inactive }
const Status = {
  Active: 'active',
  Inactive: 'inactive',
} as const;
type Status = typeof Status[keyof typeof Status];
```

---

## 五、命名規範

### 5.1 檔案命名

| 類型 | 規範 | 範例 |
|------|------|------|
| React 元件 | PascalCase | `UserProfile.tsx` |
| Hook | camelCase + use 前綴 | `useMapView.ts` |
| 服務/API | camelCase | `landInfoApi.ts` |
| 常數 | UPPER_SNAKE_CASE | `ERROR_CODES.ts` |
| 工具函數 | camelCase | `formatDate.ts` |
| 後端模組 | snake_case | `land_parcel_crud.py` |

### 5.2 變數命名

```typescript
// ✅ 正確：布林值使用 is/has/can 前綴
const isLoading = true;
const hasPermission = false;
const canEdit = true;

// ✅ 正確：事件處理使用 handle 前綴
const handleClick = () => {};
const handleSubmit = () => {};

// ✅ 正確：回調屬性使用 on 前綴
interface Props {
  onClick: () => void;
  onSubmit: (data: FormData) => void;
}
```

---

## 六、Import 排序

### 6.1 排序順序

```typescript
// 1. React 相關
import React, { useState, useEffect } from 'react';

// 2. 第三方函式庫
import { Button, Modal } from 'antd';
import { useQuery } from '@tanstack/react-query';

// 3. 專案內部模組（絕對路徑）
import { useAuth } from '@/hooks/useAuth';
import { landInfoApi } from '@/api/unified';

// 4. 相對路徑匯入
import { UserCard } from './UserCard';
import { formatDate } from '../utils';

// 5. 類型匯入
import type { User, UserSettings } from '@/types';

// 6. 樣式匯入
import styles from './Component.module.css';
```

---

## 七、Console.log 管理規範 (2026-01-03 更新)

### 7.1 DEBUG 環境變數模式 (推薦)

**目的**：在開發時保留有用的日誌，但不影響 ESLint 檢查

**正確做法**：
```typescript
// ✅ 正確：使用 DEBUG 環境變數控制
// 在檔案頂部定義
const DEBUG_CACHE = import.meta.env.DEV && import.meta.env.VITE_DEBUG_CACHE === 'true';
const DEBUG_GIS = import.meta.env.DEV && import.meta.env.VITE_DEBUG_GIS === 'true';
const DEBUG_LAYER = import.meta.env.DEV && import.meta.env.VITE_DEBUG_LAYER === 'true';

// 使用時
if (DEBUG_CACHE) console.warn('[useLayerCache] Cache hit:', key);
if (DEBUG_GIS) console.warn('[GisPlatformPage] Layer loaded:', layerName);
```

**啟用調試**：
```bash
# 在 .env 或 .env.development 中設定
VITE_DEBUG_CACHE=true
VITE_DEBUG_GIS=true
VITE_DEBUG_LAYER=true
```

**命名規範**：
| 模組 | 環境變數 | 用途 |
|------|---------|------|
| useLayerCache | `VITE_DEBUG_CACHE` | 圖層快取操作 |
| GisPlatformPage | `VITE_DEBUG_GIS` | GIS 地圖頁面 |
| UnifiedLayerManagement | `VITE_DEBUG_LAYER` | 圖層管理 |
| useLayerSourceOverlay | `VITE_DEBUG_OVERLAY` | 圖層疊加 |

### 7.2 允許的 console.log 使用

**偵錯工具類（永久保留）**：
- `utils/diagnostics.ts` - 診斷工具
- `utils/performanceMonitor.ts` - 效能監控
- `utils/errorMonitoring.ts` - 錯誤監控
- `utils/logger.ts` - 日誌工具

**測試類（永久保留）**：
- `__tests__/` 目錄下的測試檔案
- `.stories.tsx` Storybook 故事檔

**文檔類（永久保留）**：
- JSDoc 註解中的範例代碼
- README.md 中的使用範例

### 6.2 開發偵錯日誌規範

**正確做法**：
```typescript
// ✅ 正確：使用 DEV 環境檢查 + eslint-disable
if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.log('[ModuleName] Debug message:', data);
}

// ✅ 正確：帶有模組標識的日誌
console.log('[useCoordinateSync] State update:', newState);

// ✅ 正確：錯誤日誌（可在生產環境保留）
console.error('[API Error]', error);
console.warn('[Deprecation]', message);
```

**錯誤做法**：
```typescript
// ❌ 錯誤：未包裝的開發日誌
console.log('debugging');

// ❌ 錯誤：無模組標識
console.log(response);

// ❌ 錯誤：敏感資訊
console.log('Token:', userToken);
```

### 6.3 日誌分類

| 類型 | 方法 | 環境 | 說明 |
|------|------|------|------|
| 偵錯 | `console.log` | DEV only | 開發階段除錯 |
| 警告 | `console.warn` | All | 潛在問題警示 |
| 錯誤 | `console.error` | All | 錯誤追蹤 |
| 資訊 | `console.info` | DEV only | 狀態資訊 |

### 6.4 清理原則

- 提交前移除臨時偵錯日誌
- 保留有意義的開發日誌（需包裝）
- 生產環境自動過濾開發日誌

---

## 八、Python 後端規範

### 7.1 格式化工具

**必要工具配置**：

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
    migrations
    | __pycache__
    | \.git
)/
'''

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["backend"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
exclude = [".git", "__pycache__", "migrations", ".venv"]
```

### 8.2 Flake8 配置注意事項 (重要)

**問題**：`extend-ignore` 區塊不可包含行內註解

**正確做法**（`.flake8` 檔案）：
```ini
# ✅ 正確：註解放在 extend-ignore 區塊之前
# E203: Whitespace before ':' (conflicts with black)
# W503: Line break before binary operator (conflicts with black)
# E501: Line too long (handled by black)
extend-ignore =
    E203,
    W503,
    E501

# ❌ 錯誤：行內註解會造成解析錯誤
extend-ignore =
    E203,  # conflicts with black  ← 這會報錯！
    W503
```

### 8.3 測試環境配置

**問題**：測試時缺少環境變數導致 `ValidationError`

**正確做法**（`conftest.py`）：
```python
# ✅ 必須在導入 app 模組之前設定環境變數
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://...")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars-required")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-min-32-chars-required")
os.environ.setdefault("DB_PASSWORD", "test-password")

# ❌ 錯誤：在導入後才設定（太晚）
from backend.app.main import app
os.environ["SECRET_KEY"] = "..."  # 此時 Pydantic settings 已驗證失敗
```

### 8.4 類型註解

**強制要求**：

```python
# ✅ 正確：公開函數必須有類型註解
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """根據 ID 取得使用者"""
    return db.query(User).filter(User.id == user_id).first()

# ✅ 正確：使用 Pydantic 做資料驗證
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=8)

# ❌ 錯誤：缺少類型註解
def get_user(db, user_id):
    return db.query(User).filter(User.id == user_id).first()
```

### 8.5 匯入排序

```python
# 1. 標準函式庫
from datetime import datetime
from typing import List, Optional

# 2. 第三方函式庫
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 3. 專案內部模組
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserResponse
```

### 8.6 命名規範

| 類型 | 規範 | 範例 |
|------|------|------|
| 模組/套件 | snake_case | `user_service.py` |
| 類別 | PascalCase | `UserService` |
| 函數/方法 | snake_case | `get_user_by_id` |
| 常數 | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| 私有成員 | _前綴 | `_internal_cache` |

### 8.7 FastAPI 路由規範

```python
# ✅ 正確：使用 response_model 和完整文件
@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="取得使用者資料",
    description="根據 ID 取得單一使用者的詳細資料",
)
async def get_user(
    user_id: int = Path(..., description="使用者 ID", ge=1),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ❌ 錯誤：缺少類型和文件
@router.get("/{user_id}")
def get_user(user_id, db=Depends(get_db)):
    return user_crud.get(db, id=user_id)
```

### 8.8 錯誤處理

```python
# ✅ 正確：使用統一的錯誤回應格式
from backend.app.core.exceptions import (
    NotFoundException,
    ValidationError,
)

def get_user_or_404(db: Session, user_id: int) -> User:
    user = user_crud.get(db, id=user_id)
    if not user:
        raise NotFoundException(
            detail=f"User with id {user_id} not found",
            error_code="USER_NOT_FOUND"
        )
    return user

# ✅ 正確：日誌記錄
import logging

logger = logging.getLogger(__name__)

try:
    result = external_api_call()
except ExternalAPIError as e:
    logger.error(f"External API failed: {e}", exc_info=True)
    raise HTTPException(status_code=502, detail="External service unavailable")
```

### 8.9 後端驗證清單

```bash
# 1. 程式碼格式化
black backend/app/
isort backend/app/

# 2. 靜態檢查
flake8 backend/app/
mypy backend/app/ --ignore-missing-imports

# 3. 測試執行
pytest backend/tests/ -v --cov=backend/app

# 4. 棄用匯入檢測
python scripts/check_deprecated_imports.py
```

---

## 九、驗證清單

### 開發完成前檢查

```bash
# 1. TypeScript 編譯檢查
npm run typecheck

# 2. ESLint 檢查
npm run lint

# 3. 測試執行
npm run test:run

# 4. 建置檢查
npm run build
```

### 目標指標

| 指標 | 目標 |
|------|------|
| TypeScript 錯誤 | 0 個 |
| ESLint 錯誤 | 0 個 |
| ESLint 警告 | < 60 個 |
| 測試覆蓋率 | > 70% |

---

## 十、圖層管理模組規範 (2026-01-03)

### 10.1 架構分層

```
backend/app/layer_management/
├── services/           # 業務邏輯層
│   ├── basemap_service.py
│   ├── gis_layer_service.py
│   └── layer_source_service.py
├── repositories/       # 資料存取層 (欄位映射)
│   ├── base.py
│   ├── basemap_repository.py
│   ├── gis_layer_repository.py
│   └── spatial_layer_repository.py
└── schemas/            # Pydantic 模型
    ├── basemap.py
    ├── gis_layer.py
    └── layer_source.py
```

### 10.2 Repository 欄位映射規範

**目的**：統一資料庫欄位與 Schema 欄位命名

| 表名 | 資料庫欄位 | Schema 欄位 | 說明 |
|------|-----------|-------------|------|
| `spatial_layers` | `layer_name` | `name` | 圖層名稱 |
| `spatial_layers` | `is_visible` | `is_enabled` | 啟用狀態 |
| `dynamic_layers` | `layer_code` | `name` | 圖層代碼 |
| `dynamic_layers` | `api_endpoint` | `service_url` | 服務 URL |
| `dynamic_layers` | `is_active` | `is_enabled` | 啟用狀態 |

**正確做法**：
```python
# ✅ 正確：在 Repository 層進行欄位映射
def find_all_shapefiles(self) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id, layer_name as name,    -- 欄位別名
            is_visible as is_enabled   -- 欄位別名
        FROM spatial_layers
    """
```

### 10.3 group_id 類型規範

**強制規則**：`group_id` 統一使用 `str` 類型

```python
# ✅ 正確：字串類型
class ImportFromSourceRequest(BaseModel):
    group_id: str = Field(..., description="目標群組 ID")

# ❌ 錯誤：整數類型（會導致與資料庫不符）
class ImportFromSourceRequest(BaseModel):
    group_id: int  # 避免使用
```

### 10.4 opacity 預設值規範

| 圖層類型 | 預設 opacity | 說明 |
|---------|--------------|------|
| Basemap | 1.0 | 底圖完全不透明 |
| GIS Layer | 0.8 | 疊加圖層 80% |

```python
# ✅ 正確：依目標類型設定預設值
opacity = request.opacity
if opacity is None:
    opacity = 1.0 if target_type == "basemap" else 0.8
```

### 10.5 Service 層整合模式

**Delegation Pattern**：新服務包裝舊服務

```python
# ✅ 正確：ModularBasemapService 委派到 LegacyBasemapService
class ModularBasemapService:
    def __init__(self, db: Session):
        self._legacy = LegacyBasemapService(db)

    def get_all(self) -> List[BasemapConfig]:
        return self._legacy.get_all_basemaps()
```

### 10.6 原地重構策略

**強制規則**：保持現有 API 路徑，禁止建立 V2 API

```python
# ✅ 正確：端點內部使用 Service 層
@router.post("/layers/import-from-source")
async def import_from_source(request: ImportFromSourceRequest, db: Session = Depends(get_db)):
    service = GisLayerService(db)
    return service.import_from_source(request)

# ❌ 錯誤：建立新版 API 路徑
@router.post("/v2/layers/import")  # 避免 V2 路徑
```

---

---

## 十一、前後端 API 整合驗證程序 (2026-01-03 新增)

### 11.1 驗證流程

**目的**：確保前端 API 呼叫與後端端點完整對應

**步驟**：

```bash
# 1. 後端 API 端點驗證 (直接呼叫後端)
curl -X POST http://localhost:8002/api/v1/basemap-db/groups/list \
  -H "Content-Type: application/json" -d "{}"

# 2. 前端代理驗證 (透過 Vite 代理)
curl -X POST http://localhost:3003/api/v1/basemap-db/groups/list \
  -H "Content-Type: application/json" -d "{}"

# 3. TypeScript 編譯檢查
cd frontend && npx tsc --noEmit
```

### 11.2 常見 API 端點路徑

| 模組 | 後端路徑 | HTTP 方法 | 說明 |
|------|---------|----------|------|
| Basemap 群組 | `/basemap-db/groups/list` | POST | 取得底圖群組列表 |
| Basemap 圖層 | `/basemap-db/layers/list` | POST | 取得底圖圖層列表 |
| GIS 群組 | `/gis/gislayers/groups/list` | POST | 取得 GIS 群組列表 |
| GIS 圖層 | `/gis/gislayers/layers/list` | POST | 取得 GIS 圖層列表 |
| Spatial 圖層 | `/spatial/layers/list` | POST | 取得 Shapefile 圖層列表 |
| 統一圖層 | `/system/unified/layers/all` | GET | 取得所有圖層統一檢視 |

### 11.3 前端 API 客戶端對應

```typescript
// gisUnifiedApi.ts 中的對應方法
import { gisApi } from '@/api/unified/gisUnifiedApi';

// 底圖管理
await gisApi.basemaps.listGroups();  // → POST /basemap-db/groups/list
await gisApi.basemaps.listLayers();  // → POST /basemap-db/layers/list

// GIS 圖層管理
await gisApi.layers.listGroups();    // → POST /gis/gislayers/groups/list
await gisApi.layers.listLayers();    // → POST /gis/gislayers/layers/list

// 空間圖層
await gisApi.spatial.listLayers();   // → POST /spatial/layers/list
```

### 11.4 Vite 代理配置驗證

**位置**：`frontend/vite.config.ts`

```typescript
// 確認代理配置正確
proxy: {
  '/api': {
    target: apiTarget,  // 預設: http://localhost:8002
    changeOrigin: true,
    rewrite: (path) => path,  // 保持路徑不變
  },
}
```

### 11.5 問題排除

| 症狀 | 可能原因 | 解決方案 |
|-----|---------|---------|
| 404 Not Found | 路徑錯誤或方法錯誤 | 檢查 POST vs GET |
| 405 Method Not Allowed | HTTP 方法不正確 | 確認端點要求的方法 |
| 代理不生效 | Vite 未重啟 | 重新啟動前端服務 |
| 連線被拒 | 後端未啟動 | 檢查 docker ps |

---

## 十二、統一 API 模組規範 (2026-01-03 新增)

### 12.1 模組結構

**目的**：統一 API 層架構，減少重複程式碼，便於維護

```
frontend/src/api/
├── client.ts                    # 統一 axios 實例
├── unified/                     # 統一 API 模組目錄
│   ├── index.ts                 # 匯出入口
│   ├── gisUnifiedApi.ts         # GIS 空間查詢
│   ├── cadastralUnifiedApi.ts   # 地籍資訊
│   ├── landUnifiedApi.ts        # 土地資訊
│   ├── navigationUnifiedApi.ts  # 導覽管理
│   ├── positioningUnifiedApi.ts # 定位工具
│   └── building3dUnifiedApi.ts  # 3D 建物
├── [已棄用] navigationApi.ts    # → unified/navigationUnifiedApi.ts
├── [已棄用] positioningToolsApi.ts # → unified/positioningUnifiedApi.ts
```

### 12.2 命名空間模式

**正確做法**：
```typescript
// ✅ 正確：使用命名空間物件
export const positioningApi = {
  tools: {
    list: (filter) => apiClient.post('/system/positioning-tools/list', filter),
    create: (params) => apiClient.post('/system/positioning-tools/create', params),
    update: (id, params) => apiClient.post(`/system/positioning-tools/${id}/update`, params),
    delete: (id) => apiClient.post(`/system/positioning-tools/${id}/delete`),
    toggle: (id, enabled) => positioningApi.tools.update(id, { is_enabled: enabled }),
  },
  locations: {
    list: (filter) => apiClient.post('/system/topic-locations/list', filter),
    // ...
  },
  constants: {
    PAGE_OPTIONS,
    POSITIONING_TOOL_ICONS,
  },
};

// ❌ 錯誤：獨立函數散落各處
export function getPositioningTools() { }
export function createPositioningTool() { }
```

### 12.3 使用統一 API

```typescript
// ✅ 正確：從 unified 匯入
import { positioningApi, navigationApi } from '@/api/unified';

const { data: tools } = await positioningApi.tools.list({ page_id: 'gis-map' });
const items = await navigationApi.items.query({ view: 'tree' });

// ❌ 錯誤：從舊版檔案匯入
import positioningToolsApi from '@/api/positioningToolsApi'; // 已棄用
```

### 12.4 向後兼容匯出

```typescript
// unified/index.ts
// 命名空間匯出（推薦）
export { positioningApi } from './positioningUnifiedApi';

// 向後兼容的個別函數匯出
export {
  getPositioningTools,
  createPositioningTool,
  // ...
} from './positioningUnifiedApi';
```

---

## 十三、API 棄用流程規範 (2026-01-03 新增)

### 13.1 棄用標記格式

**目的**：提供清晰的遷移路徑，避免突然破壞

```typescript
/**
 * 定位工具 API
 *
 * @deprecated 請使用 '@/api/unified/positioningUnifiedApi' 或 '@/api/unified'
 * @sunset 2026-03-01 - 此檔案將於 2026-03-01 後移除
 *
 * 遷移指南:
 * ```typescript
 * // 舊版
 * import positioningToolsApi from '@/api/positioningToolsApi';
 * const tools = await positioningToolsApi.getTools({ page_id: 'gis-map' });
 *
 * // 新版 (統一 API)
 * import { positioningApi } from '@/api/unified';
 * const { data: tools } = await positioningApi.tools.list({ page_id: 'gis-map' });
 * ```
 */
```

### 13.2 棄用週期

| 階段 | 時長 | 動作 |
|------|------|------|
| 宣告棄用 | Day 0 | 加入 `@deprecated` 標記 |
| 遷移期 | 60-90 天 | 保持功能正常，新功能不加入舊 API |
| 日落期 | Day 60-90 | 加入 console.warn 警告 |
| 移除 | Day 90+ | 刪除舊檔案 |

### 13.3 console.warn 範例

```typescript
// 棄用警告（接近日落日期時加入）
if (import.meta.env.DEV) {
  console.warn(
    '[Deprecation Warning] positioningToolsApi 將於 2026-03-01 移除。' +
    '請遷移至 @/api/unified/positioningUnifiedApi'
  );
}
```

---

## 十四、React Query vs useState 決策指南 (2026-01-03 新增)

### 14.1 使用 React Query 的場景

| 場景 | 適用 | 範例 |
|------|------|------|
| CRUD 操作 | ✅ | `usePositioningToolsQuery` |
| 快取重要 | ✅ | 導覽項目、系統配置 |
| 資料共享 | ✅ | 多組件需要同資料 |
| 背景更新 | ✅ | 定期輪詢資料 |
| 錯誤重試 | ✅ | API 請求自動重試 |

### 14.2 保持 useState 的場景

| 場景 | 原因 | 範例 |
|------|------|------|
| 複雜協調邏輯 | 多源併行查詢難以用 Query Key 管理 | `useComprehensiveQuery` |
| 即時狀態管理 | 狀態轉換複雜 | `useUnifiedPolygonQuery` |
| 事件處理 | 非資料獲取 | `useMapClickHandler` |
| 本地 UI 狀態 | 不需伺服器同步 | 表單輸入、開關狀態 |

### 14.3 Query Key 命名規範

```typescript
// ✅ 正確：使用陣列結構，從大到小
const QUERY_KEYS = {
  all: ['positioning'] as const,
  tools: () => [...QUERY_KEYS.all, 'tools'] as const,
  toolsList: (filter: Filter) => [...QUERY_KEYS.tools(), filter] as const,
  locations: () => [...QUERY_KEYS.all, 'locations'] as const,
  locationsList: (filter: Filter) => [...QUERY_KEYS.locations(), filter] as const,
};

// 使用
useQuery({
  queryKey: QUERY_KEYS.toolsList({ page_id: 'gis-map' }),
  queryFn: () => positioningApi.tools.list(filter),
});
```

---

## 十五、後端服務容器模式 (2026-01-03 新增)

### 15.1 AIServiceContainer 架構

**目的**：統一服務依賴注入，避免重複實例化

```python
# backend/app/services/ai/service_container.py
class AIServiceContainer:
    # 全局服務 (進程生命週期)
    @property
    def geocoding_service(self) -> TGOSGeocodingService: ...
    @property
    def land_price_service(self) -> LandPriceService: ...

    # 請求服務 (請求生命週期)
    @cached_property
    def db(self) -> Session: ...
    @cached_property
    def parcel_repository(self) -> ParcelRepository: ...
    @cached_property
    def transaction_service(self) -> UnifiedTransactionService: ...
```

### 15.2 執行器使用規範

```python
# ✅ 正確：使用 context.services 存取服務
class TopicLocationExecutor(BaseExecutor):
    async def execute(self, intent: ParsedIntent, context: ExecutionContext) -> Dict:
        # 透過服務容器取得資料庫 session
        db = context.services.db

        result = db.query(TopicLocation).filter(
            TopicLocation.id == location_id
        ).first()
        return {"location": result}

# ❌ 錯誤：直接建立 Session
class TopicLocationExecutor(BaseExecutor):
    async def execute(self, intent: ParsedIntent, context: ExecutionContext) -> Dict:
        db = SessionLocal()  # 避免！使用 context.services.db
```

### 15.3 快取參數提取函數

```python
# ✅ 正確：使用統一的快取參數提取
from backend.app.services.ai.intent_cache_service import extract_cache_params_from_context

async def execute(self, intent: ParsedIntent, context: ExecutionContext) -> Dict:
    cache_params = extract_cache_params_from_context(context)
    cache_key = f"topic_location:{location_id}:{cache_params.get('user_id', 'anon')}"
```

---

---

## 十六、GIS 地圖功能 Hook 模式 (2026-01-06 新增)

### 16.1 Map Feature Hook 規範

**目的**：統一管理地圖功能的狀態（面板、圖層、高亮標記）

詳見 `.claude/skills/gis-map-feature-patterns.md`

**命名規範**：
```typescript
// Hook 命名
use{Feature}MapFeature  // useUrbanRenewalMapFeature

// 組件命名
{Feature}HighlightMarker  // UrbanRenewalHighlightMarker
{Feature}InfoPanel        // UrbanRenewalInfoPanel
{Feature}Layer            // UrbanRenewalLayer
```

**標準介面**：
```typescript
interface MapFeatureReturn {
  // 面板狀態
  panelVisible: boolean;
  togglePanel: () => void;

  // 圖層狀態
  layerVisible: boolean;
  setLayerVisible: (v: boolean) => void;

  // 高亮標記
  highlightedItem: HighlightedType | null;
  clearHighlightedItem: () => void;

  // 組件 Props (memoized)
  panelProps: { ... };
  layerProps: { ... };
  highlightMarkerProps: { ... };
}
```

### 16.2 高亮標記視覺規範

| 功能類型 | 主色調 | Hex Code |
|---------|-------|----------|
| 都市更新 | 紫色 | `#722ed1` |
| 開發區 | 綠色 | `#52c41a` |
| 控制點 | 藍色 | `#1890ff` |
| 地標 | 橙色 | `#fa8c16` |

### 16.3 必要自動行為

```typescript
// 高亮標記組件必須實作
useEffect(() => {
  if (item && map) {
    // 1. 飛到目標位置
    map.flyTo([item.lat, item.lon], 15, { duration: 0.8 });

    // 2. 延遲後打開 Popup
    setTimeout(() => markerRef.current?.openPopup(), 900);

    // 3. 15 秒後自動清除
    const timer = setTimeout(() => onClear?.(), 15000);
    return () => clearTimeout(timer);
  }
}, [item, map, onClear]);
```

---

## 十七、清除圖徵完整性規範 (2026-01-06 新增)

### 17.1 強制規則

**「清除圖徵」按鈕必須清除所有套疊圖層與標記**

```typescript
// ✅ 正確：完整的清除邏輯
const handleClearAllFeatures = useCallback(() => {
  // 1. 定位標記
  setLocationMarker(null);
  setHighlightedControlPoint(null);

  // 2. 開發區
  devZone.setLayerVisible(false);
  devZone.clearHighlightedZone();

  // 3. 都市更新
  setUrbanRenewalLayerVisible(false);
  setHighlightedUrbanRenewal(null);

  // 4. 查估案件
  setAssessmentLayerVisible(false);

  // 5. 不動產交易
  setRealEstateLayerVisible(false);

  // 6. 底圖套疊
  clearAllOverlays();

  // 7. 工具面板
  setToolContainerVisible(false);
}, [devZone, clearAllOverlays]);
```

### 17.2 新增功能檢查清單

當新增地圖功能時：
- [ ] 在 `handleClearAllFeatures` 加入清除邏輯
- [ ] 清除包含：圖層可見性 + 高亮標記 + 相關面板

---

## 十八、KML 匯出規範 (2026-01-06 新增)

### 18.1 中文檔名編碼

```python
# ✅ 正確：使用 RFC 5987 編碼
from urllib.parse import quote

headers = {
    "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}.kml"
}

# ❌ 錯誤：直接使用中文（會亂碼）
headers = {
    "Content-Disposition": f"attachment; filename=\"{filename}.kml\""
}
```

### 18.2 前端統一組件

```typescript
// 使用統一的 KmlExportButton
import { KmlExportButton } from '@/components/Export';

<KmlExportButton
  endpoint="/api/v1/development-zones/export/kml"
  filters={{ status: 'active' }}
  filename="開發區資料"
/>
```

---

**建立日期**：2025-12-24
**最後更新**：2026-01-08 (加入 API 路徑重複 P0 警告)
