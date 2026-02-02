---
name: test-generator
description: 快速生成單元測試與整合測試
version: 1.0.0
category: shared
triggers:
  - 測試生成
  - generate test
  - 單元測試
  - unit test
  - pytest
  - vitest
updated: 2026-01-22
---

# Test Generator Skill

快速生成單元測試與整合測試

**適用場景**：新功能開發、重構、提升測試覆蓋率

## 測試類型

### 1. 後端單元測試（Pytest）

**測試範本**：

#### API 端點測試

```python
# tests/api/test_real_estate_query.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_unified_query_success():
    """測試統一查詢 API - 成功案例"""
    response = client.post(
        "/api/v1/real-estate/query",
        json={
            "filters": {
                "city": "台北市",
                "transaction_year": "112"
            },
            "page": 1,
            "page_size": 10
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "items" in data["data"]
    assert len(data["data"]["items"]) <= 10

def test_unified_query_validation_error():
    """測試統一查詢 API - 驗證錯誤"""
    response = client.post(
        "/api/v1/real-estate/query",
        json={
            "page": -1,  # 無效的頁碼
        }
    )

    assert response.status_code == 422

@pytest.mark.asyncio
async def test_query_with_coordinates():
    """測試坐標範圍查詢"""
    response = client.post(
        "/api/v1/real-estate/query",
        json={
            "coordinate_range": {
                "min_lon": 121.0,
                "max_lon": 121.5,
                "min_lat": 24.5,
                "max_lat": 25.0
            }
        }
    )

    assert response.status_code == 200
```

#### 服務層測試

```python
# tests/services/test_spatial_analysis.py
import pytest
from backend.app.services.spatial_analysis_service import calculate_buffer

def test_calculate_buffer_valid_point():
    """測試緩衝區計算 - 有效點"""
    point = {"type": "Point", "coordinates": [121.5, 25.0]}
    radius = 1000  # 1 公里

    result = calculate_buffer(point, radius)

    assert result is not None
    assert result["type"] == "Polygon"
    assert len(result["coordinates"][0]) > 0

def test_calculate_buffer_invalid_input():
    """測試緩衝區計算 - 無效輸入"""
    with pytest.raises(ValueError):
        calculate_buffer(None, 1000)
```

#### 資料庫測試

```python
# tests/db/test_connection.py
import pytest
from backend.app.db.connection import get_db, health_check

def test_database_connection():
    """測試資料庫連線"""
    db = next(get_db())
    assert db is not None
    db.close()

def test_health_check():
    """測試資料庫健康檢查"""
    result = health_check()
    assert result["status"] == "healthy"
    assert "response_time_ms" in result
```

### 2. 前端單元測試（Vitest）

**測試範本**：

#### API 客戶端測試

```javascript
// src/api/pathAnalysisApi.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { createFacility, getFacilityList } from './pathAnalysisApi';

vi.mock('axios');

describe('Path Analysis API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create facility successfully', async () => {
    const mockResponse = {
      data: {
        success: true,
        data: { id: 1, name: 'Test Facility' },
      },
    };
    axios.post.mockResolvedValue(mockResponse);

    const facility = {
      name: 'Test Facility',
      category: 'school',
      coordinates: [121.5, 25.0],
    };

    const result = await createFacility(facility);

    expect(result.success).toBe(true);
    expect(result.data.id).toBeDefined();
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/facilities/create'),
      facility
    );
  });

  it('should handle API error', async () => {
    axios.post.mockRejectedValue(new Error('Network error'));

    await expect(createFacility({})).rejects.toThrow('Network error');
  });
});
```

#### React 組件測試

