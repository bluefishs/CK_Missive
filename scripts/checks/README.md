# scripts/checks/ — 檢查器索引

> **建立**：2026-04-27（v5.9.9 整合優化）
> **目的**：30+ 檢查器的分類目錄，避免新人迷航
> **關聯**：`docs/architecture/TEMPLATE_EXTRACTION.md` §1.2 腳本類資產

---

## 0. 用法分類速查

依「何時跑」分為四類，新人**只需記住「fitness 月度 + pre-commit 必跑」**即可。

| 分類 | 何時跑 | 列表入口 |
|---|---|---|
| 🧪 **FITNESS** | 月度 / 大重構前 | §1 — `run_fitness.sh` 一鍵跑全部 |
| 🛡️ **PRE-COMMIT** | git commit 自動觸發 | §2 — 由 `.git/hooks/pre-commit` 執行 |
| 📊 **ON-DEMAND** | 開發/維運遇問題時手動跑 | §3 — 各種專項診斷 |
| ⏰ **SCHEDULED** | PM2/cron 自動執行 | §4 — 已掛排程的監控/合成腳本 |

---

## 1. 🧪 FITNESS（月度架構覆盤）

由 `run_fitness.sh` 6 step 統一觸發。範本提取首選，可直接 cherry-pick 到其他 repo。

| Step | 腳本 | 檢查項 | 閾值 | 失敗修復 |
|---|---|---|---|---|
| 1 | `service_dir_entropy.py` | services/ 頂層散戶比例 | < 20% | 入子包（見 SERVICE_CONTEXT_MAP）|
| 2 | `config_dead_reader_scan.py` | yaml 設定有 reader 但 0 生產呼叫 | 0 dead | 刪設定 / 加生產讀取點 |
| 3 | `soul_mirror_drift_check.py` | 跨 repo SOUL.md drift | 0 drift | `sync_soul_to_hermes.sh --apply` |
| 4 | `wiki_kg_link_audit.py` | Wiki↔KG 連結率 | ≥ 80% | `backfill_wiki_*_kg.py --apply` |
| 5 | `kg_embedding_coverage_check.py` | pgvector 覆蓋率 | ≥ 50% | `backfill_kg_embeddings_all.py --apply --all` |
| 6 | (inline) | 架構標準文件存在 | exists | 補 STANDARD_REFERENCE.md / SERVICE_CONTEXT_MAP.md |

```bash
# 一鍵跑全部
bash scripts/checks/run_fitness.sh

# Slash command 等價
/arch-fitness
```

**範本化等級**：L4 Plug-and-Play（改 1~2 個 path 變數即可移植）。

---

## 2. 🛡️ PRE-COMMIT（git commit 守護）

由 `.git/hooks/pre-commit` 自動執行；**靜態守護**為主，不跑就過不了 commit。

| 腳本 | 檢查項 | ADR |
|---|---|---|
| `async_session_race_guard.py` | `asyncio.gather` + 共用 db session | ADR-0028（承接 ADR-0021）|
| `sse_headers_guard.py` | SSE endpoint 必須含 `Content-Encoding: identity` | ADR-0028 |
| `schema_lazy_load_guard.py` | Pydantic schema 不得訪問 ORM lazy relationship | ADR-0027 |
| `pattern_yaml_type_guard.py` | pattern yaml 型別約束 | — |

**範本化等級**：L4。新 repo 用 FastAPI + asyncpg + Pydantic 即可直接套用。

---

## 3. 📊 ON-DEMAND（手動診斷）

問題發生時的針對性診斷，**不跑也不影響日常開發**。

### 3.1 配置一致性

| 腳本 | 用途 | 範例情境 |
|---|---|---|
| `verify_architecture.py` | 7 項架構驗證 | 架構審查 / PR review |
| `verify_ai_stubs.py` | re-export stub 一致性 | AI 子包重構後 |
| `check_consistency.py` | 跨檔一致性 | 前後端 type drift 懷疑時 |
| `config-check.py` | env 配置完整性 | .env 改動後 |
| `config-persistence-check.py` | 設定持久化驗證 | 部署前 |
| `security-config-check.py` | 資安設定 | `/security-audit` 配套 |
| `check-config.ps1` (PowerShell) | Windows 端配置檢查 | Windows 開發環境 |

### 3.2 API / 路由 / 文件

| 腳本 | 用途 |
|---|---|
| `api-endpoints-check.js` | 後端 endpoint 註冊與前端呼叫對齊 |
| `route-sync-check.js` | ROUTES / AppRouter / NavigationData 三方同步 |
| `doc-sync-check.cjs` | 文件漂移偵測 |
| `wiki-orphan-classify.cjs` | wiki 孤兒頁面分類 |
| `service-line-count-check.py` | service 行數監控（**僅觀察用，非拆分依據**）|

### 3.3 Hermes 專項

| 腳本 | 用途 | ADR |
|---|---|---|
| `hermes-checkpoint-report.cjs` | Hermes 遷移檢查點報告 | ADR-0014 |
| `shadow-baseline-report.cjs` | Shadow baseline 統計（GO 條件 #1）| ADR-0030 |
| `soul-fidelity-eval.py` | Soul 人格跨 provider 一致性（GO 條件 #3）| ADR-0023 |
| `soul-fidelity-multi-baseline.sh` | Multi-provider 批次評估 | ADR-0030 |

### 3.4 Ollama / GPU

| 腳本 | 用途 |
|---|---|
| `check-ollama.ps1` | Ollama 服務 + GPU VRAM 健康度 |

### 3.5 ADR 治理

