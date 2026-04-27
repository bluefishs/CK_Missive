# Wave 1 Services DDD 遷移 Playbook

> **建立**：2026-04-27（v5.9.9）
> **狀態**：ready-to-execute（待 owner 拍板執行時機）
> **範圍**：6 個 bounded context、27 個 service 檔
> **預估工時**：4~6 小時（含驗證），可拆 4 個 sub-batch 各 1~1.5 小時
> **風險評級**：MEDIUM（純 import 改 + re-export stub 相容，但牽涉產品代碼）
> **關聯**：`SERVICE_CONTEXT_MAP.md` §1.2 / `STANDARD_REFERENCE.md` §1.2

---

## 0. 執行前檢查（DON'T SKIP）

```bash
# 1. 確認 main 分支乾淨
git status

# 2. 跑全測試確認 baseline 全綠
cd backend && PYTHONIOENCODING=utf-8 pytest tests/ -q --tb=no 2>&1 | tail -5

# 3. 跑 fitness 確認當前 entropy 比率
bash scripts/checks/run_fitness.sh 2>&1 | grep "service.*entropy" -A 5

# 4. 開新分支（強烈建議，便於回滾）
git checkout -b refactor/services-ddd-wave1
```

**若任一步驟失敗，停止 Wave 1**，先處理問題。

---

## 1. Wave 1 執行範圍

按 SERVICE_CONTEXT_MAP §1.2，6 個 bounded context、27 個檔：

### 1.1 Sub-batch A: document（11 檔，最複雜，建議單獨一個 commit）

```
services/
├── document/
│   ├── __init__.py                          ← 新建（re-export 全部）
│   ├── core.py            ← document_service.py
│   ├── dispatch_linker.py ← document_dispatch_linker_service.py
│   ├── import_logic.py    ← document_import_logic_service.py
│   ├── import_facade.py   ← document_import_service.py
│   ├── filter.py          ← document_filter_service.py
│   ├── statistics.py      ← document_statistics_service.py
│   ├── export.py          ← document_export_service.py
│   ├── processor.py       ← document_processor.py
│   ├── query_filter.py    ← document_query_filter_service.py
│   ├── serial_number.py   ← document_serial_number_service.py
│   └── receiver_normalizer.py ← receiver_normalizer.py
```

舊路徑 `services/document_service.py` 等改為 stub：

```python
# services/document_service.py（改為 stub）
"""Re-export shim — moved to services/document/core.py per Wave 1 DDD migration."""
import warnings
warnings.warn(
    "services.document_service is deprecated; import from services.document.core",
    DeprecationWarning,
    stacklevel=2,
)
from .document.core import *  # noqa: F401,F403
from .document.core import DocumentService  # noqa: F401（顯式 re-export 主類別）
```

### 1.2 Sub-batch B: contract + agency + vendor（9 檔，較簡單）

```
services/
├── contract/
│   ├── __init__.py
│   ├── core.py                  ← project_service.py
│   ├── staff.py                 ← project_staff_service.py
│   ├── analytics.py             ← project_analytics_service.py
│   ├── case_code.py             ← case_code_service.py
│   ├── field_sync.py            ← case_field_sync_service.py
│   └── agency_contact.py        ← project_agency_contact_service.py
├── agency/
│   ├── __init__.py
│   ├── core.py                  ← agency_service.py
│   ├── matching.py              ← agency_matching_service.py
│   └── statistics.py            ← agency_statistics_service.py
└── vendor/
    ├── __init__.py
    └── core.py                  ← vendor_service.py
```

### 1.3 Sub-batch C: audit + notification（7 檔，最簡單，建議首做）

```
services/
├── audit/
│   ├── __init__.py
│   ├── core.py                  ← audit_service.py
│   ├── event_loggers.py         ← audit_event_loggers.py
│   └── mixin.py                 ← audit_mixin.py
└── notification/
    ├── __init__.py
    ├── core.py                  ← notification_service.py
    └── dispatcher.py            ← notification_dispatcher.py
```

---

## 2. 每個 Sub-batch 的標準 SOP（5 步驟）

