# 專案結構與架構

## 根目錄結構

```
CK_Missive/
├── .claude/                    # Claude Code 配置
├── backend/                    # FastAPI 後端
├── frontend/                   # React 前端
├── configs/                    # 外部配置 (PostgreSQL tuning, init.sql)
├── docs/                       # 文件目錄
├── scripts/                    # 腳本目錄 (分類組織)
│   ├── dev/                    #   開發工具 (dev-start, dev-stop, start-backend)
│   ├── checks/                 #   驗證檢查 (architecture, api, route, skills-sync)
│   ├── health/                 #   系統健康 (health_check, monitor)
│   ├── deploy/                 #   部署腳本 (deploy-nas)
│   ├── init/                   #   初始化/配置 (database-init, config-manager)
│   ├── backup/                 #   備份腳本
│   └── archive/                #   過時腳本存檔
├── .env                        # 環境設定 (唯一來源)
├── docker-compose.infra.yml    # 基礎設施 Compose (PostgreSQL+Redis)
├── docker-compose.dev.yml      # 全 Docker 開發 Compose
├── backend/config/
│   ├── agent-policy.yaml       # Agent 路由/工具/回退策略
│   ├── inference-profiles.yaml # 推理 Profile (6 profiles: nim/groq/ollama...)
│   └── remote_backup.json      # 異地備份配置
├── CLAUDE.md                   # 主配置
├── README.md                   # 專案說明
└── ecosystem.config.js         # PM2 配置
```

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

