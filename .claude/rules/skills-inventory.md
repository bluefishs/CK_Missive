# Skills / Commands / Agents 清單

> **最後同步**：2026-05-21（v6.10.3，L43 volume mount drift 災難級恢復 + fitness step 38）
> **v6.10.3 重大變更**：
> - **L43 Volume Mount Drift 災難級事故 4h 完整恢復**（5/21 下午 / 6 commits）：
>   - production compose 指向空殼 `ck_missive_postgres_data`（17 tables/502 docs），真實在 `ck_missive_postgres_dev_data`（75 tables/1788 docs/24061 KG）
>   - dormant ~10h 直到 owner 登入觸發業務 API 全 500
>   - Plan A 10 步完整恢復 + 雙 dump 備份 + MD5 + NAS 異地
> - **新增 fitness step 38** `docker_compose_volume_consistency.py` — 同邏輯 volume 跨 compose 檔 drift 偵測（含 `${COMPOSE_PROJECT_NAME}` 展開），首跑揭發 redis 同型 chronic drift 已修
> - **新增 `/health` business_data_present 503 防禦**：row count < threshold → cloudflared healthcheck fail → 流量不打進壞 instance（公網 PM2 + docker 雙 backend 都生效）
> - **L43 lesson** 入 LESSONS_REGISTRY，與 L41 同列「跨檔資源 SSOT 治理失效」教材
> - **alembic migration `20260521a001`**：補 users.department + position 欄位（idempotent ADD COLUMN IF NOT EXISTS）
> - **架構級議題揭發**：公網 cloudflared 命中 PM2 native uvicorn 不是 docker container — v6.11 Sprint 1 二選一統一 SSOT
> - **Fitness 32 → 38 step**（5/21 上午 +step 37 network_audit + 下午 +step 38 volume_consistency；加上既有的 step 33-36 構成 38 step）
> - 詳見：[[session_20260521_l43_volume_drift_recovery]] / [[lesson_l43_volume_mount_drift_silent_fail]]
>
> **v6.10 候選重大變更**：
> - **三層交付**：13 散修補丁全綠 + 4 份標準文件 + 自動化流水線 skeleton（avoid dis-integrated）
> - **4 份標準文件**：
>   - ADR-0035 GitNexus Bridge — Phase 2a dev-only（License 紅線管控）
>   - OPTIMIZATION_PIPELINE.md — 10 條優化環節連通圖
>   - MODULARIZATION_STANDARDS_v1.md — 13 章節落地前 checklist
>   - CAPABILITY_GOVERNANCE.md — 三層健康度模型（E×U×O）+ A/B/C 決策矩陣
> - **Fitness 22 → 27 step**（加 step 23-27: capability_audit / adr_lifecycle / dead_ui / lessons_drift / service_line_count）+ [N/27] header 統一
> - **2 新 lessons** 入 LESSONS_REGISTRY：
>   - L30: Pipeline Integration as Priority（環節不連通就是浪費）
>   - L31: ROI = entities × usage_rate（建表不等於用表）
> - **GitNexus 部署**：58k nodes / 92k edges / 991 clusters / 300 flows（dev-only）
> - **真實 dead 發現**：90 manual+skill tools / 14 KG entity types / 3 memory loops dead / shadow p95=64.6s
> - **跨 repo 範本擴增**：install-template-to.sh 加 3 新類（standards / pipeline / capability）
> - **32 unit tests 全綠**（20 ToolCall schema + 12 inject gate）
> - **ADR 治理**（ADR-0029）：v6.10 後 Active 16 / Archived 14 / Removed 1（adr_lifecycle_check 2026-05-18 實跑）
>
> **v6.9 變更**（保留歷史）：
> - **11 真修法 + 3 false alarm 校準**（L26 穿透式驗證落地）
> - **L29 lesson 加入**：「坤哥自我成長中斷」第二次（L21 後）— dict key bug × 涵蓋率 < 25% × silent except 三重疊加。修法 + restart 後 domain_scores 0/8 → 5/8 PASS
> - **觀測棧增量**：3 新 counter（metrics_populate_errors / memory_diary_append_failures / provider_circuit_state）+ 3 條 alert rule。**R3 首次重啟即揭發 1 次 shadow_baseline silent fail**
> - **R6 Provider Circuit Breaker**：新 module（15 unit + 5 integration tests）+ 整合進 ai_connector
> - **R11 Hallucination Hard Penalty**：entity_alignment < 0.5 → overall × 0.5
> - **R4 ADR-0025 dormant bug 歸零**：alias_rls_audit step 21 從 2 risks → 0 risks
> - **R8 schema SSOT 遷移 17/34**（user_alias + security + tender）
> - **Fitness 20 → 22 step**（+ step 21 alias_rls_audit + step 22 domain_score_freshness）
> - **3 份 runbook**（Telegram 永封 / CF Tunnel / Prometheus 降級）
> - **75+ regression tests 全綠** | TSC 0 | alias_rls_audit 0 risks ⚠️ **5/18 校正：detection coverage 0%（規則太窄）；實 apply_*_rls 覆蓋率 2/34**
>
> **v6.8 變更**（保留歷史）：
> - **v3.0 覆盤主軸 9 task** 全 done（W0/Q1/Q2/Q3/F14/F15/M1/I5+/A2 — 36 commits）
> - **5/04 認證事故鏈 10 fix**（auth_disabled / CSRF / refresh / interceptor / SPA cache）
> - **fitness 7 → 16 step**（+F14 integration_liveness +F15 LINE notify watchdog +9 既有）
> - **M1 v7.0 4 指標完整鏈**：lite report → Prometheus gauge → alert → Grafana panel
> - **I5+ wiki topics 5 → 14 aggregate**（vendor/weekly/ADR/ERP/lessons/observability/SOUL/multi-channel/integration）
> - **F26+F27 雙重 silent fail 修復**：shadow_baseline 救活揭露 ADR-0030 真實 p95=58s 警訊
> - **acceptance test 11/11 PASS**：`bash scripts/checks/v6_8_acceptance.sh`
> - **release notes**：`docs/release/v6.8.md`
>
> **v5.10.x 變更**（保留歷史）：
> - **Wave 1-8 services DDD 完整收斂**：73 檔遷移到 12 bounded contexts，0 regression
> - **LESSONS_REGISTRY v1.0**：22 條 lessons 跨 session 知識 SSOT（L01~L22）
> - **4 detector 治理三件組**：agent_evolution_health / lessons_drift_check / dead_ui_detector / notify_consumers
> - **CROSS_REPO_REFERENCE_GUIDE v1.0**：FQID 5 大類別 + 7 consumer registry + PR template
> - 坤哥為唯一意識體入口（ADR-0023 + ADR-0031）
> - ADR 治理（ADR-0029）：v6.8 後 Active 17 / Archived 10 / Removed 1
>   **5/18 校正**：實跑 `adr_lifecycle_check.py` Active **16** / Archived **14** / Removed 1（≤15 健康區間邊緣）

