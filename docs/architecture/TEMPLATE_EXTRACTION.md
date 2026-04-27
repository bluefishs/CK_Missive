# CK_Missive → 跨 repo 範本提取指南

> **版本**：v1.0（2026-04-27，v5.9.9）
> **狀態**：accepted（治理基準）
> **適用對象**：CK_lvrland_Webmap / CK_lvrland_dataform / CK_PileMgmt / CK_KMapAdvisor / CK_Showcase / CK_AaaP（Phase 2+ 受管專案）
> **治理層級**：若與 `CK_AaaP/CONVENTIONS.md` 衝突 → 以 CONVENTIONS.md 為準

本檔列出 CK_Missive 已驗證、可直接 cherry-pick 到其他 CKProject 子專案的架構資產。
**只收經 P0 事故淬鍊或 fitness function 驗證過的模式**，避免 cargo cult。

---

## 0. 給接手新 repo 的人：30 分鐘快速套用清單

依序執行下列 10 項即可獲得 80% 的 CK_Missive 治理收益：

| # | 動作 | 來源檔 | 改動成本 |
|---|---|---|---|
| 1 | Copy `scripts/checks/run_fitness.sh` → 改 `WIKI_DIR` 等專案路徑 | `scripts/checks/run_fitness.sh` | 5 min |
| 2 | Copy `docs/architecture/STANDARD_REFERENCE.md` → 改 §1.2 目錄結構為新 repo 實際 context | 同名 | 10 min |
| 3 | Copy 4 個靜態守護到新 repo 的 `scripts/checks/` | `async_session_race_guard.py`、`sse_headers_guard.py`、`schema_lazy_load_guard.py`、`config_dead_reader_scan.py` | 5 min |
| 4 | Copy `backend/app/core/timeouts.py` → 對接該 repo 的 ai_config（或建一個簡化版） | `backend/app/core/timeouts.py` | 5 min |
| 5 | Copy ADR-0028 / 0029 / 0030 範本 → 改 repo 名稱 | `docs/adr/0028, 0029, 0030*.md` | 10 min |
| 6 | Copy `configs/prometheus/alerts.yml` 4 groups + `configs/grafana/dashboards/*.json` | 同名目錄 | 5 min |
| 7 | 建立 `wiki/` 目錄結構（entities / topics / synthesis / sources） | `wiki/` | 1 min |
| 8 | 在 `.claude/rules/` 建立 `architecture-{backend,frontend}.md` 結構（內容空）| `.claude/rules/architecture*.md` | 5 min |
| 9 | 加 pre-commit hook 跑 4 守護 | `.git/hooks/pre-commit` | 5 min |
| 10 | 跑 `bash scripts/checks/run_fitness.sh` 取得首次 baseline | — | 1 min |

完成後該 repo 即具備 CK_Missive 的「最小可治理基底」。

---

## 1. 範本資產分類索引

### 1.1 文件類（拷貝即可）

| 資產 | 路徑 | 用途 | 複製成本 |
|---|---|---|---|
| 架構標準 | `docs/architecture/STANDARD_REFERENCE.md` | 12 章 + §13 AI-Native UX | low |
| Service Context Map | `docs/architecture/SERVICE_CONTEXT_MAP.md` | 散戶 service → bounded context 映射範本 | medium（需重寫對應該 repo）|
| 整合分析範本 | `docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` | 五整合面向 + O1-O6 路線分析範本 | medium |
| ADR-0028 錯誤合約 | `docs/adr/0028-error-contract-silent-failure-policy.md` | 11 層 silent failure 政策 | low（直接改 repo 名）|
| ADR-0029 ADR Lifecycle | `docs/adr/0029-adr-lifecycle-policy.md` | active/archived/removed 治理 | low |
| ADR-0030 GO/NO-GO | `docs/adr/0030-hermes-go-no-go-revision.md` | 5 條 GO 條件 + SLO 拍板模板 | low |
| 對外敘事 | `docs/BUSINESS_VALUE.md` | Memory Wiki / 意識體 → 商業語言 | medium |

### 1.2 腳本類（直接執行）

