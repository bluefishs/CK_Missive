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

---

## v5.2.3 多通道整合 — Discord Bot + Cloudflare Tunnel + ChannelAdapter (2026-03-25)

### 新增模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `core/tunnel_guard.py` | Middleware | 外網路由守衛 (Cloudflare/ngrok aware, 111L) |
| `services/discord_bot_service.py` | Service | Discord Bot Interactions Endpoint (212L) |
| `services/channel_adapter.py` | Abstract | 統一通道抽象 LINE/Discord/Telegram (126L) |
| `api/endpoints/discord_webhook.py` | API | Discord webhook + push (170L) |
| `schemas/discord.py` | Schema | Discord Bot Schemas |
| `services/ai/agent_tool_loop.py` | Service | Agent 工具迴圈 (拆分自 orchestrator, 273L) |
| `configs/cloudflare-tunnel.yml` | Config | Cloudflare Tunnel 路由配置 |
| `scripts/dev/start-tunnel.ps1` | Script | Tunnel 啟動腳本 (Cloudflare 優先, ngrok 回退) |

### 優化項目

| 項目 | 變更 | 說明 |
|------|------|------|
| `digital_twin_service.py` | v1.0→v1.1 | Dashboard asyncio.gather 並行化 + git branch 安全驗證 |
| `agent_orchestrator.py` | 682→497L | 工具迴圈提取至 agent_tool_loop.py (-27%) |
| `line_webhook.py` | +dedup | 訊息去重 (message_id, 10s TTL, 防 LINE 重發) |
| `main.py` | +middleware | TunnelGuardMiddleware 註冊 |
| `routes.py` | +router | Discord webhook router 註冊 |

### 品質指標 (v5.2.3)

| 維度 | 值 |
|------|-----|
| TypeScript | **0 errors** |
| Backend Tests | **2792 passed** / 1 flaky / 6 skipped |
| Orchestrator | **497L** (was 682L) |
| 新增模組 | 8 files, 961L total |
| 通道支援 | LINE + Discord (+ Telegram via OpenClaw) |

---

## v5.2.2 穩定化 — 數位分身拆分 + 審計 Mixin + FK 索引 + 元件輕量化 (2026-03-25)

### 新增模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `services/ai/digital_twin_service.py` | Service | 數位分身業務邏輯 (337L, 從 endpoint 提取) |
| `services/audit_mixin.py` | Mixin | CRUD 審計追蹤 Mixin (87L, 10 服務套用) |
| `alembic/20260325a001` | Migration | 補齊 7 個 FK 索引 (calendar/core/document/erp/finance/invoice) |
| `components/common/UnifiedTableFilters.tsx` | Component | 表格篩選器抽取 (246L, 從 UnifiedTable 拆分) |
| `components/taoyuan/DispatchOrdersModals.tsx` | Component | 派工單 Modal 抽取 (143L) |
| `components/taoyuan/ProjectsTabColumns.tsx` | Component | 專案欄位定義抽取 (189L) |
| `pages/digitalTwin/` | Page子元件 | CapabilityRadarTab + ProfileCard + TraceWaterfallTab (489L) |
| `scripts/checks/service-line-count-check.py` | Script | 後端服務行數監控 (>600L 警告) |

### 新增測試

| 檔案 | 說明 |
|------|------|
| `test_services/test_line_bot_service.py` | LINE Bot Service 單元測試 (104L) |
| `test_services/test_digital_twin_endpoints.py` | 數位分身端點測試 |
| `test_services/test_document_natural_search.py` | 文件自然語言搜尋測試 |
| `test_services/test_pm_attachments.py` | PM 案件附件測試 |
| `test_services/test_cross_domain_linker.py` | 跨域關聯器測試 |
| `__tests__/pages/ERPExpensePages.test.tsx` | 費用報銷頁面前端測試 |
| `__tests__/pages/ERPLedgerPages.test.tsx` | 統一帳本頁面前端測試 |

### 重構 / 瘦身

| 模組 | 變更 | 說明 |
|------|------|------|
| `digital_twin.py` (endpoint) | 626L 減量 | 業務邏輯遷移到 digital_twin_service.py |
| `UnifiedTable.tsx` | -204L | 篩選邏輯抽取到 UnifiedTableFilters.tsx |
| `DispatchOrdersTab.tsx` | -100L | Modal 抽取到 DispatchOrdersModals.tsx |
| `ProjectsTab.tsx` | -175L | 欄位定義抽取到 ProjectsTabColumns.tsx |
| `DigitalTwinPage.tsx` | -379L | 子元件拆分到 pages/digitalTwin/ |
| 10 服務 | +audit_mixin | 統一審計追蹤 (agency/vendor/case_code/document/project/billing/invoice/quotation/vendor_payable/expense_invoice/finance_ledger) |

### 品質指標 (v5.2.2)