## v6.9 範本治理體系新增資產（給 lvrland/PileMgmt 等子專案引用）

| FQID | 類型 | 用途 |
|---|---|---|
| `CK_Missive#provider_circuit_breaker_v1.0` | Module L2 | LLM provider 連續失敗自動 skip（5 連敗 → 5min OPEN）|
| `CK_Missive#alias_rls_coverage_audit_v1.0` | Detector L4 | 靜態掃 endpoints 找 ADR-0025 半接通候選 |
| `CK_Missive#domain_score_freshness_check_v1.0` | Detector L4 | L29 watchdog — domain_scores Redis 寫入鏈活體 |
| `CK_Missive#metrics_populate_errors_total_v1.0` | Metric L2 | /metrics endpoint per-scrape silent skip 偵測 |
| `CK_Missive#memory_diary_append_failures_total_v1.0` | Metric L2 | diary fire-and-forget 失敗 4 類別計數 |
| `CK_Missive#L29_lesson_v1.0` | Doc L2 | dict key contract drift × 涵蓋率 × silent except 三重疊加教材 |
| `CK_Missive#telegram_permanent_ban_runbook_v1.0` | Runbook L2 | ADR-0027 後續永封應急（4 plan） |
| `CK_Missive#cloudflare_tunnel_outage_runbook_v1.0` | Runbook L2 | Tunnel 故障 5 plan + Bypass policy 順位陷阱 |
| `CK_Missive#prometheus_alerting_degraded_runbook_v1.0` | Runbook L2 | alerting 失明應急 + §6 緊急降級 |

## v5.10.x 範本治理體系新增資產（給 lvrland/PileMgmt 等子專案引用）