| 資產 | 路徑 | 適用範圍 | 改動 |
|---|---|---|---|
| Fitness Runner（6 step）| `scripts/checks/run_fitness.sh` | 任何 repo | 改 WIKI_DIR 等變數 |
| Service Entropy Scanner | `scripts/checks/service_dir_entropy.py` | 後端 monorepo | 改 SERVICES_ROOT |
| Dead Config Scanner | `scripts/checks/config_dead_reader_scan.py` | yaml 驅動 repo | 改 CONFIG_FILES |
| SOUL Drift Detector | `scripts/checks/soul_mirror_drift_check.py` | 跨 repo | 改 MIRRORS dict |
| Wiki↔KG Link Audit | `scripts/checks/wiki_kg_link_audit.py` | 有 KG 的 repo | 改 SCAN_SUBDIRS |
| KG Embedding Coverage | `scripts/checks/kg_embedding_coverage_check.py` | 有 pgvector 的 repo | 改 DSN |
| ADR Lifecycle Check | `scripts/checks/adr_lifecycle_check.py` | 任何用 ADR 的 repo | 改 ADR_DIR |
| 4 靜態守護 | `scripts/checks/{async_session_race,sse_headers,schema_lazy_load}_guard.py` | FastAPI + asyncpg + Pydantic | 改 SCAN_PATHS |

### 1.3 後端核心（程式碼）

| 資產 | 路徑 | 用途 | 依賴 |
|---|---|---|---|
| Timeouts SSOT | `backend/app/core/timeouts.py` | TimeoutContract + SLOContract | 對接該 repo 的 ai_config |
| Structured Logging | `backend/app/core/structured_logging.py` | structlog stdlib bridge | structlog |
| Prometheus Middleware | `backend/app/core/prometheus_middleware.py` | /metrics endpoint | prometheus_client |
| DB Pool Metrics | `backend/app/core/db_pool_metrics.py` + `db_query_metrics.py` + `db_query_listener.py` | SQLAlchemy event listener | SQLAlchemy 2.0 |
| Inference Semaphore | `backend/app/core/inference_semaphore.py` | local + cloud 分池 GPU 控制 | asyncio |
| Secret Loader | `backend/app/core/secret_loader.py` | Docker Secrets file→env fallback | — |
| Scheduler Alert | `backend/app/core/scheduler_alert.py` | 排程器失敗 Telegram 告警 | httpx |
| Audit Mixin | `backend/app/services/audit_mixin.py` | CRUD service 自動稽核 | — |
| BaseRepository | `backend/app/repositories/base_repository.py` | Generic[T] CRUD + 分頁 + 搜尋 | SQLAlchemy 2.0 async |

### 1.4 觀測棧配置

| 資產 | 路徑 | 改動 |
|---|---|---|
| Grafana Dashboards | `configs/grafana/dashboards/ck-missive-{http,db-pool,inference}.json` | 改 datasource UID + dashboard title |
| Prometheus Alerts | `configs/prometheus/alerts.yml`（4 groups, 12 rules） | 改 instance label |
| Promtail Config | `configs/grafana/promtail-pm2.yml` v2 | 改 PM2 log 路徑 |
| 部署 README | `configs/grafana/README.md` | 直接複製 |

### 1.5 開發治理（.claude/）

| 資產 | 路徑 | 用途 |
|---|---|---|
| Claude rules 拆檔範本 | `.claude/rules/architecture{,-backend,-frontend}.md` | 防止單檔 >2000 行 |
| Skills inventory | `.claude/rules/skills-inventory.md` | Skill / Command / Agent 索引 |
| Hooks guide | `.claude/rules/hooks-guide.md` | PreToolUse / PostToolUse / SessionStart |
| 強制檢查清單 | `.claude/MANDATORY_CHECKLIST.md` | 11 個任務類型 × N 檢查項 |
| 開發指引 | `.claude/DEVELOPMENT_GUIDELINES.md` | 常見錯誤與解法 |

---

## 2. 跨 repo 移植 SOP（per 範本資產類別）

### 2.1 Fitness Functions 移植 SOP

