# CK_Missive 系統 CODEWIKI

> 版本：1.0.0 | 更新日期：2026-01-06

## 📋 目錄

- [系統架構總覽](#系統架構總覽)
- [後端架構](#後端架構)
- [前端架構](#前端架構)
- [資料庫設計](#資料庫設計)
- [開發指南](#開發指南)
- [最佳實踐](#最佳實踐)

---

## 系統架構總覽

### 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| **後端框架** | FastAPI | 0.100+ |
| **ORM** | SQLAlchemy (Async) | 2.0+ |
| **資料庫** | PostgreSQL | 15+ |
| **前端框架** | React + TypeScript | 18+ |
| **UI 組件庫** | Ant Design | 5.x |
| **建構工具** | Vite | 5.x |
| **狀態管理** | React Hooks + Context |  |

### 系統分層架構

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Frontend)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Pages     │  │  Components │  │  Hooks/Services │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                         │                               │
│                    API Client                           │
└─────────────────────────────────────────────────────────┘
                          │
                     HTTP/REST
                          │
┌─────────────────────────────────────────────────────────┐
│                    後端 (Backend)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Endpoints  │  │  Services   │  │   Strategies    │  │
│  │  (API 路由) │  │  (業務邏輯) │  │   (可重用策略)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                         │                               │
│                    SQLAlchemy                           │
│                         │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │               Models (資料模型)                      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          │
                      PostgreSQL
```

---

## 後端架構

### 目錄結構

```
backend/
├── app/
│   ├── api/
│   │   └── endpoints/          # API 端點
│   ├── core/
│   │   ├── config.py           # 設定
│   │   ├── dependencies.py     # 依賴注入
│   │   └── cache_manager.py    # 快取管理
│   ├── extended/
│   │   └── models.py           # 資料模型
│   ├── schemas/                # Pydantic 結構
│   └── services/
│       ├── base/               # 基礎服務
│       │   └── unit_of_work.py # UnitOfWork 模式
│       └── strategies/         # 策略類別
│           └── agency_matcher.py
├── alembic/                    # 資料庫遷移
└── main.py                     # 應用程式入口
```

### 服務層架構

#### UnitOfWork 模式

```python
from app.services import UnitOfWork, get_uow

# 使用方式
async with get_uow() as uow:
    document = await uow.documents.get_document_by_id(doc_id)
    await uow.commit()
```

#### 策略模式 (Strategy Pattern)

```python
from app.services.strategies import AgencyMatcher, ProjectMatcher

# 機關名稱智慧匹配
matcher = AgencyMatcher(db)
agency_id = await matcher.match_or_create("某某機關")

# 案件名稱智慧匹配
project_matcher = ProjectMatcher(db)
project_id = await project_matcher.match_or_create("工程案件")
```

### N+1 查詢優化

使用 `selectinload` 預載入關聯資料：

```python
from sqlalchemy.orm import selectinload

query = select(Document).options(
    selectinload(Document.contract_project),
    selectinload(Document.sender_agency),
    selectinload(Document.receiver_agency),
)
```

### 快取策略

```python
from app.core.cache_manager import cache_dropdown_data, cache_statistics

# 下拉選單資料快取
@cache_dropdown_data(ttl=300)
async def get_agencies():
    ...

# 統計資料快取
@cache_statistics(ttl=60)
async def get_document_stats():
    ...
```

---

## 前端架構

### 目錄結構

```
frontend/src/
├── api/                        # API 層
│   ├── client.ts               # 統一 HTTP Client
│   ├── types.ts                # 共用型別
│   └── documentsApi.ts         # 文件 API
├── components/
│   ├── common/                 # 共用元件
│   ├── document/               # 文件元件
│   └── hoc/                    # 高階元件 (HOC)
│       ├── withAuth.tsx        # 認證 HOC
│       └── withLoading.tsx     # 載入狀態 HOC
├── hooks/
│   ├── useAuthGuard.ts         # 認證守衛 Hook
│   ├── useDocuments.ts         # 文件 Hook
│   └── usePerformance.ts       # 效能監控 Hook
├── pages/                      # 頁面元件
├── router/
│   ├── AppRouter.tsx           # 路由器
│   ├── ProtectedRoute.tsx      # 受保護路由
│   └── types.ts                # 路由常量
└── services/
    └── authService.ts          # 認證服務
```

### 認證與權限

#### useAuthGuard Hook

```tsx
import { useAuthGuard, usePermission } from '@/hooks/useAuthGuard';

// 基本用法
const { isAuthenticated, isAdmin, logout } = useAuthGuard();

// 需要認證
const { isAllowed } = useAuthGuard({ requireAuth: true });

// 權限檢查
const canEdit = usePermission('documents:write');
```

#### 受保護路由

```tsx
import { ProtectedRoute, AdminRoute } from '@/router';

// 需要認證
<ProtectedRoute>
  <MyPage />
</ProtectedRoute>

// 需要管理員
<AdminRoute>
  <AdminPage />
</AdminRoute>

// 需要特定權限
<ProtectedRoute permissions={['documents:write']}>
  <DocumentEditPage />
</ProtectedRoute>
```

### 高階元件 (HOC)

#### withAuth

```tsx
import { withAuth, withAdminAuth } from '@/components/hoc';

// 需要認證
export default withAuth(MyPage);

// 需要管理員
export default withAdminAuth(AdminPage);
```

#### withLoading

```tsx
import { withLoading, useLoadingState } from '@/components/hoc';

// Hook 用法
const { isLoading, withLoading, error } = useLoadingState();

const handleFetch = async () => {
  await withLoading(fetchData());
};
```

### API Client

```tsx
import { apiClient } from '@/api';

// GET 請求
const data = await apiClient.get<Document>('/documents/1');

// 分頁列表
const result = await apiClient.getList<Document>('/documents', {
  page: 1,
  limit: 20,
});

// 檔案上傳
await apiClient.uploadWithProgress(
  '/files/upload',
  files,
  'files',
  (percent) => console.log(`${percent}%`)
);
```

---

## 資料庫設計

### 核心資料表

| 資料表 | 說明 |
|--------|------|
| `documents` | 公文主表 |
| `contract_projects` | 承攬案件 |
| `government_agencies` | 機關單位 |
| `vendors` | 協力廠商 |
| `calendar_events` | 行事曆事件 |

### 效能索引

```sql
-- 公文查詢優化
CREATE INDEX idx_documents_type_date ON documents (doc_type, doc_date DESC);
CREATE INDEX idx_documents_status ON documents (status);

-- 案件查詢優化
CREATE INDEX idx_projects_year_status ON contract_projects (year, status);

-- 機關查詢優化
CREATE INDEX idx_agencies_name ON government_agencies (agency_name);
```

---

## 開發指南

### 環境設置

```bash
# 後端
cd backend
pip install -r requirements.txt
alembic upgrade head

# 前端
cd frontend
npm install
npm run dev
```

### 環境變數

```env
# .env.local
VITE_API_BASE_URL=http://localhost:8001
VITE_AUTH_DISABLED=true  # 開發模式禁用認證
```

### 開發伺服器

```bash
# 啟動後端 (port 8001)
uvicorn main:app --reload --port 8001

# 啟動前端 (port 3000)
npm run dev
```

---

## 最佳實踐

### 後端

1. **使用 UnitOfWork** 管理交易
2. **使用策略模式** 處理可重用邏輯
3. **使用 selectinload** 預載入關聯資料
4. **使用快取裝飾器** 提升效能

### 前端

1. **使用 useAuthGuard** 處理認證
2. **使用 HOC** 封裝共用邏輯
3. **使用懶載入** 優化首屏載入
4. **使用 apiClient** 統一 API 呼叫

### 程式碼品質

1. 遵循 TypeScript 嚴格模式
2. 使用 ESLint + Prettier 格式化
3. 撰寫 JSDoc 註解
4. 遵循 SKILL 規範文件

---

## 相關文件

- [開發指南](./DEVELOPMENT_GUIDE.md)
- [資料庫結構](./DATABASE_SCHEMA.md)
- [API 對應](./FRONTEND_API_MAPPING.md)
- [系統維護](./SYSTEM_MAINTENANCE.md)