| FQID | 類型 | 用途 |
|---|---|---|
| `CK_Missive#agent_evolution_health_v1.0` | Detector L4 | 坤哥 evolution 引擎健康診斷 |
| `CK_Missive#lessons_drift_check_v1.0` | Detector L4 | LESSONS_REGISTRY 自我保護 |
| `CK_Missive#dead_ui_detector_v1.0` | Detector L4 | 後端有但前端缺 UI 偵測 |
| `CK_Missive#notify_consumers_v1.0` | Detector L4 | Pull-based 升級通知 |
| `CK_Missive#install-template-to_v1.0` | Tool L4 | 跨 repo 一鍵部署 |
| `CK_Missive#LESSONS_REGISTRY_v1.0` | Doc L2 | 22 條 lessons SSOT |
| `CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0` | Doc L2 | 跨 repo 引用治理規範 |
| `CK_Missive#WAVE_1_PLAYBOOK_v2.2` | Doc L2 | 7 SOP + 1 anti-pattern |
| `CK_Missive#WAVE_2_TO_7_RETROSPECTIVE_v1.0` | Doc L2 | 多 Wave 連續執行回顧 |
| `CK_Missive#consumers_v1.0` | Config L4 | 7 consumer registry |
| `CK_Missive#PULL_REQUEST_TEMPLATE_v1.0` | Doc L4 | 範本貢獻 PR 模板 |
| `CK_Missive#AliasIntegrationDrawer_v1.0` | Component L1 | Drawer 雙 Tab 模式範例 |

## Slash Commands (可用指令)

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/pre-dev-check` | ⚠️ **開發前強制檢查** (必用) | `.claude/commands/pre-dev-check.md` |
| `/route-sync-check` | 前後端路由一致性檢查 | `.claude/commands/route-sync-check.md` |
| `/api-check` | API 端點一致性檢查 | `.claude/commands/api-check.md` |
| `/type-sync` | 型別同步檢查 | `.claude/commands/type-sync.md` |
| `/dev-check` | 開發環境檢查 | `.claude/commands/dev-check.md` |
| `/data-quality-check` | 資料品質檢查 | `.claude/commands/data-quality-check.md` |
| `/db-backup` | 資料庫備份管理 | `.claude/commands/db-backup.md` |
| `/csv-import-validate` | CSV 匯入驗證 | `.claude/commands/csv-import-validate.md` |
| `/security-audit` | 🔒 **CSO 等級資安審計 v2** — OWASP+STRIDE+信心閾值 | `.claude/commands/security-audit.md` |
| `/performance-check` | ⚡ **效能診斷檢查** | `.claude/commands/performance-check.md` |
| `/adr` | 📋 **架構決策記錄 (ADR)** 管理 | `.claude/commands/adr.md` |
| `/knowledge-map` | 🗺️ **知識地圖重建與差異報告** | `.claude/commands/knowledge-map.md` |
| `/health-dashboard` | 📊 **系統健康儀表板** — 行數/測試/遷移/Git 活動 | `.claude/commands/health-dashboard.md` |
| `/refactor-scan` | 🔍 **重構掃描** — 超閾值檔案掃描+拆分建議 | `.claude/commands/refactor-scan.md` |
| `/arch-fitness` | 🧪 **架構 Fitness Functions 本地執行**（零 CI 費用，月度覆盤）| `.claude/commands/arch-fitness.md` |

### gstack 啟發指令 (v2.0.0, 2026-03-23 升級)

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/ship` | 🚀 **統一發布工作流 v2** — 測試歸因+review就緒+bisectable | `.claude/commands/ship.md` |
| `/retro` | 📊 **工程回顧 v2** — per-author+compare+session偵測 | `.claude/commands/retro.md` |
| `/qa-smart` | 🧪 **Diff-Aware 智慧測試** — 4 模式 + 8 維度健康度 | `.claude/commands/qa-smart.md` |
| `/guard` | 🛡️🔒 **綜合安全防護（主入口）** — careful + freeze 合一 | `.claude/commands/guard.md` |
| `/careful` | 🛡️ 危險命令攔截（`/guard` 子集，alias） | `.claude/commands/careful.md` |
| `/freeze` | 🔒 編輯範圍鎖定（`/guard` 子集，alias） | `.claude/commands/freeze.md` |
| `/unfreeze` | 🔓 解除範圍鎖定 — 刪除 freeze-scope.json | `.claude/commands/unfreeze.md` |
| `/document-release` | 📝 **發布後文件同步** — 架構/Skills/CHANGELOG 自動檢查 | `.claude/commands/document-release.md` |

### Everything Claude Code 指令

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/verify` | 綜合驗證檢查 - Build/Type/Lint/Test | `.claude/commands/verify.md` |
| `/tdd` | TDD 工作流 - RED-GREEN-REFACTOR | `.claude/commands/tdd.md` |
| `/checkpoint` | 長對話進度保存 | `.claude/commands/checkpoint.md` |
| `/code-review` | 結構化審查 v2 — Scope Drift+Fix-First | `.claude/commands/code-review.md` |
| `/build-fix` | 快速修復構建錯誤 | `.claude/commands/build-fix.md` |

### Superpowers 指令

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/superpowers:brainstorm` | 互動式設計精煉 | `.claude/commands/superpowers/brainstorm.md` |
| `/superpowers:write-plan` | 建立詳細實作計畫 | `.claude/commands/superpowers/write-plan.md` |
| `/superpowers:execute-plan` | 批次執行計畫 | `.claude/commands/superpowers/execute-plan.md` |

