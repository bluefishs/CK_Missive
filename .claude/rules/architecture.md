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
├── system.py            # 系統 (Notification, Session, Navigation, Config)
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
├── ai/                         # AI 服務 (98 個模組)
│   ├── # --- 核心基礎 ---
│   ├── ai_config.py            # AI 配置管理 Singleton (v3.0.0, 48 params)
│   ├── base_ai_service.py      # 基類：滑動窗口限流+Redis快取+統計 (v3.0.0)
│   ├── document_ai_service.py  # 公文摘要/分類/關鍵字/意圖 (v5.0.0)
│   ├── document_analysis_service.py  # 文件分析服務
│   ├── document_chunker.py     # 文件分段 (段落+滑動窗口+合併)
│   ├── embedding_manager.py    # Embedding LRU快取+覆蓋率統計 (v1.1.0)
│   ├── entity_extraction_service.py  # NER 實體提取+4策略JSON解析 (v1.0.0)
│   ├── rag_query_service.py          # RAG 問答服務 (v2.4.0, 267L 拆分後)
│   ├── rag_retrieval.py             # RAG 檢索服務 (348L, 拆分自 rag_query)
│   ├── # --- 乾坤智能體 Agent 模組 (36 個) ---
│   ├── agent_orchestrator.py        # 主編排 v2.7.0 ReAct+SSE+Router (497L)
│   ├── agent_tool_loop.py           # 工具迴圈 (273L, 拆分自 orchestrator)
│   ├── agent_tools.py               # 工具調度入口 (260L, 委派子執行器)
│   ├── agent_planner.py             # 意圖前處理+LLM規劃 (拆分後)
│   ├── agent_plan_enricher.py       # 規劃豐富器 (158L, 拆分自 planner)
│   ├── agent_synthesis.py           # 答案合成 v2.0.0 (165L, 拆分後)
│   ├── tool_result_formatter.py     # 工具結果格式化+摘要+自省 (389L, 拆分自 synthesis)
│   ├── agent_chitchat.py            # 閒聊偵測+8回退模式 v1.0.0
│   ├── agent_trace.py               # 執行追蹤+Span計時 v1.0.0
│   ├── agent_router.py              # 3層路由(chitchat→pattern→llm) v1.0.0
│   ├── agent_roles.py               # 5角色定義(SSOT) v1.1.0
│   ├── agent_tool_monitor.py        # 滑動窗口+自動降級/恢復 v1.0.0
│   ├── agent_pattern_learner.py     # 模式學習+MD5匹配 (486L, 拆分後)
│   ├── pattern_semantic_matcher.py  # 語意匹配 (拆分自 pattern_learner)
│   ├── agent_summarizer.py          # 3-Tier自適應壓縮+學習萃取 v2.0.0
│   ├── agent_supervisor.py          # 多域分解+並行子任務+結果合併 v1.0.0
│   ├── agent_diagram_builder.py     # 4類Mermaid圖表生成 v1.0.0
│   ├── agent_conversation_memory.py # Redis對話記憶+TTL v1.0.0
│   ├── agent_conductor.py           # Conductor式並行Agent編排 v1.0.0
│   ├── agent_self_evaluator.py      # 自動評分(5維度) v1.0.0
│   ├── agent_evolution_scheduler.py # 自動進化排程(50次/24h) v1.0.0
│   ├── agent_utils.py               # parse_json_safe, sse 共用工具
│   ├── # --- 工具子執行器 (拆分自 agent_tools) ---
│   ├── tool_executor_search.py      # 搜尋工具 (306L): doc/dispatch (拆分後)
│   ├── tool_executor_kg_search.py   # KG搜尋工具 (314L): entity/similar/correspondence (拆分自 search)
│   ├── tool_executor_analysis.py    # 分析工具 (498L): detail/stats/health/graph
│   ├── tool_executor_domain.py      # PM/ERP工具 (105L): projects/vendors/contracts
│   ├── tool_executor_document.py    # 文件工具子執行器 v1.0.0
│   ├── tool_chain_resolver.py       # Chain-of-Tools 自動參數注入 (175L)
│   ├── citation_validator.py        # 引用準確性驗證 (精確+模糊匹配)
│   ├── thinking_filter.py           # LLM thinking 標記 5 階段過濾
│   ├── pattern_seeds.py             # 冷啟動種子模式 (29 個, 7 類別)
│   ├── user_preference_extractor.py # 雙層使用者記憶 (Redis+DB)
│   ├── user_query_tracker.py        # 使用者查詢追蹤統計 v1.0.0
│   ├── voice_transcriber.py         # 語音轉文字服務 v1.0.0
│   ├── federation_client.py         # OpenClaw聯邦整合客戶端 v1.0.0
│   ├── agent_auto_corrector.py      # 6策略自動修正 (拆分自planner) v1.0.0
│   ├── agent_learning_injector.py   # 跨會話學習注入 (拆分自planner) v1.0.0
│   ├── agent_post_processing.py     # 後處理管線 (拆分自orchestrator) v1.0.0
│   ├── agent_streaming_helpers.py   # SSE串流輔助 (拆分自orchestrator) v1.0.0
│   ├── digital_twin_service.py      # 數位分身業務邏輯 (442L, 拆分自endpoint)
│   ├── # --- 知識圖譜模組 (8 個) ---
│   ├── relation_graph_service.py     # 知識圖譜7-Phase建構 (v1.0.0)
│   ├── canonical_entity_service.py   # 正規化實體4階段策略 (拆分後)
│   ├── canonical_entity_resolver.py # 實體解析器 (200L, 拆分自 canonical_entity_service)
│   ├── graph_ingestion_pipeline.py   # 圖譜資料入圖管線 (v1.0.0)
│   ├── graph_helpers.py              # 圖譜工具函數+常數+快取 (v1.0.0)
│   ├── graph_merge_strategy.py       # 圖譜實體合併策略 Phase 2.5~4 (v1.0.0)
│   ├── graph_query_service.py        # 圖譜查詢服務 (v1.2.0 拆分重構)
│   ├── graph_statistics_service.py   # 圖譜統計服務
│   ├── graph_traversal_service.py    # 圖譜遍歷服務
│   ├── # --- Code Graph 模組 (7 個) ---
│   ├── code_graph_service.py         # 程式碼圖譜 Facade (194L, 拆分後)
│   ├── code_graph_ingest.py          # 程式碼圖譜入庫 (445L, 拆分自 service)
│   ├── code_graph_analysis.py        # 程式碼圖譜分析
│   ├── code_graph_ast_analyzer.py    # AST 分析器 (497L, 拆分後)
│   ├── ast_endpoint_extractor.py     # API端點提取 Mixin (170L, 拆分自 ast_analyzer)
│   ├── code_graph_types.py           # 型別+常數定義 (76L)
│   ├── graph_code_wiki_service.py    # Code Wiki 整合
│   ├── schema_reflector.py           # DB Schema 反射 (asyncio.to_thread)
│   ├── ts_extractor.py               # TypeScript AST 提取
│   ├── # --- 搜尋/排序模組 ---
│   ├── reranker.py                   # Hybrid 重排序器
│   ├── search_intent_parser.py       # 搜尋意圖解析 (v1.0.0)
│   ├── search_entity_expander.py     # 搜尋實體擴展 (v1.0.0)
│   ├── synonym_expander.py           # 同義詞擴展 (v1.0.0)
│   ├── rule_engine.py                # 規則引擎 (v2.0.0)
│   ├── # --- PM/ERP 查詢模組 ---
│   ├── pm_query_service.py           # 專案管理查詢 (v1.0.0)
│   ├── erp_query_service.py          # ERP廠商/合約查詢 (v1.0.0)
│   ├── tool_registry.py              # Agent 工具註冊中心 Singleton (22工具)
│   ├── # --- 排程/管理模組 ---
│   ├── extraction_scheduler.py       # NER提取排程器 混合模式 (v2.0.0)
│   ├── proactive_triggers.py         # 主動觸發掃描 (deadline/overdue/品質)
│   ├── proactive_recommender.py      # 主動推薦引擎 v1.0.0
│   ├── ai_prompt_manager.py          # Prompt模板管理(DB熱重載)
│   ├── prompts.yaml                  # 5組Prompt模板 (v1.1.0)
│   ├── synonyms.yaml                # 53組同義詞字典 (v1.0.0)
│   └── intent_rules.yaml            # 意圖規則定義
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
├── audit_service.py            # 審計服務 (獨立 session)
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
├── invoice_recognizer.py       # 統一發票辨識器 (QR Head+Detail+OCR, 378L)
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
├── discord_bot_service.py      # Discord Bot Interactions Endpoint
├── channel_adapter.py          # 統一通道抽象 (LINE/Discord/Telegram)
├── tender_search_service.py        # 標案檢索 (PCC API + Redis 快取)
├── tender_subscription_scheduler.py # 標案訂閱排程 (每日3次 + LINE/Discord)
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
│   ├── ai_stats.py               # AI 統計端點
│   ├── ai_monitoring.py          # AI 監控端點 (拆分自 ai_stats)
│   ├── ai_feedback.py            # AI 回饋端點
│   ├── ollama_management.py      # Ollama 管理端點
│   ├── prompts.py                # Prompt 模板端點
│   ├── search_history.py         # 搜尋歷史端點
│   └── synonyms.py               # 同義詞管理端點
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
├── tender.py              # 標案檢索 API (17 端點: search/detail/graph/subscriptions/bookmarks)
├── knowledge_base.py      # 知識庫瀏覽器 API (tree/file/adr/diagrams/search)
├── security.py            # 資安管理中心 API (掃描/問題追蹤/通知/模式庫)
├── line_webhook.py        # LINE Webhook 整合端點
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
├── admin_repository.py             # AdminRepository — DB introspection/stats
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

