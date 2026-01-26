# 前端架構規範 (Frontend Architecture)

> **版本**: 1.0.0
> **建立日期**: 2026-01-22
> **適用範圍**: 前端 React + TypeScript 專案

---

## 一、HTTP 客戶端規範

### 統一使用 apiClient

**所有 API 呼叫必須使用 `@/api/client` 的 `apiClient`**

```typescript
// ✅ 正確：使用 apiClient
import { apiClient } from '@/api/client';

apiClient.get('/items');
apiClient.post('/items', data);

// ❌ 禁止：直接 import axios
import axios from 'axios';  // ESLint 會報錯

// ❌ 禁止：直接使用 fetch()
fetch('/api/v1/items');  // ESLint 會報錯
```

### apiClient 已包含功能

| 功能 | 說明 |
|------|------|
| Cookie 認證 | HTTPOnly Cookie 自動處理 |
| CSRF Token | 自動注入至 header |
| Token 刷新 | 自動處理過期 token |
| 錯誤處理 | 統一的錯誤格式化 |
| **baseURL** | `/api/v1` (重要！不需再加前綴) |

### 路徑重複問題 (P0)

```typescript
// ❌ 錯誤：路徑會變成 /api/v1/api/v1/...
const API_BASE_URL = '/api/v1';
apiClient.post(`${API_BASE_URL}/analytics/trends`);

// ✅ 正確：apiClient 已有 baseURL
apiClient.post('/analytics/trends');
```

### 例外情況

| 情況 | 說明 |
|------|------|
| `src/api/**` | 核心客戶端實作可使用 axios |
| 測試檔案 | `*.test.*`, `__tests__/**` 可 mock axios |
| 型別導入 | `import type { AxiosResponse }` 允許 |
| 工具函數 | `import { isAxiosError }` 允許 |

---

## 二、UnifiedApi 統一入口

### 架構概述

```
frontend/src/api/
├── client.ts           # apiClient 核心
├── unified/            # UnifiedApi 統一入口
│   ├── index.ts        # 總匯出
│   ├── gisUnifiedApi.ts
│   ├── realEstateUnifiedApi.ts
│   ├── systemUnifiedApi.ts
│   ├── compensationUnifiedApi.ts
│   └── spatialUnifiedApi.ts
└── [deprecated modules] # 已標記 @deprecated
```

### 使用方式

```typescript
// ✅ 推薦：使用 UnifiedApi 統一入口
import { gisApi, realEstateApi, systemApi } from '@/api/unified';

// GIS 相關
gisApi.dtm.getSlopeValue(params);
gisApi.tileProxy.fetchTile(url);
gisApi.i3s.proxy(path);

// 不動產相關
realEstateApi.transactions.list(params);
realEstateApi.seasons.getCurrent();
realEstateApi.photos.upload(file);

// 系統相關
systemApi.erd.getAllTables();
systemApi.docs.getApiSpec();
systemApi.health.check();
```

### Deprecated 模組

以下模組已標記 `@deprecated`，應逐步遷移至 UnifiedApi：

| 舊模組 | 新模組 |
|--------|--------|
| `dtmApi` | `gisApi.dtm` |
| `buildingLicenseApi` | `gisApi.buildingLicense` |
| `erdApi` | `systemApi.erd` |
| `documentationApi` | `systemApi.docs` |
| `compensationService` | `compensationUnifiedApi` |

---

## 三、專案目錄結構

```
frontend/src/
├── api/                # API 客戶端層
│   ├── client.ts       # apiClient 核心
│   ├── unified/        # UnifiedApi 統一入口
│   └── [modules]/      # 各模組 API (部分已 deprecated)
├── components/         # 共用組件
│   ├── common/         # 通用組件
│   ├── forms/          # 表單組件
│   └── layout/         # 佈局組件
├── hooks/              # 自定義 Hooks
│   ├── business/       # 業務邏輯 Hooks
│   ├── system/         # 系統功能 Hooks
│   └── utility/        # 工具類 Hooks
├── modules/            # 功能模組
│   └── layer-unified/  # 統一圖層管理
├── pages/              # 頁面組件
├── types/              # 型別定義
│   └── models/         # 資料模型型別
├── utils/              # 工具函數
└── config/             # 配置檔案
```

---

## 四、React Hooks 規範

### 核心規則：Hooks 必須在組件頂層呼叫

```tsx
// ❌ 違規：在 render 函數內呼叫 Hook
function MyComponent() {
  const renderSection = () => {
    const value = Form.useWatch('field', form);  // 錯誤！
    return <div>{value}</div>;
  };
  return <div>{renderSection()}</div>;
}

// ✅ 正確：所有 Hook 在組件頂層
function MyComponent() {
  const value = Form.useWatch('field', form);  // 頂層

  const renderSection = () => {
    return <div>{value}</div>;  // 使用頂層變數
  };
  return <div>{renderSection()}</div>;
}
```