```javascript
// src/components/PathAnalysis/FacilityListPanel.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FacilityListPanel from './FacilityListPanel';

describe('FacilityListPanel', () => {
  it('renders facility list', async () => {
    const mockFacilities = [
      { id: 1, name: 'School A', category: 'school' },
      { id: 2, name: 'Hospital B', category: 'hospital' },
    ];

    render(<FacilityListPanel facilities={mockFacilities} />);

    expect(screen.getByText('School A')).toBeInTheDocument();
    expect(screen.getByText('Hospital B')).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', async () => {
    const mockOnDelete = vi.fn();
    const facility = { id: 1, name: 'Test', category: 'school' };

    render(<FacilityListPanel facilities={[facility]} onDelete={mockOnDelete} />);

    const deleteButton = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalledWith(1);
    });
  });
});
```

#### Hook 測試

```javascript
// src/hooks/usePathAnalysis.test.js
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import usePathAnalysis from './usePathAnalysis';
import * as api from '../api/pathAnalysisApi';

vi.mock('../api/pathAnalysisApi');

describe('usePathAnalysis', () => {
  it('fetches facilities on mount', async () => {
    const mockFacilities = [{ id: 1, name: 'Test' }];
    api.getFacilityList.mockResolvedValue({ data: mockFacilities });

    const { result } = renderHook(() => usePathAnalysis());

    await waitFor(() => {
      expect(result.current.facilities).toEqual(mockFacilities);
      expect(result.current.loading).toBe(false);
    });
  });

  it('creates facility', async () => {
    api.createFacility.mockResolvedValue({
      success: true,
      data: { id: 1 },
    });

    const { result } = renderHook(() => usePathAnalysis());

    await act(async () => {
      await result.current.createFacility({ name: 'New' });
    });

    expect(api.createFacility).toHaveBeenCalled();
  });
});
```

---

## 測試配置

### Pytest 配置

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=backend.app
    --cov-report=html
    --cov-report=term
    --cov-fail-under=70
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

### Vitest 配置

```javascript
// frontend/vitest.config.js
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['node_modules/', 'src/test/', '**/*.test.{js,jsx}', '**/*.spec.{js,jsx}'],
      lines: 50,
      functions: 50,
      branches: 50,
      statements: 50,
    },
  },
});
```

---

## 測試執行

### 後端測試

```bash
# 執行所有測試
cd backend
pytest

# 執行特定測試檔案
pytest tests/api/test_real_estate_query.py

# 執行特定測試函數
pytest tests/api/test_real_estate_query.py::test_unified_query_success

# 只執行單元測試
pytest -m unit

# 生成覆蓋率報告
pytest --cov=backend.app --cov-report=html
```

### 前端測試

```bash
# 執行所有測試
cd frontend
npm run test

# 監聽模式
npm run test -- --watch

# 生成覆蓋率報告
npm run test -- --coverage

# 執行特定測試檔案
npm run test -- pathAnalysisApi.test.js
```

---

## 測試最佳實踐

### 1. AAA 模式

- **Arrange**（準備）：設定測試數據
- **Act**（執行）：執行被測試的功能
- **Assert**（斷言）：驗證結果

### 2. 測試命名

```python
# ✅ 好的命名
def test_create_facility_with_valid_data_returns_success():
    pass

# ❌ 不好的命名
def test_facility():
    pass
```

### 3. 測試隔離

- 每個測試獨立運行
- 不依賴其他測試的結果
- 使用 fixture 或 beforeEach 設定初始狀態

### 4. Mock 外部依賴

```python
# 使用 pytest-mock
def test_api_call(mocker):
    mock_redis = mocker.patch('backend.app.core.redis_client.redis_client')
    mock_redis.get.return_value = None
    # 測試邏輯
```

---

## 快速生成測試

### 使用 AI 生成測試

**提示詞範例**：

```
為以下函數生成 pytest 單元測試：

[貼上函數代碼]

要求：
1. 包含成功案例和失敗案例
2. 使用 AAA 模式
3. 測試邊界條件
4. 包含適當的 mock
```

---

**建立日期**：2025-10-27
**最後更新**：2025-10-27