| 腳本 | 用途 |
|---|---|
| `adr_lifecycle_check.py` | active / archived / removed 統計（ADR-0029）|

---

## 4. ⏰ SCHEDULED（自動排程）

由 PM2 / FastAPI scheduler 自動觸發；**新 repo 設定排程時參考**。

| 腳本 | 觸發方式 | 頻率 |
|---|---|---|
| `synthetic-baseline-inject.py` | FastAPI scheduler | 3x/日（`docs/HERMES_MIGRATION_PLAN.md`）|
| `synthetic-baseline-loop.sh` | 手動長跑（dev 模擬）| on-demand |
| `skills-sync-check.ps1` | 手動 / pre-deploy | on-demand |

---

## 5. 各分類腳本的範本化等級

對 §1 §2 提到的「範本化等級」總表（給跨 repo 移植參考）：

| 腳本類別 | 範本化等級 | 移植成本 |
|---|---|---|
| Fitness 6 step | **L4 Plug-and-Play** | 5~10 min |
| 4 靜態守護 | **L4** | 5 min |
| Hermes 專項（baseline / soul fidelity）| **L3 Configurable** | 30 min |
| 配置一致性類 | **L2 Reference** | 需重寫 |
| ADR / 文件漂移 | **L4** | 5 min |
| Ollama/GPU 檢查 | **L4** | 5 min（若用相同推理棧）|
| Schedule 腳本 | **L3** | 改設定 |

---

## 6. 不在本目錄但相關

| 位置 | 用途 |
|---|---|
| `.git/hooks/pre-commit` | 統合呼叫 §2 守護 |
| `.claude/hooks/*.ps1` | Claude Code session 內的檢查（typescript / python lint）|
| `scripts/sync/backfill_*.py` | fitness step 4/5 失敗後的修復腳本 |
| `scripts/health/*.sh` | watchdog（不在 checks/ 因為是長駐而非 spot check）|

---

## 7. 維護準則

新增 checker 前自問：

1. 它屬於哪一類（fitness / pre-commit / on-demand / scheduled）？
2. 同分類已有 30 個 checker，本檢查能否合進既有的而非新檔？
3. 若必須新檔，是否更新本 README 的對應 §？
4. 範本化等級為何？能否抽出 path/threshold 變數讓其他 repo 套用？

> **經驗法則**：寧可改現有 checker 加 `--mode xxx` 參數，也不要新增孤立 .py。

---

> 引用此檔請用 FQID `CK_Missive#scripts-checks-README-v1.0`

---

## v6.11 補篇：48 step 完整索引（2026-05-27 更新）

`run_fitness.sh` 目前含 **48 step**，按 family 分類：

### Step 37-48 — L41-L48 跨檔 SSOT family（重點）

> 共通模式：「同一資源多檔分別宣告，沒 audit enforce 一致」→ silent dormant

| Step | Audit | Lesson | dormant |
|---|---|---|---|
| 37 | `network_audit.py` | ADR-0043 跨 repo network | (preventive) |
| 38 | `docker_compose_volume_consistency.py` | **L43** volume drift | **10h** |
| 39 | `facade_consumer_audit.py` | v6.10 P1 | (preventive) |
| 40 | `compose_dockerfile_healthcheck_ssot.py` | **L45** healthcheck override | **18 min** |
| 41 | `cross_repo_secret_audit.py` | **L41** jwt secret drift | **6 days** |
| 42 | `cross_repo_auth_state_audit.py` | **L44** sso state lock | < 1 day |
| 43 | `db_schema_drift_audit.py` | #1 model vs migration | (preventive) |
| 44 | `container_lifecycle_audit.py` | **L46** :latest tag | 2026-04-21 chronic |
| 45 | `subdomain_registry_audit.py` | **L47** subdomain typo | (preventive) |
| 46 | `sso_autoload_completeness_audit.py` | **L48** frontend autoload | (preventive) |
| 47 | `startup_dependency_race_audit.py` | v6.12 P3 race | (preventive) |
| 48 | `db_pool_exhaustion_audit.py` | v6.12 P3 pool | (preventive) |

### Meta-pattern 規範

5 規則 — 詳見 [`.claude/rules/cross-file-ssot-governance.md`](../../.claude/rules/cross-file-ssot-governance.md)：

1. 每個跨檔資源指定 SSOT 位置
2. 每個資源類型有 fitness audit script
3. Runtime healthcheck 驗證業務量
4. Dual-write atomic 或 dual-validation
5. 跨 repo 必走 ADR + Registry + Audit 三件套

### 跨 repo 範本擴散

9 個 audit 已同步到 `shared-modules/ck-modular-toolkit/checks/`：
- 7 L41-L48 family（37-46）
- 2 v6.12 P3（47-48）
- 既有 portability / naming

其他 repo 引用：`bash shared-modules/ck-modular-toolkit/install.sh --target=<repo>`

### 嚴重度 + Exit Code

| Indicator | Meaning | Exit | `--strict` |
|---|---|---|---|
| 🟢 GREEN | 對齊 SSOT | 0 | 0 |
| 🟡 YELLOW | informational drift | 1 | 2 |
| 🔴 RED | critical risk | 2 | 2 |
| ⚪ 跳過 | 環境不可達 | 0 | 0 |

### 維護新增 audit 流程

1. 寫 `<topic>_audit.py`（cp950 fix + 嚴重度分級 + 修法建議 5 步）
2. 接進 `run_fitness.sh` 並更新 `[N/49]` 計數
3. 同步到 `shared-modules/ck-modular-toolkit/checks/`
4. 更新 toolkit README + 本檔對應 §