## 前端元件結構

### 頁面模組化拆分 (v1.83.0)

```
frontend/src/pages/
├── codeGraph/                  # CodeGraphManagementPage 子元件
│   ├── CodeGraphSidebar.tsx    # 左側欄：統計+管理動作+篩選 (222L)
│   ├── ModuleConfigPanel.tsx   # 模組映射編輯/瀏覽面板 (131L)
│   ├── ArchitectureOverviewTab.tsx  # 架構總覽頁籤 (190L)
│   └── index.ts
├── backup/                     # BackupManagementPage 子元件
│   ├── BackupListTab.tsx       # 備份列表頁籤 (177L)
│   ├── RemoteBackupTab.tsx     # 遠端備份頁籤 (116L)
│   ├── SchedulerTab.tsx        # 排程器頁籤 (104L)
│   ├── BackupLogsTab.tsx       # 日誌頁籤 (153L)
│   ├── BackupStatsCards.tsx    # 統計卡片 (78L)
│   └── index.ts
├── knowledgeGraph/             # KnowledgeGraphPage 子元件
│   ├── GraphLeftPanel.tsx      # 左側面板 (369L) 含 CoveragePanel+TimelineTrendMini
│   ├── ShortestPathFinder.tsx  # 最短路徑搜尋 (104L)
│   ├── MergeEntitiesModal.tsx  # 實體合併對話框 (80L)
│   ├── EntityTypeDistribution.tsx  # 實體類型分布 (60L)
│   ├── TopEntitiesRanking.tsx  # 高頻實體排行 (61L)
│   └── KGAdminPanel.tsx        # 管理面板 (152L)
├── document/                   # 公文詳情頁子元件
│   └── hooks/
│       └── useDocumentProjectStaff.ts  # 公文專案人員管理 Hook (113L)
├── erpQuotation/               # ERP 報價詳情子元件
│   ├── AccountRecordTab.tsx    # 統一帳款紀錄 (應收/應付共用, 294L)
│   ├── BillingsTab.tsx         # 請款管理頁籤 (367L)
│   ├── InvoicesTab.tsx         # 開票管理頁籤 (352L)
│   ├── VendorPayablesTab.tsx   # 廠商應付頁籤 (310L)
│   └── ProfitTrendTab.tsx      # 損益趨勢頁籤 (130L)
├── pmCase/                     # PM 案件詳情子元件
│   ├── MilestonesGanttTab.tsx  # 里程碑/甘特圖頁籤 (含 XLS 匯出入)
│   ├── ExpensesTab.tsx         # 費用核銷頁籤 (統計+列表)
│   ├── QuotationRecordsTab.tsx # 報價紀錄頁籤 (225L)
│   ├── StaffTab.tsx            # 專案人員頁籤
│   └── CrossModuleCard.tsx     # 跨模組資訊卡片
├── taoyuanProject/             # 桃園工程專案詳情子元件
│   ├── TaoyuanProjectDetailPage.tsx # 專案詳情主頁 (213L)
│   ├── hooks/useTaoyuanProjectDetail.ts # 資料載入 Hook
│   └── tabs/                   # 頁籤元件 (12 files)
│       ├── BasicInfoTab.tsx, BudgetEstimateTab.tsx, EngineeringScopeTab.tsx
│       ├── DispatchLinksTab.tsx, LandBuildingTab.tsx, ReviewStatusTab.tsx
│       ├── KanbanBoardTab.tsx, ProjectWorkOverviewTab.tsx
│       ├── ProjectWorkflowTab.tsx (386L), WorkflowTimeline.tsx, WorkflowStatsCard.tsx
│       └── index.ts
├── taoyuanDispatch/            # TaoyuanDispatchDetailPage 子元件
│   ├── DispatchDetailHeader.tsx # 詳情頁標頭 (91L)
│   └── tabs/                   # 既有頁籤元件
├── knowledgeBase/              # 知識庫瀏覽器
│   ├── KnowledgeMapTab.tsx     # 樹狀目錄 + Markdown 渲染
│   ├── AdrTab.tsx              # ADR 表格 + 狀態標籤 + 詳情
│   └── DiagramsTab.tsx         # Segmented 切換 + Mermaid 架構圖
├── digitalTwin/                # 數位分身子元件 (v5.2.2+)
│   ├── CapabilityRadarTab.tsx  # 能力雷達圖頁籤
│   ├── DashboardTab.tsx        # 數位分身儀表板
│   ├── DispatchProgressTab.tsx # 派工進度頁籤
│   ├── EvolutionTab.tsx        # 進化歷程頁籤
│   ├── ProfileCard.tsx         # Agent 個人檔案卡片
│   └── TraceWaterfallTab.tsx   # 追蹤瀑布圖頁籤
├── skillEvolution/             # 技能進化頁面子元件 (v5.2.0+)
│   ├── EvolutionGraph.tsx      # 進化圖表
│   ├── LegendPanel.tsx         # 圖例面板
│   ├── SkillListPanel.tsx      # 技能列表面板
│   └── StatsPanel.tsx          # 統計面板
├── profile/                    # 個人檔案子元件
│   ├── AccountInfoCard.tsx     # 帳號資訊卡片
│   ├── PasswordChangeModal.tsx # 密碼變更 Modal
│   └── ProfileInfoCard.tsx     # 個人資訊卡片
├── erpExpense/                 # 費用報銷子元件 (v5.4.0)
│   ├── SmartScanModal.tsx      # 智慧掃描 (QR+OCR) Modal (251L)
│   ├── ExpenseImportModal.tsx  # Excel 匯入 Modal (175L)
│   └── index.ts
├── SecurityCenterPage.tsx      # 資安管理中心 (OWASP Top 10 + 掃描 + 通知)
├── ERPExpenseCreatePage.tsx    # 費用報銷新增 (三輸入合一: 手動/掃描/財政部, 396L)
├── ERPExpenseListPage.tsx      # 費用報銷列表 (案件分組視圖+金額佔比, 450L)
├── ERPExpenseDetailPage.tsx    # 費用報銷詳情 (明細+審核+收據上傳)
├── ERPLedgerPage.tsx           # 統一帳本 (科目分類+餘額)
├── ERPFinancialDashboardPage.tsx # 財務儀表板 (月趨勢+預算排名+Recharts)
├── ERPHubPage.tsx              # ERP 財務管理中心入口 (5+5 主要/進階)
├── ERPInvoiceSummaryPage.tsx   # 發票跨案件查詢 (168L)
├── ERPVendorAccountsPage.tsx   # 協力廠商帳款列表 (211L)
├── ERPVendorAccountDetailPage.tsx # 協力廠商帳款詳情 3-Tab (186L)
├── ERPClientAccountsPage.tsx   # 委託單位帳款列表 (232L)
├── ERPClientAccountDetailPage.tsx # 委託單位帳款詳情 3-Tab (189L)
├── ERPAssetListPage.tsx        # 資產管理列表 (344L)
├── ERPAssetDetailPage.tsx      # 資產詳情 3-Tab (293L)
├── ERPAssetFormPage.tsx        # 資產新增/編輯表單 (221L)
├── ERPEInvoiceSyncPage.tsx     # 電子發票同步 (MOF 同步狀態+待核銷)
├── AdminLoginHistoryPage.tsx   # 管理員登入歷史
├── CaseNatureManagementPage.tsx # 作業性質代碼管理 (CRUD)
├── SkillEvolutionPage.tsx      # 技能進化主頁面
├── DigitalTwinPage.tsx         # 數位分身主頁面
├── TenderSearchPage.tsx        # 標案搜尋 3-Tab (搜尋/收藏/訂閱)
├── TenderDetailPage.tsx        # 標案詳情 4-Tab (總覽/生命週期/得標/同機關)
├── TenderCompanyPage.tsx       # 廠商投標歷史 (統計+圓餅圖)
├── TenderGraphPage.tsx         # 標案知識圖譜 (力導引)
└── ...
```

