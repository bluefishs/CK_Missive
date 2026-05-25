# 前端架構 (Frontend Architecture)

> 版本：1.0.0 | 更新日期：2026-01-06

## 概述

CK_Missive 前端採用 React + TypeScript 技術棧，結合 Ant Design 元件庫，實現現代化的單頁應用程式 (SPA)。

## 技術棧

| 技術 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI 框架 |
| TypeScript | 5.x | 型別安全 |
| Vite | 5.x | 建構工具 |
| Ant Design | 5.x | UI 元件庫 |
| React Router | 6.x | 路由管理 |
| Axios | 1.x | HTTP 請求 |

---

## 目錄結構

```
frontend/src/
├── api/                        # API 層
│   ├── client.ts               # 統一 HTTP Client
│   ├── types.ts                # 共用型別定義
│   ├── documentsApi.ts         # 公文 API
│   ├── projectsApi.ts          # 案件 API
│   └── index.ts                # 統一匯出
│
├── components/                 # 元件
│   ├── common/                 # 共用元件
│   │   ├── ErrorBoundary.tsx   # 錯誤邊界
│   │   ├── PageLoading.tsx     # 頁面載入
│   │   └── UnifiedTable.tsx    # 統一表格
│   ├── document/               # 公文元件
│   ├── hoc/                    # 高階元件
│   │   ├── withAuth.tsx        # 認證 HOC
│   │   ├── withLoading.tsx     # 載入狀態 HOC
│   │   └── index.ts
│   └── Layout/                 # 版面配置
│
├── hooks/                      # 自訂 Hooks
│   ├── useAuthGuard.ts         # 認證守衛
│   ├── useDocuments.ts         # 公文操作
│   ├── useProjects.ts          # 案件操作
│   ├── usePerformance.ts       # 效能監控
│   └── index.ts
│
├── pages/                      # 頁面元件
│   ├── DocumentPage.tsx        # 公文列表頁
│   ├── DashboardPage.tsx       # 儀表板
│   └── ...
│
├── router/                     # 路由
│   ├── AppRouter.tsx           # 主路由器
│   ├── ProtectedRoute.tsx      # 受保護路由
│   ├── types.ts                # 路由常量
│   └── index.ts
│
├── services/                   # 服務層
│   └── authService.ts          # 認證服務
│
└── types/                      # 型別定義
    └── index.ts
```

---

## API 層架構

### 統一 API Client

`frontend/src/api/client.ts`

#### 核心功能

```typescript
import { apiClient } from '@/api';

// GET 請求
const document = await apiClient.get<Document>('/documents/1');

// POST 請求
const newDoc = await apiClient.post<Document>('/documents', data);

// 分頁列表
const result = await apiClient.getList<Document>('/documents', {
  page: 1,
  limit: 20,
  sortBy: 'doc_date',
  sortOrder: 'desc',
});

// 檔案上傳 (含進度)
await apiClient.uploadWithProgress(
  '/files/upload',
  files,
  'files',
  (percent, loaded, total) => {
    console.log(`上傳進度: ${percent}%`);
  }
);

// 檔案下載
await apiClient.download('/files/1/download', 'document.pdf');
```

#### 錯誤處理

```typescript
import { ApiException, ErrorCode } from '@/api';

try {
  await apiClient.post('/documents', data);
} catch (error) {
  if (error instanceof ApiException) {
    // 取得使用者友善訊息
    const message = error.getUserMessage();

    // 取得表單欄位錯誤
    const fieldErrors = error.getFieldErrors();

    // 根據錯誤碼處理
    if (error.code === ErrorCode.VALIDATION_ERROR) {
      // 處理驗證錯誤
    }
  }
}
```

---

## 認證與權限

### useAuthGuard Hook

`frontend/src/hooks/useAuthGuard.ts`

#### 基本用法

```tsx
import { useAuthGuard, usePermission, usePermissions } from '@/hooks';

function MyComponent() {
  const {
    isAuthenticated,  // 是否已認證
    isAdmin,          // 是否為管理員
    userId,           // 使用者 ID
    username,         // 使用者名稱
    role,             // 角色
    permissions,      // 權限列表
    logout,           // 登出函數
    authDisabled,     // 認證是否禁用
  } = useAuthGuard();

  // 單一權限檢查
  const canWrite = usePermission('documents:write');

  // 多權限檢查
  const perms = usePermissions(['documents:write', 'documents:delete']);
  // perms = { 'documents:write': true, 'documents:delete': false }
}
```

#### 需要認證的頁面

```tsx
function ProtectedPage() {
  const { isAllowed } = useAuthGuard({
    requireAuth: true,
    roles: ['admin'],
    permissions: ['documents:write'],
    redirectTo: '/login',
  });

  if (!isAllowed) {
    return null; // Hook 會自動處理重定向
  }

  return <div>受保護的內容</div>;
}
```

### 權限類型

```typescript
type Permission =
  | 'documents:read'
  | 'documents:write'
  | 'documents:delete'
  | 'projects:read'
  | 'projects:write'
  | 'projects:delete'
  | 'admin:access'
  | 'admin:users'
  | 'admin:settings';
```

