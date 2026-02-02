# Showcase Components Skill

> **技能名稱**: 組件展示規範
> **觸發**: `/showcase`, `組件展示`, `Demo`, `文檔`, `預覽`
> **版本**: 1.0.0
> **分類**: project
> **更新日期**: 2026-01-16

**用途**：定義 CK_Showcase 組件展示中心的開發規範
**適用場景**：新增組件展示、撰寫 Demo、更新文檔

---

## 一、組件註冊流程

### 1.1 新增組件到展示中心

1. **建立 Demo 檔案**

   ```
   src/registry/demos/{component-name}/
   ├── index.tsx           # Demo 主檔案
   ├── BasicDemo.tsx       # 基礎用法 Demo
   ├── AdvancedDemo.tsx    # 進階用法 Demo
   └── README.md           # 組件說明
   ```

2. **註冊到 Registry**

   ```typescript
   // src/registry/componentRegistry.ts
   import { lazy } from 'react';

   export const componentRegistry = {
     // ... 現有組件
     'new-component': {
       name: '新組件名稱',
       category: 'ui-components',
       demos: [
         {
           title: '基礎用法',
           component: lazy(() => import('./demos/new-component/BasicDemo')),
         },
         {
           title: '進階用法',
           component: lazy(() => import('./demos/new-component/AdvancedDemo')),
         },
       ],
     },
   };
   ```

### 1.2 組件分類

| 分類              | 說明            | 路徑別名                              |
| ----------------- | --------------- | ------------------------------------- |
| core              | 核心工具組件    | `@ck-shared/core`                     |
| ui-components     | UI 組件         | `@ck-shared/ui-components`            |
| chart-components  | 圖表組件        | `@ck-shared/chart-components`         |
| site-management   | 站台管理模組    | `@ck-shared/site-management-module`   |
| skills-management | Skills 管理模組 | `@ck-shared/skills-management-module` |

---

## 二、Demo 撰寫規範

### 2.1 Demo 結構

```typescript
// BasicDemo.tsx
import React, { useState } from 'react';
import { Card, Space } from 'antd';
import { ComponentName } from '@ck-shared/ui-components';

/**
 * 基礎用法 Demo
 *
 * 說明此 Demo 展示的功能點
 */
export const BasicDemo: React.FC = () => {
  const [value, setValue] = useState('');

  return (
    <Card title="基礎用法">
      <Space direction="vertical" style={{ width: '100%' }}>
        <ComponentName
          value={value}
          onChange={setValue}
        />
        <div>當前值: {value}</div>
      </Space>
    </Card>
  );
};

export default BasicDemo;
```

### 2.2 程式碼展示

使用 `CodeBlock` 組件展示程式碼：

```typescript
import { CodeBlock } from '@/components/preview';

<CodeBlock
  code={`
const example = () => {
  // 程式碼範例
};
  `}
  language="typescript"
/>
```

### 2.3 必要元素

每個 Demo 必須包含：

- [ ] 標題說明
- [ ] 完整可運行的程式碼
- [ ] Props 說明表格
- [ ] 常見用法範例

---

## 三、API 文檔規範

### 3.1 Props 表格格式

```markdown
| 屬性     | 說明       | 類型                      | 預設值  | 必填 |
| -------- | ---------- | ------------------------- | ------- | ---- |
| value    | 當前值     | `string`                  | -       | 是   |
| onChange | 值變更回調 | `(value: string) => void` | -       | 是   |
| disabled | 是否禁用   | `boolean`                 | `false` | 否   |
```

### 3.2 事件說明格式

```markdown
### Events

| 事件名   | 說明           | 回調參數                  |
| -------- | -------------- | ------------------------- |
| onChange | 值變更時觸發   | `(value: string) => void` |
| onFocus  | 獲得焦點時觸發 | `() => void`              |
```

---

## 四、預覽功能

### 4.1 即時預覽

使用 `LiveDemo` 組件提供即時預覽：

```typescript
import { LiveDemo } from '@/components/preview';

<LiveDemo
  component={ComponentName}
  props={{
    value: 'test',
    onChange: console.log,
  }}
/>
```

### 4.2 響應式預覽

```typescript
<LiveDemo
  component={ComponentName}
  responsive={true}  // 啟用響應式預覽
  breakpoints={['mobile', 'tablet', 'desktop']}
/>
```

---

## 五、路由配置

### 5.1 新增組件頁面

```typescript
// src/routes/index.tsx
{
  path: '/component/:id',
  element: <ComponentDetail />,
}
```

### 5.2 分類頁面

```typescript
{
  path: '/category/:id',
  element: <CategoryPage />,
}
```

---

## 六、檢查清單

### 新增組件展示檢查

- [ ] Demo 檔案結構完整
- [ ] 已註冊到 componentRegistry
- [ ] Props 文檔完整
- [ ] 程式碼範例可運行
- [ ] 響應式預覽正常
- [ ] 導航選單已更新

---

**建立日期**：2026-01-16
**維護者**：CK_Showcase 團隊
