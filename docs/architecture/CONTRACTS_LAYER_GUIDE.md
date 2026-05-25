# Bounded Context Contract Layer 使用指南

> **版本**：v1.0（2026-05-18）
> **狀態**：accepted
> **FQID**：`CK_Missive#CONTRACTS_LAYER_GUIDE_v1.0`
> **目標 consumer**：CK_AaaP / hermes-agent / CK_lvrland_* / CK_PileMgmt / CK_KMapAdvisor
> **接通完整度**：L2（程式碼 + RLSPort 已有 default impl + 整合驗證）

---

## 為何需要這層

CK_Missive 的 12 bounded contexts（document / contract / agency / vendor / audit / notification / erp / integration / tender / calendar / wiki / system / backup）目前是「**按名稱分類**」，跨 context 仍直接 import 內部 module，違反 DDD anti-corruption layer 原則。

5/18 整體架構覆盤發現 3 個結構性反模式：

1. **散落 audit_mixin** — 13 處直接 `from app.services.audit.mixin import AuditMixin`
2. **散落 expand_user_alias** — 11 個 repository 各自 import `services/user/alias.py`
3. **散落 LINE/Telegram/Discord** — `autobiography.py` 等 module 跨打三 channel

contracts/ 是這些反模式的**統一收斂處**。

---

## 4 個 Port + 預設實作

```
backend/app/services/contracts/
├── __init__.py                          ← 對外出口（4 個 Port）
├── ports/
│   ├── messaging.py    MessagingPort    ← LINE/Telegram/Discord 統一
│   ├── audit.py        AuditPort        ← 取代散落 audit_mixin
│   ├── cache.py        CachePort        ← 後端 cache cascade（前端 useDispatchCacheInvalidator 對等）
│   └── rls.py          RLSPort          ← 封 expand_user_alias + apply_*_rls
└── adapters/
    └── rls_default.py  DefaultRLSAdapter ← RLSPort 預設實作（已驗證）
```

---

## 對外採用模式

### 1. CK_Missive 內部呼叫（規範）

```python
# ❌ Bad — 直 import services/user/alias.py
from app.services.user.alias import expand_user_alias
user_ids = await expand_user_alias(db, user_id)

# ✅ Good — 走 Port
from app.services.contracts.adapters.rls_default import DefaultRLSAdapter
rls = DefaultRLSAdapter(db)
user_ids = await rls.expand_alias(user_id)
```

### 2. 跨 repo 採用（CK_AaaP / lvrland / pile）

最小代價採用範式：

```python
# 在 consumer repo 內：
# Option A：拷貝 ports/ 內容 + 自行寫 adapter（重）
# Option B：直接 git submodule CK_Missive/contracts/ → shared-modules（推薦）
# Option C：抽出 contracts/ 成獨立 PyPI package `ck-contracts`（v7.0 規劃）

# 採用後：
from ck_contracts import MessagingPort, AuditPort, CachePort, RLSPort

class MyServiceLvrLand:
    def __init__(self, audit: AuditPort, msg: MessagingPort):
        self.audit = audit
        self.msg = msg
```

### 3. 配合 ADR-0020 Phase 1（Hermes bridge）

ck-missive-bridge skill 應對應 contracts/ Port 暴露 tool：

```json
{
  "name": "rls_expand_alias",
  "description": "Expand user_id to alias group (ADR-0025)",
  "input_schema": {"user_id": "int"},
  "backend_path": "/api/contracts/rls/expand"
}
```

讓 Hermes 跨 repo 呼叫時走 Port，不直接戳 CK_Missive 業務 service。

---

## 落地路線

### Phase 1 — CK_Missive 內部接通（v6.10）
- [x] contracts/ 骨架 + 4 Port + RLSPort default impl（5/18 完成）
- [ ] 寫 MessagingAdapter 預設實作（封 line_bot/telegram_bot/discord_bot）
- [ ] 寫 AuditAdapter 預設實作（取代 13 處 audit_mixin）
- [ ] 寫 CacheAdapter 預設實作（接通 Redis 後端 cache）
- [ ] 修 calendar_repository / notification_repository / ERP 11 處 user_id 比對改用 RLSPort
- [ ] 加 fitness step 29：`contracts_only_import_guard.py` 禁直 import 跨 context 內部

### Phase 2 — 跨 repo 推（v6.11 ~ v7.0）
- [ ] CK_AaaP 採用 `MessagingPort`（hermes-stack 統一 channel）
- [ ] lvrland/pile 採用 `AuditPort`（首批 consumer）
- [ ] contracts/ 抽出成 git submodule `shared-modules/contracts/`
- [ ] `consumers.yml` 加 `FQID: CK_Missive#CONTRACTS_LAYER_GUIDE_v1.0` 推送通知

### Phase 3 — PyPI 化（v7.x）
- [ ] 評估抽 `ck-contracts` 為 internal PyPI package
- [ ] 每月 owner check-in：consumer 採用率（healthy ≥ 4/7 → 真活宣告）

---

## 規範

### A. 新增 service / repository 強制檢查

任何新 user-scoped service / repository 必須使用 `RLSPort.apply()` 而非自己寫 `.where(user_id == ...)`。違反 → step 29 fail。

### B. 跨 context import 禁令

```python
# ❌ Bad — context 內部直接 import 另一 context 內部
from app.services.calendar.event_auto_builder import build_event

# ✅ Good — 走 context facade（v6.10 P2 規劃寫）
from app.services.contracts.facades.calendar import CalendarFacade
event = await CalendarFacade(db).build_event(...)
```

### C. ADR 自評須註明接通完整度

新 ADR 從 proposed → accepted 必須在 metadata 註明使用哪些 Port：

```yaml
contracts_used:
  - RLSPort
  - AuditPort
```

---

## 與既有規範對齊

| 既有規範 | 對應 contracts/ |
|---|---|
| ADR-0025 Identity Unification | `RLSPort` 為唯一入口 |
| ADR-0028 錯誤合約化 | `AuditPort` 統一 silent failure 紀錄 |
| ADR-0020 AaaP Phase 1 | `MessagingPort` 為 Hermes bridge 標準 |
| MODULARIZATION_STANDARDS_v1 §1.3 | contracts/ 為「跨 context 隔離」基石 |
| RETRO_20260515_UPDATE §3 G2 | 解 ck-missive-bridge 24% 工具暴露率（透過 Port 暴露 facade） |

---

## 採用 FAQ

**Q1**：為什麼不用 dependency injection container？
A：FastAPI 已有 `Depends()`，contracts/ Port 與 `Depends()` 相容。Phase 2 加 `get_rls()` / `get_audit()` 工廠。

**Q2**：4 個 Port 是否會過度設計？
A：每個 Port 對應一個**已知反模式**（13 處 audit_mixin 散落 / 11 處 user_id 散落等）。沒有解決現實問題的 Port 不會加。

**Q3**：跨 repo 採用後升級成本？
A：因為是 ABC interface，升級 = 在 consumer 改 adapter 實作即可。Port signature 一年內保證向後相容。

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（含 4 Port + RLSPort default impl） |