---

## 高階元件 (HOC)

### withAuth

`frontend/src/components/hoc/withAuth.tsx`

```tsx
import { withAuth, withAdminAuth, withPermission } from '@/components/hoc';

// 需要認證
export default withAuth(MyPage);

// 需要管理員權限
export default withAdminAuth(AdminPage);

// 需要特定權限
export default withPermission(['documents:write'])(DocumentEditPage);

// 自訂選項
export default withAuth(MyPage, {
  requireAuth: true,
  roles: ['admin', 'editor'],
  redirectTo: '/login',
  UnauthorizedComponent: CustomUnauthorized,
});
```

### withLoading

`frontend/src/components/hoc/withLoading.tsx`

```tsx
import { withLoading, useLoadingState } from '@/components/hoc';

// HOC 方式
const MyPage = withLoading(({ loadingState }) => {
  const handleFetch = async () => {
    await loadingState.withLoading(fetchData());
  };

  if (loadingState.isLoading) return <Spin />;
  if (loadingState.error) return <Alert message={loadingState.error.message} />;

  return <div>內容</div>;
});

// Hook 方式
function MyComponent() {
  const { isLoading, error, withLoading } = useLoadingState();

  const handleFetch = async () => {
    try {
      await withLoading(fetchData());
    } catch (err) {
      // 錯誤已由 Hook 處理
    }
  };
}
```

---

## 路由系統

### 路由常量

`frontend/src/router/types.ts`

```typescript
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  DOCUMENTS: '/documents',
  DOCUMENT_DETAIL: '/documents/:id',
  CONTRACT_CASES: '/contract-cases',
  // ...
} as const;
```

### 受保護路由

`frontend/src/router/ProtectedRoute.tsx`

```tsx
import { ProtectedRoute, AdminRoute, PublicRoute } from '@/router';

// 基本認證保護
<Route path="/dashboard" element={
  <ProtectedRoute>
    <DashboardPage />
  </ProtectedRoute>
} />

// 管理員專用
<Route path="/admin" element={
  <AdminRoute>
    <AdminPage />
  </AdminRoute>
} />

// 需要特定權限
<Route path="/documents/edit/:id" element={
  <ProtectedRoute permissions={['documents:write']}>
    <DocumentEditPage />
  </ProtectedRoute>
} />
```

### 懶載入

`frontend/src/router/AppRouter.tsx`

```tsx
import { lazy, Suspense } from 'react';

// 懶載入頁面
const DocumentPage = lazy(() =>
  import('../pages/DocumentPage')
    .then(module => ({ default: module.DocumentPage }))
);

// 使用 Suspense 包裝
<Suspense fallback={<PageLoading message="載入中..." />}>
  <Routes>
    <Route path="/documents" element={<DocumentPage />} />
  </Routes>
</Suspense>
```

---

## 狀態管理

### 本地狀態

使用 React Hooks 管理元件狀態：

```tsx
const [documents, setDocuments] = useState<Document[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<Error | null>(null);
```

### 自訂 Hooks

封裝業務邏輯為可重用 Hooks：

```tsx
// useDocuments.ts
export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchDocuments = async (params?: QueryParams) => {
    setLoading(true);
    try {
      const result = await documentsApi.getList(params);
      setDocuments(result.items);
    } finally {
      setLoading(false);
    }
  };

  return { documents, loading, fetchDocuments };
}
```

---

## 開發模式

### 禁用認證

在 `.env.local` 設定：

```env
VITE_AUTH_DISABLED=true
```

效果：
- 跳過所有認證檢查
- 自動使用開發帳號 (dev-user)
- 擁有所有權限

### API 基礎 URL

```env
VITE_API_BASE_URL=http://localhost:8001
```

---

## 最佳實踐

### 1. 使用統一 API Client

```tsx
// ✅ 推薦
import { apiClient } from '@/api';
const data = await apiClient.get('/endpoint');

// ❌ 避免
import axios from 'axios';
const data = await axios.get('/api/endpoint');
```

### 2. 使用 useAuthGuard 處理認證

```tsx
// ✅ 推薦
const { isAuthenticated } = useAuthGuard({ requireAuth: true });

// ❌ 避免：直接檢查 localStorage
const token = localStorage.getItem('auth_token');
```

### 3. 使用 HOC 封裝通用邏輯

```tsx
// ✅ 推薦
export default withAuth(MyPage);

// ❌ 避免：在每個元件重複認證邏輯
```

### 4. 使用懶載入優化效能

```tsx
// ✅ 推薦
const Page = lazy(() => import('./Page'));

// ❌ 避免：靜態匯入所有頁面
import Page from './Page';
```

### 5. 使用 TypeScript 嚴格模式

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

---

## 相關文件

- [CODEWIKI 主頁](./CODEWIKI.md)
- [服務層架構](./Service-Layer-Architecture.md)
- [前端元件](./Frontend-Components.md)