### Step 1：建立子包目錄

```bash
mkdir -p backend/app/services/<context>
touch backend/app/services/<context>/__init__.py
```

### Step 2：git mv 檔案到子包（保 history）

```bash
git mv backend/app/services/<old_name>.py backend/app/services/<context>/<new_name>.py
```

### Step 3：在原路徑建 stub 檔（向後相容）

```python
# backend/app/services/<old_name>.py
"""DDD Wave 1 migration shim — moved to services/<context>/<new_name>.py.

This stub re-exports the public API for backward compatibility.
Plan to remove after 2026-Q3 once all imports are updated.
"""
import warnings
warnings.warn(
    f"services.<old_name> is deprecated; import from services.<context>.<new_name>",
    DeprecationWarning,
    stacklevel=2,
)
from .<context>.<new_name> import *  # noqa: F401,F403
```

### Step 4：建子包 `__init__.py`（顯式 re-export 主類別）

```python
# backend/app/services/<context>/__init__.py
"""<Context> bounded context — DDD Wave 1 (2026-04-27)."""
from .core import *  # noqa: F401,F403
# 顯式 re-export 重要類別讓 IDE/import 提示能找到
from .core import <MainServiceClass>  # noqa: F401
```

### Step 5：跑測試 + fitness 確認

```bash
cd backend && PYTHONIOENCODING=utf-8 pytest tests/ -q --tb=short -x 2>&1 | tail -20
# 預期：全綠（stub 機制保證舊 import 仍 work）

bash scripts/checks/run_fitness.sh 2>&1 | grep entropy
# 預期：頂層散戶比例下降 N%
```

---

## 3. 執行順序與 commit 切片

| 順序 | Sub-batch | 檔數 | 預估 | Commit Subject |
|---|---|---|---|---|
| **1** | C: audit + notification | 7 | 1h | `refactor: services/{audit,notification} ddd 子包遷移 (wave 1c)` |
| **2** | B: contract + agency + vendor | 9 | 1.5h | `refactor: services/{contract,agency,vendor} ddd 子包遷移 (wave 1b)` |
| **3** | A: document | 11 | 2h | `refactor: services/document ddd 子包遷移 (wave 1a)` |

每個 commit 後**必跑全測試 + fitness**，不通過立刻 revert 該 sub-batch。

**為什麼這個順序**：
- C 最簡單（audit/notification 內部依賴少）→ 驗證 SOP
- B 中等（contract 是業務核心，但 service 已拆得很乾淨）
- A 最複雜（document 11 檔互相依賴）→ 經過 C/B 驗證後才動

---

## 4. 風險與回滾

### 4.1 已知風險

| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| `from services.<old> import <Class>` 在 stub 找不到 | 中 | 開發者煩 | __init__.py 顯式 re-export 主類別 |
| 環形 import（document.core → contract.core → document.core）| 低 | runtime ImportError | sub-batch C 先做（無業務依賴） |
| 測試套件 fixture path 寫死 | 低 | 測試 fail | 跑測試時若 fail 看 `tests/conftest.py` 是否硬編碼 |
| pre-commit pyflakes 拒收 unused import | 低 | commit 失敗 | 用 `# noqa: F401` 標註 |
| **mock.patch 字串路徑指向舊位置** ⚠️ | **高** | 測試 fail（assert called_once 失效） | 見 §4.3 SOP — 必跑測試前批次更新 patch 路徑 |
| Class name collision（同子包 2+ 模組同名 type） | 中 | __init__.py wildcard 失敗 | 見 §4.4 — 改 explicit re-export 主類別策略 |

### 4.3 mock.patch 路徑遷移 SOP（**Wave 1 sub-batch B 實測踩雷後新增**）

mock.patch 替換的是「使用該名稱的 namespace」，不是定義位置。
service 從 `services/foo_service.py` 搬到 `services/foo/core.py` 後：

```python
# foo/core.py 內部
from app.repositories.foo_repository import FooRepository

class FooService:
    def __init__(self, db):
        self.repository = FooRepository(db)  # 引用 foo.core.FooRepository
```

