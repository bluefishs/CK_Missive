---
name: error-handling
description: Error Handling Skill - 錯誤處理指南
version: 1.2.0
category: shared
triggers:
  - 錯誤處理
  - error
  - exception
  - 例外
  - try-catch
  - 紀錄消失
  - 列表清空
  - SATimeoutError
  - 連線池
updated: '2026-02-05'
---

# Error Handling Skill - 錯誤處理指南


## 概述

本 Skill 提供 CK_Missive 專案的錯誤處理最佳實踐，涵蓋前端和後端的錯誤處理策略。

---

## 後端錯誤處理 (FastAPI + SQLAlchemy)

### 1. 標準 API 錯誤回應

```python
from fastapi import HTTPException, status

# 標準錯誤格式
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="錯誤訊息描述"
)

# 帶有額外資訊的錯誤
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={
        "message": "驗證失敗",
        "errors": [
            {"field": "email", "message": "無效的電子郵件格式"}
        ]
    }
)
```

### 2. 交易污染防護 (Transaction Pollution)

**問題**: 未正確處理的 SQLAlchemy 異常會導致交易污染

```python
# ❌ 錯誤 - 會導致交易污染
async def create_document(db: AsyncSession, data: dict):
    try:
        document = Document(**data)
        db.add(document)
        await db.commit()  # 如果這裡失敗...
    except Exception as e:
        # 沒有 rollback，後續操作會失敗
        raise HTTPException(status_code=500, detail=str(e))

# ✅ 正確 - 安全的交易處理
async def create_document(db: AsyncSession, data: dict):
    try:
        document = Document(**data)
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document
    except IntegrityError as e:
        await db.rollback()  # 必須 rollback
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="資料重複或違反約束"
        )
    except Exception as e:
        await db.rollback()  # 必須 rollback
        logger.exception(f"建立文件失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="伺服器內部錯誤"
        )
```

### 3. 安全包裝方法

```python
# utils/safe_db.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def safe_transaction(db: AsyncSession):
    """安全的交易上下文管理器"""
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise

# 使用方式
async def create_with_safety(db: AsyncSession, data: dict):
    async with safe_transaction(db):
        document = Document(**data)
        db.add(document)
        # commit 會在 context 結束時自動執行
    return document
```

### 4. 錯誤日誌記錄

```python
import logging

logger = logging.getLogger(__name__)

# 不同級別的日誌
logger.debug("詳細除錯資訊")
logger.info("一般操作資訊")
logger.warning("警告但不影響運行")
logger.error("錯誤但可恢復")
logger.exception("嚴重錯誤，包含堆疊追蹤")  # 用於 except 區塊
```

---

## 前端錯誤處理 (React + TypeScript)

### 🔴 0. 錯誤時清空列表 - 嚴重問題 (2026-02-04 新增)

**問題描述**: 用戶反映「紀錄儲存後消失」、「列表突然清空」

**根因**: 在 `catch` 區塊中呼叫 `setXxx([])` 清空列表

```typescript
// ❌ 錯誤做法 - 會導致資料消失
const loadItems = useCallback(async () => {
  try {
    const result = await api.getItems();
    setItems(result.items);
  } catch (error) {
    logger.error('載入失敗:', error);
    setItems([]);  // ❌ 危險：清空已存在的資料
  }
}, []);

// ✅ 正確做法 - 保留現有資料
const loadItems = useCallback(async () => {
  try {
    const result = await api.getItems();
    setItems(result.items);
  } catch (error) {
    logger.error('載入失敗:', error);
    // ✅ 不清空列表
    // setItems([]);
    message.error('載入失敗，請重新整理頁面');
  }
}, [message]);
```

**判斷何時可以清空**:
| 場景 | 是否清空 | 說明 |
|------|----------|------|
| 詳情頁局部刷新 | ❌ 不清空 | 用戶已看到資料 |
| 操作後重新載入 | ❌ 不清空 | 操作成功但刷新失敗 |
| 頁面初始載入 | ⚠️ 視情況 | 新頁面無舊資料 |
| 切換實體 | ✅ 可清空 | 避免顯示舊實體資料 |

**強制測試要求**:
```typescript
it('API 錯誤時應該保留現有資料，不清空列表', async () => {
  mockApi.mockResolvedValueOnce({ items: [mockItem] });
  await act(() => result.current.refresh());
  expect(result.current.items).toHaveLength(1);

  mockApi.mockRejectedValueOnce(new Error('Error'));
  await act(() => result.current.refresh());

  // 關鍵斷言：資料仍然保留
  expect(result.current.items).toHaveLength(1);
});
```

### 1. API 請求錯誤處理

```typescript
// services/apiService.ts
export const handleApiError = (error: any): string => {
  if (error.response) {
    // 伺服器回應的錯誤
    const { status, data } = error.response;

    switch (status) {
      case 400:
        return data.detail || '請求參數錯誤';
      case 401:
        // 自動導向登入頁
        authService.logout();
        window.location.href = '/login';
        return '登入已過期，請重新登入';
      case 403:
        return '您沒有權限執行此操作';
      case 404:
        return '請求的資源不存在';
      case 422:
        return formatValidationErrors(data.detail);
      case 500:
        return '伺服器內部錯誤，請稍後再試';
      default:
        return data.detail || '發生未知錯誤';
    }
  } else if (error.request) {
    // 網路錯誤
    return '無法連接伺服器，請檢查網路連線';
  }
  return '發生未知錯誤';
};
```