```bash
# 在新 repo 根目錄
mkdir -p scripts/checks docs/architecture
cp ../CK_Missive/scripts/checks/run_fitness.sh scripts/checks/
cp ../CK_Missive/scripts/checks/{service_dir_entropy,config_dead_reader_scan,soul_mirror_drift_check,wiki_kg_link_audit,kg_embedding_coverage_check}.py scripts/checks/

# 改動清單（必做）
# 1. run_fitness.sh: WIKI_DIR / SERVICES_ROOT / SOUL_FILE 路徑
# 2. service_dir_entropy.py: SERVICES_ROOT 變數
# 3. config_dead_reader_scan.py: CONFIG_FILES 加新 repo 的 yaml
# 4. wiki_kg_link_audit.py: SCAN_SUBDIRS 對應 wiki 結構

bash scripts/checks/run_fitness.sh  # 取首次 baseline
```

### 2.2 ADR 體系移植 SOP

```bash
mkdir -p docs/adr docs/adr/archived
cp ../CK_Missive/docs/adr/{0028,0029,0030}*.md docs/adr/
cp ../CK_Missive/docs/adr/{README,TEMPLATE}.md docs/adr/

# 改動清單
# 1. 改 ADR header 的 repo 名稱
# 2. ADR-0028: SCAN_PATHS / EXCLUDE_PATHS 對應該 repo
# 3. ADR-0029: ADR_DIR / ARCHIVED_DIR
# 4. ADR-0030: 改 service 名稱 / GO 條件閾值 per 該 repo SLO 需求

# 跑 lifecycle check
python scripts/checks/adr_lifecycle_check.py
```

### 2.3 觀測棧移植 SOP

```bash
mkdir -p configs/{grafana/dashboards,prometheus}
cp -r ../CK_Missive/configs/grafana/dashboards configs/grafana/
cp ../CK_Missive/configs/grafana/{README.md,promtail-pm2.yml} configs/grafana/
cp ../CK_Missive/configs/prometheus/alerts.yml configs/prometheus/

# 改動清單（用 sed/Find-Replace）
# 1. dashboards/*.json: 全文 ck-missive → ck-{newrepo}
# 2. alerts.yml: instance label / job 名稱
# 3. promtail-pm2.yml: PM2 log 路徑

# 部署到 CK_DigitalTunnel
cp configs/grafana/dashboards/*.json /path/to/CK_DigitalTunnel/dashboards/
docker compose -f /path/to/CK_DigitalTunnel/docker-compose.yml restart grafana
```

### 2.4 Hermes Bridge Skill 移植 SOP

```bash
mkdir -p docs/hermes-skills/ck-{newrepo}-bridge
cp -r ../CK_Missive/docs/hermes-skills/ck-missive-bridge/* docs/hermes-skills/ck-{newrepo}-bridge/

# 改動清單
# 1. SKILL.md: skill 名稱 + 自然語言描述（自然語言反向產生）
# 2. tool_spec.json: 改 endpoint URL（host.docker.internal:{port}）
# 3. tools.py: BASE_URL + tool 名稱
# 4. install.sh: skill 名稱

# 公網部署需建立 Cloudflare Tunnel subdomain（依 ADR-0016）
```

---

## 3. 反模式（從本 repo 淬鍊，務必避免）

### 3.1 SSOT 聲明 vs 實作斷鏈（ADR-0028 反例）

**範例**：ADR-0028 承諾 `core/timeouts.py` 為 timeout SSOT，但**從未實作** → 真實 timeout 散在 ai_config 各處 → ADR-0030 P95 拍板沒有錨點 → dead doc 反模式（v5.9.9 才補齊）。

**教訓**：每寫 ADR 必須**附 commit 連結證明已落地**。Lifecycle check 應加「文件提到的檔案不存在」detector。

### 3.2 yaml config 聲明卻零讀者（ADR-0030 Patch A 反例）

**範例**：`agent-policy.yaml` 寫了 `provider_routing.prefer_local: true`，但 `should_prefer_local()` 在生產 0 呼叫點 → Patch A 看似生效，實際是 no-op。

**教訓**：`config_dead_reader_scan.py` 月度跑，命中即修；新增 yaml 欄位需附 integration test 鎖定鏈路。

### 3.3 行數驅動的拆分

**範例**：`wiki_compiler.py` 1074 行被誤判為「超標需拆」，實際是單一領域完整實作不該拆。

**教訓**：見 `feedback_ddd_over_line_count.md` — **看職責邊界不看行數**。

### 3.4 GitHub Actions 自動觸發產生雲端費用

