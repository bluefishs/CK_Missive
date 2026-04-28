# 專案結構與架構

> **v5.9.0 錯誤合約化（ADR-0028）**：3 靜態守護 + Silent failure 零容忍 + Timeout 合約
> **v5.9.0 觀測棧完工**：Prometheus 16 指標 + 3 Grafana dashboards + 12 alert rules + Promtail v2

## 根目錄結構

```
CK_Missive/
├── .claude/                    # Claude Code 配置
├── backend/                    # FastAPI 後端
├── frontend/                   # React 前端
├── configs/                    # 外部配置
│   ├── grafana/                #   3 dashboards (HTTP / DB Pool / Inference) + README + promtail-pm2.yml
│   ├── prometheus/             #   alerts.yml (12 rules: error_budget / silent_failure / capacity / business)
│   ├── init.sql, nginx.conf, postgresql-tuning.conf, cloudflare-tunnel.yml
├── docs/                       # 文件目錄（含 adr/ archived/ archive/）
├── scripts/                    # 腳本目錄 (分類組織)
│   ├── dev/                    #   開發工具 (dev-start, dev-stop, start-backend)
│   ├── checks/                 #   驗證檢查
│   │                              • verify_architecture, api, route, skills-sync
│   │                              • synthetic-baseline, soul-fidelity, shadow-baseline-report
│   │                              • 🆕 async_session_race_guard（ADR-0028）
│   │                              • 🆕 sse_headers_guard（ADR-0028）
│   │                              • 🆕 adr_lifecycle_check（ADR-0029）
│   │                              • schema_lazy_load_guard（ADR-0027）
│   ├── health/                 #   系統健康 (health_check, monitor, health-watchdog)
│   ├── deploy/                 #   部署腳本 (deploy-nas, deploy-public)
│   ├── init/                   #   初始化/配置 (database-init, config-manager)
│   ├── backup/                 #   備份腳本
│   └── archive/                #   過時腳本存檔
├── .env                        # 環境設定 (唯一來源)
├── docker-compose.infra.yml    # 基礎設施 Compose (PostgreSQL+Redis)
├── docker-compose.dev.yml      # 全 Docker 開發 Compose
├── docker-compose.multichannel.yml  # v5.9.2 openclaw service 已移除（NemoClaw Sprint 2）
├── backend/config/
│   ├── agent-policy.yaml       # Agent 路由/工具/回退策略
│   ├── inference-profiles.yaml # 推理 Profile (6 profiles: nim/groq/ollama...)
│   └── remote_backup.json      # 異地備份配置
├── CLAUDE.md                   # 主配置
├── README.md                   # 專案說明
└── ecosystem.config.js         # PM2 配置
```

## 錯誤合約化（ADR-0028）

所有 `except` 區塊必須同時滿足三件事：
1. `logger.error`（非 warning）+ `exc_info=True` + 結構化 context
2. 打 Prometheus metric counter（error_type label）
3. 默認 re-raise；吞錯必須註明理由

**Timeouts 統一合約**（`backend/app/core/timeouts.py`）：
- LLM synthesis 35s / Quality review 10s / RAG retrieval 8s / Tool execution 15s / DB query 5s

**3 靜態守護 pre-commit 執行**：
- `async_session_race_guard.py` — `asyncio.gather` + `ctx.db` 共用偵測
- `sse_headers_guard.py` — SSE endpoint 必須含 `Content-Encoding: identity`
- `schema_lazy_load_guard.py` — Pydantic schema 不得訪問 ORM lazy relationship

**Regression lock tests**：每一個 silent failure 修復必須附 `test_*_regression.py` 鎖定。

## 觀測棧（configs/grafana/ + configs/prometheus/）

