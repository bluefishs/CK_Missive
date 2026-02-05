# Frontend API 服務層規範

> **版本**: 1.0.0
> **建立日期**: 2026-02-06
> **參考**: docs/SERVICE_ARCHITECTURE_STANDARDS.md

---

## 目前結構

```
api/
├── client.ts           # API Client (axios 封裝)
├── endpoints.ts        # 端點常數定義
├── types.ts            # API 通用型別
├── index.ts            # 統一匯出
│
├── documentsApi.ts     # 公文 API
├── agenciesApi.ts      # 機關 API
├── vendorsApi.ts       # 廠商 API
├── projectsApi.ts      # 專案 API
├── filesApi.ts         # 檔案 API
├── calendarApi.ts      # 行事曆 API
├── dashboardApi.ts     # 儀表板 API
├── usersApi.ts         # 用戶 API
├── adminUsersApi.ts    # 管理員 API
├── aiApi.ts            # AI 服務 API
├── deploymentApi.ts    # 部署管理 API
│
├── taoyuan/            # 桃園派工模組
│   ├── index.ts
│   ├── dispatchOrders.ts
│   ├── projects.ts
│   ├── payments.ts
│   ├── documentLinks.ts
│   ├── projectLinks.ts
│   └── attachments.ts
│
└── __tests__/          # 測試檔案
    └── client.test.ts
```

---

## 命名規範

### API 服務檔案

| 類型 | 命名規則 | 範例 |
|------|----------|------|
| 實體 API | `{entity}Api.ts` (複數) | `documentsApi.ts`, `agenciesApi.ts` |
| 關聯 API | `{entity1}{Entity2}Api.ts` | `projectVendorsApi.ts` |
| 功能 API | `{feature}Api.ts` | `dashboardApi.ts`, `calendarApi.ts` |

### 匯出物件

```typescript
// ✅ 推薦：具名匯出物件
export const documentsApi = {
  getList: async (params) => { ... },
  create: async (data) => { ... },
  update: async (id, data) => { ... },
  delete: async (id) => { ... },
};

// ❌ 避免：預設匯出
export default { ... };
```

---

## API 方法命名規則

| 操作類型 | 方法命名 | HTTP 方法 |
|----------|----------|-----------|
| 列表查詢 | `getList()`, `list()` | POST (本專案慣例) |
| 詳情查詢 | `getDetail(id)`, `get(id)` | POST |
| 建立 | `create(data)` | POST |
| 更新 | `update(id, data)` | POST |
| 刪除 | `delete(id)`, `remove(id)` | POST |
| 特定操作 | `{動詞}{名詞}()` | POST |

### 範例

```typescript
export const documentsApi = {
  // 列表
  async getList(params?: DocumentListQuery): Promise<PaginatedResponse<Document>> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params ?? {});
  },

  // 詳情
  async getDetail(id: number): Promise<Document> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.DETAIL(id), {});
  },

  // 建立
  async create(data: DocumentCreate): Promise<Document> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.CREATE, data);
  },

  // 更新
  async update(id: number, data: DocumentUpdate): Promise<Document> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.UPDATE(id), data);
  },

  // 刪除
  async delete(id: number): Promise<DeleteResponse> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.DELETE(id), {});
  },

  // 特定操作
  async exportToCsv(params: ExportParams): Promise<Blob> {
    return apiClient.post(API_ENDPOINTS.DOCUMENTS.EXPORT, params, {
      responseType: 'blob',
    });
  },
};
```

---

## 端點管理

所有 API 端點必須在 `endpoints.ts` 中集中定義：

```typescript
// ✅ 正確：使用 endpoints.ts 常數
import { API_ENDPOINTS } from './endpoints';
apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);

// ❌ 禁止：硬編碼路徑
apiClient.post('/documents-enhanced/list', params);
```

---

## 型別管理

API 型別必須從 `types/api.ts` 匯入，不在 API 檔案中定義：

```typescript
// ✅ 正確：從 types/api.ts 匯入
import { Document, DocumentCreate, DocumentUpdate } from '../types/api';

// ❌ 禁止：在 API 檔案中定義
interface Document { ... }  // 不允許！
```

---

## 未來規劃結構

### Phase 2 (可選重構)

```
api/
├── core/                    # 核心模組
│   ├── client.ts
│   ├── endpoints.ts
│   └── types.ts
│
├── document/               # 公文模組
│   ├── index.ts
│   ├── documentsApi.ts
│   └── attachmentsApi.ts
│
├── project/                # 專案模組
│   ├── index.ts
│   ├── projectsApi.ts
│   ├── projectVendorsApi.ts
│   └── projectStaffApi.ts
│
├── agency/                 # 機關模組
│   ├── index.ts
│   └── agenciesApi.ts
│
├── vendor/                 # 廠商模組
│   ├── index.ts
│   └── vendorsApi.ts
│
├── taoyuan/                # 桃園派工模組 (已存在)
│   └── ...
│
├── system/                 # 系統模組
│   ├── index.ts
│   ├── authApi.ts
│   ├── usersApi.ts
│   ├── configApi.ts
│   └── backupApi.ts
│
└── ai/                     # AI 模組
    ├── index.ts
    └── aiApi.ts
```

---

## 錯誤處理

```typescript
// API 服務層應拋出錯誤，由呼叫端處理
export const documentsApi = {
  async getDetail(id: number): Promise<Document> {
    const response = await apiClient.post(
      API_ENDPOINTS.DOCUMENTS.DETAIL(id),
      {}
    );
    // 讓 apiClient interceptor 處理錯誤
    return response;
  },
};

// 呼叫端處理錯誤
try {
  const doc = await documentsApi.getDetail(id);
} catch (error) {
  message.error('載入公文失敗');
}
```

---

## 相關文件

- `docs/SERVICE_ARCHITECTURE_STANDARDS.md` - 服務層架構規範
- `frontend/src/types/api.ts` - API 型別定義 (SSOT)
- `frontend/src/hooks/README.md` - Hook 分層規範
