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
└── ai_analysis.py       # AI 分析 (PromptTemplate, Synonym, SearchHistory)
```

## 後端 Service 層結構

```
backend/app/services/
├── base/                       # 基礎服務 (ImportBaseService, ServiceResponse)
├── ai/                         # AI 服務 (27 個模組)
│   ├── ai_config.py            # AI 配置管理 Singleton (v1.1.0)
│   ├── base_ai_service.py      # 基類：滑動窗口限流+Redis快取+統計 (v3.0.0)
│   ├── document_ai_service.py  # 公文摘要/分類/關鍵字/意圖 (v5.0.0)
│   ├── document_analysis_service.py  # 文件分析服務
│   ├── embedding_manager.py    # Embedding LRU快取+覆蓋率統計 (v1.1.0)
│   ├── entity_extraction_service.py  # NER 實體提取+4策略JSON解析 (v1.0.0)
│   ├── rag_query_service.py          # RAG 問答服務 (v2.3.0)
│   ├── agent_orchestrator.py        # Agentic 主編排 (v2.0.0 模組化)
│   ├── agent_chitchat.py            # 閒聊偵測+LLM對話+回應清理
│   ├── agent_tools.py               # 6工具定義+實作 (AgentToolExecutor)
│   ├── agent_planner.py             # 意圖前處理+LLM規劃+自動修正
│   ├── agent_synthesis.py           # 答案合成+thinking過濾+context建構
│   ├── agent_utils.py               # parse_json_safe, sse 共用工具
│   ├── relation_graph_service.py     # 知識圖譜7-Phase建構 (v1.0.0)
│   ├── canonical_entity_service.py   # 正規化實體4階段策略 (v1.0.0)
│   ├── graph_ingestion_pipeline.py   # 圖譜資料入圖管線 (v1.0.0)
│   ├── graph_query_service.py        # 圖譜查詢服務 (v1.0.0)
│   ├── reranker.py                   # Hybrid 重排序器
│   ├── search_intent_parser.py       # 搜尋意圖解析 (v1.0.0)
│   ├── search_entity_expander.py     # 搜尋實體擴展 (v1.0.0)
│   ├── synonym_expander.py           # 同義詞擴展 (v1.0.0)
│   ├── rule_engine.py                # 規則引擎 (v2.0.0)
│   ├── extraction_scheduler.py       # NER提取排程器 (v1.0.0)
│   ├── ai_prompt_manager.py          # Prompt模板管理(DB熱重載)
│   ├── prompts.yaml                  # 5組Prompt模板 (v1.1.0)
│   ├── synonyms.yaml                # 53組同義詞字典 (v1.0.0)
│   └── intent_rules.yaml            # 意圖規則定義
├── calendar/                   # 行事曆服務
│   ├── event_auto_builder.py   # 事件自動建立
│   └── batch_create_events.py  # 批次建立事件
├── strategies/                 # 策略模式
│   └── agency_matcher.py       # 機關智慧匹配
├── taoyuan/                    # 桃園派工服務 (dispatch_import/order/payment + enrichment)
├── backup/                     # 備份服務套件 (v3.0.0)
│   ├── __init__.py             # BackupService (組合 4 個 Mixin)
│   ├── utils.py                # Docker 偵測、路徑、環境、日誌
│   ├── db_backup.py            # PostgreSQL pg_dump/restore
│   ├── attachment_backup.py    # 附件增量備份
│   └── scheduler.py            # 備份建立/列表/刪除、異地同步
├── backup_scheduler.py         # 備份排程器 + 異地自動同步 (v2.0.0)
├── system_health_service.py    # 系統健康檢查 (含備份狀態)
├── agency_service.py           # 機關服務
├── document_service.py         # 公文服務
├── project_service.py          # 專案服務
├── vendor_service.py           # 廠商服務
├── audit_service.py            # 審計服務 (獨立 session)
└── *_service.py                # 其他業務服務
```

## 後端 API 結構

```
backend/app/api/endpoints/
├── documents/              # 公文 API (模組化)
│   ├── list.py, crud.py, stats.py, export.py, import_.py, audit.py
├── document_calendar/      # 行事曆 API (模組化)
├── taoyuan_dispatch/       # 桃園派工 API (模組化)
├── ai/                     # AI API (薄端點層，邏輯在 services/ai/)
│   ├── agent_query.py            # Agentic 問答 SSE 端點
│   ├── agent_query_sync.py       # 同步問答端點 (MCP/LINE)
│   ├── document_ai.py            # 文件 AI 端點
│   ├── document_analysis.py      # 文件分析端點
│   ├── embedding_pipeline.py     # Embedding 管線端點
│   ├── entity_extraction.py      # NER 實體提取端點
│   ├── graph_query.py            # 知識圖譜查詢端點
│   ├── rag_query.py              # RAG 問答端點
│   ├── relation_graph.py         # 關係圖譜端點
│   ├── ai_stats.py               # AI 統計端點
│   ├── ai_feedback.py            # AI 回饋端點
│   ├── ollama_management.py      # Ollama 管理端點
│   ├── prompts.py                # Prompt 模板端點
│   ├── search_history.py         # 搜尋歷史端點
│   └── synonyms.py               # 同義詞管理端點
└── *.py                    # 其他 API 端點
```

## 前端元件結構

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

## 前端型別 SSOT (v1.60.0)

```
frontend/src/types/
├── api.ts              # 業務實體型別 (User, Agency, Document, Project 等)
├── ai.ts               # AI 功能型別 (GraphNode, IntentParsedResult 等)
├── document.ts         # 公文專用型別 (DocumentCreate, DocumentUpdate)
├── forms.ts            # 表單共用型別
├── admin-system.ts     # 系統管理型別
├── taoyuan.ts          # 桃園派工型別
├── navigation.ts       # 導覽型別
└── index.ts            # 統一匯出 (含相容別名)
```

## 前端全域錯誤處理 (v1.79.0)

```
frontend/src/api/errors.ts          # ApiException + ApiErrorBus 事件匯流排
frontend/src/api/client.ts          # Axios 攔截器 → apiErrorBus.emit()
frontend/src/api/throttler.ts       # RequestThrottler (GLOBAL_MAX=200) → 429 熔斷
frontend/src/components/common/
├── GlobalApiErrorNotifier.tsx       # 訂閱 ApiErrorBus，自動顯示 429/403/5xx/網路錯誤
└── ...
```

錯誤分流規則：
- **業務錯誤** (400/409/422): 元件自行 catch 處理
- **全域錯誤** (403/429/5xx/網路): `GlobalApiErrorNotifier` 自動通知，3 秒去重
- **429 熔斷**: `RequestThrottler` 超過上限 → `ApiException(429)` → 用戶通知
