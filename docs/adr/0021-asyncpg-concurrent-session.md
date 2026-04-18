# ADR-0021: asyncpg 並行 DB 操作需使用獨立 session

> **狀態**: accepted
> **日期**: 2026-04-19
> **決策者**: 專案 Owner（事件觸發）
> **關聯**: ADR-0019 (structlog), incident 2026-04-19T00:13:30 Telegram 告警

## 背景 — 告警事件

2026-04-19 00:13:30 收到 Telegram 告警：
```
🚨 公文系統健康異常
狀態: unhealthy
資料庫: error
```

**實際根因**（非資料庫故障）：
```
asyncpg.exceptions._base.InterfaceError:
  cannot perform operation: another operation is in progress
sqlalchemy.exc.InterfaceError:
  cannot use Connection.transaction() in a manually started transaction
```

asyncpg 的 connection 是**單飛模式**（single-flight）—
一個 connection 同一時刻只能執行一個 operation。若兩個 async coroutine 同時
對同一 connection 發 query，後者直接拋 `InterfaceError`。

SQLAlchemy 以 session → connection 的形式暴露 asyncpg，session
共用等同 connection 共用。**`asyncio.gather` 多 task 共用同一 session 是
典型反模式**。

## 代碼審計發現（2026-04-19）

`grep -rn "asyncio.gather" backend/app` 共 18 處 gather，其中 **3 個確定
race condition**：

| 位置 | 模式 | 影響端點 |
|---|---|---|
| `agent_orchestrator.py:317` | `gather(preprocess(db), plan_tools(db=db))` | /api/ai/agent/query |
| `digital_twin_service.py:245` | 6 路 closure 共用 `db` | /api/ai/digital-twin/dashboard |
| `graph_unified.py:231` | kg/code/erp/tender 四路共用 `db` | /api/ai/graph/unified-search |

## 決策

### 1. 提供統一 helper — `run_with_fresh_session`

`app/db/database.py`:

```python
async def run_with_fresh_session(fn):
    """為單一 coroutine 提供獨立 session，避免 asyncio.gather 共用造成
    asyncpg 'another operation is in progress' race。"""
    async with AsyncSessionLocal() as session:
        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
```

### 2. 並行 DB 強制規範

> **Rule**: `asyncio.gather` 內若有 2+ 個 task 需要 DB access，**每個 task 必須**
> 透過 `run_with_fresh_session` 建立獨立 session。

**✅ 正確**：

```python
from app.db.database import run_with_fresh_session

hints, plan = await asyncio.gather(
    run_with_fresh_session(lambda s: preprocess(s)),
    run_with_fresh_session(lambda s: plan_tools(s)),
)
```

**❌ 錯誤**（會 race）：

```python
hints, plan = await asyncio.gather(
    preprocess(self.db),
    plan_tools(self.db),  # 共用 self.db
)
```

### 3. 告警去抖動（配套）

`scheduler.health_check_broadcast_job` 加 2-strike threshold — 連續 2 次
（10 分鐘）失敗才告警，避免 transient 連線 invalidate 觸發誤報。

## 後果

### 正面
- **根治 race condition**：asyncpg InterfaceError 不再出現
- **一致性 pattern**：helper 讓開發者有明確可呼叫的 API
- **向後相容**：舊 signature `async def foo(db)` 不變，僅 call site 修改
- **測試驅動**：`test_run_with_fresh_session.py` 4 tests 驗證 helper 行為

### 負面
- **額外 session 建立成本**：每個 fresh session ~1-2ms，但遠低於 race 的 rollback 成本
- **transaction scope 不再共享**：gather 內多 task 各有獨立 transaction，
  無法跨 task 原子性。此限制通常可接受（並行本來意味獨立查詢）。

### 中性
- 仍存在其他 `asyncio.gather` 用法（純 HTTP / 純 LLM call 無 DB）— 不受影響

## 實作（2026-04-19）

- 新增 `app/db/database.py: run_with_fresh_session`
- 修補 `agent_orchestrator.py` / `digital_twin_service.py` / `graph_unified.py`
- 新增 `tests/unit/test_run_with_fresh_session.py`（4 tests）
- `scheduler.py: health_check_broadcast_job` 去抖動 + 恢復通知
- `.claude/CHANGELOG.md` v5.6.1
- 本 ADR

## 未來工作

- **Lint 規則**：考慮增加 grep/ast rule 偵測 `gather` + `db=` 共用模式（防回歸）
- **其他 gather 點審計**：session memory queue 記錄 15 個 gather 位置，逐一檢查是否仍有隱性共用（尤其 `agent_conductor` / `agent_supervisor` / `tender_analytics*`）