### 前端 Hooks 結構 (39 檔案, 150+ hooks)

```
frontend/src/hooks/
├── index.ts                        # 統一匯出入口
├── useCodeWikiGraph.ts             # 程式碼圖譜資料載入 Hook
├── business/                       # 業務邏輯 (13 檔)
│   ├── useDocuments.ts             # 公文 CRUD + 統計 (8 hooks)
│   ├── useDocumentsWithStore.ts    # 公文 React Query + Zustand 整合
│   ├── useDocumentCreateForm.ts    # 公文建立表單 Hook (v2.0 組合層, 364L)
│   ├── useDocumentFormData.ts     # 表單資料載入 (拆分自 CreateForm, 190L)
│   ├── useDocumentFileUpload.ts   # 附件上傳邏輯 (拆分自 CreateForm, 126L)
│   ├── useProjects.ts             # 承攬案件 CRUD (9 hooks)
│   ├── useProjectsWithStore.ts    # 專案整合 Hook
│   ├── useVendors.ts              # 廠商 CRUD (5 hooks)
│   ├── useVendorsWithStore.ts     # 廠商整合 Hook
│   ├── useAgencies.ts             # 機關 CRUD (5 hooks)
│   ├── useAgenciesWithStore.ts    # 機關整合 Hook
│   ├── useTaoyuanProjects.ts      # 桃園專案列表
│   ├── useTaoyuanDispatch.ts      # 桃園派工列表
│   ├── useTaoyuanPayments.ts      # 桃園請款列表
│   ├── useDropdownData.ts         # 全域下拉快取 (10-30min staleTime)
│   ├── useERPFinance.ts           # ERP 財務 hooks (expenses/ledger/dashboard/einvoice)
│   └── createEntityHookWithStore.ts # WithStore Hook 工廠函數
├── system/                         # 系統服務 (11 檔)
│   ├── useCalendar.ts             # 行事曆 CRUD (5 hooks)
│   ├── useCalendarIntegration.ts  # 公文→行事曆整合
│   ├── useDashboard.ts            # 儀表板資料
│   ├── useDashboardCalendar.ts    # 儀表板行事曆
│   ├── useAdminUsers.ts           # 管理員使用者管理
│   ├── useDepartments.ts          # 部門選項 (5min 快取)
│   ├── useDocumentStats.ts        # 公文統計
│   ├── useDocumentAnalysis.ts     # AI 分析結果
│   ├── useNotifications.ts        # 通知中心 (4 hooks)
│   ├── useAISynonyms.ts           # AI 同義詞管理
│   ├── useAIPrompts.ts            # AI Prompt 版本管理
│   ├── useStreamingChat.ts        # re-export @ck-shared 泛型流式聊天
│   └── useAgentSSE.ts             # Agent SSE 串流問答 Hook
├── utility/                        # 工具 (8 檔)
│   ├── useAuthGuard.ts            # 認證守衛 + 路由保護
│   ├── usePermissions.ts          # 動態權限檢查 + 導覽篩選
│   ├── useAppNavigation.ts        # 應用導航 (goBack/goTo/goToDocument)
│   ├── useResponsive.ts           # 響應式設計 (斷點/布林助手)
│   ├── useTableColumnSearch.tsx   # Ant Design 表格搜尋
│   ├── useIdleTimeout.ts          # 閒置超時自動登出
│   ├── usePerformance.ts          # 效能監控
│   └── useApiErrorHandler.ts      # API 錯誤處理 + 重試
└── taoyuan/                        # 派工專用 (2 檔)
    ├── useDispatchMutations.ts    # 8 個 mutation 集中管理 (241L)
    └── useDispatchQueries.ts      # 資料查詢+衍生狀態 (110L)
```

