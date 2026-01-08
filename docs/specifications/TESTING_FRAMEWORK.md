# 測試框架規劃

> 版本: 1.0.0
> 建立日期: 2026-01-08
> 狀態: 規劃中
> 用途: 建立專案自動化測試框架

---

## 一、現況分析

### 1.1 現有測試狀態

| 項目 | 狀態 | 說明 |
|------|------|------|
| 後端單元測試 | 部分 | 僅有 `test_schema_consistency.py` |
| 前端單元測試 | 無 | 未建立測試框架 |
| 整合測試 | 無 | 手動測試為主 |
| E2E 測試 | 無 | 未規劃 |
| CI/CD 測試 | 無 | 未整合 |

### 1.2 測試覆蓋率目標

根據 `@AGENT.md` 規範，新功能需達到 **85%** 測試覆蓋率。

---

## 二、後端測試規劃

### 2.1 技術棧

| 工具 | 用途 |
|------|------|
| pytest | 測試框架 |
| pytest-asyncio | 異步測試支援 |
| pytest-cov | 覆蓋率報告 |
| httpx | API 測試客戶端 |
| factory-boy | 測試資料工廠 |

### 2.2 目錄結構

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 共用 fixtures
│   ├── factories/               # 測試資料工廠
│   │   ├── __init__.py
│   │   ├── document_factory.py
│   │   ├── project_factory.py
│   │   └── user_factory.py
│   ├── unit/                    # 單元測試
│   │   ├── __init__.py
│   │   ├── test_document_service.py
│   │   ├── test_csv_processor.py
│   │   └── test_validators.py
│   ├── integration/             # 整合測試
│   │   ├── __init__.py
│   │   ├── test_documents_api.py
│   │   ├── test_projects_api.py
│   │   └── test_calendar_api.py
│   └── test_schema_consistency.py  # 現有
```

### 2.3 Fixtures 範例

```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.database import Base

@pytest.fixture
async def db_session():
    """建立測試用資料庫會話"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

@pytest.fixture
def test_client():
    """建立測試用 API 客戶端"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
```

### 2.4 單元測試範例

```python
# tests/unit/test_document_service.py

import pytest
from app.services.document_service import DocumentService

class TestDocumentService:
    """公文服務單元測試"""

    @pytest.fixture
    def service(self, db_session):
        return DocumentService(db_session)

    async def test_create_document(self, service):
        """測試公文建立"""
        data = {
            "doc_number": "TEST-001",
            "subject": "測試主旨",
            "doc_type": "收文",
        }
        result = await service.create(data)
        assert result.success is True
        assert result.data.doc_number == "TEST-001"

    async def test_duplicate_document(self, service):
        """測試重複公文字號"""
        data = {"doc_number": "TEST-002", "subject": "測試"}
        await service.create(data)
        result = await service.create(data)
        assert result.success is False
        assert result.error_code == "DUPLICATE_DOCUMENT"
```

### 2.5 整合測試範例

```python
# tests/integration/test_documents_api.py

import pytest
from httpx import AsyncClient

class TestDocumentsAPI:
    """公文 API 整合測試"""

    @pytest.fixture
    async def client(self, app):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_list_documents(self, client):
        """測試公文列表 API"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 1, "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data

    async def test_create_document(self, client):
        """測試公文建立 API"""
        response = await client.post(
            "/api/documents-enhanced/create",
            json={
                "doc_number": "API-TEST-001",
                "subject": "API 測試公文",
                "doc_type": "收文"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

---

## 三、前端測試規劃

### 3.1 技術棧

| 工具 | 用途 |
|------|------|
| Vitest | 測試框架 (比 Jest 更快) |
| React Testing Library | 元件測試 |
| MSW | API Mock |
| @testing-library/user-event | 使用者事件模擬 |

### 3.2 目錄結構

```
frontend/
├── src/
│   ├── components/
│   │   └── document/
│   │       ├── DocumentList.tsx
│   │       └── __tests__/
│   │           └── DocumentList.test.tsx
│   ├── hooks/
│   │   └── __tests__/
│   │       └── useDocuments.test.ts
│   └── utils/
│       └── __tests__/
│           └── dateUtils.test.ts
├── tests/
│   ├── setup.ts
│   ├── mocks/
│   │   ├── handlers.ts
│   │   └── server.ts
│   └── integration/
│       └── DocumentFlow.test.tsx
└── vitest.config.ts
```

### 3.3 設定檔範例

```typescript
// vitest.config.ts

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'tests/'],
    },
  },
});
```

### 3.4 元件測試範例

```typescript
// src/components/document/__tests__/DocumentList.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentList } from '../DocumentList';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

describe('DocumentList', () => {
  it('renders loading state initially', () => {
    render(<DocumentList />, { wrapper });
    expect(screen.getByText(/載入中/i)).toBeInTheDocument();
  });

  it('renders documents after loading', async () => {
    render(<DocumentList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('TEST-001')).toBeInTheDocument();
    });
  });
});
```

### 3.5 Hook 測試範例

```typescript
// src/hooks/__tests__/useDocuments.test.ts

import { renderHook, waitFor } from '@testing-library/react';
import { useDocuments } from '../useDocuments';

describe('useDocuments', () => {
  it('fetches documents successfully', async () => {
    const { result } = renderHook(() => useDocuments());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.items).toHaveLength(10);
  });
});
```

---

## 四、測試執行

### 4.1 後端測試指令

```bash
# 執行所有測試
cd backend && pytest

# 執行並顯示覆蓋率
cd backend && pytest --cov=app --cov-report=term-missing

# 執行特定測試
cd backend && pytest tests/unit/test_document_service.py -v

# 執行整合測試
cd backend && pytest tests/integration/ -v
```

### 4.2 前端測試指令

```bash
# 執行所有測試
cd frontend && npm run test

# 監視模式
cd frontend && npm run test:watch

# 覆蓋率報告
cd frontend && npm run test:coverage

# UI 模式
cd frontend && npm run test:ui
```

---

## 五、CI/CD 整合

### 5.1 GitHub Actions 範例

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm run test:coverage
```

---

## 六、實施計劃

### 6.1 第一階段 (基礎建置) ✅ 完成

- [x] 安裝後端測試套件 (pytest, pytest-asyncio, pytest-cov)
- [x] 建立 `tests/conftest.py` 共用 fixtures
- [x] 建立驗證器單元測試 (33 個測試)
- [x] 安裝前端測試套件 (Vitest, Testing Library, MSW)
- [x] 建立 Vitest 設定檔
- [x] 建立範例測試 (7 個測試)

**測試執行結果 (2026-01-08)**:
- 後端：39 passed (排除整合測試)
- 前端：7 passed

### 6.2 第二階段 (核心功能測試)

- [ ] CSV 匯入服務測試
- [ ] 公文 CRUD API 測試
- [ ] 前端公文列表元件測試
- [ ] 前端表單元件測試

### 6.3 第三階段 (CI/CD 整合)

- [ ] 建立 GitHub Actions workflow
- [ ] 整合覆蓋率報告
- [ ] 設定 PR 測試必須通過

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `@AGENT.md` | 測試覆蓋率要求 (85%) |
| `docs/DEVELOPMENT_STANDARDS.md` | 開發規範 |
| `backend/tests/` | 後端測試目錄 |
| `frontend/vitest.config.ts` | 前端測試設定 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.1.0 | 2026-01-08 | 完成第一階段建置，更新實施狀態 |
| 1.0.0 | 2026-01-08 | 初版規劃 |

---

*文件維護: Claude Code Assistant*
