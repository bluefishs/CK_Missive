# CK_Missive 架構標準化範本（作為他案參考依據）

> **版本**：v1.0（2026-04-25）
> **狀態**：accepted（作為 CKProject 其他 repo 的架構基準）
> **範圍**：CK_lvrland_Webmap / CK_lvrland_dataform / CK_PileMgmt / CK_KMapAdvisor / CK_Showcase
> **治理**：若與 `CK_AaaP/CONVENTIONS.md` 衝突，以 CONVENTIONS.md 為準（跨 repo 層級更高）
> **維護**：每月架構覆盤時同步（`@每月架構覆盤`）

本文件抽象 CK_Missive v5.9.5 的生產級架構決策，作為其他 CKProject 子專案的參考實作。
只收錄**有經驗證據的模式**（經過一次以上 P0 事故淬鍊），避免 cargo cult。

---

## 0. 核心理念（Prime Directive）

1. **領域驅動（DDD）取代行數驅動** — 檔案該分不該分，看職責邊界不看行數
   - 1074 行但單一領域完整實作 → **不拆**
   - 200 行但混三領域邏輯 → **必拆**

2. **SSOT 聲明必有 integration test 鎖定** — 配置若無生產讀取點，就是 dead config
   - 單元測試只能測「配置能讀」，不能測「配置有效」
   - 必配 integration test 驗證配置→行為鏈路

3. **證據優於聲稱** — 所有「效能改善」「bug 修復」必須附 shadow_trace.db / metric snapshot

4. **reversible by default** — 每個 commit 獨立 bisectable，每個設定有明確回滾指令

---

## 1. 服務層 DDD 組織原則

### 1.1 Bounded Context 劃分準則

判斷一個功能該不該自成子包（`services/xxx/`）：

| 訊號 | 該獨立子包 |
|---|---|
| 有自己的 domain events | ✅ |
| 有獨立的 Repository + Model 群 | ✅ |
| 可被其他 context 透過明確 API 呼叫（而非偷抓內部方法） | ✅ |
| 可獨立部署（理論上） | ✅ |
| 跨 context 的業務規則需明確 anti-corruption layer | ✅ |
| 功能小但跨 3+ 個既有 context | ❌（做成共享 util）|

### 1.2 目標結構（CK_Missive 的成熟形態）

```
services/
├── base/                ← BaseService / ServiceResponse / audit Mixin
├── document/            ← 公文 bounded context（收發文/附件/編號）
├── contract/            ← 承攬案件（PMCase + ContractProject + project_code）
├── agency/              ← 機關 + 委託單位
├── vendor/              ← 協力廠商
├── erp/                 ← 財務（報價/請款/開票/費用/資產/帳本）
├── pm/                  ← 專案管理（里程碑/甘特/人員）
├── taoyuan/             ← 桃園派工（區域性 subsystem）
├── tender/              ← 標案（PCC/ezbid/g0v）
├── ai/                  ← AI 核心（agent/tools/graph/search/synthesis）
├── memory/              ← 坤哥記憶（patterns/crystals/diary/soul）
├── calendar/            ← 行事曆整合
├── notification/        ← 通知派發（LINE/Telegram/Discord/Email）
├── integration/         ← 通道適配（channel_adapter/sender_context）
├── audit/               ← 審計（事件記錄 + mixin）
├── backup/              ← 備份（DB/附件/遠端同步）
├── einvoice/            ← 電子發票
├── security/            ← 資安掃描 + 問題追蹤
└── observability/       ← 觀測棧（metric/health/log）
```

### 1.3 反模式（從本案淬鍊）

| 反模式 | 例子 | 解法 |
|---|---|---|
| 頂層散戶 | `services/document_service.py` 直接放根目錄 | 入 `services/document/` 子包 |
| 行數門檻拆分 | 「>500 行就拆」 | 看職責；單一 domain 完整實作可很大 |
| God Service | 一檔含 CRUD + 匯入 + 匯出 + 統計 | 按使用案例拆（如 quotation_service + quotation_service_io）|
| Repository 繞過 | Service 直接 `session.execute()` | 全走 Repository（含複雜查詢）|
| Schema 重定義 | API endpoint 自訂 BaseModel | 從 `app.schemas/` 單一匯入 |