```
backend/app/services/
├── base/                       # 基礎服務 (ImportBaseService, ServiceResponse)
├── ai/                         # AI 服務 (11 子包 + ~120 re-export stubs)
│   ├── core/                   # 核心基礎 (16): ai_config, base_ai_service, embedding_manager, token_tracker
│   ├── agent/                  # 智能體 Agent (36): orchestrator, planner, evolution, pattern_learner, missive_agent
│   │   └── missive_agent.py    # MissiveAgent (v3.0, renamed from NemoClawAgent)
│   ├── tools/                  # 工具執行器 (16): tool_definitions, tool_registry, 6 executor
│   ├── graph/                  # 知識圖譜 (26): relation_graph, canonical_entity, code_graph, erp_graph
│   ├── document/               # 文件處理 (10): document_ai, chunker, entity_extraction
│   ├── domain/                 # 領域業務 (12): digital_twin, morning_report, pm/erp_query
│   │   ├── morning_report_service.py     # 晨報生成 (937L) — 聚合 CTE + queries (v2.0 委派 formatter)
│   │   ├── morning_report_formatter.py   # 晨報格式化 (~250L) — 純函數，無 DB (v1.0 拆分)
│   │   ├── morning_report_queries.py     # 晨報查詢層 (Phase 1 stub)
│   │   ├── morning_report_delivery.py    # 晨報派送 (240L)
│   │   └── dispatch_progress_synthesizer.py  # 派工進度彙整
│   ├── search/                 # 搜尋排序 (9): rag_query, rag_retrieval, reranker
│   ├── proactive/              # 主動觸發 (5): proactive_triggers + erp/finance/pm
│   ├── federation/             # 聯邦整合 (3): federation_client/discovery/delegation
│   ├── misc/                   # 雜項工具 (10): voice_transcriber, skill_snapshot, code_wiki, missive_agent
│   ├── *.py                    # ~120 re-export stubs (向後相容 sys.modules 轉發)
│   ├── prompts.yaml            # 5組Prompt模板
│   ├── synonyms.yaml           # 53組同義詞字典
│   └── intent_rules.yaml       # 意圖規則定義
├── calendar/                   # 行事曆服務
│   ├── event_auto_builder.py   # 事件自動建立
│   └── batch_create_events.py  # 批次建立事件
├── strategies/                 # 策略模式
│   └── agency_matcher.py       # 機關智慧匹配
├── taoyuan/                    # 桃園派工服務 (dispatch_import/order/payment/dispatch_link + enrichment)
├── backup/                     # 備份服務套件 (v3.0.0)
│   ├── __init__.py             # BackupService (組合 4 個 Mixin)
│   ├── utils.py                # Docker 偵測、路徑、環境、日誌
│   ├── db_backup.py            # PostgreSQL pg_dump/restore
│   ├── attachment_backup.py    # 附件增量備份
│   └── scheduler.py            # 備份建立/列表/刪除、異地同步
├── receiver_normalizer.py       # 收發文單位正規化 (v1.0.0)
├── backup_scheduler.py         # 備份排程器 + 異地自動同步 (v2.0.0)
├── system_health_service.py    # 系統健康檢查 (含備份狀態)
├── security_scanner.py         # 自動安全掃描 (每日 02:00, OWASP 15 規則)
├── agency_service.py           # 機關服務
├── agency_matching_service.py  # 機關智慧匹配服務
├── agency_statistics_service.py # 機關統計服務
├── document_service.py         # 公文服務 (421L)
├── document_dispatch_linker_service.py  # 公文-派工關聯服務 (拆分自 document_service)
├── document_import_logic_service.py     # 匯入邏輯服務 (拆分自 document_service)
├── document_filter_service.py  # 公文篩選服務
├── document_statistics_service.py # 公文統計服務
├── project_service.py          # 專案服務 (419L)
├── project_staff_service.py    # 專案人員服務
├── case_code_service.py        # 案件代碼服務
├── vendor_service.py           # 廠商服務
├── audit_service.py            # 審計服務 (303L, 拆分後)
├── audit_event_loggers.py      # 審計事件記錄器 Mixin (拆分自 audit, 198L)
├── audit_mixin.py              # CRUD 審計 Mixin (10 服務套用)
├── taoyuan_link_service.py     # 桃園派工關聯服務
├── erp/                        # ERP 子服務
│   ├── quotation_service.py   # 報價管理 CRUD (343L, 拆分後)
│   ├── quotation_service_io.py # 報價匯出入 (243L, 拆分自 quotation)
│   ├── invoice_service.py     # 開票管理
│   ├── billing_service.py     # 請款管理
│   ├── vendor_payable_service.py # 廠商應付帳款
│   ├── asset_service.py       # 資產管理 CRUD (217L, 拆分後)
│   ├── asset_service_io.py    # 資產匯出入 (393L, 拆分自 asset)
│   └── operational_service.py # 營運帳目 (預算+審批+分類)
├── einvoice/                   # 電子發票
│   └── einvoice_sync_service.py # MOF 電子發票同步 (HMAC-SHA256)
├── expense_invoice_service.py  # 費用報銷 Facade (v2.0 委派式, 207L)
├── expense_approval_service.py # 費用審核工作流 (多層審批+預算聯防+通知, 228L)
├── expense_import_service.py   # 費用匯入匯出 (QR+Excel+電子發票關聯, 265L)
├── invoice_recognizer.py       # 統一發票辨識器 (QR Head+Detail+OCR, 拆分後)
├── invoice_ocr_parser.py       # 發票 OCR 解析器 (拆分自 recognizer)
├── invoice_qr_decoder.py       # 發票 QR 解碼器 (拆分自 recognizer)
├── finance_ledger_service.py   # 統一帳本 (餘額 + 分類)
├── financial_summary_service.py # 財務彙總 (專案/全案/公司級)
├── finance_export_service.py   # 財務報表匯出 (Excel/CSV)
├── invoice_ocr_service.py      # 發票 OCR 解析 (Tesseract)
├── line_bot_service.py         # LINE Bot 整合服務 (362L, 拆分後)
├── line_flex_builder.py        # LINE Flex Message 建構器 (拆分自 line_bot)
├── line_image_handler.py       # LINE 圖片處理 (拆分自 line_bot)
├── line_push_scheduler.py      # LINE 推播排程器
├── notification_dispatcher.py  # 通知派發服務
├── document_calendar_integrator.py # 公文行事曆整合
├── discord_bot_service.py      # Discord Bot (430L, 拆分後)
├── discord_helpers.py          # Discord 格式化工具 (拆分自 bot, 137L)
├── telegram_bot_service.py     # Telegram Bot 智慧回覆整合 v1.0.0
├── channel_adapter.py          # 統一通道抽象 (LINE/Discord/Telegram)
├── sender_context.py           # 發送者上下文 (頻道感知)
├── agent_stream_helper.py      # Agent 串流輔助 (跨通道統一)
├── tender_search_service.py        # 標案檢索 (302L, 拆分後)
├── tender_data_transformer.py     # 標案資料轉換 (拆分自 search, 263L)
├── tender_subscription_scheduler.py # 標案訂閱排程 (每日3次 + LINE/Discord)
├── tender_analytics_service.py     # 標案分析 Facade (283L, 委派子模組)
├── tender_analytics_battle.py     # 投標戰情室 + 機關生態 (108L, 拆分)
├── tender_analytics_price.py      # 底價分析 + 廠商分析 (184L, 拆分)
├── ezbid_scraper.py               # ezbid.tw 即時爬蟲 (當日資料補充)
├── tender_cache_service.py        # 標案 DB 持久化 (save/search/refresh/stats)
├── project_analytics_service.py    # 專案分析服務 (拆分自 project_service)
└── *_service.py                # 其他業務服務
```

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
