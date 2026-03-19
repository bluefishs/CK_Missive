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

### gstack 啟發指令 (v1.83.3)

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/ship` | 🚀 **統一發布工作流** — branch→test→review→commit→PR | `.claude/commands/ship.md` |
| `/retro` | 📊 **工程回顧** — commit 統計/趨勢/熱點/JSON 持久化 | `.claude/commands/retro.md` |
| `/qa-smart` | 🧪 **Diff-Aware 智慧測試** — 4 模式 + 8 維度健康度 | `.claude/commands/qa-smart.md` |

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

## v1.84.3 乾坤智能體 v4.0.0 — 全模組盤點 (2026-03-19)

### 乾坤智能體 (OpenClaw Agent) 模組清單 (33 模組, ~8000L, 600+ 測試)

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
| 核心基礎 | 8 | ai_config, base_ai, doc_ai, doc_analysis, doc_chunker, embedding, NER, RAG |
| 乾坤 Agent | 33 | 編排+規劃+合成+路由+學習+監控+圖表+記憶+子執行器+conductor+evaluator+federation+recommender+tracker+transcriber+auto_corrector+learning_injector |
| 知識圖譜 | 8 | relation, canonical, ingestion, helpers, merge, query, statistics, traversal |
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
| `ToolRegistry` | `services/ai/tool_registry.py` | Agent 工具註冊中心 (Singleton, 22 工具) |

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
| `@AGENT.md` | 開發代理指引 |