---

## 2. Repository 層模式

### 2.1 BaseRepository[T] 泛型

```python
class BaseRepository(Generic[T]):
    """CRUD + 分頁 + 搜尋的泛型基礎"""
    model_class: Type[T]

    async def get_by_id(self, id: int) -> Optional[T]: ...
    async def list_paginated(self, skip, limit, filters) -> tuple[list[T], int]: ...
    async def create(self, data: dict) -> T: ...
    async def update(self, id, data: dict) -> Optional[T]: ...
    async def soft_delete(self, id: int) -> bool: ...
```

### 2.2 領域 Repository 增添

```python
class DocumentRepository(BaseRepository[OfficialDocument]):
    async def filter_documents(self, *, doc_type, keyword, ...) -> tuple[list, int]:
        """不可用通用 list_paginated 表達的複雜查詢"""
```

### 2.3 Query Builder（三層複雜查詢）

```
repositories/
├── base_repository.py
├── document_repository.py
└── query_builders/
    └── document_query_builder.py  ← Fluent API
```

---

## 3. API 端點組織

### 3.1 子目錄 = bounded context

```
api/endpoints/
├── documents/          ← 公文 CRUD + import + export + audit
├── ai/                 ← agent / graph / rag / tools_manifest
├── erp/                ← quotations / invoices / expenses / ledger
├── taoyuan_dispatch/   ← 派工 CRUD + 匯入 + correspondence
└── auth/               ← OAuth / Google / LINE / session
```

### 3.2 單檔 <300 行原則（**行數上限，非拆分門檻**）
- 超過 300 行 → 按動作拆（list.py / crud.py / export.py / stats.py）
- 這是 **API 層特例**：因為 API 多樣但每動作邏輯薄
- Service 層**不適用**此原則（service 按 domain 拆）

---

## 4. SSOT 完整性守則

### 4.1 「yaml config + 整合測試」模式

```yaml
# config/*.yaml — 聲明 SSOT
provider_routing:
  chat:
    preferred: [groq, nvidia, ollama]
    prefer_local: false
```

```python
# services/core/config.py — reader
def should_prefer_local(task_type: str) -> bool:
    return self._provider_routing.get(task_type, {}).get("prefer_local", False)
```

```python
# core/consumer.py — 生產呼叫點
if config.should_prefer_local(task_type):
    prefer_local = True
```

```python
# tests/integration/test_config_reaches_consumer.py — 鎖定鏈路
async def test_yaml_wins_over_hardcode(monkeypatch):
    stub = _StubConfig({"chat": {"prefer_local": False}})
    monkeypatch.setattr("app.core.config.get_config", lambda: stub)
    # assert 生產行為符合 yaml
```

### 4.2 死配置偵測

每月跑一次（可作 CI）：

```bash
# scan: config methods/properties with zero production callers
python scripts/checks/config_dead_reader_scan.py
```

---

## 5. Hermes Skill 整合模板

### 5.1 單 bridge 聚合模式（MVP）

```
docs/hermes-skills/
└── ck-<repo>-bridge/
    ├── SKILL.md              ← 自然語言說明 + 使用案例
    ├── tool_spec.json        ← OpenAPI-like 工具 schema（單 toolset）
    ├── tools.py              ← HTTP 轉發到本 repo agent API
    ├── install.sh            ← 一鍵部署到 HERMES_HOME
    ├── cloudflared-config.example.yml  ← Tunnel 設定範例
    ├── references/           ← 進階使用範例（skin 對話）
    └── tests/                ← skill 自測（離線 mock）
```

### 5.2 Skill 對應的後端 API 邊界

