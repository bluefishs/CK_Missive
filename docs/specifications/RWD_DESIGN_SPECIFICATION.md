# RWD 響應式設計規範

> **版本**: 1.1.0
> **建立日期**: 2026-01-09
> **最後更新**: 2026-01-22
> **狀態**: 生效中

---

## 一、設計原則

### 1.1 核心原則

1. **Mobile First** - 優先設計手機版，再向上擴展
2. **漸進增強** - 基礎功能在所有設備可用，進階功能在大螢幕展現
3. **一致性** - 統一使用 `useResponsive` Hook，避免各自實作
4. **可維護性** - 集中管理斷點與間距，便於未來調整

### 1.2 適用範圍

本規範適用於：
- 所有前端頁面元件 (`frontend/src/pages/`)
- 共用元件 (`frontend/src/components/`)
- 佈局元件 (`frontend/src/layouts/`)

---

## 二、斷點定義

### 2.1 Ant Design 標準斷點

| 斷點名稱 | 最小寬度 | 典型設備 |
|---------|---------|---------|
| `xs` | 0px | 小型手機 |
| `sm` | 576px | 手機 (橫向) |
| `md` | 768px | 平板 |
| `lg` | 992px | 小型筆電 |
| `xl` | 1200px | 桌面顯示器 |
| `xxl` | 1600px | 大型顯示器 |

### 2.2 語意化斷點映射

| 語意名稱 | 對應斷點 | 條件 |
|---------|---------|------|
| `mobile` | xs, sm | `!screens.md` |
| `tablet` | md | `screens.md && !screens.lg` |
| `desktop` | lg, xl | `screens.lg` |
| `widescreen` | xxl | `screens.xxl` |

### 2.3 使用方式

```typescript
import { useResponsive } from '../hooks/useResponsive';

const MyComponent = () => {
  const { isMobile, isTablet, isDesktop, responsiveValue } = useResponsive();

  // 布林值判斷
  if (isMobile) {
    return <MobileView />;
  }

  // 響應式值
  const padding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  return <div style={{ padding }}>{/* ... */}</div>;
};
```

---

## 三、間距規範

### 3.1 頁面間距

| 元素 | Mobile | Tablet | Desktop |
|------|--------|--------|---------|
| 頁面 padding | 12px | 16px | 24px |
| 區塊間距 (gutter) | 8px | 12px | 16px |
| 卡片內間距 | 12px | 16px | 24px |

### 3.2 標準實作

```typescript
const { responsiveValue } = useResponsive();

// 頁面 padding
const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

// 卡片 gutter
const cardGutter = responsiveValue({ mobile: 8, tablet: 12, desktop: 16 }) as number;
```

### 3.3 預設常數

使用 `RESPONSIVE_SPACING` 常數：

```typescript
import { RESPONSIVE_SPACING } from '../hooks/useResponsive';

// 可用選項: small, medium, large, gutter
const gutter = responsive(RESPONSIVE_SPACING.gutter);
```

---

## 四、元件規範

### 4.1 Table 元件

#### 手機版簡化策略

1. **減少欄位** - 只保留核心資訊
2. **合併顯示** - 多欄合併為單欄
3. **隱藏次要資訊** - 點擊展開詳情

```typescript
const columns = isMobile
  ? [
      {
        title: '主要資訊',
        dataIndex: 'name',
        render: (_, record) => (
          <Space direction="vertical" size={0}>
            <strong>{record.name}</strong>
            <small>{record.subtitle}</small>
          </Space>
        ),
      },
      {
        title: '操作',
        width: 60,
        render: (_, record) => <Button type="link" icon={<EyeOutlined />} />,
      },
    ]
  : [/* 完整桌面版欄位 */];
```

#### 分頁設定

```typescript
<Table
  size={isMobile ? 'small' : 'middle'}
  scroll={{ x: isMobile ? 300 : undefined }}
  pagination={{
    current,
    pageSize: isMobile ? 10 : pageSize,
    showSizeChanger: !isMobile,
    showQuickJumper: !isMobile,
    showTotal: isMobile ? undefined : (total, range) =>
      `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
    size: isMobile ? 'small' : 'default',
  }}
/>
```

### 4.2 Card 元件

```typescript
<Card size={isMobile ? 'small' : 'default'}>
  {/* 內容 */}
</Card>
```

### 4.3 Button 元件

```typescript
<Button
  type="primary"
  icon={<PlusOutlined />}
  size={isMobile ? 'small' : 'middle'}