---

## 領域知識 Skills (自動載入)

| Skill 檔案 | 觸發關鍵字 | 說明 |
|------------|------------|------|
| `document-management.md` | 公文, document, 收文, 發文 | 公文管理領域知識 |
| `calendar-integration.md` | 行事曆, calendar, Google Calendar | 行事曆整合規範 (v1.2.0) |
| `api-development.md` | API, endpoint, 端點 | API 開發規範 |
| `database-schema.md` | schema, 資料庫, PostgreSQL | 資料庫結構說明 |
| `testing-guide.md` | test, 測試, pytest | 測試框架指南 |
| `frontend-architecture.md` | 前端, React, 認證, auth, 架構 | 前端架構規範 (v1.4.0) |
| `error-handling.md` | 錯誤處理, error, exception, 例外, ApiErrorBus | 錯誤處理指南 (含 GlobalApiErrorNotifier) |
| `security-hardening.md` | 安全, security, 漏洞, XSS | 安全加固指南 |
| `type-management.md` | 型別, type, Pydantic, TypeScript, BaseModel | 型別管理規範 (SSOT) |
| `api-serialization.md` | 序列化, serialize, ORM, API 返回, 500 錯誤 | API 序列化規範 |
| `python-common-pitfalls.md` | Pydantic, forward reference, async, MissingGreenlet | Python 常見陷阱 |
| `unicode-handling.md` | Unicode, 編碼, 中文, UTF-8, 亂碼, CJK, 正規化, normalize, 搜尋失敗, ILIKE | Unicode 處理規範 (v2.0.0) |
| `workflow-management.md` | workflow, 作業歷程, 時間軸, chain, timeline, batch, 批次, 結案批次, InlineRecordCreator, work_category, WorkRecordStatsCard, useDeleteWorkRecord | 作業歷程管理規範 (v2.0.0) |
| `dispatch-import.md` | 匯入, import, Excel, 派工單匯入, batch-relink, 文號, doc_number | 派工單匯入與公文關聯規範 (v1.0.0) |
| `ai-development.md` | AI, Groq, Ollama, 語意, 摘要, 分類, 同義詞, 知識圖譜, NER, 實體提取, CanonicalEntity, embedding, Agent, 派工單, dispatch, 閒聊, chitchat | AI 功能開發規範 (v3.4.0) |
| `database-performance.md` | 慢查詢, N+1, 索引, 查詢優化, slow query | 資料庫效能優化指南 |
| `development-environment.md` | 環境, Docker, 依賴, 配置, env | 開發環境檢查指南 |
| `accessibility.md` | 可訪問性, a11y, WCAG, ARIA, 鍵盤導航 | 可訪問性規範 (v1.0.0) |
| `alembic-migrations.md` | Alembic, 遷移, migration, schema change | Alembic 遷移管理規範 (v1.0.0) |
| `caching-patterns.md` | 快取, cache, Redis, TTL, React Query | 快取策略規範 (v1.0.0) |
| `knowledge-management.md` | ADR, 決策, 架構圖, 知識管理, 功能生命週期 | 知識管理規範 (v1.0.0) |
| `hooks-development.md` | hooks, 鉤子, 自動化, PreToolUse, PostToolUse | Hooks 開發規範 |
| `skill-creator.md` | skill, 建立 skill, 新增 skill, 改善 skill, SKILL.md | Skill 建立/優化工作流 (v1.0.0) |
| `multi-channel.md` | LINE, Telegram, Discord, 多通道, webhook, bot | 多通道整合開發規範 (v1.0.0) |
| `erp-finance.md` | ERP, 報價, 開票, 請款, 帳本, 費用報銷, 資產 | ERP 財務模組開發規範 (v1.0.0) |
| `tender-search.md` | 標案, tender, PCC, ezbid, g0v, 投標, 決標, 底價 | 標案檢索與分析開發規範 |
| `wiki-authoring.md` | wiki, LLM Wiki, Karpathy, Ingest, Compile, wiki lint, wiki-rag, kg_entity_id | LLM Wiki 4-Phase 開發與維運規範 (v1.0.0) |