### 2. Ant Design 訊息提示

```typescript
import { App } from 'antd';

// ✅ 正確 - 使用 App.useApp()
const MyComponent = () => {
  const { message, notification } = App.useApp();

  const handleSubmit = async () => {
    try {
      await apiService.createDocument(data);
      message.success('建立成功');
    } catch (error) {
      message.error(handleApiError(error));
    }
  };
};

// ❌ 錯誤 - 靜態方法無法使用主題
import { message } from 'antd';
message.error('這會產生警告');
```

### 3. 全域錯誤邊界

```typescript
// components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
    // 可發送到錯誤追蹤服務
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Result
          status="error"
          title="頁面發生錯誤"
          subTitle={this.state.error?.message}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              重新整理
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
```

---

## 常見錯誤模式與解決方案

### 模式 1: 時區錯誤

```python
# ❌ 錯誤 - 混用 timezone
from datetime import datetime, timezone

naive_dt = datetime.now()  # naive datetime
aware_dt = datetime.now(timezone.utc)  # aware datetime

# 比較會報錯: can't compare offset-naive and offset-aware datetimes

# ✅ 解決方案
def to_naive_utc(dt: datetime) -> datetime:
    """統一轉為 naive UTC datetime"""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt
```

### 模式 2: N+1 查詢

```python
# ❌ 錯誤 - N+1 查詢問題
documents = await db.execute(select(Document))
for doc in documents.scalars():
    # 每次迴圈都會查詢一次
    print(doc.project.name)

# ✅ 解決方案 - 使用 selectinload
from sqlalchemy.orm import selectinload

documents = await db.execute(
    select(Document).options(selectinload(Document.project))
)
```

### 模式 3: 並發序號衝突

```python
# ❌ 錯誤 - 可能產生重複序號
next_num = await get_max_sequence() + 1
doc.sequence_number = next_num  # 並發時可能重複

# ✅ 解決方案 - 使用 Service 層處理
from app.services.document_number_service import DocumentNumberService

sequence = await DocumentNumberService.get_next_sequence(
    db, year=2026, doc_type="發文"
)
```

---

## 錯誤處理檢查清單

### 後端
- [ ] 所有 DB 操作都有 try-except-rollback
- [ ] 使用標準 HTTPException 格式
- [ ] 敏感資訊不暴露在錯誤訊息中
- [ ] 有適當的日誌記錄
- [ ] 區分業務邏輯錯誤和系統錯誤

### 前端
- [ ] API 請求有統一的錯誤處理
- [ ] 使用 App.useApp() 取得 message
- [ ] 關鍵頁面有 ErrorBoundary
- [ ] 表單驗證有清楚的錯誤提示
- [ ] 網路錯誤有友善的提示訊息

---

## 連線池與資料庫層錯誤處理 (v1.2.0 新增)

### SATimeoutError — 連線池耗盡

```python
from sqlalchemy.exc import TimeoutError as SATimeoutError

async def get_async_db() -> AsyncSession:
    try:
        session = AsyncSessionLocal()
    except SATimeoutError:
        # 連線池耗盡，所有連線都被佔用
        logger.error(f"Database connection pool exhausted. pool_size={settings.POOL_SIZE}")
        raise
```

**觸發條件**: 所有 `pool_size + max_overflow` 個連線都被佔用超過 pool timeout。

**根因排查**:
1. 慢查詢佔用連線 → 檢查 `statement_timeout` 設定
2. 未關閉的 session → 檢查 `finally: await session.close()`
3. 連線池太小 → 調整 `.env` 的 `POOL_SIZE` / `MAX_OVERFLOW`

### statement_timeout — 查詢超時

```python
# database.py 中配置
connect_args={
    "server_settings": {
        "statement_timeout": str(settings.STATEMENT_TIMEOUT),  # 30000ms
    },
    "command_timeout": 60,  # asyncpg 客戶端 60s
}
```

**雙層防護**:
| 層級 | 設定 | 超時值 | 作用 |
|------|------|--------|------|
| PostgreSQL 端 | `statement_timeout` | 30s | 單一 SQL 語句超時 |
| asyncpg 客戶端 | `command_timeout` | 60s | 整個命令超時（含等待） |

**錯誤識別**:
```python
error_msg = str(e).lower()
if "statement_timeout" in error_msg or "canceling statement" in error_msg:
    logger.warning(f"Query exceeded statement_timeout: {e}")
```

### connection_lost — 連線中斷

```python
if "connection_lost" in error_msg:
    logger.warning(f"Database connection lost: {e}")
    # SQLAlchemy pool 會自動 invalidate 並建立新連線
```

**常見原因**: Docker 重啟 PostgreSQL、網路中斷、idle 連線被 PG 回收。

### Pool Event 監控

```python
@event.listens_for(engine.sync_engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    if exception:
        logger.warning(f"Connection invalidated due to: {exception}")
```

---

## 參考資源

- **系統化除錯**: `.claude/skills/_shared/shared/systematic-debugging.md`
- **Bug 調查代理**: `.claude/agents/bug-investigator.md`
- **交易污染詳解**: `.claude/DEVELOPMENT_GUIDELINES.md` (第 272-346 行)
- **連線池配置**: `backend/app/db/database.py` v2.0.0