```python
# api/endpoints/ai/ — 固定 4 個類別端點
agent_query.py         ← POST /agent/query/stream（主對話）
agent_capability.py    ← POST /agent/capability-profile + federated-*
agent_evolution.py     ← POST /agent/evolution/status
tools_manifest.py      ← GET /ai/tools-manifest（public contract）
```

### 5.3 Hermes 跨 repo 聯邦模式（進階）

```
hermes-stack（單一 gateway）
    │
    ├─ ck-missive-bridge    → POST missive.cksurvey.tw/api/ai/agent/query
    ├─ ck-lvrland-bridge    → POST lvrland.cksurvey.tw/api/ai/agent/query
    ├─ ck-pile-bridge       → POST pile.cksurvey.tw/api/ai/agent/query
    └─ ck-kg-bridge         → POST kg.cksurvey.tw/api/graph/federated-search
```

每 repo 自主維護 bridge skill 的 `tool_spec.json`，hermes-agent 自動載入。

---

## 6. 觀測棧標配

### 6.1 三層必備

```
metric（Prometheus）       ← /metrics endpoint + 16+ 指標
 │   http_requests_total
 │   inference_provider_completion_total
 │   inference_queue_waiting
 │   db_pool_{active,idle,checkout,overflow}
 │   ai_provider_chosen_total  ← 推薦加
 │
log（Loki via Promtail）   ← JSON structlog + PII 遮罩
 │   backend-error.log（level=error）
 │   backend-out.log（stdout）
 │   app.log / api.log / admin_push_failures.log
 │
trace（shadow_trace.db）   ← SQLite 本地 + 30d retention
     query_trace(ts, channel, provider, latency_ms, success, error_code)
```

### 6.2 Alerting Rules（4 groups）

```yaml
# configs/prometheus/alerts.yml
- error_budget:        # SLO 消耗速率
- silent_failure:      # 沒打 metric 但觀察到的異常
- capacity:            # pool / queue / semaphore 飽和
- business:            # 業務指標（如晨報推播失敗）
```

### 6.3 Dashboard 至少三張

```
Grafana dashboards/
├── ck-<repo>-http.json      ← 流量 / 錯誤率 / latency
├── ck-<repo>-db-pool.json   ← Pool / 慢查詢 / overflow
└── ck-<repo>-inference.json ← LLM completion / fallback / shadow baseline
```

---

## 7. Frontend 架構

### 7.1 資料取得強制走 React Query

```typescript
// ❌ 禁用
useEffect(() => {
  apiClient.post('/api/...').then(...)
}, [])

// ✅ 必用
const { data, isLoading } = useQuery({
  queryKey: ['documents', filters],
  queryFn: () => apiClient.post(DOCUMENTS_ENDPOINTS.LIST, filters),
})
```

### 7.2 Types SSOT

```
frontend/src/types/
├── api.ts (barrel)         + api-{project,user,...}.ts
├── ai.ts (barrel)          + ai-{document,search,...}.ts
└── [domain].ts
```

後端 schema 改動的同步流程：
1. 改 `backend/app/schemas/{entity}.py`
2. 改 `frontend/src/types/api.ts`（手動或 Orval）

### 7.3 Detail 頁統一 Layout

所有詳情頁必用 `components/common/DetailPage/DetailPageLayout`，禁用 Modal/Drawer CRUD。

---

## 8. 認證與環境

### 8.1 集中式檢測

```typescript
// config/env.ts SSOT
export function isAuthDisabled(): boolean
export function isInternalIP(hostname: string): boolean
export function detectEnvironment(): 'localhost' | 'internal' | 'ngrok' | 'public'
```

### 8.2 SSO 唯一路徑（2026-04-24 ADR-0033 後）

| 環境 | 認證要求 |
|---|---|
| localhost | Google OAuth |
| internal (10/172.16-31/192.168) | 免認證 |
| public | Google OAuth + LINE Login |

### 8.3 `.env` SSOT

- 專案根目錄唯一 `.env`
- `backend/.env` / `frontend/.env.local` **禁止存在**

---

## 9. Alembic 治理

### 9.1 命名規範

