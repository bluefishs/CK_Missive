---
trigger_keywords: [可訪問性, accessibility, a11y, WCAG, ARIA, 鍵盤導航, keyboard, screen reader]
version: "1.0.0"
date: "2026-02-21"
---

# 可訪問性 (Accessibility) 規範

## WCAG 2.1 AA 基線要求

### 感知性 (Perceivable)
- 所有非文字內容需有替代文字 (`alt`, `aria-label`)
- 色彩對比度至少 4.5:1 (普通文字) / 3:1 (大文字)
- 不僅依賴顏色傳達資訊（需搭配圖標或文字）

### 可操作性 (Operable)
- 所有功能可透過鍵盤操作
- 焦點順序邏輯正確 (`tabIndex` 使用規範)
- 無鍵盤陷阱（用戶可離開任何元件）
- 動態內容提供暫停/停止機制

### 可理解性 (Understandable)
- 錯誤訊息清楚描述問題與解決方法
- 表單欄位有明確 label 關聯
- 操作前提供確認（不可逆操作）

### 穩健性 (Robust)
- HTML 語意正確（使用適當的 heading 層級）
- 自訂元件提供正確的 ARIA role/state

## ARIA 屬性使用規範

### 必要 ARIA 屬性

```tsx
// 互動按鈕
<Button aria-label="刪除公文" onClick={handleDelete}>
  <DeleteOutlined />
</Button>

// 載入狀態
<Spin spinning={loading} aria-busy={loading} aria-label="載入中">
  {content}
</Spin>

// 表格
<Table
  aria-label="公文列表"
  role="table"
  columns={columns}
  dataSource={data}
/>

// 導航
<nav aria-label="主導航">
  <Menu mode="inline" items={menuItems} />
</nav>

// 搜尋
<Input.Search
  aria-label="搜尋公文"
  placeholder="輸入關鍵字..."
/>

// 對話框
<Modal
  title="確認刪除"
  aria-describedby="delete-description"
>
  <p id="delete-description">此操作無法復原</p>
</Modal>
```

### ARIA 規則

| 規則 | 說明 |
|------|------|
| 第一規則 | 優先使用原生 HTML 語意，不用 ARIA |
| 第二規則 | 不改變原生語意（`<h2 role="tab">` 禁止） |
| 第三規則 | 互動元素必須可鍵盤操作 |
| 第四規則 | 不對可見焦點元素用 `role="presentation"` |
| 第五規則 | 互動元素必須有可存取名稱 |

## 鍵盤導航模式

### 通用快捷鍵

| 鍵位 | 行為 |
|------|------|
| `Tab` | 前進到下一個可聚焦元素 |
| `Shift+Tab` | 後退到上一個可聚焦元素 |
| `Enter/Space` | 啟動按鈕/連結 |
| `Escape` | 關閉 Modal/Drawer/Dropdown |
| `Arrow Keys` | Menu/Tree/Table 內導航 |

### 自訂元件鍵盤支援

```tsx
// 自訂卡片元件需要鍵盤支援
const ClickableCard = ({ onClick, children }) => (
  <div
    role="button"
    tabIndex={0}
    onClick={onClick}
    onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    }}
    aria-label="點擊查看詳情"
  >
    {children}
  </div>
);
```

## Ant Design a11y 最佳實踐

### 已內建支援
- `Button`: 自動 focus 管理
- `Input`: 支援 `aria-label`, `aria-describedby`
- `Modal`: 自動 focus trap + Escape 關閉
- `Dropdown`: Arrow key 導航
- `Table`: 原生 table 語意

### 需手動補強
- **Icon-only Button**: 加 `aria-label`
- **自訂 Tooltip trigger**: 加 `aria-describedby`
- **動態更新區域**: 加 `aria-live="polite"`
- **分頁切換**: 加 `aria-current="page"`
- **Tab 切換**: Ant Tabs 已支援，確認 `tabIndex` 正確

### 常見修復模式

```tsx
// Spin 包裹（Ant 5.x 警告修復）
<Spin spinning={loading}>
  <div>{content}</div>  {/* Spin tip 需包裹子元素 */}
</Spin>

// Table 空狀態
<Table
  locale={{ emptyText: <Empty description="沒有資料" /> }}
  aria-label="公文列表"
/>

// 確認對話框
Modal.confirm({
  title: '確認刪除',
  content: '此操作無法復原，確定要刪除嗎？',
  okText: '確認刪除',
  cancelText: '取消',
  okButtonProps: { danger: true, 'aria-label': '確認刪除' },
});
```

## axe-core 自動化測試

### 安裝與配置

```bash
npm install --save-dev @axe-core/react axe-core
```

### 開發模式整合

```tsx
// main.tsx (僅開發模式)
if (import.meta.env.DEV) {
  import('@axe-core/react').then((axe) => {
    axe.default(React, ReactDOM, 1000);
  });
}
```

### E2E 測試整合 (Playwright)

```typescript
// e2e/accessibility.spec.ts
import AxeBuilder from '@axe-core/playwright';

test('document list page should be accessible', async ({ page }) => {
  await page.goto('/documents');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});
```

## CK_Missive 已完成項目 (v1.55.0)

- 24 個元件已補強 ARIA 語意屬性
- `DocumentDetailPage` 拆分後改善焦點管理
- Phase 6A 規劃：鍵盤導航 + axe-core 自動化測試
