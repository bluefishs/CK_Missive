# 組件重構檢查清單

> **目的**：確保 React 組件拆分或重構後，所有功能保持完整
> **建立日期**：2026-01-19
> **觸發時機**：P3-xxx 組件拆分任務、大型組件重構

---

## 一、重構前準備 (Phase 1)

### 1.1 功能盤點

- [ ] **列出所有 UI 元素**
  - 按鈕 (onClick handler)
  - 輸入欄位 (value, onChange)
  - 下拉選單 (options, onSelect)
  - 顯示區塊 (條件渲染)

- [ ] **記錄狀態依賴**
  - useState 變數列表
  - useCallback 函數列表
  - useMemo 計算值列表
  - props 傳入項目

- [ ] **截圖當前行為**
  - 各種操作流程截圖
  - 錯誤狀態截圖
  - 載入狀態截圖

### 1.2 相依性分析

```bash
# 搜尋哪些檔案 import 此組件
grep -r "import.*ComponentName" frontend/src/
```

- [ ] 記錄所有消費者 (consumer) 檔案
- [ ] 確認 props interface 變更影響範圍

---

## 二、重構執行 (Phase 2)

### 2.1 狀態管理決策

**決策樹**：

```
狀態是否被多個組件使用？
├─ 是 → 提升至共同父組件或使用 Context
└─ 否 → 狀態可保留在當前組件
         ├─ 是否需要被父組件控制？
         │   ├─ 是 → 傳入 value/onChange props (受控組件)
         │   └─ 否 → 維持內部狀態
         └─ 是否有 callback 需要傳遞？
             └─ 是 → 確保 callback 正確傳遞
```

### 2.2 常見錯誤模式

#### 錯誤 1：狀態斷裂

```tsx
// ❌ 錯誤：父組件的 setInputs 無法更新子組件的 inputs
// 父組件
const [inputs, setInputs] = useState({});
const handleFill = () => setInputs({ value: 'new' }); // 無效！
<ChildPanel />  // 子組件有自己的 inputs state

// ✅ 正確方案 A：傳遞狀態給子組件
<ChildPanel inputs={inputs} setInputs={setInputs} />

// ✅ 正確方案 B：將功能移至子組件內
// 把 handleFill 按鈕和邏輯都移到 ChildPanel 中
```

#### 錯誤 2：遺漏 callback 傳遞

```tsx
// ❌ 錯誤：子組件需要 onLocationFound 但未傳遞
<CoordinatePanel onError={setError} />

// ✅ 正確：傳遞所有必要 callback
<CoordinatePanel
  onError={setError}
  onLocationFound={onLocationFound}
  currentMapCenter={currentMapCenter}
/>
```

#### 錯誤 3：Props 類型不一致

```tsx
// ❌ 錯誤：原本是 { lat, lon }，拆分後變成 { lat, lng }
interface OldProps {
  center: { lat: number; lon: number };
}
interface NewProps {
  center: { lat: number; lng: number }; // lng vs lon
}

// ✅ 正確：保持類型一致，或提供轉換層
```

### 2.3 拆分步驟

1. [ ] 建立子組件檔案 (`ComponentName.tsx`)
2. [ ] 定義 Props interface (包含所有必要 props)
3. [ ] 複製相關 state 和 callbacks
4. [ ] 複製 JSX 渲染邏輯
5. [ ] 更新父組件傳遞 props
6. [ ] 更新 index.ts 匯出

---

## 三、重構後驗證 (Phase 3)

### 3.1 功能逐項驗證

對照 Phase 1 盤點的 UI 元素，逐一測試：

| 元素類型 | 驗證項目                  |
| -------- | ------------------------- |
| 按鈕     | onClick 觸發正確函數      |
| 輸入欄位 | value 顯示、onChange 更新 |
| 下拉選單 | 選項載入、選擇後狀態變更  |
| 條件渲染 | 各條件下正確顯示/隱藏     |

### 3.2 TypeScript 檢查

```bash
# 確保無編譯錯誤
cd frontend && npm run type-check
```

### 3.3 視覺比對

- [ ] 與 Phase 1 截圖比對，確認 UI 一致
- [ ] 測試響應式佈局（如有）

---

## 四、案例研究：CoordinatePanel 重構問題

### 問題描述

P3-002 組件拆分後，「插入」按鈕失效

### 根因分析

```
拆分前：
┌─────────────────────────────────────┐
│ QuickLocationPanel                   │
│ ├─ inputs (state)                   │
│ ├─ handleFillFromCenter (callback)  │
│ ├─ 「插入」按鈕 ──────────────────────┼──→ handleFillFromCenter
│ └─ 輸入欄位 ←────────────────────────┼──← inputs
└─────────────────────────────────────┘

拆分後（錯誤）：
┌─────────────────────────────────────┐
│ QuickLocationPanel                   │
│ ├─ inputs (state) ← 未使用          │
│ ├─ handleFillFromCenter ← 更新父組件 inputs
│ └─ 「插入」按鈕 ──────────────────────┼──→ handleFillFromCenter
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ CoordinatePanel                      │
│ ├─ inputs (獨立 state) ← 實際顯示   │
│ └─ 輸入欄位 ←────────────────────────┼──← 自己的 inputs
└─────────────────────────────────────┘

問題：父組件更新自己的 inputs，但子組件的 inputs 不受影響
```

### 正確解法

```
拆分後（正確）：
┌─────────────────────────────────────┐
│ QuickLocationPanel                   │
│ └─ currentMapCenter ─────────────────┼──→ 傳給子組件
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ CoordinatePanel                      │
│ ├─ inputs (state)                   │
│ ├─ currentMapCenter (prop)          │
│ ├─ handleFillFromCenter ← 更新自己的 inputs
│ ├─ 「插入」按鈕 ──────────────────────┼──→ handleFillFromCenter
│ └─ 輸入欄位 ←────────────────────────┼──← inputs
└─────────────────────────────────────┘

解法：把按鈕和狀態放在同一個組件中
```

---

## 五、重構影響分析工具

### 5.1 手動分析流程

```bash
# 1. 找出所有使用該組件的地方
grep -rn "import.*QuickLocationPanel" frontend/src/

# 2. 找出該組件的所有 props
grep -n "interface.*Props" frontend/src/components/Map/QuickLocationPanel.tsx

# 3. 找出所有 useState 和 useCallback
grep -n "useState\|useCallback\|useMemo" frontend/src/components/Map/QuickLocationPanel.tsx
```

### 5.2 影響範圍確認

- [ ] 列出所有會受影響的檔案
- [ ] 評估變更是否需要更新這些消費者
- [ ] 若 props interface 變更，更新所有使用處

---

## 六、Checklist 模板

### 組件拆分 Checklist

**組件名稱**：******\_\_\_\_******
**拆分日期**：******\_\_\_\_******
**執行者**：******\_\_\_\_******

#### Phase 1：準備

- [ ] UI 元素盤點完成
- [ ] 狀態依賴記錄完成
- [ ] 截圖留存完成

#### Phase 2：執行

- [ ] Props interface 定義完成
- [ ] 狀態管理決策完成
- [ ] 子組件建立完成
- [ ] 父組件更新完成

#### Phase 3：驗證

- [ ] 所有按鈕功能正常
- [ ] 所有輸入欄位功能正常
- [ ] 所有下拉選單功能正常
- [ ] TypeScript 編譯無錯誤
- [ ] 視覺比對一致

---

**最後更新**：2026-01-19
