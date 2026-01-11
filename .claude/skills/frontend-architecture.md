# 前端架構規範 (Frontend Architecture)

> **版本**: 1.0.0
> **更新日期**: 2026-01-11
> **適用範圍**: frontend/src/**

---

## 一、目錄結構

```
frontend/src/
├── api/                    # API 客戶端
│   ├── client.ts          # 統一 API 客戶端
│   └── endpoints.ts       # API 端點定義
├── components/            # React 元件
│   ├── common/           # 共用元件
│   ├── document/         # 公文相關元件
│   ├── hoc/              # 高階元件 (HOC)
│   └── Layout.tsx        # 主佈局元件
├── config/               # 配置檔案
│   ├── env.ts           # 環境變數與認證函數 ⭐
│   ├── navigationConfig.ts
│   └── queryConfig.ts
├── constants/            # 常數定義
├── hooks/               # 自訂 Hooks
│   ├── useAuthGuard.ts  # 認證守衛
│   └── usePermissions.ts # 權限檢查
├── pages/               # 頁面元件
├── router/              # 路由配置
│   ├── AppRouter.tsx
│   ├── ProtectedRoute.tsx
│   └── types.ts
├── services/            # 業務服務
│   ├── authService.ts   # 認證服務
│   ├── cacheService.ts  # 快取服務
│   └── secureApiService.ts # 安全 API 服務
├── types/               # TypeScript 型別
└── utils/               # 工具函數
```

---

## 二、核心模組說明

### 2.1 環境配置模組 (`config/env.ts`)

**此為認證邏輯的唯一真實來源 (Single Source of Truth)**

```typescript
// 導出的函數與常數
export const isInternalIP: () => boolean;      // 內網 IP 檢測
export const isAuthDisabled: () => boolean;    // 認證停用判斷
export const detectEnvironment: () => EnvironmentType;  // 環境類型
export const AUTH_DISABLED_ENV: boolean;       // 環境變數值
export const GOOGLE_CLIENT_ID: string;         // Google OAuth 客戶端 ID
```

### 2.2 認證守衛 (`hooks/useAuthGuard.ts`)

```typescript
// 使用範例
const {
  isAuthenticated,  // 是否已認證
  isAllowed,        // 是否允許存取
  authDisabled,     // 認證是否停用
  hasPermission,    // 權限檢查函數
} = useAuthGuard({
  requireAuth: true,
  roles: ['admin'],
  permissions: ['documents:write']
});
```

### 2.3 受保護路由 (`router/ProtectedRoute.tsx`)

```tsx
// 基本認證保護
<ProtectedRoute>
  <MyPage />
</ProtectedRoute>

// 需要管理員權限
<ProtectedRoute roles={['admin']}>
  <AdminPage />
</ProtectedRoute>

// 需要特定權限
<ProtectedRoute permissions={['documents:write']}>
  <DocumentEditPage />
</ProtectedRoute>
```

---

## 三、開發規範

### 3.1 新增認證相關功能

```typescript
// ✅ 正確做法 - 導入共用函數
import { isAuthDisabled, isInternalIP } from '../config/env';

function MyComponent() {
  const authDisabled = isAuthDisabled();
  // ...
}

// ❌ 禁止做法 - 重複定義邏輯
function MyComponent() {
  const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
  // ...
}
```

### 3.2 新增 API 呼叫

```typescript
// ✅ 正確做法 - 使用 apiClient
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';

const result = await apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);

// ❌ 禁止做法 - 硬編碼路徑
const result = await axios.post('/api/documents/list', params);
```

### 3.3 新增頁面元件

1. 建立頁面檔案於 `pages/` 目錄
2. 在 `router/AppRouter.tsx` 加入路由
3. 使用 `ProtectedRoute` 包裝（如需認證）
4. 在導覽配置中加入選單項目

---

## 四、環境變數

| 變數名稱 | 說明 | 預設值 |
|----------|------|--------|
| `VITE_AUTH_DISABLED` | 停用認證 | `false` |
| `VITE_API_BASE_URL` | API 基礎 URL | `http://localhost:8001` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth 客戶端 ID | - |
| `VITE_PORT` | 開發伺服器端口 | `3000` |

---

## 五、認證流程

```
┌─────────────────────────────────────────────────────────┐
│                      使用者存取                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               detectEnvironment()                        │
│         判斷存取來源 (localhost/internal/public)          │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐    ┌─────────────────────┐
│   內網 IP (internal) │    │  其他 (localhost等)  │
│                     │    │                     │
│  isAuthDisabled()   │    │  isAuthDisabled()   │
│     = true          │    │     = false         │
└─────────────────────┘    └─────────────────────┘
              │                         │
              ▼                         ▼
┌─────────────────────┐    ┌─────────────────────┐
│    直接進入系統       │    │   顯示登入頁面       │
│    (開發者權限)       │    │   (Google OAuth)    │
└─────────────────────┘    └─────────────────────┘
```

---

## 六、相關文件

- `CLAUDE.md` - 專案配置總覽
- `docs/DEVELOPMENT_STANDARDS.md` - 開發規範總綱
- `docs/specifications/API_ENDPOINT_CONSISTENCY.md` - API 端點規範

---

*維護者: Claude Code Assistant*