### 前端工具 (v5.3.0)

```
frontend/src/utils/
├── tableEnhancer.ts            # enhanceColumns — 一行加入排序篩選
└── ...
```

### 通用元件

```
frontend/src/components/common/
├── GlobalApiErrorNotifier.tsx  # 全域 API 錯誤通知 (429/403/5xx)
├── MarkdownRenderer.tsx        # 通用 Markdown 渲染器 (GFM + Mermaid 委派)
├── PreviewDrawer/              # 預覽抽屜
├── PageLoading.tsx             # 頁面載入指示器
└── ...
```

### 作業歷程模組 (v2.0.0)

```
frontend/src/components/taoyuan/workflow/
├── workCategoryConstants.ts    # 里程碑/狀態/作業類別 統一常數 (SSOT 葉節點)
├── chainConstants.ts           # 鏈式視圖專用常數
├── chainUtils.ts               # buildChains + 公文配對 + 篩選/統計
├── ChainTimeline.tsx           # 鏈式時間軸主元件
├── InlineRecordCreator.tsx     # Tab 內 Inline 新增表單
├── WorkflowTimelineView.tsx    # 批次分組時間軸
├── WorkflowKanbanView.tsx      # Kanban 看板視圖
├── CorrespondenceMatrix.tsx    # 雙欄公文對照
├── CorrespondenceBody.tsx      # 對照內容
├── useProjectWorkData.ts       # 工程作業資料 Hook
├── useDispatchWorkData.ts      # 派工單作業資料 Hook
├── useDeleteWorkRecord.ts      # 共用刪除 mutation
├── useWorkRecordColumns.tsx    # 共用表格欄位定義
├── WorkRecordStatsCard.tsx     # 共用統計卡片 (dispatch/project 雙模式)
├── index.ts                    # 統一匯出
└── __tests__/
    └── chainUtils.test.ts      # 核心算法單元測試
```

