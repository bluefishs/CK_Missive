---
name: TDD 測試驅動開發工作流程
description: 遵循 RED-GREEN-REFACTOR 循環的測試驅動開發方法論，確保 80%+ 測試覆蓋率
version: 1.0.0
category: shared
triggers:
  - /tdd
  - 測試驅動
  - TDD
  - 先寫測試
updated: 2026-02-03
author: everything-claude-code (adapted)
---

# TDD 測試驅動開發工作流程

強制執行先寫測試的開發方法論。

## 核心原則

**測試必須在實作之前撰寫。**

TDD 循環: RED → GREEN → REFACTOR

- **RED**: 撰寫會失敗的測試
- **GREEN**: 實作最小程式碼使測試通過
- **REFACTOR**: 改善程式碼品質

**絕不跳過 RED 階段。**

## TDD 工作流程

### 1. 定義介面 (Scaffold)

```typescript
// 先定義輸入/輸出類型
interface CalculatorInput {
  values: number[];
  operation: 'sum' | 'average' | 'max';
}

interface CalculatorResult {
  value: number;
  count: number;
}
```

### 2. 撰寫失敗測試 (RED)

```typescript
describe('Calculator', () => {
  it('should calculate sum of values', () => {
    const input: CalculatorInput = {
      values: [1, 2, 3],
      operation: 'sum',
    };

    const result = calculate(input);

    expect(result.value).toBe(6);
    expect(result.count).toBe(3);
  });
});
```

### 3. 執行測試確認失敗

```bash
npm test -- --watch
# 確認測試失敗
```

### 4. 實作最小程式碼 (GREEN)

```typescript
function calculate(input: CalculatorInput): CalculatorResult {
  const { values, operation } = input;

  let value: number;
  switch (operation) {
    case 'sum':
      value = values.reduce((a, b) => a + b, 0);
      break;
    // ... 其他操作
  }

  return { value, count: values.length };
}
```

### 5. 重構 (REFACTOR)

```typescript
// 提取常數和改善可讀性
const OPERATIONS = {
  sum: (arr: number[]) => arr.reduce((a, b) => a + b, 0),
  average: (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length,
  max: (arr: number[]) => Math.max(...arr),
} as const;

function calculate(input: CalculatorInput): CalculatorResult {
  const value = OPERATIONS[input.operation](input.values);
  return { value, count: input.values.length };
}
```

### 6. 驗證覆蓋率

```bash
npm test -- --coverage
# 確認達到 80%+ 覆蓋率
```

## 覆蓋率目標

| 類型           | 最低覆蓋率 |
| -------------- | ---------- |
| 一般程式碼     | 80%        |
| 財務計算       | 100%       |
| 身份驗證       | 100%       |
| 安全關鍵程式碼 | 100%       |
| 核心業務邏輯   | 100%       |

## 必須涵蓋的測試類型

### 單元測試

- Happy path (正常路徑)
- Edge cases (邊界情況)
- Boundary conditions (邊界條件)
- Error handling (錯誤處理)

### 整合測試

- API 端點
- 資料庫操作
- React 元件互動

### E2E 測試

- 關鍵使用者流程
- 業務關鍵路徑

## 邊界情況清單

- [ ] null/undefined 輸入
- [ ] 空陣列/空物件
- [ ] 無效類型
- [ ] 邊界值 (0, -1, MAX_INT)
- [ ] 錯誤路徑
- [ ] 競態條件
- [ ] 大型資料集
- [ ] 特殊字元

## Mock 模式範例

```typescript
// Mock 外部服務
jest.mock('@/services/api', () => ({
  fetchData: jest.fn().mockResolvedValue({ data: 'mock' }),
}));

// Mock 資料庫
const mockDb = {
  query: jest.fn().mockResolvedValue([{ id: 1 }]),
};
```

## 反模式 (避免)

1. **測試實作細節**: 測試行為，非內部狀態
2. **測試相依性**: 每個測試應獨立執行
3. **過度 Mock**: 只 Mock 外部依賴
4. **跳過 RED 階段**: 永遠先確認測試失敗

## 何時使用

- 實作新功能
- 新增函數或元件
- Bug 修復前先寫測試
- 重構現有程式碼
- 建構核心業務邏輯

## 相關指令

- `/plan` - 規劃工作流程
- `/code-review` - 程式碼審查
- `/test-coverage` - 檢查測試覆蓋率
