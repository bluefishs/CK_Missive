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
| `/security-audit` | 🔒 **資安審計檢查** | `.claude/commands/security-audit.md` |
| `/performance-check` | ⚡ **效能診斷檢查** | `.claude/commands/performance-check.md` |
| `/adr` | 📋 **架構決策記錄 (ADR)** 管理 | `.claude/commands/adr.md` |
| `/knowledge-map` | 🗺️ **知識地圖重建與差異報告** | `.claude/commands/knowledge-map.md` |

### Everything Claude Code 指令

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/verify` | 綜合驗證檢查 - Build/Type/Lint/Test | `.claude/commands/verify.md` |
| `/tdd` | TDD 工作流 - RED-GREEN-REFACTOR | `.claude/commands/tdd.md` |
| `/checkpoint` | 長對話進度保存 | `.claude/commands/checkpoint.md` |
| `/code-review` | 全面程式碼審查 | `.claude/commands/code-review.md` |
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
| `ai-development.md` | AI, Groq, Ollama, 語意, 摘要, 分類, 同義詞, 知識圖譜, NER, 實體提取, CanonicalEntity, embedding, Agent, 派工單, dispatch, 閒聊, chitchat | AI 功能開發規範 (v3.2.0) |
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

| Agent | 用途 | 檔案 |
|-------|------|------|
| Code Review | 程式碼審查 | `.claude/agents/code-review.md` |
| API Design | API 設計 | `.claude/agents/api-design.md` |
| Bug Investigator | Bug 調查 | `.claude/agents/bug-investigator.md` |
| E2E Runner | E2E 測試執行與管理 | `.claude/agents/e2e-runner.md` |
| Build Error Resolver | 構建/TypeScript 錯誤快速修復 | `.claude/agents/build-error-resolver.md` |

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
| `@AGENT.md` | 開發代理指引 |