| 維度 | 值 |
|------|-----|
| TypeScript | **0 errors** |
| Backend Tests | **2789 passed** / 4 failed / 6 skipped |
| 前端元件 >500L | **0** (max: 499L) |
| 後端非 AI 服務 >600L | **0** (max: 525L) |
| 後端 AI 服務 >700L | **0** (max: 682L) |
| FK 索引覆蓋 | **+7** (calendar/core/document/erp/finance/invoice) |

---

## v5.2.5 深度修復 — 派工資料清理 + 公文配對精準化 + API 錯誤碼正規化 + 效能優化 (2026-03-27)

### 新增/修改模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `services/ai/rag_retrieval.py` | Service | RAG 檢索 (348L, 拆分自 rag_query) |
| `core/service_health_probe.py` | Core | 服務健康探測器 (213L, 自動偵測斷線+週期修復) |
| `core/cache_decorator.py` | Core | Redis 快取裝飾器 (107L) |
| `useDocumentProjectStaff.ts` | Hook | 公文專案人員管理 (113L, 拆分自 useDocumentDetail) |

### 修復項目

| 項目 | 變更 | 說明 |
|------|------|------|
| dispatch/list | Bug | **MissingGreenlet** — selectinload 補齊深層關聯 |
| StaffTab + useDocumentDetail | SSOT | 硬編碼 API 路徑 → 端點常數 |
| dispatch correspondence | Bug | "unassigned" 跨派工修復 (referenced_by_dispatch_ids) |
| score_document_relevance | 精準化 | 閾值 0.15→0.3, generic doc score 0.5→0.1 |
| extract_core_identifiers | Regex | 排除至/與/弄/巷/站 prefix 避免路名誤判 |
| digital-twin/health | 安全 | 補齊 require_auth 認證 |
| task proxy | API | 錯誤回應 200→4xx/5xx (JSONResponse) |
| useLiveActivitySSE | 前端 | 事件去重 (防重複渲染) |
| relation_graph FK | 效能 | 兩處 FK 查詢合併 UNION |
| canonical_entity embedding | 效能 | 批次 API N→1 呼叫 |
| dispatch detail endpoint | Bug | 移除 response_model, 改用 Response(json.dumps) 避免序列化錯誤 |

### 資料清理

| 項目 | 說明 |
|------|------|
| 115年派工資料 | 清除 70 筆錯誤公文關聯 |
| Docker port 衝突 | 解決 ck_missive_app 容器 8001 端口佔用 |

### 品質指標 (v5.2.5)

| 維度 | 值 |
|------|-----|
| TypeScript | **0 errors** |
| Python 語法 | **0 errors** |
| 公文配對精準度 | 提升 (閾值 + regex 修正) |
| API 錯誤碼 | 正規化 (task proxy 200→4xx/5xx) |
| 效能 | relation_graph UNION + embedding batch |
| 資料清理 | 70 筆錯誤關聯移除 |

---

## v5.2.4 品質強化 — SSOT 修復 + 拆分 + MissingGreenlet 修復 (2026-03-27)

### 新增/拆分模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `services/ai/rag_retrieval.py` | Service | RAG 檢索 (348L, 拆分自 rag_query 555→267L) |
| `services/ai/agent_tool_loop.py` | Service | Agent 工具迴圈 (273L, 拆分自 orchestrator) |
| `services/ai/agent_plan_enricher.py` | Service | 規劃豐富器 (158L, 拆分自 planner) |
| `services/ai/canonical_entity_resolver.py` | Service | 實體解析器 (200L, 拆分自 canonical_entity_service) |
| `services/ai/pattern_semantic_matcher.py` | Service | 語意匹配 (拆分自 agent_pattern_learner 592→486L) |
| `services/line_flex_builder.py` | Service | LINE Flex Message 建構器 (拆分自 line_bot 582→362L) |
| `services/line_image_handler.py` | Service | LINE 圖片處理 |
| `services/notification_dispatcher.py` | Service | 通知派發 |
| `services/document_calendar_integrator.py` | Service | 公文行事曆整合 |
| `core/service_health_probe.py` | Core | 服務健康探測器 (213L, 自動偵測斷線+週期修復) |
| `core/cache_decorator.py` | Core | Redis 快取裝飾器 (107L) |
| `useDocumentProjectStaff.ts` | Hook | 公文專案人員管理 (113L, 拆分自 useDocumentDetail 514→442L) |

### 修復項目

| 項目 | 變更 | 說明 |
|------|------|------|
| StaffTab.tsx | SSOT | 硬編碼 API 路徑 → 端點常數 + 新增 `ASSIGNMENT_DELETE` 端點 |
| useDocumentDetail.ts | SSOT | 硬編碼 API 路徑 → 端點常數 |
| hooks/system/index.ts | Export | 補齊 `useDigitalTwinSSE` 匯出 |
| endpoints.ts | 整合 | `DIGITAL_TWIN_ENDPOINTS` 納入主 `API_ENDPOINTS` |
| finance_ledger_service.py | TODO | 完成全公司餘額查詢邏輯 |
| dispatch_order_repository.py | Bug | **MissingGreenlet 修復** — 列表查詢補齊深層 selectinload |