| 類別 | 檔案 | 內容 |
|---|---|---|
| Dashboards | `configs/grafana/dashboards/ck-missive-http.json` | HTTP 流量 / 錯誤率 / P50/95/99 latency（6 panels） |
| Dashboards | `configs/grafana/dashboards/ck-missive-db-pool.json` | Pool 狀態 / 查詢 p95 / 慢查詢（6 panels） |
| Dashboards | `configs/grafana/dashboards/ck-missive-inference.json` | LLM completion / fallback / rate limit / shadow baseline（7 panels） |
| Alert rules | `configs/prometheus/alerts.yml` | 4 groups × 12 rules — error_budget / silent_failure / capacity / business |
| Promtail | `configs/grafana/promtail-pm2.yml` v2 | 5 scrape targets（error / out / app / admin_push / watchdog） |
| 部署指南 | `configs/grafana/README.md` | CK_DigitalTunnel 端 provisioning 步驟 |

## 後端模型結構

ORM 模型位於 `backend/app/extended/models/` 目錄，拆分為多個子模組：

```
backend/app/extended/models/
├── __init__.py          # 統一匯出所有模型
├── _base.py             # Base, pgvector 條件載入
├── associations.py      # 關聯表 (project_vendor, project_user)
├── core.py              # 基礎實體 (Vendor, ContractProject, Agency, User)
├── document.py          # 公文模組 (OfficialDocument, Attachment)
├── calendar.py          # 行事曆 (CalendarEvent, Reminder)
├── system.py            # 系統 (Notification, Session, Navigation, Config, MorningReport 3 表)
├── staff.py             # 專案人員 (AgencyContact, Certification)
├── taoyuan.py           # 桃園派工 (Project, DispatchOrder, WorkRecord, etc.)
├── entity.py            # 實體識別 (DocumentEntity, EntityRelation)
├── knowledge_graph.py   # 知識圖譜 (CanonicalEntity, Alias, Mention)
├── ai_analysis.py       # AI 分析 (PromptTemplate, Synonym, SearchHistory)
├── agent_trace.py       # Agent 執行追蹤 (AgentTrace, AgentSpan)
├── agent_learning.py    # Agent 學習持久化 (AgentLearning)
├── document_chunk.py    # 文件分段 (DocumentChunk, BM25 tsvector)
├── invoice.py           # 費用報銷 (ExpenseInvoice, ExpenseInvoiceItem)
├── finance.py           # 統一帳本 (FinanceLedger)
└── asset.py             # 資產管理 (Asset, AssetLog)
```

## 後端 Service 層結構

### Wave 1-8 後 12 Bounded Contexts 結構（v5.10.2）

**重要**：73 個原頂層散戶已遷入 12 bounded context 子包（73 stub 維持向後相容，預計 2026-Q3 移除）。
詳見 `docs/architecture/SERVICE_CONTEXT_MAP.md` + `docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md` v2.2。