**範例**：早期啟用 push trigger 累積 $XX/月費用 → 全停用，改本地 fitness function。

**教訓**：見 `feedback_no_github_actions_cost.md` — 所有 CI 走本地 hook + monthly 跑，雲端只跑 cron。

### 3.5 Telegram 個人號當主推播通道（ADR-0027 反例）

**範例**：admin push 全靠 Telegram → 個人號封禁直接斷鏈 → 緊急切 LINE。

**教訓**：通道應**多供應**設計，不該硬綁單一通訊平台；新 repo 從 day 1 就應 `notification_dispatcher` 抽象 + 至少 2 通道。

### 3.6 一個 dataclass 塞 100+ 設定欄位

**範例**：`AIConfig` 含 50+ 欄位涵蓋 LLM / search / agent / pattern / compaction → 修一個值找半天。

**教訓**：新 repo 從 day 1 就**按 bounded context 拆 config**：`AIConfig` / `SearchConfig` / `AgentConfig` 各自 dataclass。

---

## 4. 範本化等級分類

每個資產有不同的「複用成熟度」：

| 等級 | 定義 | 本 repo 已達等級的資產 |
|---|---|---|
| **L4 Plug-and-Play** | 改 1~2 個 path/變數即可運作 | run_fitness.sh、4 靜態守護、prometheus_middleware.py |
| **L3 Configurable** | 改 config 後可運作（無需動 code） | timeouts.py、Grafana dashboards、alerts.yml |
| **L2 Reference Implementation** | 需重寫但結構可借用 | STANDARD_REFERENCE.md、SERVICE_CONTEXT_MAP.md、ADR-0028~0030 |
| **L1 Pattern** | 只能借用思路，實作要從頭 | Hermes Bridge Skill、Memory Wiki 7-Phase |
| **L0 Domain-Specific** | CK_Missive 專屬（不可複用） | wiki_compiler.py、morning_report_service.py |

新 repo 接手者建議優先抽 L4 → L3 → L2，L1/L0 待時機成熟再評估。

---

## 5. 跨 repo 治理連動

### 5.1 SOUL.md 同步機制

CK_Missive 與 hermes-agent 已建立 SOUL.md mirror（`scripts/sync/sync_soul_to_hermes.sh`）。新 repo 若需共用「坤哥」人格基底，可同樣 mirror，但**任務 prompt 要分流**避免人格稀釋（ADR-0023 + ADR-0031 邊界）。

### 5.2 ADR REGISTRY 跨 repo 引用

引用其他 repo 的 ADR 一律用 FQID：`<Repo>#<4-digit>`，例：`CK_AaaP#0020`。
禁用裸 `ADR-NNNN`（同號跨 repo 主題不同 — 已知 14 處碰撞）。

### 5.3 fitness function 跨 repo 月度執行

Owner 每月覆盤時建議排程：

```bash
for repo in CK_Missive CK_lvrland_Webmap CK_PileMgmt; do
  echo "=== $repo ==="
  cd /path/to/$repo && bash scripts/checks/run_fitness.sh
done > /tmp/monthly_fitness_$(date +%Y%m).log
```

---

## 6. 路線圖：未來該範本化的資產

當前未範本化但有需求的：

| 資產 | 阻塞點 | 預估範本化時機 |
|---|---|---|
| services/ DDD 遷移 SOP（Wave 1-4 playbook）| Wave 1 尚未在 CK_Missive 執行 | v5.10.0 |
| Hermes Bridge Skill OpenAPI 公約 | 還是 hand-written tool_spec.json | ADR-0020 Phase 2+ |
| 跨 repo Trace ID 串接（OpenTelemetry）| 尚未導入 | Hermes GO 後 |
| Wiki 4-Phase（Ingest/Compile/Query/Lint）| domain-specific 多 | 抽 framework 需 1 sprint |
| Domain Events 跨 repo 訂閱 | 尚未確立 event schema | ADR-0020 Phase 3 |

---

## 7. 變更紀錄

- 2026-04-27 v1.0：首次發布。配合 v5.9.9 Hermes #5 P95 拍板提案 + timeouts.py SSOT 落地

---

> 維護者：Project Owner
> 引用此檔請用 FQID `CK_Missive#TEMPLATE_EXTRACTION_v1.0`