### DocumentOperations 模組 (v1.13.0)

```
frontend/src/components/document/operations/
├── types.ts                    # 型別定義
├── documentOperationsUtils.ts  # 工具函數
├── useDocumentOperations.ts    # 操作邏輯 Hook
├── useDocumentForm.ts          # 表單處理 Hook
├── CriticalChangeConfirmModal.tsx
├── DocumentOperationsTabs.tsx
├── DocumentSendModal.tsx
├── DuplicateFileModal.tsx
├── ExistingAttachmentsList.tsx
├── FileUploadSection.tsx
└── index.ts                    # 統一匯出
```

## 前端型別 SSOT (v5.3.24)

```
frontend/src/types/
├── api.ts              # Barrel re-export + 公文類別常數 + 工具型別 (132L, v3.0 拆分)
├── api-project.ts      # 專案/承攬案件/人員/廠商關聯型別 (444L)
├── api-user.ts         # 使用者/管理員/權限型別 (172L)
├── api-calendar.ts     # 行事曆事件/Google Calendar 型別 (131L)
├── api-entity.ts       # 廠商/機關基礎型別 (140L)
├── api-knowledge.ts    # 知識庫/公文配對型別 (131L)
├── ai.ts               # AI 型別 barrel re-export (28L, v2.0 拆分)
├── ai-document.ts      # AI 文件處理型別 (摘要/分類/匹配/配置, 151L)
├── ai-search.ts        # AI 搜尋型別 (意圖/Embedding/同義詞/Prompt, 332L)
├── ai-knowledge-graph.ts # AI 知識圖譜型別 (KG/Code Graph/DB Schema, 514L)
├── ai-services.ts      # AI 服務型別 (RAG/Agent/數位分身/統計, 490L)
├── document.ts         # 公文專用型別 (DocumentCreate, DocumentUpdate)
├── forms.ts            # 表單共用型別
├── admin-system.ts     # 系統管理型別
├── taoyuan.ts          # 桃園派工型別
├── pm.ts               # 專案管理型別 (PM Cases, 234L, SSOT 含核心定義)
├── erp.ts              # ERP 財務型別 (1080L, SSOT 含核心定義)
├── tender.ts           # 標案檢索型別
├── navigation.ts       # 導覽型別
└── index.ts            # 統一匯出 (含相容別名)
```