### 品質指標 (v5.2.4)

| 維度 | 值 |
|------|-----|
| TypeScript | **0 errors** |
| Python 語法 | **0 errors** |
| 硬編碼 API 路徑 | **0** (2→0) |
| dispatch/list 500 | **修復** (MissingGreenlet → selectinload) |
| 前端 >500L hooks | **0** (useDocumentDetail 514→442L) |
| 後端服務全部 <600L | **確認** |

---

## v5.1 ERP 財務模組 Phase 1~7-D + Agent Federation v2.0 (2026-03-22)

### 新增後端模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `models/invoice.py` | ORM | ExpenseInvoice + ExpenseInvoiceItem (79L) |
| `models/finance.py` | ORM | FinanceLedger — 統一帳本 (66L) |
| `schemas/erp/expense.py` | Schema | 費用報銷 CRUD + QR + Query (8 classes, EXPENSE_CATEGORIES Literal) |
| `schemas/erp/ledger.py` | Schema | 帳本 CRUD + Balance + Breakdown (7 classes) |
| `schemas/erp/financial_summary.py` | Schema | 專案/公司彙總 (6 classes) |
| `schemas/ai/rag.py` | Schema | Schema v1.0 CK-AaaP 統一信封 (7 classes + detect_request_format) |
| `repositories/erp/expense_invoice_repository.py` | Repo | 費用報銷查詢 + inv_num 唯一 |
| `repositories/erp/ledger_repository.py` | Repo | 帳本餘額 (Decimal) + 分類彙總 |
| `repositories/erp/financial_summary_repository.py` | Repo | 跨模組 JOIN — project_summary + company_overview |
| `services/expense_invoice_service.py` | Service | QR 解析 + CRUD + 審核入帳 (7 方法) |
| `services/finance_ledger_service.py` | Service | 帳本記錄 + 餘額 + 分類 (7 方法) |
| `services/financial_summary_service.py` | Service | 專案/全案/公司級彙總 + 月趨勢 + 預算排名 |
| `services/finance_export_service.py` | Service | 財務報表匯出 (Excel/CSV) |
| `services/invoice_ocr_service.py` | Service | 發票 OCR 解析 (Tesseract) |
| `services/einvoice/einvoice_sync_service.py` | Service | MOF 電子發票同步 (HMAC-SHA256 + APScheduler) |
| `services/ai/cross_domain_contribution_service.py` | Service | 跨域貢獻追蹤 (KG federation) |
| `repositories/erp/einvoice_sync_repository.py` | Repo | 電子發票同步日誌 + 去重 |
| `endpoints/erp/expenses.py` | API | 9 端點 (list/create/detail/update/approve/reject/qr-scan/upload-receipt/ocr-parse) |
| `endpoints/erp/ledger.py` | API | 6 端點 (list/create/detail/balance/category-breakdown/delete) |
| `endpoints/erp/financial_summary.py` | API | 7 端點 (project/projects/company/monthly-trend/budget-ranking/export-expenses/export-ledger) |
| `endpoints/erp/einvoice_sync.py` | API | 4 端點 (sync/pending-list/upload-receipt/sync-logs) |
| `alembic/3fc21c653f96` | Migration | 3 表: expense_invoices, expense_invoice_items, finance_ledgers |
| `alembic/20260321a001` | Migration | 電子發票同步日誌表 einvoice_sync_logs |
| `alembic/20260321a002` | Migration | 費用多幣別欄位 (currency, exchange_rate) |
| `alembic/20260322a001` | Migration | KG federation 欄位 (source_system, federation_id) |

### 修改核心模組

| 模組 | 版本 | 變更說明 |
|------|------|---------|
| `agent_query_sync.py` | v1.2→v2.0 | 雙格式支援 (v0 legacy + v1 Schema), 3 錯誤碼 |
| `federation_client.py` | v1.0→v3.0 | NemoClaw Registry 動態發現 + Gateway 路由 + TTL 快取 |
| `main.py` | — | Prometheus /metrics 端點 (5 Gauge: app/db/memory/cpu) |
| `startup.py` | — | BACKEND_PORT 環境變數 + bind-based port 偵測 |
| `requirements.txt` | — | +4 依賴 (email-validator, PyYAML, APScheduler, prometheus-client) |

### 新增前端模組