>
  {isMobile ? '' : '新增項目'}
</Button>
```

### 4.4 Typography 元件

```typescript
<Title level={isMobile ? 4 : 3}>
  {isMobile ? '簡短標題' : '完整標題文字'}
</Title>
```

### 4.5 Input/Select 元件

```typescript
<Input
  placeholder={isMobile ? '搜尋' : '請輸入搜尋關鍵字'}
  size={isMobile ? 'small' : 'middle'}
  style={{ width: isMobile ? '100%' : 300 }}
/>
```

### 4.6 Modal 元件

```typescript
<Modal
  title="標題"
  open={visible}
  width={isMobile ? '95%' : 600}
>
  {/* 內容 */}
</Modal>
```

### 4.7 Form 元件

```typescript
// 手機版單欄，桌面版雙欄
<Row gutter={16}>
  <Col span={isMobile ? 24 : 12}>
    <Form.Item name="field1" label="欄位1">
      <Input />
    </Form.Item>
  </Col>
  <Col span={isMobile ? 24 : 12}>
    <Form.Item name="field2" label="欄位2">
      <Input />
    </Form.Item>
  </Col>
</Row>
```

---

## 五、Grid 佈局規範

### 5.1 Row 元件

```typescript
<Row
  gutter={[cardGutter, cardGutter]}
  align={isMobile ? 'top' : 'middle'}
>
  {/* Col 內容 */}
</Row>
```

**注意**: `align` 屬性只接受 `'top' | 'middle' | 'bottom' | 'stretch'`，不接受 `'start'`。

### 5.2 Col 響應式配置

```typescript
// 標準卡片佈局: 手機1欄、平板2欄、桌面3欄、寬螢幕4欄
<Col xs={24} sm={12} md={8} lg={6}>
  <Card>...</Card>
</Col>

// 統計卡片: 手機2欄、其他4欄
<Col xs={12} sm={6}>
  <Statistic title="總數" value={100} />
</Col>
```

---

## 六、頁面結構範本

### 6.1 標準列表頁面

```tsx
import React, { useState } from 'react';
import { Card, Table, Button, Input, Row, Col, Statistic } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useResponsive } from '../hooks/useResponsive';