```
backend/app/services/
├── base/                       # 基礎服務 (ImportBaseService, ServiceResponse, audit Mixin)
├── ai/                         # AI 服務 (11 子包 + ~120 re-export stubs，未被 Wave 動)
│   ├── core/                   # ai_config, base_ai_service, embedding_manager, token_tracker
│   ├── agent/                  # orchestrator, planner, evolution, pattern_learner, missive_agent
│   │   └── missive_agent.py    # MissiveAgent (v3.0, renamed from NemoClawAgent)
│   │   └── agent_evolution_scheduler.py  # L21: redis counter, should_evolve()
│   ├── tools/                  # tool_definitions, tool_registry, 6 executor
│   ├── graph/                  # relation_graph, canonical_entity, code_graph, erp_graph
│   ├── document/               # document_ai, chunker, entity_extraction
│   ├── domain/                 # digital_twin, morning_report (937L+formatter), pm/erp_query
│   ├── search/                 # rag_query, rag_retrieval, reranker
│   ├── proactive/              # proactive_triggers + erp/finance/pm
│   ├── federation/             # federation_client/discovery/delegation
│   ├── misc/                   # voice_transcriber, skill_snapshot, code_wiki, missive_agent
│   ├── prompts.yaml / synonyms.yaml / intent_rules.yaml
│
├── memory/                     # 坤哥意識體 (ADR-0022 / ADR-0023)
│   ├── crystallizer.py         # pattern → proposal（每日 04:30 cron）
│   ├── crystal_applier.py      # 人工 gate: proposal → crystal（admin approve）
│   ├── pattern_extractor.py    # trace → pattern（每日 04:00 cron）
│   ├── soul_loader.py / autobiography.py / diary_service.py / anti_echo.py
│   └── auto_defense.py / narrative_validator.py / yaml_safe_editor.py
│
├── # === Wave 1-8 12 Bounded Contexts（73 檔遷移完成，0 regression）===
├── document/                   # Wave 1A (11 檔): core/dispatch_linker/import_logic/import_facade/
│                              #   filter/statistics/export/processor/query_filter/serial_number/receiver_normalizer
├── contract/                   # Wave 1B (6 檔): core (project)/staff/analytics/case_code/field_sync/agency_contact
├── agency/                     # Wave 1B (3 檔): core/matching/statistics
├── vendor/                     # Wave 1B (1 檔): core
├── audit/                      # Wave 1C (3 檔): core/mixin/event_loggers
├── notification/               # Wave 1C (4 檔) + Wave 7 (1): dispatcher/service/helpers/template + project_notification
├── erp/                        # Wave 0 (4) + Wave 2 (5) + Wave 7 (1):
│   │                          #   quotation/invoice/billing/vendor_payable/asset/operational +
│   │                          #   expense_invoice/expense_approval/expense_import/finance_ledger/finance_export +
│   │                          #   invoice_recognizer/invoice_ocr_*/invoice_qr_decoder + financial_summary
├── integration/                # Wave 3 (10 檔): line_bot/line_flex_builder/line_image_handler/line_push_scheduler/
│                              #   telegram_bot/discord_bot/discord_helpers/channel_adapter/sender_context/agent_stream_helper
├── tender/                     # Wave 4 (10 檔): search/search_query/data_transformer/subscription_scheduler/
│                              #   analytics + analytics_battle + analytics_price/cache/ezbid_scraper/pcc_today_scraper
├── calendar/                   # Wave 0 (2) + Wave 5 (5) + Wave 7 (2):
│                              #   event_auto_builder/batch_create_events +
│                              #   document_integrator/document_service/google_sync/reminder_scheduler/reminder_service +
│                              #   google_client/google_sync_scheduler
├── wiki/                       # Wave 6 (4 檔): compiler/coverage/formatter/service
├── system/                     # Wave 8 (NEW, 2 檔): health_service/health_checks
├── backup/                     # Wave 0 (5) + Wave 8 (1):
│                              #   utils/db_backup/attachment_backup/scheduler/remote_syncer + auto_scheduler
│
├── einvoice/                   # MOF 電子發票同步 (HMAC-SHA256)
├── strategies/                 # 策略模式 (agency_matcher 等)
├── taoyuan/                    # 桃園派工 (dispatch_import/order/payment/dispatch_link + enrichment)
│
├── # === 12+ 個保留散戶（single-purpose，符合「3+ contexts 才獨立子包」例外）===
├── admin_service.py / coding_helpers.py / csv_processor.py / excel_import_service.py /
├── import_validators.py / kb_embedding_service.py / navigation_sync_service.py /
├── search_optimizer.py / security_scanner.py / skill_evolution_service.py /
├── taoyuan_link_service.py / user_alias_service.py
│
└── # === 73 stub 檔（Wave 1-8 遷移後保留向後相容，預計 2026-Q3 移除）===
    document_service.py → document/core.py
    project_service.py → contract/core.py
    line_bot_service.py → integration/line_bot.py
    ... (詳見 SERVICE_CONTEXT_MAP §1.2)
```

**Service Entropy 軌跡**：29.4% (Wave 0) → 23.5% (Wave 8) → ~12% (v6.0 stub 移除後預估 GREEN)

## 後端 API 結構