| 模組 | 類型 | 說明 |
|------|------|------|
| `pages/ERPExpenseListPage.tsx` | Page | 費用報銷列表 (篩選+搜尋+狀態標籤) |
| `pages/ERPExpenseDetailPage.tsx` | Page | 費用報銷詳情 (明細+審核+收據上傳) |
| `pages/ERPLedgerPage.tsx` | Page | 統一帳本 (科目分類+餘額) |
| `pages/ERPFinancialDashboardPage.tsx` | Page | 財務儀表板 (月趨勢+預算排名+Recharts) |
| `pages/ERPEInvoiceSyncPage.tsx` | Page | 電子發票同步 (MOF 同步狀態+待核銷) |
| `api/erp/expensesApi.ts` | API | 費用報銷 API (9 端點) |
| `api/erp/ledgerApi.ts` | API | 統一帳本 API (6 端點) |
| `api/erp/financialSummaryApi.ts` | API | 財務彙總 API (7 端點) |
| `api/erp/einvoiceSyncApi.ts` | API | 電子發票同步 API (4 端點) |
| `hooks/business/useERPFinance.ts` | Hook | ERP 財務 hooks (expenses/ledger/dashboard/einvoice) |
| `types/erp.ts` | Type | ERP 型別擴充 (+452L: 費用/帳本/發票/儀表板) |

### 測試

| 檔案 | 測試數 | 說明 |
|------|--------|------|
| `tests/unit/test_expense_invoice.py` | 76 | Schema 驗證 + QR 解析 + Service 邏輯 + Query + 安全加固 |
| `tests/unit/test_finance_export.py` | 19 | 財務報表匯出測試 |
| `tests/unit/test_invoice_ocr.py` | 11 | 發票 OCR 解析測試 |
| `tests/unit/test_services/test_financial_dashboard.py` | 13 | 月趨勢 + 預算排名 + Schema 驗證 |
| `tests/unit/test_services/test_nightly_scanner.py` | 8 | NemoClaw 夜間吹哨者排程測試 |
| `tests/unit/test_services/test_erp_quotation_service.py` | 26 | 報價 CRUD + 利潤 + 預算控制 |
| `tests/integration/test_agent_query_sync_v1.py` | — | Agent 同步 API v1 整合測試 |

---

## v5.0 NemoClaw 代理人 — 全模組盤點 (2026-03-20)

### NemoClaw 代理人新增模組 (v4.0→v5.0)

| 模組 | 版本 | 說明 |
|------|------|------|
| `nemoclaw_agent.py` | v2.0 | NemoClaw 代理人主體 (自覺層 wrapper) |
| `agent_self_profile.py` | v1.0 | Agent 自我檔案 (強項/弱項/總查詢) |
| `agent_proactive_scanner.py` | v1.0 | 主動掃描 (截止日/異常/通知) |
| `agent_capability_tracker.py` | v1.0 | 能力自覺 (按領域分析表現) |
| `agent_mirror_feedback.py` | v1.0 | 鏡像回饋 (LLM 自我觀察報告) |
| `skill_scanner.py` | v1.0 | 技能自動發現 (51 skills from .claude/) |
| `skill_evolution_service.py` | v1.0 | 技能演化樹數據生成 |
| `kb_embedding_service.py` | v1.0 | 知識庫向量搜尋 (2343 chunks) |

### 獨立專案: CK_NemoClaw (監控塔)

| 檔案 | 說明 |
|------|------|
| `Dockerfile` | nginx:alpine 沙箱策略 API |
| `docker-compose.yml` | 多容器編排 (tower + plugins) |
| `sandbox/policy.yaml` | 全域安全策略 |
| `config/platform.yaml` | 插件註冊 + 共享服務 |
| `agents/ck-missive/` | 公文代理人腳本 |

### 乾坤智能體 (NemoClaw Agent) 模組清單 (41 模組, 74 工具)