const ListPage: React.FC = () => {
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 響應式欄位定義
  const columns = isMobile ? mobileColumns : desktopColumns;

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : 'default'}>
        {/* 統計區塊 */}
        <Row gutter={[8, 8]} align="middle" style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Col xs={12} sm={6}>
            <Statistic title={isMobile ? '總數' : '總項目數'} value={total} />
          </Col>
          <Col xs={12} sm={18} style={{ textAlign: 'right' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '新增'}
            </Button>
          </Col>
        </Row>

        {/* 搜尋區塊 */}
        <Input
          placeholder={isMobile ? '搜尋' : '請輸入搜尋關鍵字'}
          prefix={<SearchOutlined />}
          size={isMobile ? 'small' : 'middle'}
          style={{ width: isMobile ? '100%' : 300, marginBottom: isMobile ? 12 : 16 }}
        />

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: isMobile ? 300 : undefined }}
          pagination={{
            current,
            pageSize: isMobile ? 10 : pageSize,
            total,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            size: isMobile ? 'small' : 'default',
          }}
        />
      </Card>
    </div>
  );
};
```

---

## 七、已完成 RWD 頁面

| 頁面 | 檔案路徑 | 狀態 | 更新日期 |
|------|---------|------|---------|
| 公文管理 | `pages/DocumentPageEnhanced.tsx` | ✅ 完成 | 2026-01-09 |
| 公文篩選 | `components/document/DocumentFilterEnhanced.tsx` | ✅ 完成 | 2026-01-09 |
| 公文列表 | `components/document/DocumentListEnhanced.tsx` | ✅ 完成 | 2026-01-09 |
| 儀表板 | `pages/DashboardPage.tsx` | ✅ 完成 | 2026-01-09 |
| 行事曆 | `pages/CalendarPage.tsx` | ✅ 完成 | 2026-01-09 |
| 廠商列表 | `components/vendor/VendorList.tsx` | ✅ 完成 | 2026-01-09 |
| 機關管理 | `pages/AgenciesPage.tsx` | ✅ 完成 | 2026-01-22 |
| 案件管理 | `pages/ContractCasePage.tsx` | ✅ 完成 | 2026-01-22 |
| 承辦同仁 | `pages/StaffPage.tsx` | ✅ 完成 | 2026-01-22 |
| 桃園派工 | `pages/TaoyuanDispatchPage.tsx` | ✅ 完成 | 2026-01-22 |
| 詳情頁佈局 | `components/common/DetailPage/DetailPageLayout.tsx` | ✅ 完成 | 2026-01-22 |
| 詳情頁標題 | `components/common/DetailPage/DetailPageHeader.tsx` | ✅ 完成 | 2026-01-22 |

---

## 八、待優化頁面

### 優先級 1 (核心頁面)
- [x] 專案管理頁面 (`ContractCasePage.tsx`) - 已完成
- [x] 機關管理頁面 (`AgenciesPage.tsx`) - 已完成
- [ ] 使用者管理頁面 (`UserManagementPage.tsx`)

### 優先級 2 (次要頁面)
- [ ] 登入頁面 (`LoginPage.tsx`)
- [ ] 個人設定頁面 (`ProfilePage.tsx`)
- [ ] 報表頁面 (`ReportsPage.tsx`)

---

## 九、測試檢查清單

### 9.1 必測項目

- [ ] 手機版 (375px) - iPhone SE
- [ ] 手機版 (414px) - iPhone 12
- [ ] 平板版 (768px) - iPad
- [ ] 桌面版 (1024px) - 小螢幕
- [ ] 桌面版 (1440px) - 標準螢幕
- [ ] 寬螢幕 (1920px) - Full HD

### 9.2 功能檢查

- [ ] 表格欄位是否正確隱藏/顯示
- [ ] 按鈕文字是否正確縮減
- [ ] Modal 寬度是否適當
- [ ] 輸入框是否滿版
- [ ] 分頁控制是否簡化

---

## 十、常見問題

### Q1: 何時使用 `isMobile` vs `responsiveValue`?

- **`isMobile`**: 用於條件渲染（顯示/隱藏元件）
- **`responsiveValue`**: 用於取得響應式數值（間距、尺寸）

### Q2: 手機版表格欄位如何選擇?

保留原則：
1. ID/編號 (識別用)
2. 名稱/標題 (主要資訊)
3. 狀態標籤 (必要)
4. 操作按鈕 (僅保留最重要的1-2個)

### Q3: TypeScript 報錯 `align` 屬性?

Row 元件的 `align` 只接受：`'top' | 'middle' | 'bottom' | 'stretch'`
不要使用 `'start'` 或 `'end'`，改用 `'top'` 或 `'bottom'`。

### Q4: Spin 元件 `tip` 警告?

```
[antd: Spin] `tip` only work in nest or fullscreen pattern
```

**解決方案**：Spin 必須包裹子元件（nest 模式）才能使用 `tip`：

```tsx
// ❌ 錯誤
<Spin size="large" tip="載入中..." />

// ✅ 正確
<Spin spinning={loading} tip="載入中...">
  <div style={{ minHeight: 200 }}>
    {!loading && children}
  </div>
</Spin>
```

### Q5: Tag 元件沒有 `size` 屬性?

Tag 元件不支援 `size` 屬性，使用 `style` 控制大小：

```tsx
// ❌ 錯誤
<Tag size="small">標籤</Tag>

// ✅ 正確
<Tag style={{ fontSize: 12 }}>標籤</Tag>
```

---

## 十一、通用元件 RWD 支援

### 11.1 DetailPageLayout

詳情頁佈局元件已整合 RWD 支援：

```typescript
import { DetailPageLayout } from '../components/common/DetailPage';

<DetailPageLayout
  header={{
    title: '案件名稱',
    tags: [{ text: '執行中', color: 'processing' }],
    backPath: '/contract-cases',
  }}
  tabs={[
    { key: 'info', label: <span><InfoIcon /> 基本資訊</span>, children: <InfoTab /> },
    { key: 'staff', label: <span><TeamIcon /> 承辦同仁</span>, children: <StaffTab /> },
  ]}
  loading={loading}
  hasData={!!data}
/>
```

RWD 特性：
- 響應式間距（mobile: 12px, tablet: 16px, desktop: 24px）
- 響應式標題大小（mobile: h4, desktop: h3）
- 響應式 Tab 大小（mobile: middle, desktop: large）
- 手機版自動收起返回按鈕文字

### 11.2 FormPageLayout

表單頁佈局元件支援：
- 統一的返回/保存按鈕佈局
- 響應式表單欄位排列
- Loading 狀態顯示

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-01-22*
