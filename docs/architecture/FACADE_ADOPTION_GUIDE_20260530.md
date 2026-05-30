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

## 6. Refs

- v6.10 P1 Phase B commits
- L51.7 覆盤: `KUNGE_AGENT_CHAIN_REVIEW_20260530.md` 提及 facade 1.7 importer 數據
- 12 facades source: `backend/app/services/contracts/facades/`
- v6.11 整合: `V6_11_INTEGRATED_GOVERNANCE_PROCEDURE_20260530.md`