| 模組 | 版本 | 說明 |
|------|------|------|
| `agent_orchestrator.py` | v2.6.0 | 主編排: ReAct loop + SSE + Router 整合 |
| `agent_tools.py` | v2.0.0 | 工具調度入口 (260L, 委派 3 子執行器) |
| `agent_planner.py` | v2.4.0 | 意圖解析 + LLM 規劃 + 6 策略自動修正 + 跨會話學習注入 |
| `agent_synthesis.py` | v1.8.0 | 答案合成 (518L, citation+thinking 已提取) |
| `agent_pattern_learner.py` | v2.0.0 | 模式學習: MD5 精確 → Embedding cosine similarity |
| `agent_summarizer.py` | v2.0.0 | 3-Tier 自適應壓縮 + 學習萃取持久化 |
| `agent_diagram_builder.py` | v1.0.0 | 4 類 Mermaid 圖表 (ER/依賴/流程/類別) |
| `agent_tool_monitor.py` | v1.0.0 | 滑動窗口監控 + 自動降級(<30%)/恢復(>70%) |
| `agent_supervisor.py` | v1.0.0 | 多域分解 (doc/pm/erp/dispatch) + 並行子任務 |
| `agent_trace.py` | v1.0.0 | Span 計時 + 指標收集 + DB 持久化 |
| `agent_chitchat.py` | v1.0.0 | 閒聊偵測 (反向關鍵字) + 8 回退模式 |
| `agent_roles.py` | v1.1.0 | 5 角色定義 (CK/Doc/Dev/Dispatch/Graph) |
| `agent_router.py` | v1.0.0 | 3 層路由: chitchat → pattern → llm |
| `agent_conversation_memory.py` | v1.0.0 | Redis 對話記憶 (1h TTL, 自動延展) |
| `agent_utils.py` | v1.0.0 | JSON 4 階段解析 + SSE 格式化 |
| `tool_executor_search.py` | v1.0.0 | 搜尋工具 (540L): doc/dispatch/entity/similar/correspondence |
| `tool_executor_analysis.py` | v1.0.0 | 分析工具 (405L): detail/stats/health/graph/diagram |
| `tool_executor_domain.py` | v1.0.0 | PM/ERP 工具 (105L): projects/vendors/contracts |
| `tool_chain_resolver.py` | v1.0.0 | Chain-of-Tools 自動參數注入 |
| `citation_validator.py` | v1.0.0 | 引用準確性驗證 (精確+模糊匹配) |
| `thinking_filter.py` | v1.0.0 | LLM thinking 標記 5 階段過濾 |
| `pattern_seeds.py` | v1.0.0 | 冷啟動種子模式 (29 個, 7 類別) |
| `user_preference_extractor.py` | v1.0.0 | 雙層使用者記憶 (Redis+DB) + 偏好注入 |
| `document_chunker.py` | v1.0.0 | 文件分段 (段落+滑動窗口+合併) |
| `agent_conductor.py` | v1.0.0 | Conductor 式並行 Agent 編排 |
| `agent_self_evaluator.py` | v1.0.0 | 每次回答自動評分 (5 維度) |
| `agent_evolution_scheduler.py` | v1.0.0 | 每 50 次/24h 自動進化排程 |
| `voice_transcriber.py` | v1.0.0 | 語音轉文字服務 |
| `federation_client.py` | v1.0.0 | OpenClaw 聯邦整合客戶端 |
| `tool_executor_document.py` | v1.0.0 | 文件工具子執行器 |
| `proactive_recommender.py` | v1.0.0 | 主動推薦引擎 |
| `user_query_tracker.py` | v1.0.0 | 使用者查詢追蹤統計 |
| `agent_auto_corrector.py` | v1.0.0 | 6 策略自動修正 (拆分自 planner) |
| `agent_learning_injector.py` | v1.0.0 | 跨會話學習注入 (拆分自 planner) |

### AI 服務全量盤點 (70 模組)

| 分類 | 模組數 | 說明 |
|------|--------|------|
| 核心基礎 | 9 | ai_config, base_ai, doc_ai, doc_analysis, doc_chunker, embedding, NER, rag_query, rag_retrieval |
| 乾坤 Agent | 36 | orchestrator+tool_loop+planner+plan_enricher+synthesis+router+pattern_learner+pattern_semantic_matcher+monitor+diagram+memory+search/analysis/domain/document executors+conductor+evaluator+federation+recommender+tracker+transcriber+auto_corrector+learning_injector+streaming_helpers+post_processing |
| 知識圖譜 | 9 | relation, canonical, canonical_entity_resolver, ingestion, helpers, merge, query, statistics, traversal |
| Code Graph | 5 | service, analysis, ast_analyzer, types, wiki + ts_extractor + schema_reflector |
| 搜尋排序 | 5 | reranker, intent_parser, entity_expander, synonym, rule_engine |
| PM/ERP | 3 | pm_query, erp_query, tool_registry |
| 排程管理 | 5 | extraction_scheduler, proactive_triggers, proactive_recommender, ai_prompt_manager + YAML 配置 |
| 追蹤/統計 | 4 | agent_self_evaluator, agent_evolution_scheduler, user_query_tracker, voice_transcriber |

### 乾坤智能體配置參數 (ai_config v3.1.0, 48 params)

| 類別 | 參數數 | 重點參數 |
|------|--------|---------|
| 核心 Agent | 5 | max_iterations=3, tool_timeout=15s, stream_timeout=60s |
| Tool Monitor | 4 | window=100, degraded<30%, recovery>70%, probe=600s |
| Pattern Learner | 6 | max=500, decay=7d, semantic_threshold=0.85 |
| Summarizer | 3 | trigger=6turns, max_chars=500, keep_recent=2 |
| Router | 2 | pattern_threshold=0.8, rule_threshold=0.9 |
| Self-Reflection | 3 | threshold=5, timeout=5s |
| Memory Flush | 3 | ttl=24h, max_learnings=10 |
| Persistent Learning | 3 | max_per_session=10, inject_limit=5 |
| 3-Tier Compaction | 3 | tier1_timeout=10s, tier2_max=500ch, tier3_topics=10 |