```
<YYYYMMDD><seq>_<領域>_<action>.py

例：
20260424a001_tender_canonical_url_kind.py
20260424a002_memory_frontmatter_yaml_migration.py
```

### 9.2 高頻變動期的守則

當週 > 10 個 migration 時：
- 必須有 `memory/migration_waves_<YYYYMMDD>.md` 紀錄原因
- 避免跨 wave 的 rollback
- 每月末 cut 一個 `db-<YYYY-MMw>` tag（anchor point）

---

## 10. Commit 紀律

### 10.1 Bisectable 原則

- 單一 commit 必須能獨立 revert 而不破整體
- Pre-commit 驗證：skills/tsc/python syntax/敏感檔案
- Husky + commitlint 強制 conventional commits
- Subject **必須小寫**（`CHANGELOG` 被拒，`changelog` OK）

### 10.2 Fix + Doc + Test 三配一

重大修復 = 3 commits（最理想）：
1. `fix:` 核心程式碼改動
2. `test:` 鎖定 regression
3. `docs:` ADR / CHANGELOG / memory 同步

---

## 11. 跨 repo 復用檢查清單

新 repo（如 CK_lvrland_Webmap）採用本範本時：

- [ ] 建立 `services/` 子包按 DDD（至少 base/ + 領域 3-5 個）
- [ ] BaseRepository[T] + 每領域 Repository
- [ ] API endpoints 子目錄 = context
- [ ] `.env` 單一根 + `.gitignore` 保護
- [ ] `config/*.yaml` 配整合測試驗證 SSOT
- [ ] 觀測：`/metrics` endpoint + 三張 Grafana dashboard
- [ ] Hermes: 建 `docs/hermes-skills/ck-<repo>-bridge/` 範本
- [ ] Commit: commitlint + pre-commit hooks
- [ ] ADR: `docs/adr/` + 跨 repo 引用用 FQID（`<Repo>#<4-digit>`）
- [ ] CI: 至少跑 verify_architecture.py + Python syntax + TypeScript

---

## 12. 可量化架構 Fitness Functions

每月跑一次：

| 指標 | 目標 | 腳本 |
|---|---|---|
| Services 頂層散戶比例 | < 20% | `scripts/checks/service_dir_entropy.py` |
| Dead config reader 數 | 0 | `scripts/checks/config_dead_reader_scan.py` |
| Baseline 成功率（7 天）| ≥ 95% | `node scripts/checks/shadow-baseline-report.cjs` |
| Soul fidelity 跨 provider | ≥ 70% | `python scripts/checks/soul-fidelity-eval.py` |
| 超大檔（非單一 domain）數 | 0 | 手動 review |
| ADR active:archived | active ≤ 20 | `scripts/checks/adr_lifecycle_check.py` |
| Frontend useEffect+apiClient | 0 | ESLint custom rule |

---

## 附：CK_Missive v5.9.5 實況對照

| 章節 | CK_Missive 達標? | 備註 |
|---|---|---|
| §1.2 DDD 目標結構 | 🟡 50% | services 頂層仍 85 散戶（R1 待執行）|
| §2 Repository | ✅ | 34 類別 + BaseRepository |
| §3 API 組織 | ✅ | 13 子目錄 |
| §4 SSOT 完整性 | ✅（2026-04-24 後）| e33df6fd 接線 + 4 tests |
| §5 Hermes skill | 🟡 | 1/5 bridge（ADR-0020 Phase 1 待）|
| §6 觀測棧 | ✅ | 16 metrics + 3 dashboards + 12 alerts |
| §7 Frontend | ✅ | React Query + types SSOT |
| §8 認證 | ✅（ADR-0033 後）| SSO 唯一路徑 |
| §9 Alembic | 🟡 | 命名良好，缺 wave 紀錄 |
| §10 Commit | ✅ | husky + commitlint |

此表可作他案參考自測的起點。

---

**變更歷史**
- v1.0（2026-04-25）：首版，抽象自 CK_Missive v5.9.5 P0 事故與 SSOT 修復教訓
