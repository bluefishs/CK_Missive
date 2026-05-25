# Contracts Migration Pattern — v6.10 P1 補充

> **狀態**: accepted（v6.10 P1 補件）
> **日期**: 2026-05-18
> **配套**: ADR-0036 / CONTRACTS_LAYER_GUIDE.md / NAMING_CONVENTIONS.md
> **目的**: 提供 step 32 baseline 84 cross-context imports 漸進收斂的 SOP

---

## 為何需要這份文件

step 29/32 揭發 84 cross-context imports baseline。Phase B 12 facades 已建好，但**改寫 caller 的 SOP 缺失** — 沒有具體 migration pattern 對應「`from app.services.X import Y` → `from app.services.contracts.facades import XFacade`」的標準步驟。

本文件填補此缺口 — **新 PR 改寫前必讀**。

---

## 5 大典型 Migration Patterns

### Pattern 1：取代「function factory」型 import

**Anti-pattern**：

```python
# ai/agent/agent_orchestrator.py:227
async def some_method(self):
    from app.services.memory.diary_service import get_diary_service
    diary_svc = get_diary_service()
    await diary_svc.append("today's event")
```

**改寫**：

```python
# 走 MemoryFacade
async def some_method(self):
    from app.services.contracts.facades import MemoryFacade
    facade = MemoryFacade(self.db)  # 須有 db session
    await facade.append_diary("today's event")
```

**注意**：
- facade 需要 `db` 參數（factory function 可能不需要）
- caller 須持有 `self.db` 或從 context 取得

---

### Pattern 2：取代「class inheritance」型

**Anti-pattern**：

```python
# erp/asset_service.py
from app.services.audit.mixin import AuditableServiceMixin

class AssetService(AuditableServiceMixin):
    AUDIT_TABLE = "assets"

    async def create_asset(self, data, user_id):
        # ... business logic
        await self.audit_create(asset.id, data, user_id=user_id)
```

**改寫**：

```python
# 走 AuditFacade（DI 注入或方法內取）
from app.services.contracts.facades import AuditFacade

class AssetService:
    def __init__(self, db, audit: AuditFacade = None):
        self.db = db
        self.audit = audit or AuditFacade(db, table_name="assets")

    async def create_asset(self, data, user_id):
        # ... business logic
        await self.audit.record_create(
            actor_id=user_id, entity_id=asset.id, payload=data,
        )
```

**收益**：消除 13 處散落 `AuditableServiceMixin` 直繼承。

---

### Pattern 3：取代「直接呼叫 channel push」

**Anti-pattern**：

```python
# memory/autobiography.py
async def send_weekly_summary(self):
    from app.services.integration.line_bot import push_admin_alert
    from app.services.integration.telegram_bot import send_admin_message
    await push_admin_alert("Weekly", body)
    try:
        await send_admin_message(chat_id, body)
    except Exception:
        pass
```

**改寫**：

```python
# 走 MessagingPort + DefaultMessagingAdapter (含多通道 fallback)
async def send_weekly_summary(self):
    from app.services.contracts.adapters import DefaultMessagingAdapter
    msg = DefaultMessagingAdapter()
    await msg.push_admin("Weekly", body)  # 自動 LINE → Telegram → Discord fallback
```

**收益**：取代 autobiography.py 等多處跨通道散打。

---

### Pattern 4：取代「ORM 級 user_id ==」型（RLS 強制）

**Anti-pattern**：

```python
# repositories/calendar_repository.py
async def filter_events(self, user_id):
    query = select(DocumentCalendarEvent).where(
        or_(
            DocumentCalendarEvent.assigned_user_id == user_id,
            DocumentCalendarEvent.created_by == user_id,
        )
    )
```

**改寫**（兩階段）：

```python
# 1. 先用 RLSPort.expand_alias 展開（ADR-0025 alias group）
from app.services.user.alias import expand_user_alias
user_ids = await expand_user_alias(self.db, user_id)

# 2. 改 .in_(user_ids) 取代 == user_id
query = select(DocumentCalendarEvent).where(
    or_(
        DocumentCalendarEvent.assigned_user_id.in_(user_ids),
        DocumentCalendarEvent.created_by.in_(user_ids),
    )
)
```

**長期**（v7.0）：

```python
# RLSPort.apply() 自動處理
from app.services.contracts.adapters import DefaultRLSAdapter
rls = DefaultRLSAdapter(self.db)
query = await rls.apply(
    select(DocumentCalendarEvent), DocumentCalendarEvent,
    user_id, column="created_by",
)
```

**收益**：解 ADR-0025 半接通風險（32/34 repository 仍裸 user_id == 比對）。

---

### Pattern 5：取代「散落 redis.delete()」

**Anti-pattern**：

```python
# 多處 service 散打 cache invalidate
async def update_dispatch(self, id, data):
    # ... business logic
    await redis.delete(f"dispatch:{id}")
    await redis.delete("dispatch_list:*")  # KEYS 風險
    await redis.delete("kanban_data")
```

**改寫**：

```python
# 走 CachePort（SCAN 安全 + cascade invalidation）
from app.services.contracts.adapters import DefaultCacheAdapter

async def update_dispatch(self, id, data):
    # ... business logic
    cache = DefaultCacheAdapter()
    await cache.invalidate_aggregate("dispatch")
    # 自動清 dispatch: / dispatch_list: / kanban: / morning_status: 全部
```

**收益**：取代散落 cache delete 呼叫 + 防 KEYS 阻塞 Redis。

---

## Migration 執行清單（per-PR 規約）

每個改寫 PR 必須：

- [ ] 改寫前跑 `python scripts/checks/facade_only_check.py` 紀錄 baseline N
- [ ] 改寫後跑同命令確認 N-1 或 N-K
- [ ] 加 unit test 確保 facade method 等價於原邏輯
- [ ] PR description 註明「step 32 baseline: N → N-K」
- [ ] 不允許**新增** cross-context import（即使改其他處）

---

## 漸進收斂目標

| 時間點 | step 32 baseline 目標 |
|---|---|
| 2026-05-18（今日 - Phase B 完成） | **84** |
| 2026-06-30（v6.11） | **< 60** |
| 2026-09-30（v7.0 Q3） | **< 20** |
| 2027-Q1（PyPI 化評估） | **< 10** |

---

## Anti-pattern：誤改

❌ **Don't** 改 `services/X/` 內部互相 import（同 context 不算 violation）

```python
# services/ai/agent/agent_orchestrator.py
from app.services.ai.tools.tool_registry import ToolRegistry  # OK！同 ai context
```

❌ **Don't** 改 contracts/ 內部 import

```python
# contracts/facades/calendar.py
from app.services.calendar.event_auto_builder import ...  # OK！facade 內部本來就要 import 業務 module
```

❌ **Don't** 改 `services/base/` 或 `services/strategies/` 內 import（neutral dirs）

---

## 與 fitness step 對齊

- step 29 `contracts_only_import_guard` — 偵測 cross-context
- step 32 `facade_only_check` — 同 step 29 但帶 facade 修法指引
- 兩者 baseline 同為 84，配合本文件可漸進降低

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（5 大 migration patterns + 漸進收斂目標） |