**測試碼若還用舊路徑** patch，會完全失效：

```python
# ❌ 失效（patch 的是 stub 模組的 namespace，service 不引用該 namespace）
with patch("app.services.foo_service.FooRepository") as MockRepo:
    svc = FooService(mock_db)
    assert svc.repository is mock_repo.return_value  # AssertionError

# ✅ 正解（patch service 實際所在的 namespace）
with patch("app.services.foo.core.FooRepository") as MockRepo:
    ...
```

**SOP**：每個 sub-batch 完成 git mv 後立即跑：

```bash
# 找出所有需要更新的 patch 路徑
grep -rn 'patch("app\.services\.<old_name>\.' backend/tests/

# 批次替換（per service）
sed -i 's|app\.services\.foo_service\.\([A-Z]\w*\)|app.services.foo.core.\1|g' \
  backend/tests/unit/test_services/test_foo_service.py
```

修正後 commit 應 include test 檔（這是預期的行為變更，違反「pure stub 零行為變更」原則但**必須**做）。

### 4.4 Class name collision SOP（notification 子包實測）

當子包 2+ 模組定義同名類別（如 `notification.service.NotificationType` 與
`notification.template.NotificationType`），`__init__.py` 不能用 wildcard：

```python
# ❌ 失敗：from .service import * → NotificationType A
#         from .template import * → NotificationType B 覆蓋 A
from .service import *
from .template import *

# ✅ 改採 explicit re-export 主 service 類別策略
from .service import NotificationService
from .template import NotificationTemplateService
# 子類型 NotificationType 等需從具體 .service / .template 路徑 import
```

對應 stub 必須 explicit 列出全部 names：

```python
# stub services/notification_service.py
from .notification.service import (
    NotificationService,
    NotificationType,
    NotificationSeverity,
    CRITICAL_FIELDS,
)
```

### 4.2 回滾 SOP

```bash
# 若該 sub-batch 失敗，最後 commit 為該 batch
git revert HEAD --no-edit
git push  # 若已 push

# 若是工作中發現問題（未 commit）
git checkout backend/app/services/
```

---

## 5. 驗證準則（DoD）

每個 sub-batch 完成必須滿足：

- [ ] `pytest tests/ -q` 全綠
- [ ] `bash scripts/checks/run_fitness.sh` 全綠
- [ ] `python -m py_compile backend/app/main.py` 通過
- [ ] **舊 import 仍 work**（隨機抽 1~2 個其他檔案的 import 跑）
  ```bash
  cd backend && python -c "from app.services.document_service import DocumentService; print('OK')"
  ```
- [ ] services/ 頂層散戶比例**下降**（fitness step 1 entropy）

---

## 6. 完成後的清理（v5.10.0+）

Wave 1 後，等所有業務代碼都改用新路徑（grep 確認 0 引用），再移除 stub：

```bash
# 確認無使用方
grep -rn "from app.services.document_service import" backend/
# 預期 0 行

# 移除 stub
rm backend/app/services/document_service.py
git commit -m "refactor: 移除 wave 1 deprecated stub（document_service.py）"
```

預計 2026-Q3 統一移除（給內部開發者 3 個月遷移時間）。

---

## 7. 範本提取備註（給 lvrland/PileMgmt 等子專案）

本 playbook 本身就是範本資產：

- 任何 monorepo 用 services/ 散戶模式都可套用此 SOP
- 替換 `<context>` 為該 repo 的 bounded context
- 替換 `services/` 為該 repo 的根目錄
- Sub-batch 切片數依該 repo service 數量調整（建議每批 ≤ 12 檔）

引用：`CK_Missive#WAVE_1_SERVICES_MIGRATION_PLAYBOOK_v1.0`

---

## 8. 不該執行 Wave 1 的時機

- 距下次 release 不到 1 週
- 有未完成的 service 層 PR pending
- pre-commit hook 失靈（會跳過守護）
- 開發者 < 2 人在線（緊急問題無人協助）

**強烈建議**：選擇週一上午、有完整 4 小時專注時段執行。
