# 命名規約 SSOT — v1.0

> **狀態**：accepted（v6.10 P1 Phase A）
> **日期**：2026-05-18
> **依據**：5/18 用戶批評「多次強調模組化 結果整體發展卻無依此方向 此也涉及程式命名關聯等機制」
> **FQID**：`CK_Missive#NAMING_CONVENTIONS_v1.0`
> **接通完整度**：L2（含 fitness step 31 自動偵測）
> **目標 consumer**：本 repo + CK_AaaP / hermes-agent / CK_lvrland_* / CK_PileMgmt

---

## 為何需要這份規約

當前命名混亂矩陣（**真實 inventory**）：

| 範疇 | 現況有 3+ 套 | 後果 |
|---|---|---|
| Python module | `auth_service` / `ck_auth` / `authentication` | import 路徑漂移 |
| Folder | `ck-auth/` / `auth/` / `authentication/` | shared-modules 採用困難 |
| ABC Port | `RLSPort` / `IRLS` / `BaseRLS` | 跨 repo 採用認知負擔 |
| Adapter | `DefaultRLSAdapter` / `RLSAdapter` / `RLSImpl` | facade 重構困難 |
| Env var | `GOOGLE_CLIENT_ID` / `TAOYUAN_PROJECT_ID` / `SHADOW_ENABLED` | 跨 repo 衝突風險 |
| FQID | `CK_Missive#0028` / `CK_Missive#ck-auth_v1.0` | consumer 0 採用根因之一 |
| API endpoint | `/api/auth/oauth` / `/api/taoyuan-dispatch` | RESTful 不一致 |
| DB table | `users` / `contract_projects` / `taoyuan_dispatch_orders` | schema migration 衝突 |

**規約不存在 = 模組化空談**。

---

## 一、Python Module / Package 命名

### 規約

| 種類 | 規則 | 範例 |
|---|---|---|
| Python module 檔名 | `snake_case.py` | `auth_service.py` / `kb_embedding.py` |
| Python package（目錄） | `snake_case/` | `services/calendar/` / `core/paths.py` |
| **跨 repo shared package**（資料夾） | `ck-{domain}/` kebab-case | `shared-modules/ck-auth/` |
| **跨 repo shared package**（Python import 名） | `ck_{domain}` snake_case | `from ck_auth import ...` |
| Class | `PascalCase` | `AuthService` / `LineBotService` |
| ABC Interface | `*Port` 後綴 + PascalCase | `RLSPort` / `MessagingPort` / `CachePort` |
| Default 實作 | `Default{Name}Adapter` | `DefaultRLSAdapter` / `DefaultAuditAdapter` |
| 業務 Service | `{Domain}Service` 後綴 | `CalendarService` / `ERPInvoiceService` |
| Repository | `{Domain}Repository` 後綴 | `DocumentRepository` |
| Facade | `{Context}Facade` 後綴 | `CalendarFacade` / `ERPFacade` |

### 禁用 pattern

```python
# ❌ 不用 I 前綴（Java 風格）
class ICache(ABC): ...

# ❌ 不用 Base 前綴給 interface（Base 留給 default impl）
class BaseRLS(ABC): ...

# ❌ 不用 Abstract 前綴
class AbstractAuditor(ABC): ...

# ✅ 統一用 Port 後綴
class CachePort(ABC): ...
class RLSPort(ABC): ...
```

---

## 二、Folder Structure 命名

### 規約

```
專案根/
├── backend/          # snake_case 業務 repo 內部
├── frontend/         # snake_case
├── shared-modules/   # kebab-case — 跨 repo 共用
│   ├── ck-auth/      # kebab-case
│   ├── ck-paths/     # kebab-case
│   ├── ck-contracts/ # kebab-case
│   └── ck-fitness/   # kebab-case
└── docs/             # snake_case
    ├── adr/
    ├── architecture/
    └── archived/
```

**規則**：
- repo 內部目錄：`snake_case`
- 跨 repo 採用單元：`ck-{kebab}`（前綴 `ck-` 識別來源）
- ADR 編號目錄：`NNNN-{kebab}/`（如有）

---

## 三、Env Var Namespace 化

### 規約

```bash
# 規則：CKMODULE_KEY 形式（namespace 化避免跨 repo 衝突）

# ck-auth package
CKAUTH_GOOGLE_CLIENT_ID=xxx
CKAUTH_GOOGLE_CLIENT_SECRET=xxx
CKAUTH_LINE_CHANNEL_ID=xxx
CKAUTH_LINE_CHANNEL_SECRET=xxx
CKAUTH_JWT_SECRET_KEY=xxx
CKAUTH_SESSION_TTL_SECONDS=3600

# ck-observability package
CKOBS_PROMETHEUS_ENABLED=true
CKOBS_SHADOW_ENABLED=1
CKOBS_LOG_LEVEL=INFO

# ck-paths（無 env vars）

# 業務專屬（CK_Missive 主 repo，無 namespace）
TAOYUAN_PROJECT_ID=1
MORNING_REPORT_ENABLED=true
```

### 過渡相容（v6.x 兼容期）

```python
# backend/app/core/config.py
def get_google_client_id() -> str:
    # 優先讀 namespace 版本，fallback 舊版本（v6.x 兼容）
    return os.getenv("CKAUTH_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", "")
```

**Deprecation timeline**：
- v6.10 (5/18~): 兩者並存，舊版印 deprecation warning
- v6.11 (6 月底): 強制 namespace；舊變數移除

---

## 四、FQID 跨 repo 引用規約

### 規約

