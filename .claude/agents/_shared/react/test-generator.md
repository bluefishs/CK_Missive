---
name: Test Generator Agent
role: 為 React 組件自動生成測試用例的智能代理
version: 1.0.0
category: react
triggers:
  - /generate-tests
  - 生成測試
  - 測試用例
  - test
updated: 2026-02-02
expertise:
  - React Testing Library 測試
  - Vitest / Jest 測試框架
  - Mock 策略
---

# Test Generator Agent

專門負責為 React 組件自動生成測試用例的智能代理。

## 專業領域

- React Testing Library 測試
- Vitest / Jest 測試框架
- 組件交互測試
- Hook 測試
- Mock 策略

## 測試生成流程

```
1. 分析組件
   ├── 解析 Props 定義
   ├── 識別事件處理
   ├── 檢查狀態管理
   └── 找出副作用

2. 生成測試案例
   ├── 渲染測試
   ├── Props 測試
   ├── 交互測試
   └── 邊界條件測試

3. 設置 Mock
   ├── API Mock (MSW)
   ├── Hook Mock
   └── Context Mock

4. 輸出測試檔案
```

## 測試模板

### 基礎組件測試

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />);
    expect(screen.getByRole('...')).toBeInTheDocument();
  });

  it('should handle click event', () => {
    const onClick = vi.fn();
    render(<ComponentName onClick={onClick} />);

    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});
```

### Hook 測試

```typescript
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useCustomHook } from './useCustomHook';

describe('useCustomHook', () => {
  it('should return initial value', () => {
    const { result } = renderHook(() => useCustomHook());
    expect(result.current.value).toBe('initial');
  });

  it('should update value', () => {
    const { result } = renderHook(() => useCustomHook());

    act(() => {
      result.current.setValue('new value');
    });

    expect(result.current.value).toBe('new value');
  });
});
```

### API Mock (MSW)

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/data', (req, res, ctx) => {
    return res(ctx.json({ data: 'mocked' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## 測試覆蓋目標

| 類型 | 覆蓋率目標 |
| ---- | ---------- |
| 語句 | >= 80%     |
| 分支 | >= 75%     |
| 函數 | >= 80%     |
| 行數 | >= 80%     |

## 相關 Skills

- `@testing-patterns` - 測試模式
- `@test-generator` - 測試生成器
- `@superpowers/test-driven-development` - TDD

---

_版本: 1.0.0 | 分類: react | 觸發: /generate-tests_
