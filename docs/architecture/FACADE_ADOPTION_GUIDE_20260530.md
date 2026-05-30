# Facade Adoption Guide (P1.7 v6.12 收口路線, 2026-05-30)

> **狀態**: adoption guide — owner 同意後 v6.12 漸進切換
> **觸發**: v6.10 P1 Phase B 抽象層 9/12 facades 0 importer
> **L51.7 覆盤揭發**: facade 平均 importer = 0 (孤兒 facade 反模式)

---

## 1. 為何 facade 0 importer

v6.10 P1 Phase B 設計 12 facades 統一 bounded context 出口，但實際：
- 9/12 facades **business code 沒 importer**
- 3/12 facades (Memory/Integration/Calendar) 從 cron 內被用，仍 ≤5 importer

**根因**：facade 上線時沒同步切換既有 caller，當時策略是「新 code 用 facade，舊 code 慢遷」，結果新 code 也直 import service。

---

## 2. 12 Facades × Caller 對照表

按 caller 數量排（越多越值得切換）：

| Facade | API caller | 切換 ROI |
|---|---|---|
| AuditFacade | **~15** | 🔴 高 — 廣泛 audit log 散落 |
| DocumentFacade | ~6 | 🟡 中 — 6 endpoints 散查 |
| NotificationFacade | ~6 | 🟡 中 — 6 endpoints 通知散落 |
| CalendarFacade | ~6 | 🟡 中 |
| AIFacade | ~4 | 🟡 中 |
| AgencyFacade | ~2 | 🟢 低 |
| VendorFacade | ~2 | 🟢 低 |
| TenderFacade | ~2 | 🟢 低 |
| WikiFacade | ~1 | 🟢 低 |
| ContractFacade | 0 | ⚪ 設計但 caller 透過其他路徑 |
| MemoryFacade | 0 | ⚪ 只 cron 用 |
| ERPFacade | 0 | ⚪ 透過 ERP module 內部路由 |

---

## 3. 漸進切換 SOP

### 3.1 ROI 順序（v6.12 sprint 規劃）

```
v6.12 Sprint A (~2d): AuditFacade 收口 15 callers
  ├ documents/* audit 寫入點
  ├ taoyuan_dispatch/* audit
  └ erp/* audit (財務變動)

v6.12 Sprint B (~1d): DocumentFacade + NotificationFacade
  ├ documents/{list,crud,delete} 改 facade
  └ system/project_notifications 改 facade

v6.12 Sprint C (~0.5d): CalendarFacade + AIFacade
v6.12 Sprint D (~0.5d): AgencyFacade + VendorFacade + TenderFacade + WikiFacade
```

### 3.2 每個 facade 切換 4 步驟

```python
# Step 1: 確認 facade 涵蓋 caller 需要的功能
# 看 backend/app/services/contracts/facades/{name}.py
# method 是否對應 caller 用法

# Step 2: 改 import
# 原:
from app.services.document.core import DocumentService
svc = DocumentService(db)

# 改:
from app.services.contracts.facades import DocumentFacade
facade = DocumentFacade(db)

# Step 3: 改 method call
# 原:
doc = await svc.get_by_id(123)
# 改:
doc = await facade.get_by_id(123)

# Step 4: 驗證
# - pytest 跑 endpoint 對應 test
# - smoke test endpoint 回傳結構
```

### 3.3 風險

- **facade method 缺對應**：caller 可能用 service 內部複雜 method，facade 未提供 → 需擴 facade
- **transaction 邊界**：facade 與 service 對 db session 處理方式可能不同
- **效能 regression**：facade 多一層可能 import overhead

---

## 4. Fitness step 監測

### 4.1 既有 step 29 contracts_only_import_guard

`backend/scripts/checks/...` 可能已有 audit — 但「禁止 service 直 import」太嚴格，會擋住所有現有 code。

### 4.2 P1.7.1 新增 facade adoption progress audit

未來可加 fitness step：
```python
# scripts/checks/facade_adoption_progress.py
# 計算 12 facades 各自被 import 次數
# 趨勢追蹤 (compare to last month baseline)
# 報告每月增量
```

---

## 5. 推遲決策（owner 確認）