```
# 標準格式：{source_repo}#{kebab-case_asset}_v{semver}

# 範例
CK_Missive#0028                              # ADR-0028（編號型）
CK_Missive#ck-auth_v1.0                      # shared module package
CK_Missive#CONTRACTS_LAYER_GUIDE_v1.0        # doc
CK_Missive#provider_circuit_breaker_v1.0     # service component
CK_Missive#L29_lesson_v1.0                   # lesson
```

### 禁用 pattern

```yaml
# ❌ 缺 source repo prefix（無法跨 repo 識別）
fqid: "ck-auth_v1.0"

# ❌ 編號型混 kebab（不一致）
fqid: "CK_Missive#ADR0028"

# ❌ 缺 version（無法判 compat）
fqid: "CK_Missive#ck-auth"

# ✅ 標準
fqid: "CK_Missive#ck-auth_v1.0"
fqid: "CK_Missive#0028"
```

---

## 五、API Endpoint 命名

### 規約

```
規則：/api/{kebab-case-resource}/{action}

# Auth
POST /api/auth/google                # OAuth Google
POST /api/auth/line                  # LINE Login
POST /api/auth/logout

# 業務（kebab-case）
POST /api/contract-projects/list     # 不是 contract_projects
POST /api/taoyuan-dispatch/list      # 不是 taoyuan_dispatch
POST /api/document-numbers/create
```

### 例外（合理保留）

- `/api/health`（單字資源不需 hyphen）
- `/api/me`（已固定）
- 內部 SSE：`/api/ai/agent/query` 路徑深度允許

### 已知違規（v6.10 過渡期）

| 違規 | 修法 timeline |
|---|---|
| `/api/taoyuan_dispatch/*` underscore | v6.11 改 kebab |
| `/api/ai_config` | v6.11 |
| `/api/system_notifications/unread-count` | v6.11 |

---

## 六、Database Table / Column 命名

### 規約

| 範疇 | 規則 | 範例 |
|---|---|---|
| Table | `snake_case_plural` | `users` / `contract_projects` / `taoyuan_dispatch_orders` |
| Column | `snake_case` | `created_at` / `user_id` / `line_user_id` |
| Index | `ix_{table}_{column}` | `ix_users_email` |
| Unique | `uq_{table}_{column}` | `uq_users_line_user_id` |
| FK | `fk_{child_table}_{parent_table}_{column}` | `fk_documents_users_created_by` |
| Junction table | `{a}_{b}` 兩 entity 名 alphabetical | `project_user`（不用 user_project） |

### 禁用 pattern

```sql
-- ❌ PascalCase
CREATE TABLE Users ...

-- ❌ 單數 table
CREATE TABLE user ...

-- ❌ 縮寫不一致
CREATE TABLE doc ...   -- documents 才對
CREATE TABLE usr ...   -- users 才對

-- ✅ 標準
CREATE TABLE users ...
CREATE TABLE official_documents ...
```

---

## 七、Frontend (React / TypeScript) 命名

### 規約

| 種類 | 規則 | 範例 |
|---|---|---|
| Component 檔名 | `PascalCase.tsx` | `LoginPanel.tsx` / `OpsDashboard.tsx` |
| Hook 檔名 | `useXxx.ts` | `useAuthGuard.ts` / `useDispatchCacheInvalidator.ts` |
| Service 檔名 | `xxxService.ts` 或 `xxxApi.ts` | `authService.ts` / `taoyuanDispatchApi.ts` |
| Type / Interface | `PascalCase` | `UserInfo` / `LoginFlags` |
| Constant | `UPPER_SNAKE_CASE` | `DEFAULT_CHANNEL_ORDER` / `MORNING_STATUS_KEY` |
| Folder | `camelCase` 或 `kebab-case` | `taoyuanDispatch/` 或 `taoyuan-dispatch/` — **不混用** |

### 既有違規（v6.10 sweep 對象）

- `frontend/src/pages/taoyuanDispatch/` (camelCase) vs `frontend/src/pages/erpQuotation/` (camelCase) — ✅ 一致
- `frontend/src/components/taoyuan/workflow/` vs `frontend/src/components/auth/` — ✅ 一致
- 部分舊 hook 用 `use-xxx.ts` — 需 sweep（v6.11）

---

## 八、Lesson / Failure / Critique 命名

### 規約

```
wiki/memory/{lessons,failures,critiques}/{NNNN}-{kebab-title}.md

# 範例
wiki/memory/lessons/L29-self_evaluator_dict_drift.md
wiki/memory/failures/failure-adr-0025-rls-half-wired.md
wiki/memory/critiques/2026-05-18-cache-invalidate-cascade.md
```

---

## 自動偵測：Fitness Step 31

```bash
python scripts/checks/naming_convention_audit.py
```

偵測：
- Python module 違規（PascalCase 檔名等）
- ABC 不以 `Port` 結尾
- 跨 repo package 不以 `ck-` 開頭
- env var 缺 namespace（v6.11 開始強制）
- API endpoint underscore
- DB table 單數 / PascalCase

---

## 過渡相容（v6.10 → v6.11）

| 違規類 | v6.10 | v6.11 |
|---|---|---|
| env var 缺 namespace | warning | error |
| API endpoint underscore | warning | error |
| ABC 不以 Port 結尾 | warning（已存在保留） | new 必須 |
| 跨 repo package 不以 ck- 開頭 | warning | error |

---

## 採用與貢獻

- 新增 module / endpoint / table / class 前必須符合本規約
- pre-commit hook 跑 step 31 自動偵測（v6.11 上線）
- 違規修正排入 sprint backlog（不阻塞當前 PR）

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（8 大類規約 + 過渡相容） |