```
backend/app/api/endpoints/
├── documents/              # 公文 API (模組化)
│   ├── list.py, crud.py, delete.py, stats.py, export.py, import_.py, audit.py
├── document_calendar/      # 行事曆 API (模組化)
├── taoyuan_dispatch/       # 桃園派工 API (模組化)
├── ai/                     # AI API (薄端點層，邏輯在 services/ai/)
│   ├── agent_query.py            # Agentic 問答 SSE 端點
│   ├── agent_query_sync.py       # 同步問答端點 (MCP/LINE)
│   ├── document_ai.py            # 文件 AI 端點
│   ├── document_analysis.py      # 文件分析端點
│   ├── embedding_pipeline.py     # Embedding 管線端點
│   ├── entity_extraction.py      # NER 實體提取端點
│   ├── graph_entity.py            # 知識圖譜實體端點 (拆分自 graph_query)
│   ├── graph_admin.py             # 知識圖譜管理端點 (拆分自 graph_query)
│   ├── graph_unified.py           # 知識圖譜統一查詢端點 (拆分自 graph_query)
│   ├── rag_query.py              # RAG 問答端點
│   ├── relation_graph.py         # 關係圖譜端點
│   ├── ai_stats.py               # AI 統計端點 + 晨報 (preview/push/status/history)
│   ├── ai_monitoring.py          # AI 監控端點 (拆分自 ai_stats)
│   ├── ai_feedback.py            # AI 回饋端點
│   ├── ollama_management.py      # Ollama 管理端點
│   ├── prompts.py                # Prompt 模板端點
│   ├── search_history.py         # 搜尋歷史端點
│   ├── synonyms.py               # 同義詞管理端點
│   ├── diagram_analysis.py       # 工程圖表分析端點 v1.0.0
│   └── tools_manifest.py         # Agent 工具清單端點
├── pm/                     # 專案管理 API (模組化)
│   ├── cases.py, staff.py, milestones.py
├── erp/                    # ERP 財務管理 API (模組化)
│   ├── quotations.py, invoices.py, billings.py, vendor_payables.py
│   ├── vendor_accounts.py      # 廠商帳款跨案件查詢 (2 端點)
│   ├── client_accounts.py      # 委託單位帳款跨案件查詢 (2 端點)
│   ├── assets.py               # 資產管理 (13 端點: CRUD+stats+logs+export+import+inventory)
│   ├── expenses.py             # 費用報銷 CRUD (7 端點: list/create/detail/update/approve/reject/grouped-summary)
│   ├── expenses_io.py          # 費用報銷 IO (9 端點: qr/ocr/smart-scan/import/export/receipt/suggest)
│   ├── operational.py          # 營運帳目 (10 端點: CRUD+審批+預算)
│   ├── ledger.py               # 統一帳本 (6 端點)
│   ├── financial_summary.py    # 財務彙總 (8 端點, +aging+erp-overview)
│   └── einvoice_sync.py        # 電子發票同步 (4 端點)
├── tender.py              # 標案 API 入口 (12L wrapper → tender_module/)
├── tender_module/         # 標案 API 子模組 (v5.5.2 拆分)
│   ├── __init__.py        # 合併 4 個 sub-router
│   ├── search.py          # search/detail/detail-full/recommend/realtime (324L)
│   ├── graph_case.py      # graph/create-case (152L)
│   ├── subscriptions.py   # subscriptions/bookmarks/companies CRUD (318L)
│   └── analytics.py       # dashboard/battle-room/org/company/price + cache-stats (130L)
├── knowledge_base.py      # 知識庫瀏覽器 API (tree/file/adr/diagrams/search)
├── security.py            # 資安管理中心 API (掃描/問題追蹤/通知/模式庫)
├── line_webhook.py        # LINE Webhook 整合端點
├── telegram_webhook.py    # Telegram Bot Webhook 端點 v1.0.0
├── health.py              # 健康檢查端點 (含 detailed)
├── public.py              # 公開端點 (免認證)
├── events.py, events_create.py, events_batch.py  # 行事曆事件 (拆分)
├── document_numbers.py, document_numbers_crud.py  # 文號管理 (拆分)
├── user_management.py, user_permissions.py, role_permissions.py  # 使用者管理 (拆分)
├── dispatch_doc_link_crud.py, document_dispatch_links.py, dispatch_correspondence.py  # 派工關聯 (拆分)
├── system_monitoring.py   # 系統監控端點
├── debug.py               # 開發除錯端點
└── *.py                    # 其他 API 端點
```

## 後端 Repository 層結構 (34 類別)