### AI 助理管理介面 — 完整 Tab 清單 (14 個)

| Tab 元件 | 類型 | API 端點 | 說明 |
|---------|------|---------|------|
| `ServiceStatusTab` | 包裝器 | — | 組合 OllamaManagement + ServiceMonitor |
| `DataAnalyticsTab` | 包裝器 | — | 組合 Overview + History |
| `DataPipelineTab` | 包裝器 | — | 組合 Embedding + KnowledgeGraph |
| `OllamaManagementTab` | 功能 | `/ai/ollama/status,ensure-models,warmup` | Ollama 服務管理 |
| `ServiceMonitorTab` | 功能 | `/health/detailed, /ai/embedding/stats, /ai/config` | 服務監控儀表板 |
| `OverviewTab` | 功能 | `/ai/search/stats` | 搜尋統計總覽 |
| `HistoryTab` | 功能 | `/ai/search/history/list,clear` | 搜尋歷史管理 |
| `EmbeddingTab` | 功能 | `/ai/embedding/stats,batch` | Embedding 管線 |
| `KnowledgeGraphTab` | 功能 | `/ai/entity/stats,batch` | 知識圖譜 NER 管線 |
| `AgentPerformanceTab` | 功能 | `/ai/stats/tool-success-rates,agent-traces,patterns,learnings,daily-trend` + `/ai/proactive/alerts` | Agent 效能監控 |
| `PromptManagementPanel` | 功能 | Prompt CRUD API | Prompt 模板管理 |
| `SynonymManagementPanel` | 功能 | Synonym CRUD API | 同義詞管理 |
| `AIConfigTab` | 功能 | `/ai/config` | AI 配置管理 |
| `statusUtils.tsx` | 工具 | — | 狀態顯示工具函數 |

### 前端大頁面拆分成果

| 頁面 | 原始 | 拆分後 | 減少 | 新增元件數 |
|------|------|--------|------|-----------|
| CodeGraphManagementPage | 921L | 526L | -43% | 3 元件 |
| BackupManagementPage | 920L | 404L | -56% | 5 元件 |
| KnowledgeGraphPage | 812L | 326L | -60% | 5 元件 |
| TaoyuanDispatchDetailPage | 912L | 545L | -40% | 1 元件 + 2 hooks |
| ProfilePage | ~600L | ~280L | -53% | 子元件拆分 |
| AdminDashboardPage | ~700L | ~300L | -57% | 子元件拆分 |
| StaffPage/StaffDetailPage | ~650L | ~290L | -55% | 子元件拆分 |
| SimpleDatabaseViewer | ~800L | ~320L | -60% | 子元件拆分 |

### v1.84.2 全系統優化 (2026-03-18) — 六輪累計

#### 資料匯入 + 附件上傳
- 851 筆公文匯入 (541 新增 + 310 更新), 733 PDF 附件上傳
- 新建 19 承攬案件, ~30 機關; Chunking/Embedding 100%
- 匯入腳本: `backend/scripts/fixes/import_112_documents.py` (--dry-run)
- 附件腳本: `backend/scripts/fixes/batch_attach_documents.py` (--dry-run)

#### 後端服務拆分 (4 服務)
| 服務 | 前 → 後 | 新增模組 |
|------|---------|---------|
| document_service | 866→613L | document_dispatch_linker_service + document_import_logic_service |
| graph_query_service | 853→351L | graph_entity_graph_builder |
| project_service | 544→411L | 遷移至 ProjectRepository |
| agent_orchestrator | 929→700L | agent_post_processing + agent_streaming_helpers |

#### Repository 遷移 (5 服務, 50+ 查詢)
- dispatch_link, statistics(新建), agency_matching, project, case_code — 全部完成

#### 前端元件拆分 (16 元件, >500L → 0)
- 全部 18 個 >500L 元件拆分至 <500L, 最大降至 498L

#### 效能優化
- DB 索引: 274→253 (-21 重複), +8 FK 索引, +3 複合索引
- idle_in_transaction_session_timeout = 5 分鐘
- `three` lazy-load (~600KB 延遲載入), antd `List` → `Flex` (9 檔案)
- ProjectMatcher: min 8 chars + 3x ratio fuzzy match 防護
- ExcelImportService: upsert_mode 參數

#### 新增功能 (v1.84.2)
- KB 內容搜尋: `POST /knowledge-base/search` + 前端 Input.Search UI
- Graph-RAG 融合: RAG v2.4.0, KG 實體擴展 (synonyms+canonical+aliases)
- Agent 工具動態發現: ToolRegistry v1.2.0, 3 層評分 (query type+entity+KG context)
- agent_planner: 自動注入工具推薦至 LLM prompt