### 多欄位監聽模式

```tsx
// ✅ 正確：多個 watch 都在頂層
const watchedField1 = Form.useWatch('field1', form) || 0;
const watchedField2 = Form.useWatch('field2', form) || 0;
const watchedField3 = Form.useWatch('field3', form) || 0;

const total = useMemo(() => {
  return watchedField1 + watchedField2 + watchedField3;
}, [watchedField1, watchedField2, watchedField3]);
```

---

## 五、GIS 地圖功能 Hook 模式

### 統一 Hook 架構

```typescript
// 使用範例
const feature = useXxxMapFeature(map, options);

// 標準回傳介面
interface MapFeatureReturn {
  // 面板狀態
  panelVisible: boolean;
  setPanelVisible: (v: boolean) => void;
  togglePanel: () => void;

  // 圖層狀態
  layerVisible: boolean;
  setLayerVisible: (v: boolean) => void;

  // 高亮標記
  highlightedItem: HighlightedType | null;
  setHighlightedItem: (item: HighlightedType | null) => void;
  clearHighlightedItem: () => void;

  // 組件 Props (memoized)
  panelProps: { ... };
  layerProps: { ... };
  highlightMarkerProps: { ... };
}
```

### 使用方式

```tsx
function MapPage() {
  const devZone = useDevelopmentZoneMapFeature(map, options);
  const urbanRenewal = useUrbanRenewalMapFeature(map, options);

  return (
    <>
      <DevelopmentZonePanel {...devZone.panelProps} />
      <DevelopmentZoneLayer {...devZone.layerProps} />
      <HighlightMarker {...devZone.highlightMarkerProps} />

      <UrbanRenewalPanel {...urbanRenewal.panelProps} />
      ...
    </>
  );
}
```

### 高亮標記規範

| 規範 | 說明 |
|------|------|
| 圖標 | 使用 `L.divIcon` 建立自定義圖標 |
| 動畫 | 實作 pulse 動畫效果 |
| 自動聚焦 | 呼叫 `flyTo` 並開啟 Popup |
| 自動清除 | 15 秒後自動清除計時器 |

### 顏色規範

| 功能類型 | 顏色 | Hex |
|---------|------|-----|
| 都市更新 | 紫色 | #9333ea |
| 開發區 | 綠色 | #16a34a |
| 控制點 | 藍色 | #2563eb |

---

## 六、清除圖徵完整性

**「清除圖徵」按鈕必須清除所有套疊圖層**

```typescript
const handleClearAllFeatures = useCallback(() => {
  // 1. 定位標記
  setLocationMarker(null);
  setHighlightedControlPoint(null);

  // 2. 開發區圖層與高亮
  devZone.setLayerVisible(false);
  devZone.clearHighlightedZone();

  // 3. 都市更新圖層與高亮
  setUrbanRenewalLayerVisible(false);
  setHighlightedUrbanRenewal(null);

  // 4. 查估案件圖層
  setAssessmentLayerVisible(false);

  // 5. 不動產交易圖層
  setRealEstateLayerVisible(false);

  // 6. 底圖套疊圖層
  clearAllOverlays();

  // 7. 工具面板
  setToolContainerVisible(false);
}, [devZone, clearAllOverlays]);
```

**新增圖層時，必須同步更新 `handleClearAllFeatures`**

---

## 七、ESLint 強制規則

### no-restricted-imports

```javascript
// .eslintrc.js
{
  rules: {
    'no-restricted-imports': ['error', {
      patterns: ['axios'],
      message: '請使用 @/api/client 的 apiClient'
    }]
  }
}
```

### no-restricted-syntax

```javascript
{
  rules: {
    'no-restricted-syntax': ['warn', {
      selector: "CallExpression[callee.name='fetch']",
      message: '請使用 apiClient 取代 fetch()'
    }]
  }
}
```

### 合法例外

```typescript
// eslint-disable-next-line no-restricted-syntax -- 健康檢查端點允許使用 GET
const response = await apiClient.get('/health');
```

---

## 八、相關文件

| 文件 | 說明 |
|------|------|
| `CLAUDE.md` 第七節 | 前端 HTTP 客戶端規範 |
| `CLAUDE.md` 第十一節 | GIS 地圖功能 Hook 模式 |
| `CLAUDE.md` 第十二節 | 清除圖徵完整性規範 |
| `docs/specs/FRONTEND_API_MODULARIZATION.md` | API 模組拆分規劃 |
| `docs/specs/SSOT_TYPE_ARCHITECTURE.md` | SSOT 型別架構 |