```
backend/app/repositories/
├── base_repository.py              # BaseRepository[T] — 泛型 CRUD + 分頁 + 搜尋
├── # --- 核心業務 (10) ---
├── document_repository.py          # DocumentRepository — filter/keyword/projection
├── document_stats_repository.py    # DocumentStatsRepository — 統計/趨勢
├── project_repository.py           # ProjectRepository — staff/vendors/access
├── agency_repository.py            # AgencyRepository — match/suggest/tax_id
├── vendor_repository.py            # VendorRepository — projects/filter
├── user_repository.py              # UserRepository — email/sessions/soft_delete
├── attachment_repository.py        # AttachmentRepository — by_document
├── staff_certification_repository.py # StaffCertificationRepository — expiring
├── contact_repository.py           # ContactRepository — primary_contact
├── # --- 系統 (4) ---
├── calendar_repository.py          # CalendarRepository — date_range/overdue
├── notification_repository.py      # NotificationRepository — unread/mark
├── session_repository.py           # SessionRepository — active/revoke/cleanup
├── configuration_repository.py     # ConfigurationRepository — key-value
├── navigation_repository.py        # NavigationRepository — tree/order
├── admin_repository.py             # AdminRepository — DB introspection/stats (12 methods)
├── entity_extraction_repository.py # EntityExtractionRepository — NER operations (10 methods)
├── relation_graph_repository.py    # RelationGraphRepository — KG building queries (14 methods)
├── # --- AI (5) ---
├── ai_synonym_repository.py        # AISynonymRepository — category/toggle
├── ai_prompt_repository.py         # AIPromptRepository — versioning
├── ai_search_history_repository.py # AISearchHistoryRepository — trends/suggestions
├── ai_feedback_repository.py       # AIFeedbackRepository — feedback_stats
├── ai_analysis_repository.py       # AIAnalysisRepository — upsert
├── # --- Agent (2) ---
├── agent_trace_repository.py       # AgentTraceRepository — traces/metrics
├── agent_learning_repository.py    # AgentLearningRepository — learnings/similar
├── # --- 關聯表 (2) ---
├── project_vendor_repository.py    # ProjectVendorRepository — association
├── project_staff_repository.py     # ProjectStaffRepository — assignment
├── # --- 桃園派工 (7) ---
├── taoyuan/
│   ├── dispatch_order_repository.py    # DispatchOrderRepository — filter/stats
│   ├── project_repository.py           # TaoyuanProjectRepository — links/docs
│   ├── work_record_repository.py       # WorkRecordRepository — timeline/batch
│   ├── payment_repository.py           # PaymentRepository — totals/timeline
│   ├── dispatch_link_repository.py     # DispatchLinkRepository — 複合包裝器
│   ├── dispatch_doc_link_repository.py # DispatchDocLinkRepository — doc links
│   └── dispatch_project_link_repository.py # DispatchProjectLinkRepository
├── # --- PM/ERP ---
├── pm/                                # PM Repository (規劃中)
├── erp/                               # ERP Repository (10 類別)
│   ├── quotation_repository.py        # ERPQuotationRepository
│   ├── invoice_repository.py          # ERPInvoiceRepository
│   ├── billing_repository.py          # ERPBillingRepository
│   ├── vendor_payable_repository.py   # ERPVendorPayableRepository
│   ├── expense_invoice_repository.py  # ExpenseInvoiceRepository — inv_num/case_code/query
│   ├── ledger_repository.py           # LedgerRepository — balance/category_breakdown
│   ├── financial_summary_repository.py # FinancialSummaryRepository — 跨模組 JOIN
│   ├── einvoice_sync_repository.py    # EInvoiceSyncRepository — sync_logs/dedup
│   ├── asset_repository.py            # AssetRepository + AssetLogRepository
│   └── client_receivable_repository.py # ClientReceivableRepository — 跨案件應收
├── # --- Query Builder (3) ---
└── query_builders/
    ├── document_query_builder.py       # Fluent API — status/date/keyword
    ├── project_query_builder.py        # Fluent API — user/vendor/status
    └── agency_query_builder.py         # Fluent API — type/tax_id
```