#### 最終評級 (v1.84.2)
| 維度 | 等級 |
|------|------|
| SSOT (前後端) | A+ |
| TypeScript | A+ (0 errors) |
| React Query | A+ |
| Chunk/Embed/NER | A+ (100%) |
| 後端測試 | A+ (2501 passed) |
| Repository 合規 | A+ (0 繞過) |
| >500L 前端元件 | A+ (18→0) |
| DB 索引覆蓋 | A+ (0 FK 缺失) |
| Agent/KG/RAG 整合 | A+ (Graph-RAG+工具發現+全量入圖) |

### v1.84.1 SSOT 修復與架構優化 (2026-03-18)

#### 後端 SSOT 修復
- PM endpoints 本地 BaseModel → `schemas/pm/requests.py` (10 schema classes)
- ERP endpoints 本地 BaseModel → `schemas/erp/requests.py` (8 schema classes)
- 7 個 endpoint 檔案清理完成，0 本地 BaseModel 殘留

#### 系統復盤結果
| 維度 | 等級 | 說明 |
|------|------|------|
| 型別安全 (SSOT) | A | 前端零違規，後端 PM/ERP 已修復 |
| 模組化 | B+ | 前端 23 元件 >500L，後端 10 service >500L |
| 資料層 | B | PM/ERP Repository 待建立 |
| 測試覆蓋 | A | 2484 後端 + 2754 前端，2 頁面缺測試 |
| 文件一致性 | A | Skills/Commands/Agents 100% 吻合 |

### 新增前端模組

| 目錄 | 元件 | 說明 |
|------|------|------|
| `pages/codeGraph/` | CodeGraphSidebar, ModuleConfigPanel, ArchitectureOverviewTab | 程式碼圖譜管理拆分 |
| `pages/backup/` | BackupListTab, RemoteBackupTab, SchedulerTab, BackupLogsTab, BackupStatsCards | 備份管理拆分 |
| `pages/knowledgeGraph/` | GraphLeftPanel, ShortestPathFinder, MergeEntitiesModal, EntityTypeDistribution, TopEntitiesRanking | 知識圖譜拆分 |
| `pages/taoyuanDispatch/` | DispatchDetailHeader | 派工詳情標頭 |
| `hooks/taoyuan/` | useDispatchMutations (241L), useDispatchQueries (110L) | 派工 Hooks |

---

## v1.82.0 收發文正規化 + 知識圖譜強化

### 新增服務模組

| 服務 | 位置 | 說明 |
|------|------|------|
| `ReceiverNormalizer` | `services/receiver_normalizer.py` | 收發文單位正規化 (6 模式 + NFKC) |
| `ToolRegistry` | `services/ai/tool_registry.py` | Agent 工具註冊中心 (Singleton, 26 工具) |

### Schema 擴充

| 模型 | 新增欄位 | 說明 |
|------|---------|------|
| `OfficialDocument` | `normalized_sender`, `normalized_receiver`, `cc_receivers`, `keywords` | 正規化收發文 + AI 關鍵字 |
| `GovernmentAgency` | `tax_id`, `is_self`, `parent_agency_id` | 統編 + 自身機關 + 階層 |
| `CanonicalEntity` | `linked_agency_id`, `linked_project_id` | NER 實體 ↔ 業務記錄自動連結 |

### 知識圖譜查詢新參數

| 參數 | 說明 |
|------|------|
| `year` | 民國年度篩選 |
| `collapse_agency` | 同源實體合併開關 |

### 前端新增

| 元件 | 說明 |
|------|------|
| `GraphToolbar` 年度/合併控制 | 年度 Slider + collapse 開關 |
| `SystemHealthDashboard` 資料品質 | FK 覆蓋率 + NER 覆蓋率指標 |
| `AgentStepInfo` / `ChatMessage` 型別 | Agent 推理步驟 + 聊天訊息 SSOT |

---

## v1.81.0 知識庫瀏覽器 + 實體配對 API

### 新增端點

| 端點常數 | 說明 |
|---------|------|
| `KNOWLEDGE_BASE_ENDPOINTS.TREE` | `/knowledge-base/tree` |
| `KNOWLEDGE_BASE_ENDPOINTS.FILE` | `/knowledge-base/file` |
| `KNOWLEDGE_BASE_ENDPOINTS.ADR_LIST` | `/knowledge-base/adr/list` |
| `KNOWLEDGE_BASE_ENDPOINTS.DIAGRAMS_LIST` | `/knowledge-base/diagrams/list` |
| `TAOYUAN_DISPATCH.DISPATCH_ENTITY_SIMILARITY` | `(id) => /taoyuan-dispatch/dispatch/${id}/entity-similarity` |

### 新增前端元件