## 前端全域錯誤處理 (v1.79.0)

```
frontend/src/api/endpoints/         # API 端點常數 (v2.0 域拆分, 原 endpoints.ts)
├── core.ts                         #   公文/行事曆/通知/檔案 端點 (172L)
├── users.ts                        #   使用者/認證/權限 端點 (186L)
├── projects.ts                     #   承攬案件/機關/廠商 端點 (59L)
├── taoyuan.ts                      #   桃園派工 端點 (158L)
├── ai.ts                           #   AI/Agent/知識圖譜 端點 (218L)
├── erp.ts                          #   PM + ERP 財務 端點 (261L)
├── admin.ts                        #   管理/備份/部署/資安 端點 (95L)
└── index.ts                        #   Barrel 匯出 + API_ENDPOINTS (import path 不變)
frontend/src/api/errors.ts          # ApiException + ApiErrorBus 事件匯流排
frontend/src/api/client.ts          # Axios 客戶端
frontend/src/api/interceptors.ts    # Axios 攔截器 (340L, 拆分自 client.ts)
frontend/src/api/throttler.ts       # RequestThrottler (GLOBAL_MAX=200) → 429 熔斷
frontend/src/components/common/
├── GlobalApiErrorNotifier.tsx       # 訂閱 ApiErrorBus，自動顯示 429/403/5xx/網路錯誤
└── ...
```

錯誤分流規則：
- **業務錯誤** (400/409/422): 元件自行 catch 處理
- **全域錯誤** (403/429/5xx/網路): `GlobalApiErrorNotifier` 自動通知，3 秒去重
- **429 熔斷**: `RequestThrottler` 超過上限 → `ApiException(429)` → 用戶通知
