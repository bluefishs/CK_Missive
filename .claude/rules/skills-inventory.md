# Skills / Commands / Agents 清單

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

### gstack 啟發指令 (v2.0.0, 2026-03-23 升級)

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/ship` | 🚀 **統一發布工作流 v2** — 測試歸因+review就緒+bisectable | `.claude/commands/ship.md` |
| `/retro` | 📊 **工程回顧 v2** — per-author+compare+session偵測 | `.claude/commands/retro.md` |
| `/qa-smart` | 🧪 **Diff-Aware 智慧測試** — 4 模式 + 8 維度健康度 | `.claude/commands/qa-smart.md` |
| `/careful` | 🛡️ **危險命令攔截** — PreToolUse hook 自動攔截破壞性操作 | `.claude/commands/careful.md` |
| `/freeze` | 🔒 **編輯範圍鎖定** — 限制 Edit/Write 到指定目錄 | `.claude/commands/freeze.md` |
| `/unfreeze` | 🔓 **解除範圍鎖定** — 刪除 freeze-scope.json | `.claude/commands/unfreeze.md` |
| `/guard` | 🛡️🔒 **綜合安全防護** — careful + freeze 合一 | `.claude/commands/guard.md` |
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
| 工具 | `plan-workflow` | 計畫, workflow | 計畫工作流 |
| 工具 | `tdd-workflow` | TDD, 測試驅動 | TDD 工作流 |
| 工具 | `refactoring-migration-procedures` | 重構遷移, migration | 重構遷移程序 |

> 位置: `.claude/skills/_shared/shared/`

> **版本歷史已移至** `.claude/CHANGELOG.md`，此處僅保留清單與代理。

---

## v5.3.23 品質修正 (2026-04-02, 15 commits)

| 項目 | 說明 |
|------|------|
| fix: vendors 422 | 廠商 API 驗證修正 |
| fix: tender create-case | 建案邏輯修正 (僅建 PM Case，不建 ERP) + duplicate prevention |
| fix: PM cases year filter | 年度篩選改用 `date.today().year` (移除硬編碼 2025) |
| fix: PM case delete | 刪除修正 + tender create-case 欄位映射 |
| chore: ER model | 標案表更新後 ER 模型同步 |
| docs: session summary | v5.3.23 版本文件同步 |

---

## v5.3.22 標案檢索模組 (2026-04-01~02, 46 commits)

### 標案模組

| 類型 | 項目 | 說明 |
|------|------|------|
| Service | `tender_search_service.py` | PCC API 封裝 + Redis 快取 |
| Service | `tender_subscription_scheduler.py` | 訂閱排程 3次/日 + LINE/Discord |
| API | `tender.py` | 17 端點 (search/detail/graph/subscriptions/bookmarks) |
| Model | `tender.py` | TenderSubscription + TenderBookmark |
| Page | `TenderSearchPage.tsx` | 3-Tab (搜尋/收藏/訂閱) |
| Page | `TenderDetailPage.tsx` | 4-Tab (總覽/生命週期/得標/同機關) |
| Page | `TenderCompanyPage.tsx` | 廠商投標歷史 + 圓餅圖 |
| Page | `TenderGraphPage.tsx` | 知識圖譜 (力導引) |
| Agent | `#29 search_tender` | 標案搜尋 |
| Agent | `#30 auto_tender_to_case` | Multi-Agent 自動建案 |

### 品質優化

| 項目 | 說明 |
|------|------|
| Bug Fix | 公文刪除 409, 導覽 400 (根治), 年度統一, client-accounts |
| 標準化 | NFKC 5服務, .xls 統一, 千分位, 導覽自動同步 |
| 架構 | endpoints 域拆分 (1309→8 files), context -33%, .dockerignore |
| 測試 | 49→18 failures, ERP 整合 12 cases |
| ERP | 47 請款 + 47 發票 + 35 帳本, 相機拍照, 收款通知 |

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
| `scripts/checks/service-line-count-check.py` | 後端服務行數監控 (>600L 警告) |
| `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md` | LINE + OpenClaw 運維指南 |
| `docs/LINE_BOT_SETUP_GUIDE.md` | LINE Bot 直連啟用指南 |
| `docs/MULTICHANNEL_SETUP_GUIDE.md` | 多頻道部署指南 (Telegram + LINE) |
| `backend/app/services/line_bot_service.py` | LINE Bot Service (直連模式) |
| `backend/app/services/audit_mixin.py` | CRUD 審計 Mixin (10 服務套用) |
| `backend/app/services/ai/digital_twin_service.py` | 數位分身 Service 層 |
| `@AGENT.md` | 開發代理指引 |