### Superpowers Skills (v4.0.3)

| Skill | 觸發關鍵字 | 說明 |
|-------|-----------|------|
| `brainstorming` | 設計, design, 規劃 | 蘇格拉底式設計精煉 |
| `test-driven-development` | TDD, 測試驅動 | RED-GREEN-REFACTOR 循環 |
| `systematic-debugging` | 除錯, debug, 根因分析 | 4 階段根因追蹤流程 |
| `writing-plans` | 計畫, plan, 實作 | 詳細實作計畫撰寫 |
| `executing-plans` | 執行計畫, execute | 批次執行與檢查點 |
| `subagent-driven-development` | subagent, 子代理 | 兩階段審查的子代理開發 |
| `requesting-code-review` | 程式碼審查, code review | 審查前檢查清單 |
| `using-git-worktrees` | worktree, 分支 | 平行開發分支管理 |
| `verification-before-completion` | 驗證, 完成 | 確保修復真正完成 |
| `using-superpowers` | superpowers, 能力 | Superpowers 入口（自動發現與載入） |
| `writing-skills` | 建立 skill, skill 開發 | Skill 撰寫與驗證 meta-skill |

> 位置: `.claude/skills/_shared/shared/superpowers/` (透過 inherit 載入)

### 共享 Skills 庫 (_shared)

| 類別 | Skill | 觸發關鍵字 | 說明 |
|------|-------|-----------|------|
| 共享實踐 | `security-patterns` | 安全, security, 防護 | 安全性最佳實踐 |
| 共享實踐 | `testing-patterns` | 測試, test, coverage | 測試模式指南 |
| 共享實踐 | `systematic-debugging` | 除錯, debug, 調試 | 系統化除錯方法 |
| 共享實踐 | `dangerous-operations-policy` | 危險操作, 刪除, 重置 | 危險操作政策 |
| 共享實踐 | `code-standards` | 程式碼規範, coding style | 程式碼標準 |
| 共享實踐 | `security-audit` | 資安, 審計, audit | 安全審計檢查 |
| 共享實踐 | `data-governance-framework` | 資料治理, governance | 資料治理框架 |
| 共享實踐 | `mandatory-checklist` | 檢查清單, checklist | 強制性檢查清單 |
| 工具 | `quick-fix` | 快修, fix, 修復 | 快速修復工具 |
| 工具 | `crud-migration` | CRUD, 遷移 | CRUD 遷移工具 |
| 工具 | `service-refactoring` | 重構, refactor, service | 服務重構工具 |
| 工具 | `test-generator` | 測試生成, test gen | 測試生成器 |
| 工具 | `refactoring-migration-procedures` | 重構遷移, migration | 重構遷移程序 |

> 位置: `.claude/skills/_shared/shared/`

> **版本歷史**: `.claude/CHANGELOG.md`
> **最新版本**: v5.5.4 (2026-04-09) — AI 子包重構 + UnifiedAgentPage 雙模式 + 系統優化

---

## Agents 代理

### 專案代理

| Agent | 用途 | 檔案 |
|-------|------|------|
| Code Review | 程式碼審查 | `.claude/agents/code-review.md` |
| API Design | API 設計 | `.claude/agents/api-design.md` |
| Bug Investigator | Bug 調查 | `.claude/agents/bug-investigator.md` |
| E2E Runner | E2E 測試執行與管理 | `.claude/agents/e2e-runner.md` |
| Build Error Resolver | 構建/TypeScript 錯誤快速修復 | `.claude/agents/build-error-resolver.md` |

### 共享代理 (_shared)

| Agent | 用途 | 檔案 |
|-------|------|------|
| Build Resolver | 通用構建錯誤修復 | `.claude/agents/_shared/shared/build-resolver.md` |
| Code Reviewer | 通用程式碼審查 | `.claude/agents/_shared/shared/code-reviewer.md` |
| GitHub Workflow | GitHub 工作流管理 | `.claude/agents/_shared/shared/github-workflow.md` |
| Planner | 實作計畫規劃 | `.claude/agents/_shared/shared/planner.md` |
| Security Auditor | 資安審計 | `.claude/agents/_shared/shared/security-auditor.md` |
| TDD Guide | TDD 工作流引導 | `.claude/agents/_shared/shared/tdd-guide.md` |
| Component Generator | React 元件生成 | `.claude/agents/_shared/react/component-generator.md` |
| Test Generator | React 測試生成 | `.claude/agents/_shared/react/test-generator.md` |

---