### 選項 A — v6.12 全做（~4 天工作量）
- 12 facades 全切換
- 真實達 v6.10 P1 設計目標
- 但業務功能 0 改善

### 選項 B — v6.12 只做 AuditFacade（~2 天）
- 最高 ROI (15 callers)
- 其他 facades 隨業務修改自然遷移

### 選項 C — 認列 facade 為「孤兒設計」放棄
- 刪除 12 facades + 文件
- 接受跨 context 直 import
- v6.10 P1 Phase B 認列為 over-engineering

**建議**：選 B — 高 ROI 切 AuditFacade，其他維持「new code preferred facade，old code 不動」

---

## 6. Owner 選 A+B 路線（2026-05-30 確認）

收口 A+B 解讀：**A 全 12 facades 漸進切換 + B 優先 AuditFacade 起步**

### 6.1 實作揭發的根本議題：facade method 不對應 caller

實作 AuditFacade 切換時揭發：

```python
# AuditFacade signature (current)
async def record_create(self, actor_id, entity_id, payload, entity_type)
async def record_update(self, actor_id, entity_id, before, after, entity_type)

# 但 caller 真實用法
AuditService.log_auth_event(event_type=..., ip=..., success=...)
AuditService.log_document_change(...)
```

→ **9/12 facade 0 importer 真因不是「沒人切」，是「facade method 不對應業務 caller 真實需求」**

facade 是 v6.10 P1 設計時憑想像寫的，沒對齊既有 service 真實 API。

### 6.2 真實 sprint 排程（v6.12 收口 A+B 路線）

| Sprint | 任務 | 工作量 | 前置 |
|---|---|---|---|
| **A.1 (~1d)** | **facade redesign** — 對齊 caller 真實 API | ~1d | 必要前置！ |
|   | 每個 facade 對應 service method 補齊 | | |
|   | 例: AuditFacade 加 `log_auth_event()` `log_document_change()` 等 | | |
| **A.2 (~2d)** | AuditFacade 切換 15 callers | ~2d | A.1 完成 |
|   | 從 auth/* 開始 (8 callers) | | |
|   | 再 documents/* (5 callers) | | |
|   | 再 ai/document_ai (2 callers) | | |
| **A.3 (~1d)** | DocumentFacade + NotificationFacade 切換 | ~1d | A.1 |
| **A.4 (~0.5d)** | 其他 9 facades 漸進 | ~0.5d | A.1 |

**總工作量**：~4.5 天（A.1 前置 1d + 切換 3.5d）

### 6.3 v6.12 Sprint 排程提案

| 週次 | 內容 |
|---|---|
| v6.12 W1 | A.1 facade redesign (~1d) |
| v6.12 W1-2 | A.2 AuditFacade 切換 (~2d) |
| v6.12 W2 | A.3 Document + Notification (~1d) |
| v6.12 W2 | A.4 其他 facades (~0.5d) |
| v6.12 W3 | 跑 fitness step 61 → 期望 GREEN (≥3 importer avg) |

### 6.4 替代方案：選項 C（放棄 facade）

如果 v6.12 工作量太大，可選 C：
- 刪除 12 facades + 文件
- 認列為 v6.10 P1 over-engineering
- 後續所有跨 context 用直 import
- 工作量：~0.5d（刪 doc + facade module）

**取捨**：facade 抽象層真活 vs 業務開發效率（少 1 層 import）

### 6.5 本批本可做但停的原因

owner 指示「收口 A+B」實際工作量 ~4.5 天，無法 1h 內完成。本批僅：
- 揭發 facade redesign 必要性（A.1 前置）
- 提出明確 v6.12 sprint 排程
- 不強寫切換 code（避免 facade method 不對應而 break）

下次 sprint 啟動需 owner 確認:
- 接受 ~4.5 天投入做 A+B 全收口
- 或改選 C 放棄 facade 抽象層

---

## 6. Refs

- v6.10 P1 Phase B commits
- L51.7 覆盤: `KUNGE_AGENT_CHAIN_REVIEW_20260530.md` 提及 facade 1.7 importer 數據
- 12 facades source: `backend/app/services/contracts/facades/`
- v6.11 整合: `V6_11_INTEGRATED_GOVERNANCE_PROCEDURE_20260530.md`