| 元件/Hook | 位置 | 說明 |
|-----------|------|------|
| `KnowledgeBasePage` | `pages/KnowledgeBasePage.tsx` | 知識庫主頁面 (3 Tab) |
| `KnowledgeMapTab` | `pages/knowledgeBase/` | 樹狀目錄 + Markdown 渲染 |
| `AdrTab` | `pages/knowledgeBase/` | ADR 表格 + 狀態標籤 + 詳情 |
| `DiagramsTab` | `pages/knowledgeBase/` | Segmented 切換 + Mermaid 渲染 |
| `MarkdownRenderer` | `components/common/` | 通用 Markdown 渲染器 (GFM + Mermaid) |

### Bundle 優化 (manualChunks)

| Chunk | 內容 | 載入時機 |
|-------|------|---------|
| `three` | three + three-spritetext | 3D 圖譜頁面 |
| `react-force-graph-2d` | 2D 圖譜引擎 | 知識圖譜頁面 |
| `react-force-graph-3d` | 3D 圖譜引擎 | 3D 切換時 |
| `cytoscape` | 圖譜佈局引擎 | 知識圖譜頁面 |
| `mermaid` | Mermaid 圖表 | 架構圖/知識庫 |
| `markdown` | react-markdown + remark-gfm | Markdown 渲染 |

---

## v1.79.0 API 端點 SSOT 強化

### 端點定義更新

| 端點常數 | 新增/修改 | 說明 |
|---------|----------|------|
| `AI_ENDPOINTS.ANALYSIS_GET` | 修改 → 函數型 | `(documentId) => /ai/analysis/${documentId}` |
| `AI_ENDPOINTS.ANALYSIS_TRIGGER` | 修改 → 函數型 | `(documentId) => /ai/analysis/${documentId}/analyze` |
| `AUTH_ENDPOINTS.GOOGLE` | 新增 | `/auth/google` |
| `AUTH_ENDPOINTS.REGISTER` | 新增 | `/auth/register` |
| `AUTH_ENDPOINTS.CHECK` | 新增 | `/auth/check` |
| `ADMIN_USER_MANAGEMENT_ENDPOINTS.PERMISSIONS_CHECK` | 新增 | `/admin/user-management/permissions/check` |
| `PROJECT_STAFF_ENDPOINTS.PROJECT_LIST` | 新增 | `(projectId) => /project-staff/project/${projectId}/list` |
| `PROJECT_STAFF_ENDPOINTS.UPDATE` | 新增 | `(projectId, userId) => /project-staff/project/${projectId}/user/${userId}/update` |
| `PROJECT_STAFF_ENDPOINTS.DELETE` | 修改 → 雙參數 | `(projectId, userId) => /project-staff/project/${projectId}/user/${userId}/delete` |

### 端點測試防護

| 測試 | 說明 |
|------|------|
| 端點唯一性驗證 | 自動偵測重複靜態端點值 |
| API 服務匯入驗證 (12 檔) | 確保 API 服務檔案可正常匯入（防止遺漏 import） |
| 動態端點路徑驗證 | 函數型端點回傳值格式驗證 |

### v1.78.0 基礎設施元件

| 元件/Hook | 位置 | 說明 |
|-----------|------|------|
| `useProjectsDropdown` | `hooks/business/useDropdownData.ts` | 承攬案件下拉快取 (staleTime 10min) |
| `useUsersDropdown` | `hooks/business/useDropdownData.ts` | 使用者下拉快取 (staleTime 10min) |
| `useFileSettings` | `hooks/business/useDropdownData.ts` | 檔案設定快取 (staleTime 30min) |

---

## v1.77.0 新增前端元件與 Hooks

### 作業歷程共用模組 (workflow/)

| 元件/Hook | 位置 | 說明 |
|-----------|------|------|
| `WorkRecordStatsCard` | `components/taoyuan/workflow/` | 共用統計卡片（dispatch/project 雙模式），早期 narrowing |
| `useWorkRecordColumns` | `components/taoyuan/workflow/` | 共用表格欄位定義（deadline/outgoingDoc 可配置） |
| `useDeleteWorkRecord` | `components/taoyuan/workflow/` | 共用刪除 mutation + 確認對話框 + React Query invalidation |
| `workCategoryConstants` | `components/taoyuan/workflow/` | 里程碑/狀態/作業類別統一常數 (SSOT 葉節點) |

### v1.60.0 基礎設施元件

| 元件/Hook | 位置 | 說明 |
|-----------|------|------|
| `GlobalApiErrorNotifier` | `components/common/` | 全域 API 錯誤通知（429/403/5xx/網路），3 秒去重 |
| `GraphNodeSettings` | `components/ai/` | 知識圖譜節點自訂設定（顏色/標籤/可見度），localStorage 持久化 |
| `useAIPrompts` | `hooks/system/` | AI Prompt 管理 React Query hooks |
| `useAISynonyms` | `hooks/system/` | AI 同義詞管理 React Query hooks |
| `ApiErrorBus` | `api/errors.ts` | 全域錯誤事件匯流排（Axios 攔截器 → 通知元件） |

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