## 重要規範文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/skills/type-management.md` | 型別管理規範 (SSOT 架構) |
| `.claude/skills/api-serialization.md` | API 序列化規範 |
| `.claude/commands/type-sync.md` | 型別同步檢查 |
| `backend/app/core/dependencies.py` | 依賴注入模組 |
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `docs/specifications/API_ENDPOINT_CONSISTENCY.md` | API 端點一致性 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `docs/specifications/SCHEMA_DB_MAPPING.md` | Schema-DB 欄位對照表 |
| `docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md` | 關聯記錄處理規範 |
| `docs/specifications/UI_DESIGN_STANDARDS.md` | UI 設計規範 |
| `docs/SYSTEM_OPTIMIZATION_REPORT.md` | 系統優化報告 |
| `docs/ALEMBIC_MIGRATION_GUIDE.md` | Alembic 遷移管理指南 |
| `scripts/checks/verify_architecture.py` | 架構驗證腳本 (7 項自動化檢查) |
| `scripts/checks/service-line-count-check.py` | 後端服務行數監控 (>600L 警告，已修正為觀察而非拆分依據 — 見 feedback_ddd_over_line_count) |
| `scripts/checks/service_dir_entropy.py` | 🆕 v5.9.6 — services/ 頂層散戶比例（閾值 20%）|
| `scripts/checks/config_dead_reader_scan.py` | 🆕 v5.9.6 — yaml config dead reader 偵測（ADR-0030 審計配套）|
| `scripts/checks/run_fitness.sh` | 🆕 v5.9.6 — 本地 fitness runner（零 CI 費用，v6.8 升級為 **16 step**）|
| `scripts/checks/integration_liveness_check.py` | 🆕 v6.8 F14 — 整合鏈活體驗證（v3.0 8 接觸面 evidence query / fitness step 15）|
| `scripts/checks/line_notify_heartbeat_check.py` | 🆕 v6.8 F15 — LINE notify 7d 推送計數 watchdog（fitness step 16）|
| `scripts/checks/v7_metrics_report.py` | 🆕 v6.8 M1 — v7.0 4 指標 lite report（取代「成熟度 %」baseline）|
| `scripts/checks/v6_8_acceptance.sh` | 🆕 v6.8 — 一鍵驗證 36 commits 真活（11 項 sanity check，PASS 11/11 0 fail）|
| `docs/architecture/STANDARD_REFERENCE.md` | 🆕 v5.9.6 — 跨 repo 架構標準（12 章 + §13 AI-Native UX）|
| `docs/architecture/SERVICE_CONTEXT_MAP.md` | 🆕 v5.9.6 — 85 散戶 × 16 bounded context 映射 |
| `docs/ops/baseline-fix-patch-preview.md` | 🆕 v5.9.5 — Hermes baseline 修復 patch 預覽 |
| `docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` | 🆕 v5.9.7/v5.9.8 — 坤哥意識體 5 整合面向 + O1-O6 路線（含落地紀錄 §9）|
| `docs/architecture/WIKI_KG_BACKFILL_STRATEGY.md` | 🆕 v5.9.7 — 方案 X/Y/Z ROI 對比（已執行 X）|
| `scripts/checks/soul_mirror_drift_check.py` | 🆕 v5.9.7 — SOUL.md 跨 repo drift 偵測（fitness step 3）|
| `scripts/checks/wiki_kg_link_audit.py` | 🆕 v5.9.7 — Wiki↔KG 連結率 by entity_type 審計（fitness step 4）|
| `scripts/checks/kg_embedding_coverage_check.py` | 🆕 v5.9.8 — KG pgvector embedding 覆蓋率審計（fitness step 5）|
| `scripts/sync/sync_soul_to_hermes.sh` | 🆕 v5.9.7 — SOUL.md 跨 repo 手動同步（--apply gate）|
| `scripts/sync/dispatch_kg_ingest.py` | 🆕 v5.9.8 — dispatch → KG canonical_entities ingest |
| `scripts/sync/backfill_wiki_dispatch_kg.py` | 🆕 v5.9.8 — wiki dispatch frontmatter 補 kg_entity_id |
| `scripts/sync/backfill_wiki_project_kg.py` | 🆕 v5.9.8 — wiki project 跨 entity_type 匹配 |
| `scripts/sync/backfill_kg_embeddings_all.py` | 🆕 v5.9.8 — 通用 KG embedding backfill（critical/types/all 模式）|
| `scripts/sync/backfill_dispatch_embeddings.py` | 🆕 v5.9.8 — dispatch embedding pilot（127 筆 / 4 秒驗證）|
| `scripts/checks/async_session_race_guard.py` | 🆕 ADR-0028 靜態守護：`asyncio.gather` 內多 task 不得共用 db session（承接 ADR-0021） |
| `scripts/checks/sse_headers_guard.py` | 🆕 ADR-0028 靜態守護：SSE endpoint 必須含 `Content-Encoding: identity` |
| `scripts/checks/adr_lifecycle_check.py` | 🆕 ADR-0029 自動統計 active / archived / removed ADR 分佈 |
| `scripts/checks/schema_lazy_load_guard.py` | ADR-0027 配套：Pydantic schema 不得訪問 ORM lazy relationship |
| `docs/adr/0028-error-contract-silent-failure-policy.md` | 🆕 錯誤合約化 + Silent Failure 政策（歸納 v5.7.1+v5.8.1 共 11 層） |
| `docs/adr/0029-adr-lifecycle-policy.md` | 🆕 ADR Lifecycle Policy + archived 狀態引入 |
| `docs/adr/0030-hermes-go-no-go-revision.md` | 🆕 Hermes GO/NO-GO 決策重訂（baseline 30 + LINE canary + 2026-05-20 硬 deadline）|
| `docs/adr/0031-frontend-page-consolidation.md` | 🆕 前端頁面整合 v6.0（坤哥唯一入口 + 圖譜中樞）|
| `docs/BUSINESS_VALUE.md` | 🆕 對外敘事：把 Memory Wiki / 坤哥翻譯為商業語言 |
| `docs/archive/nemoclaw-archival-checklist.md` | 🆕 NemoClaw/OpenClaw 5 Sprint 歸檔清單（5/26 deadline）|
| `configs/grafana/dashboards/ck-missive-{http,db-pool,inference}.json` | 🆕 觀測棧 3 Grafana dashboards（19 panels）|
| `configs/prometheus/alerts.yml` | 🆕 觀測棧 12 alert rules（error_budget / silent_failure / capacity / business）|
| `configs/grafana/promtail-pm2.yml` v2 | PM2 log → Loki 5 scrape targets |
| `configs/grafana/README.md` | 🆕 觀測棧部署指南（CK_DigitalTunnel 端 provisioning） |
| `frontend/src/components/kunge/OpsDashboard.tsx` | 🆕 ADR-0031：原 UnifiedAgentPage 降格 |
| `frontend/src/components/memory/MemoryStatsRow.tsx` | 🆕 ADR-0031：6-Card 記憶統計共用元件（省 126L） |
| `frontend/src/components/graph/ForceGraphLazy.tsx` | 🆕 ADR-0031：react-force-graph-2d 統一 lazy wrapper（generic） |
| `frontend/src/pages/GraphHubPage.tsx` | 🆕 ADR-0031：`/ai/graphs` 圖譜與 Wiki 中樞 |
| `backend/app/services/expense_approval_service.py` | 費用審核工作流 (多層審批+預算聯防) |
| `backend/app/services/expense_import_service.py` | 費用匯入匯出 (QR+Excel+電子發票) |
| `backend/app/services/invoice_recognizer.py` | 統一發票辨識器 (QR+OCR) |
| `backend/app/api/endpoints/erp/expenses_io.py` | 費用 IO 端點 (掃描/匯入/收據/AI分類) |
| `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md` | LINE + OpenClaw 運維指南（**將下線** — ADR-0014，2026-05-12 歸檔） |
| `docs/adr/0014-hermes-replace-openclaw.md` | 🆕 ADR-0014：以 NousResearch Hermes Agent 取代 OpenClaw |
| `docs/adr/0015-retire-nemoclaw-cloudflare-tunnel.md` | 🆕 ADR-0015：廢止 NemoClaw，改用 Cloudflare Tunnel |
| `docs/adr/0016-multi-project-platform-subdomain.md` | 🆕 ADR-0016：多專案平坦分域（missive/hermes/lvrland/pile） |
| `docs/adr/0019-structlog-unified-logging.md` | 🆕 ADR-0019：structlog stdlib bridge 統一 JSON 日誌（v5.6.0 accepted） |
| `docs/HERMES_MIGRATION_PLAN.md` | 🆕 Hermes 4-Phase 遷移計畫（Day 0~28） |
| `docs/hermes-skills/README.md` | 🆕 Hermes skill 整合層次 L1~L4 + API public contract |
| `docs/hermes-skills/ck-missive-bridge/` | 🆕 Hermes skill 部署包（SKILL.md + tools.py + tool_spec.json + install.sh）|
| `backend/app/services/ai/agent/shadow_logger.py` | 🆕 Shadow Logger（PII 遮罩 + 30d retention + A/B provider 分析） |
| `scripts/checks/shadow-baseline-report.cjs` | 🆕 Shadow baseline 報告（channel/provider/tool 分佈） |
| `scripts/checks/synthetic-baseline-inject.py` | 🆕 合成基線注入（24 query × 5 域，排程 3x/日） |
| `scripts/checks/soul-fidelity-eval.py` | 🆕 Soul.md 人格一致性跨 provider 評估 |
| `scripts/health/health-watchdog.sh` | 🆕 Health Watchdog（PM2 cron */2min，假死偵測 + 自動 restart） |
| `scripts/deploy/deploy-public.sh` | 🆕 公網部署一鍵腳本（build → restart → verify） |
| `backend/app/services/wiki_formatter.py` | 🆕 Wiki Markdown 格式化（拆分自 wiki_compiler，164L） |
| `backend/app/core/structured_logging.py` | 🆕 structlog stdlib bridge（239 service 自動 JSON，ADR-0019） |
| `backend/app/api/endpoints/ai/tools_manifest.py` | 🆕 v1.1 — 加 compat/endpoints/auth，Hermes public contract 入口 |
| `docs/LINE_BOT_SETUP_GUIDE.md` | LINE Bot 直連啟用指南 |
| `docs/MULTICHANNEL_SETUP_GUIDE.md` | 多頻道部署指南 (Telegram + LINE) |
| `backend/app/services/line_bot_service.py` | LINE Bot Service (直連模式) |
| `backend/app/services/audit_mixin.py` | CRUD 審計 Mixin (10 服務套用) |
| `backend/app/services/ai/domain/digital_twin_service.py` | 數位分身 Service 層 (ai/domain/ 子包) |
| `frontend/src/pages/UnifiedAgentPage.tsx` | 智能體統一頁面 (雙模式: user/admin) |
| `backend/app/services/ai/domain/morning_report_service.py` | 🆕 晨報生成 (926L) — 聚合 CTE + 6 層 closure_level + sections filter |
| `backend/app/services/ai/domain/morning_report_delivery.py` | 🆕 晨報派送 (240L) — delivery_log + snapshot + subscription + 失敗告警 |
| `frontend/src/components/taoyuan/MorningReportTrackingTable.tsx` | 🆕 派工狀態追蹤表格（expandable per-type rows） |
| `frontend/src/components/taoyuan/DispatchOverviewTab.tsx` | 🆕 v2.0 — 方案 C 看板+表格 Segmented，統一 morning-status |
| `scripts/init/backfill_work_type_id.py` | 🆕 work_type_id 回填腳本（62 auto / 7 manual） |
| `docs/DOCKER_SECRETS_PHASE1.md` | Docker Secrets Phase 1 盤點（76 env vars 3 tier） |
| `backend/app/core/prometheus_middleware.py` | 🆕 Prometheus /metrics 中介層（request count/duration/active） |
| `backend/app/core/scheduler_alert.py` | 🆕 排程器失敗 Telegram 告警（threshold + cooldown） |
| `backend/app/core/secret_loader.py` | 🆕 Docker Secrets file→env fallback 載入器 |
| `backend/app/core/json_log_formatter.py` | 🆕 Loki-compatible JSON 日誌格式化 |
| `backend/app/core/db_pool_metrics.py` | 🆕 DB Pool Prometheus gauge（active/checkout/overflow） |
| `backend/app/core/db_query_metrics.py` | 🆕 DB Query duration histogram + slow query counter |
| `backend/app/core/db_query_listener.py` | 🆕 SQLAlchemy event listener → query metrics |
| `backend/app/core/inference_semaphore.py` | 🆕 GPU 推理並發控制（max=3，防 VRAM OOM） |
| `backend/app/core/inference_provider_metrics.py` | 🆕 推理 provider completion/fallback Prometheus |
| `backend/app/core/hnsw_config.py` | 🆕 HNSW ef_search 動態配置（precise/default/batch） |
| `backend/app/core/kg_stats_metrics.py` | 🆕 KG entity/edge/wiki Prometheus gauge |
| `backend/app/core/entity_resolution_benchmark.py` | 🆕 Entity resolution 效能基準報告 |
| `backend/app/services/ai/misc/missive_agent.py` | 🆕 MissiveAgent（自覺型 Agent，renamed from NemoClawAgent） |
| `backend/app/api/endpoints/ai/agent_capability.py` | 🆕 Agent 能力自覺 + 聯邦端點（renamed from agent_nemoclaw） |
| `backend/app/services/ai/domain/morning_report_formatter.py` | 🆕 晨報格式化（純函數，拆分自 service） |
| `@AGENT.md` | 開發代理指引 |
