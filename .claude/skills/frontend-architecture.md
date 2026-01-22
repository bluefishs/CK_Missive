# 前端架構規範 (Frontend Architecture)

> **版本**: 1.3.0
> **更新日期**: 2026-01-22
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
│   ├── Layout.tsx        # 主佈局元件 ⭐ (AppRouter 使用)
│   ├── DynamicLayout.tsx # 動態佈局元件 (備用)
│   └── site-management/  # 網站管理元件
├── config/               # 配置檔案
│   ├── env.ts           # 環境變數與認證函數 ⭐
│   ├── navigationConfig.ts
│   └── queryConfig.ts
├── constants/            # 常數定義
├── hooks/               # 自訂 Hooks
│   ├── useAuthGuard.ts  # 認證守衛
│   └── usePermissions.ts # 權限檢查
├── pages/               # 頁面元件
│   └── SiteManagementPage.tsx # 網站管理頁面 ⭐
├── router/              # 路由配置
│   ├── AppRouter.tsx    # 主路由（使用 Layout.tsx）⭐
│   ├── ProtectedRoute.tsx
│   └── types.ts
├── services/            # 業務服務
│   ├── authService.ts   # 認證服務
│   ├── cacheService.ts  # 快取服務
│   ├── navigationService.ts # 導覽服務
│   └── secureApiService.ts # 安全 API 服務 ⭐
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

### 3.4 React Hooks 使用規範 (v1.3.0 新增)

#### ⚠️ 重要：Hooks 必須在元件頂層呼叫

**典型錯誤場景**:
```
Error: Rendered more hooks than during the previous render
```

**根本原因**: Hooks 在 render 函數或條件判斷內呼叫，違反 React Hooks 規則。

#### 常見違規案例：Form.useWatch

```tsx
// ❌ 錯誤：在 render 函數內呼叫 useWatch
function MyComponent() {
  const renderSection = () => {
    const watchedValue = Form.useWatch('field', form);  // 違規！
    return <div>{watchedValue}</div>;
  };

  return <div>{renderSection()}</div>;
}

// ✅ 正確：在元件頂層呼叫
function MyComponent() {
  // 所有 useWatch 必須在頂層
  const watchedValue = Form.useWatch('field', form);

  const renderSection = () => {
    return <div>{watchedValue}</div>;  // 使用頂層的變數
  };

  return <div>{renderSection()}</div>;
}
```

#### 多欄位監聽的正確模式

```tsx
function PaymentForm({ form }: { form: FormInstance }) {
  // ✅ 所有 watch 在元件頂層定義
  const watchedWorkTypes: string[] = Form.useWatch('work_type', form) || [];
  const watchedWork01Amount = Form.useWatch('work_01_amount', form) || 0;
  const watchedWork02Amount = Form.useWatch('work_02_amount', form) || 0;
  const watchedWork03Amount = Form.useWatch('work_03_amount', form) || 0;

  // 計算總金額
  const totalAmount = useMemo(() => {
    return watchedWork01Amount + watchedWork02Amount + watchedWork03Amount;
  }, [watchedWork01Amount, watchedWork02Amount, watchedWork03Amount]);

  // render 函數使用頂層變數
  const renderPaymentSection = () => {
    return (
      <div>
        <span>已選擇: {watchedWorkTypes.join(', ')}</span>
        <span>總金額: {totalAmount}</span>
      </div>
    );
  };

  return <Form form={form}>{renderPaymentSection()}</Form>;
}
```

#### Hooks 規則檢查清單

- [ ] 所有 `useState`、`useEffect`、`useMemo`、`useCallback` 在元件頂層
- [ ] 所有 `Form.useWatch` 在元件頂層（不在 render 函數內）
- [ ] 不在條件判斷 (`if`) 或迴圈 (`for`) 內呼叫 Hooks
- [ ] 自訂 Hooks 的名稱以 `use` 開頭

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

## 六、導覽系統架構 (Navigation System)

### 6.1 核心元件關係

```
┌──────────────────────────────────────────────────────────────────┐
│                        AppRouter.tsx                              │
│                      (使用 Layout.tsx)                            │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Layout.tsx ⭐                              │
│              (主佈局元件 - 側邊導覽列)                              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  secureApiService.getNavigationItems()                       │ │
│  │  ↓                                                           │ │
│  │  convertToMenuItems() → Ant Design Menu                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  window.addEventListener('navigation-updated', handler)      │ │
│  │  ↑ 監聽來自 SiteManagementPage 的更新事件                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        ▼                                              ▼
┌─────────────────────┐                    ┌─────────────────────┐
│  secureApiService   │                    │ SiteManagementPage  │
│  (統一 API 服務)    │                    │   (網站管理頁面)     │
│                     │                    │                     │
│  GET /navigation/   │ ◄─────────────────►│  CRUD 導覽項目      │
│       items         │                    │                     │
│                     │                    │  dispatchEvent      │
│                     │                    │  ('navigation-     │
│                     │                    │   updated')         │
└─────────────────────┘                    └─────────────────────┘
```

### 6.2 重要檔案說明

| 檔案 | 說明 | 注意事項 |
|------|------|----------|
| `components/Layout.tsx` | 主佈局元件 | **AppRouter 使用此元件**，非 DynamicLayout |
| `components/DynamicLayout.tsx` | 動態佈局元件 | 備用，目前未被使用 |
| `pages/SiteManagementPage.tsx` | 網站管理頁面 | 路徑欄位使用下拉選單，觸發更新事件 |
| `services/secureApiService.ts` | 安全 API 服務 | Layout 與 SiteManagement 共用 |
| `router/types.ts` | 前端路由定義 | ROUTES 常數，是路徑的真實來源 |

### 6.2.1 後端路徑驗證 (2026-01-12 新增)

| 檔案 (後端) | 說明 |
|------------|------|
| `backend/app/core/navigation_validator.py` | 路徑白名單驗證器 |
| `backend/app/api/endpoints/secure_site_management.py` | 在 create/update 時驗證路徑 |

- SiteManagementPage 的路徑欄位已改為下拉選單
- 下拉選單選項從後端 API `/navigation/valid-paths` 載入
- 後端 API 會驗證路徑是否在白名單中，無效路徑會被拒絕

### 6.3 導覽更新機制

```typescript
// SiteManagementPage.tsx - 觸發更新事件
window.dispatchEvent(new CustomEvent('navigation-updated'));

// Layout.tsx - 監聯更新事件
useEffect(() => {
  const handleNavigationUpdate = () => {
    loadNavigationData(); // 重新載入導覽資料
  };
  window.addEventListener('navigation-updated', handleNavigationUpdate);
  return () => {
    window.removeEventListener('navigation-updated', handleNavigationUpdate);
  };
}, []);
```

### 6.4 開發模式行為

- **開發模式** (`AUTH_DISABLED=true`)：使用動態 API 載入，跳過權限過濾
- **正式模式**：使用動態 API 載入，根據用戶權限過濾導覽項目
- **API 失敗時**：使用靜態選單 `getStaticMenuItems()` 作為備用

---

## 七、相關文件

- `CLAUDE.md` - 專案配置總覽
- `docs/DEVELOPMENT_STANDARDS.md` - 開發規範總綱
- `docs/specifications/API_ENDPOINT_CONSISTENCY.md` - API 端點規範

---

*維護者: Claude Code Assistant*
