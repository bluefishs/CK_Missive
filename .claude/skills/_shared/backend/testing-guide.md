# 測試框架指南 (Testing Framework Guide)

> **觸發關鍵字**: test, 測試, pytest, jest, unit test, 單元測試
> **適用範圍**: 測試編寫、測試執行、覆蓋率

---

## 測試架構

### 後端 (Python/pytest)
```
backend/tests/
├── conftest.py              # 共用 fixtures
├── test_api/                # API 端點測試
│   ├── test_documents.py
│   ├── test_calendar.py
│   └── test_agencies.py
├── test_services/           # 服務層測試
│   ├── test_document_service.py
│   └── test_calendar_service.py
└── test_unit/               # 單元測試
    └── test_utils.py
```

### 前端 (TypeScript/Jest)
```
frontend/src/__tests__/
├── components/              # 組件測試
├── hooks/                   # Hook 測試
└── utils/                   # 工具函數測試
```

---

## 後端測試

### pytest 配置
```ini
# backend/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
```

### 共用 Fixtures
```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.database import get_db

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def db_session():
    # 提供測試用資料庫 session
    ...
```

### API 測試範例
```python
# backend/tests/test_api/test_documents.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_documents(async_client: AsyncClient):
    response = await async_client.post(
        "/api/documents-enhanced/list",
        json={"page": 1, "page_size": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

@pytest.mark.asyncio
async def test_create_document(async_client: AsyncClient):
    response = await async_client.post(
        "/api/documents-enhanced",
        json={
            "doc_number": "測試字第114000001號",
            "subject": "測試主旨",
            "category": "收文"
        }
    )
    assert response.status_code == 200
```

### 服務層測試範例
```python
# backend/tests/test_services/test_document_service.py
import pytest
from app.services.document_service import DocumentService

@pytest.mark.asyncio
async def test_document_service_create(db_session):
    service = DocumentService(db_session)
    doc = await service.create({
        "doc_number": "測試字第114000002號",
        "subject": "服務層測試",
        "category": "發文"
    })
    assert doc.id is not None
    assert doc.auto_serial.startswith("S")
```

---

## 前端測試

### Jest 配置
```javascript
// frontend/jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};
```

### 組件測試範例
```typescript
// frontend/src/__tests__/components/DocumentList.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { DocumentList } from '@/components/DocumentList';

describe('DocumentList', () => {
  it('renders document list', async () => {
    render(<DocumentList />);

    await waitFor(() => {
      expect(screen.getByText('公文列表')).toBeInTheDocument();
    });
  });
});
```

### Hook 測試範例
```typescript
// frontend/src/__tests__/hooks/useDocuments.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useDocuments } from '@/hooks/useDocuments';

describe('useDocuments', () => {
  it('fetches documents', async () => {
    const { result } = renderHook(() => useDocuments());

    await waitFor(() => {
      expect(result.current.documents).toBeDefined();
    });
  });
});
```

---

## 執行測試

### 後端
```bash
# 執行所有測試
cd backend && pytest

# 執行特定測試檔案
pytest tests/test_api/test_documents.py

# 顯示詳細輸出
pytest -v

# 顯示覆蓋率
pytest --cov=app --cov-report=html

# 只執行標記的測試
pytest -m "not slow"
```

### 前端
```bash
# 執行所有測試
cd frontend && npm test

# 監視模式
npm test -- --watch

# 覆蓋率報告
npm test -- --coverage
```

---

## 測試原則

### 測試金字塔
```
        /\
       /  \
      / E2E \        少量端對端測試
     /------\
    /  整合   \      中量整合測試
   /----------\
  /   單元     \     大量單元測試
 /--------------\
```

### 命名規範
```python
# Python
def test_should_create_document_when_valid_data():
def test_should_fail_when_doc_number_missing():

# TypeScript
it('should render document list correctly')
it('should show error when API fails')
```

### 測試隔離
- 每個測試獨立運行
- 測試後清理資料
- 不依賴測試執行順序

---

## 持續整合

### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run pytest
        run: cd backend && pytest --cov

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run jest
        run: cd frontend && npm test
```
