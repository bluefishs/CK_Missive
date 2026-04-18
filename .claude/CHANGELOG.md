# CK_Missive Claude Code 配置變更日誌

> 本文件記錄 `.claude/` 目錄下所有配置文件的變更歷史

---

## [5.6.1] - 2026-04-19

### asyncpg 併發 race 根治 + 告警去抖動 + 文件同步

#### 🐛 根因修復（P0 — 2026-04-19 00:13 Telegram 告警觸發）
- **asyncpg race condition**：`asyncio.gather` 多 task 共用同一 session 造成
  `InterfaceError: another operation is in progress`；連線被 pool invalidate，
  health probe 看到即發警報。
- **修復機制**：新增 `app.db.database.run_with_fresh_session(fn)` helper，
  每個並行 DB task 各自取 session（asyncpg 單飛模式）。
- **熱點修復（3 處）**：
  * `agent_orchestrator.py:317` — hints + plan 並行
  * `digital_twin_service.py:get_dashboard_snapshot` — 6 路並行查詢
  * `graph_unified.py:/graph/unified-search` — kg/code/erp/tender 四路搜尋
- **測試** — 4 新測試（`test_run_with_fresh_session.py`）覆蓋：
  * 正常回值 + commit
  * 例外 rollback
  * gather N task 取到 N 個獨立 session（核心保證）
  * partial failure 不污染 siblings

#### 🛡️ 告警去抖動（P2）
- **scheduler.py:health_check_broadcast_job** — 加入 2-strike threshold：
  連續 2 次（10 分鐘）失敗才推 Telegram，避免 transient DB invalidate 誤警。
- **恢復通知** — streak 歸零時若曾告警過，推送「系統已恢復」訊息閉環。

#### 📝 文件同步
- ADR-0021：asyncpg 併發模式（見 `docs/adr/0021-asyncpg-concurrent-session.md`）
- CLAUDE.md：新增「並行 DB 操作」規範（強制使用 `run_with_fresh_session`）

---

## [5.6.0] - 2026-04-18

### 穩定性強化 + 安全硬化 + structlog 統一 + 星空首頁（14 commits, 27 files）

#### 伺服器穩定性（P0 — 修復 API 假死）
- **DB Pool 擴容** — POOL_SIZE 5→15, MAX_OVERFLOW 10→20, POOL_RECYCLE 180s
- **PG max_connections** — 50→100 + idle_in_transaction_session_timeout
- **PM2 memory** — 1G→2G（防 OOM kill）
- **uvicorn 硬化** — limit_concurrency=50, timeout_keep_alive=30, graceful_shutdown=15
- **Health Watchdog** — PM2 cron */2min，連續 2 次失敗自動 restart（偵測 event loop 凍結）
- **Pool exhaustion** — 503 + pool metrics 日誌（非裸 exception）
- **Inference Semaphore** — 90s timeout（防 Ollama 掛起無限等待）
- **/health pool 遮蔽** — 公網請求僅返回 status/version/database（request IP 判斷）

#### 安全硬化（P0）
- **frontend/.env.production** — `VITE_AUTH_DISABLED=false` bake 進公網 build
- **Google Client ID** — 修正 .env.production typo（482047826162→482047526162）
- **.gitignore** — 加例外允許 frontend/.env.production 入庫

#### 觀測棧統一（ADR-0019 accepted）
- **structlog stdlib bridge** — 239 service 自動走 structlog JSON pipeline（零改動 service）
- **Loki 友善** — 預設 JSON 輸出（`STRUCTLOG_CONSOLE=1` 切 dev console）
- **Shadow Logger** — lazy env init 修復（_ENABLED 模組載入時機問題）
- **Shadow Schema** — provider 欄位自動 migration 修復
- **Synthetic bypass** — `synthetic-*` session_id 100% 記錄（不受 30% 取樣限制）
- **Shadow baseline metrics** — Prometheus gauge（Phase 0 GO/NO-GO）
- **SHADOW_ENABLED** — 加入 .env（PM2 env 區塊傳遞不穩定）

#### Hermes 基線加速
- **合成注入腳本** — `scripts/checks/synthetic-baseline-inject.py`（24 query × 5 域）
- **排程** — scheduler 每日 09:00/14:00/20:00 注入 10 筆
- **Soul Fidelity Eval** — `scripts/checks/soul-fidelity-eval.py` 跨 provider 人格一致性

#### Cloudflare Tunnel 正規化
- **docker-compose tunnel profile** — `docker compose --profile tunnel up -d cloudflared`
- **extra_hosts** — `localhost:host-gateway` + `host.docker.internal:host-gateway`（修復 502）
- **CF_TUNNEL_TOKEN** — 移入 .env 統一管理

#### 前端 — 星空首頁恢復 + RWD
- **EntryPage 恢復** — 從 LoginPage 回歸星空入口（深藍背景 + 星座裝飾）
- **LINE 登入** — EntryPage 新增 LINE OAuth 按鈕（#06C755 品牌色）
- **帳密內嵌** — 展開式玻璃磨砂表單（不跳頁到 /login）
- **Google 降級** — 5s timeout + onerror 自動隱藏不可用按鈕
- **RWD 優化** — 手機星星減半（115→53）、按鈕全寬、公網預設展開帳密
- **智慧首頁** — `/` 依登入狀態重導向（已登入→dashboard，未登入→entry）
- **/taoyuan/ 404** — 新增路由重導向到 /taoyuan/dispatch
- **查估單位欄位** — MorningReportTrackingTable 承辦後新增 survey_unit 欄

#### 技術債
- **wiki_compiler 拆分** — 1035L → 910L + wiki_formatter.py 164L
- **ADR-0019** — `docs/adr/0019-structlog-unified-logging.md` accepted

#### 部署自動化
- **deploy-public.sh** — 一鍵：build(production) → restart → health wait → public verify
- **NemoClaw 退場延展** — 5/12 → 5/26（ADR-0015 更新）

---

## [5.5.8] - 2026-04-17

### NemoClaw 退場 + 觀測棧 + 效能優化 + Hermes-centric（10 commits, 98 new tests）

#### NemoClaw/OpenClaw 全面退場（ADR-0014/0015）
- **MissiveAgent** — `NemoClawAgent` → `MissiveAgent` (re-export stub 向後相容)
- **agent_capability.py** — `agent_nemoclaw.py` → `agent_capability.py` (端點路徑不變)
- **Digital Twin** — 移除 OpenClaw federation，本地 AgentOrchestrator 直接推理
- **Task proxy** — HTTP 410 Gone（service retired）
- **Docker compose** — `nemoclaw_network` 移除，multichannel `profiles: ["deprecated"]`
- **Topology 圖** — NemoClaw+OpenClaw 節點 → Hermes Agent 節點
- **Provider resolver** — channel mapping 更新為 Hermes era (LINE/TG/Discord → gemma-hermes)
- **Frontend** — 25+ JSDoc NemoClaw/OpenClaw 引用更新
- **歷史註解** — 22 處「對標 OpenClaw」全部轉為中性描述

#### 觀測棧新增
- **Prometheus /metrics** — `prometheus_middleware.py` (request count/duration/active gauge)
- **排程器失敗告警** — `scheduler_alert.py` (Telegram, threshold=2, cooldown=5min)
- **JSON Log Formatter** — `json_log_formatter.py` (Loki-compatible structured logging)
- **DB Pool Metrics** — `db_pool_metrics.py` (active/checkout/overflow/timeout gauge)
- **DB Query Metrics** — `db_query_metrics.py` (duration histogram p50/p95/p99 + slow counter)
- **DB Query Listener** — `db_query_listener.py` (SQLAlchemy before/after_cursor_execute)
- **Inference Provider Metrics** — completion/fallback/duration per provider
- **KG Stats Metrics** — entity_count/edge_count/wiki_pages gauge

#### 安全硬化
- **Docker Secrets** — `secret_loader.py` (file → env fallback) + config model_validator
- **Compose overlay** — `docker-compose.infra.secrets.yml` + `secrets/.gitignore`

#### 效能優化
- **DB Pool** — POOL_SIZE 10→15, MAX_OVERFLOW 20→30
- **GPU Inference Semaphore** — `inference_semaphore.py` (max=3, 防 RTX 4060 OOM)
- **HNSW ef_search** — `hnsw_config.py` (precise=200/default=100/batch=40)
- **RAG + Entity Resolution** — SET LOCAL hnsw.ef_search 整合
- **Gemma 4 Prompt** — agent_planner JSON-only 指令強化
- **Entity Resolution Benchmark** — 效能基準報告產生器

#### 晨報拆分
- **morning_report_formatter.py** — 純函數格式化邏輯 (~250L)
- **morning_report_queries.py** — 查詢層 Phase 1 stub

#### Bug Fix
- **ImportResultCard** — 修復物件渲染為 React child 的 crash

---

## [5.5.7] - 2026-04-16

### 晨報機制全面重構 + 派工追蹤整合 + per-type 進度架構（17 commits）

#### 晨報 Phase A — 防禦性基礎
- **Delivery log** — `morning_report_delivery_log` 表 + `/status` 端點 + 連續 2 天失敗告警
- **時區固定** — `datetime.now()` → `datetime.now(ZoneInfo('Asia/Taipei'))` 全文替換
- **SQL CTE 抽取** — `_ACTIVE_DISPATCHES_SQL` 共用常數，消除 deadlines/overdue 重複維護
- **Regression tests** — 6 tests 固化 7 次 commit 的過濾/輸出修正

#### 晨報 Phase B — 價值擴張
- **Snapshot 歷史** — `morning_report_snapshots` 表 + `/history` 端點，每日快照供回顧
- **Per-user routing** — `user_morning_report_subscriptions` 表 + subscription fanout + ENV admin fallback
- **內容擴張** — PM 逾期里程碑 + ERP 待審費用（optional sections，`sections=` filter 機制）

#### 逾期判定重構（三層 → 六層 closure_level）
- **聚合 CTE** — `record_progress` 替代 `DISTINCT ON`，與前端進度條 (n/m) 對齊
- **6 層 closure_level** — closed / delivered / all_completed / pending_closure / scheduled / active
- **排程偵測** — `upcoming_events` CTE 偵測未來行事曆事件 → 有排程不算逾期
- **display_status** — 7 階段（逾期/闕漏紀錄/進行中/排程中/待結案/已交付/已結案）
- **瓶頸類別** — `bottleneck_record` CTE 取最新未完成紀錄的 category（非 latest by id）

#### 派工追蹤整合（方案 C）
- **Tab 0 Segmented** — 看板 + 表格雙模式，統一 `morning-status` API 為唯一狀態來源
- **Tab 5 移除** — `?tab=5` redirect → `?tab=0`，消除雙 Tab 狀態不一致
- **統計卡片** — 已完成/交付 | 排程中 | 進行中 | 需處理（看板+表格共用互動篩選）
- **API scope** — `morning-status` 加 `contract_project_id` 過濾，數字與看板對齊

#### per work_type 進度追蹤（Phase 2）
- **Migration** — `work_records.work_type_id` nullable FK + `dispatch_work_types.deadline`
- **UI** — InlineRecordCreator + WorkRecordFormPage「所屬作業」下拉（共用/特定）
- **回填** — 62 筆 records 自動歸屬，7 multi-type dispatches 需手動
- **展開行** — 表格 `expandedRowRender` 顯示 per-type n/m + 交付期限

#### 其他
- **行政作業** — `admin_notice` work_category + WORK_CATEGORY_GROUPS 排序
- **ezbid contract test** — 10 tests + HTML fixture snapshot
- **Hermes baseline cron** — 每日 20:00 匯出 `logs/shadow-baseline/`
- **Docker Secrets Phase 1** — 76 env vars 分 3 tier 盤點 + compose override 範本

#### 測試統計
- Morning report: 56 tests (meetings 35 + progress 21)
- ezbid: 10 contract tests
- **Total new: 66 tests, all green**

---

## [5.5.6] - 2026-04-14 ~ 2026-04-15

### Hermes Agent + Cloudflare Tunnel + 多專案平台級架構

#### 三 ADR（P0）
- **ADR-0014** — NousResearch/hermes-agent (MIT) 取代 OpenClaw，LINE 通道下線
- **ADR-0015** — Cloudflare Tunnel 取代 NemoClaw（Universal SSL + 零費用）
- **ADR-0016** — 平坦子網域 `*.cksurvey.tw`，獨立 DB + CF Access SSO

#### 端點 / 協議
- `POST /api/hermes/acp` — Hermes ACP 原生入口（service token）
- `POST /api/hermes/feedback` — L4 學習閉環回寫
- `POST /api/ai/agent/tools` — Manifest v1.0 → v1.2 (compat/endpoints/auth/hermes 四區塊)
- 全專案 POST-only — AST 守門 + Hermes 結構 lint

#### 公網部署
- `https://missive.cksurvey.tw` — CF Tunnel + FastAPI 掛 frontend/dist (SPA + API 同 host)
- TunnelGuard allowlist 對齊 9 條機器流量 path
- Shadow Logger v1.1 — PII 遮罩 + 30d retention + provider A/B 標籤 + VACUUM fix

#### TDD 統計
- 80+ tests added，3 真 bug 捕獲（VACUUM tx / 5 虛構 tool / GET 違規）
- CI hard-fail gate — 10 測試檔合約守護

---

## [5.5.5] - 2026-04-10 ~ 2026-04-14

### LLM Wiki 全棧 + KG 連結 + ADR 生命週期 + 效能優化

#### LLM Wiki 4-Phase 全棧 (P0, Karpathy Pattern)
- **Phase 1 Ingest** — 實體/主題抽取入 wiki/（220 pages：62 agencies + 30 projects + 127 dispatches + 1 overview，10,603 lines）
- **Phase 2 Compile** — document-to-wiki 編譯 + 增量 compile diff + token panel
- **Phase 3 Query** — Wiki-RAG 融合（wiki search → RAG sources boost similarity=0.95）
- **Phase 4 Lint** — broken links + orphans 掃描，每日 05:30 排程
- **KG 連結** — kg_entity_id 嵌入 69 wiki pages；KG coverage API + Tab
- **Wiki ↔ KG 比對** — 79 exact match (36.1%)，獨立雙源不互相污染
- **前端 /ai/wiki** — 獨立頁面 4-Tab（圖譜/瀏覽/KG比對/管理）
- **force-graph 2D** — 220 nodes / 477 edges，log scale + collision + fullscreen fix

#### ADR-0013 統一編碼系統 Phase 1'+2 (P0)
- **project_code CK 前綴** + billing/invoice/ledger code 自動產生器
- **並發保護** — savepoint retry on unique conflict
- **agency source tagging** — matcher 顯式 `source='auto'`
- **ADR lifecycle gate** — ADR 狀態機（proposed/accepted/superseded）+ orphan index pages

#### 效能優化 (P1)
- **/documents 清單 42% 加速** — 消除冗餘查詢 + DB warmup + orphan fix
- **月度費用異常偵測** — 3 規則（同比/環比/類別偏離）
- **Token Tracker 強化** — 5 provider 計量 + 日/月預算 + 智慧路由

#### Antd 6 相容性延續
- **Drawer width + List→Pagination** 移除廢棄
- **wrapper visible→open** rename

#### 維運工具
- **scheduler panel** — 前端面板呈現 19 jobs 狀態 + last_run/next_run
- **pyc-clear-reload** helper + `docker-compose.dev.yml` 重新標記
- **DEVELOPMENT_GUIDELINES 精簡** — 971→286L

#### 文件與簡報
- **CK_Missive Overview (AI)** — 10-page Marp PPTX 簡報
- **feedback memory 擴充** — 7 項使用者主張長駐 MEMORY.md
- **MEMORY.md 重建** — stale snapshots 轉 archive/

#### 文檔同步機制 (本次)
- **CLAUDE.md → v5.5.5** + skills-inventory 補 tender-search
- **.gitignore** 加入 Office 暫存檔 `~$*.pptx`

### 已知待處理 (P1/P2)
- Agent Memory Snapshot
- 費用報銷 + 資產清冊 Excel 匯入（等範例）
- Agent orchestrator/evolution 整合測試
- Wiki LLM narrative (v2)
- 47 agencies 補齊 agency_code（等業務規則）
- Wiki orphan (71) + broken links (5) 清理

---

## [5.5.4] - 2026-04-09

### AI 子包重構 + UnifiedAgentPage 雙模式 + 標案分析快取

#### AI 服務架構重構 (P0)
- **11 子包拆分** — core(14)/agent(36)/tools(16)/graph(26)/document(10)/domain(10)/search(9)/proactive(5)/federation(3)/misc(9) + ~120 re-export stubs
- **code_graph_ingest** — 685L → 407L + code_graph_persistence 318L (DB 操作獨立)
- **tool_definitions** — 705L → 403L + tool_definitions_analysis 172L + tool_definitions_search 167L

#### 統一智能體頁面 (P0)
- **UnifiedAgentPage** — 雙模式 (user: 聊天助手 / admin: 管理儀表板)
- **刪除** 3 個舊 AI 頁面 (AISearchPage/AgentPlannerPage/AIStatsPage)
- **隱藏** 數位分身導覽 (已併入 Agent Dashboard)

#### 標案分析快取 (P1)
- **Redis 30min 快取** — company_profile + org_ecosystem + dashboard 並行查詢
- **PCC 分類修正** — label_id section mapping (bid=1428/rfp=427)
- **graph_domain 遷移** — knowledge domain filter + 4 新索引 (Alembic 20260409a001)

#### Antd 6.x 相容性修正
- **rowKey index 廢棄** — 移除所有 rowKey 函數的 index 參數 (7 處)
- **Space split 廢棄** — `split` → `separator` 屬性 (2 處)

#### Skills 清單同步
- **新增** multi-channel.md + erp-finance.md 清單條目
- **移除** plan-workflow + tdd-workflow (已刪除檔案的引用)

---

## [5.5.3] - 2026-04-08

### 穩定化 + 監控 + 程式碼品質優化

#### 排程器健康監控 (P0)
- **SchedulerTracker** — 裝飾器追蹤每個排程任務的 last_run/status/duration/success_count/failure_count
- **POST /health/scheduler** — 排程器健康端點 (合併 APScheduler next_run + 追蹤器 last_run)
- **build_summary 整合** — 排程器狀態納入 /health/summary 聚合
- **17 jobs 全追蹤** — `@tracked_job` 裝飾器覆蓋所有排程函數

#### ezbid 爬蟲防禦 (P1)
- **retry + exponential backoff** — MAX_RETRIES=3, BACKOFF_BASE=2.0
- **封鎖偵測** — 403/captcha/block 自動放棄 + 日誌警告
- **連續失敗熔斷** — ≥5 次失敗自動跳過 + 人工介入通知
- **get_health_status()** — 爬蟲健康狀態 API

#### 後端服務拆分 (P1)
- **agent_evolution_scheduler** — 688L → scheduler + actions + persistence (3 files)
- **tool_result_formatter** — 569L → dispatcher + doc/entity/business formatters (4 files)
- **federation_client** — 606L → client + discovery + delegation (3 files)
- **tool_registry** — 537L → registry + discovery (2 files)
- 保留: tool_definitions(671L 純數據), agent_orchestrator(567L 薄編排), dispatch_order_service(550L 已拆分)

#### 空殼頁面清理 (P2)
- **刪除** TenderBattleRoomPage / TenderPriceAnalysisPage / TenderCompanyPage (3 redirect stubs)
- **清理** AppRouter 路由 + ROUTES 常數 + 導覽初始化 + 白名單

#### 記憶體精簡 (P2)
- **MEMORY.md** — 222L → 81L (歷史記錄合併至 session_history_v55.md)

#### 標案整合測試 (P0)
- **test_tender_cache_service.py** — tender_cache_service 7 方法 ≥10 cases
- **test_tender_analytics.py** — battle/price analytics ≥10 cases

#### 自主智能體進化閉環
- **AgentIntelligenceState** — 中央聚合 (capability+eval+critical+learning stats, 30s cache)
- **CRITICAL 即時回饋** — SelfEvaluator severity=critical 直寫 Redis 5min TTL → Planner 讀取
- **6 域評估權重** — tender/graph/doc/sales/field 自訂維度權重 + context passthrough
- **自適應角色升級** — Router 弱域 readiness<0.5 自動升級到 agent
- **進化效果量測** — baseline→7天→比較 (improved/degraded 自動判定)
- **Reflexion 軌跡** — scratchpad→trace.reasoning_trajectory 持久化
- **學習共享池** — Redis agent:shared_pool 跨 session 即時可用
- **promote→DB 閉環** — 進化升級的 pattern 寫入 AgentLearning → inject → planner 行為改變

#### 六大圖譜增強
- **置信度三級** — EntityRelationship.confidence_level (extracted/inferred/ambiguous)
- **中心性分析** — centrality_analysis() SQL 度中心性 + coupling_risk
- **Obsidian 匯出** — entity→.md + [[wiki links]] ZIP 下載
- **timeline 索引** — 3 複合索引加速 10-100x
- **反向邊自動產生** — INVERSE_RELATION_MAP 11 組對稱關係
- **標案入圖** — 機關/廠商自動 upsert CanonicalEntity(org)
- **DB Schema FK 入圖** — references 關係自動轉換
- **Code↔Business 連結** — api_endpoint serves_domain (inferred)
- **Federation health** — POST /ai/graph/admin/federation-health
- **TS 提取增強** — interface/type/enum/re-export 5 新模式

#### 派工公文關聯修正
- **bigram OR→AND** — 關鍵字需同時匹配，避免通用詞誤關聯
- **CJK 繁簡容錯** — 內/内、區/区 等 10 組異體字容錯搜尋
- **公文對照顯示** — 移除 viewMode 限制 + 移除 referenced_by 跳過邏輯
- **統計卡片統一** — 所有計數加「筆」字

#### 行動核銷 + QR Code 入口
- **ERPExpenseCreatePage v3.0** — 行動端步驟式單流程 (掃描→表單)
- **圖片壓縮** — >2MB 自動 resize 1920px + JPEG 80%
- **Steps 進度** — 掃描改用上傳→辨識中→完成三步驟
- **ExpenseQRCode** — 共用 QR 元件 (下載/複製/列印)
- **報價+PM 詳情頁** — 「核銷 QR」按鈕，工地掃描直開核銷頁

#### ERP 帳務完整性
- **AR 同步入帳** — billing→ledger 改同步呼叫，不依賴 EventBus
- **帳本冪等** — find_by_source 三路檢查 (billing/payable/expense)
- **刪除防護** — 有 paid billing/payable 的報價拒絕刪除
- **帳本孤兒清理** — 刪除來源時同步清理 ledger entries
- **AR 涵蓋未成案** — client_receivable 移除 project_code 限制
- **vendor_id 自動解析** — by vendor_code 或 vendor_name
- **帳本對帳排程** — 每日 05:00 AR+AP vs Ledger 差異告警
- **利潤計算統一** — `compute_quotation_profit()` 模組級函數
- **PM/ERP 金額差異** — detail API + 前端 Alert 警示

#### 費用核銷品質修正
- **Item 欄位 Bug** — description→item_name, quantity→qty
- **金額驗證** — amount ≥ tax_amount schema 強制
- **審批欄位回傳** — list API 附加 approval_level + next_approval
- **併發審批鎖** — SELECT...FOR UPDATE 悲觀鎖
- **批次審批** — POST /erp/expenses/batch-approve (最多 50 筆)
- **多幣別自動換算** — 前端 useEffect 計算 original_amount × exchange_rate
- **成案審計** — promote_to_project 寫入 audit_log

#### 服務拆分 Phase 2
- **agent_pattern_learner** — 528L 拆分
- **discord_bot_service** — 526L 拆分
- **audit_service** — 523L 拆分
- **tender_search_service** — 515L 拆分

#### ERPQuotation 軟刪除 + Billing FK 改單向
- **deleted_at 欄位** — 軟刪除取代物理刪除
- **ERPBilling.invoice_id 移除** — 改為 ERPInvoice 單向引用

---

## [5.5.0] - 2026-04-05~07

### Agent 進化 + Domain Events + 多通道整合 + 標案分析 Phase 2 (92 commits)

#### Domain Event System v1.0
- **EventBus 架構** — 解耦式事件匯流排，支援同步/非同步訂閱
- **5 個事件生產者** — document.received, expense.approved, billing.paid, milestone_completed, tender.awarded
- **自動帳本入帳** — billing.paid 事件觸發 FinanceLedger 自動記錄

#### 多通道整合
- **Telegram Bot** — telegram_bot_service + webhook 端點 + 智慧回覆整合
- **統一串流** — Discord/Telegram/LINE 統一 streaming + status 指示
- **Discord 增強** — edit-streaming + emoji status + sender context
- **Telegram 互動** — reactions + reply thread + tool visibility
- **通道抽象** — channel_adapter 統一介面 + sender_context 上下文

#### Agent 智慧進化
- **Agent Dashboard** — 統一儀表板 (聊天+反思+進化+拓撲)
- **Introspection Service** — 統一自感知運行時 + Redis 快取 + ETag
- **Response Enricher** — domain_prompts + analysis-first synthesis 品質提升
- **Role-based Personas** — 角色化 Agent 回應 + 10 新業務工具
- **Morning Report** — 每日 08:00 自動推送 7 模組晨報 (Telegram/LINE)
- **Cross-agent Pattern Sharing** — 跨 Agent 模式共享 + 技能快照
- **Session Handoff** — 跨會話續接協議
- **Learning Graduation** — 學習畢業系統 + after-action hints
- **Search Benchmark** — 30 ground truth 查詢品質基準

#### 標案分析 Phase 2
- **TenderDashboardPage** — 採購儀表板
- **TenderOrgEcosystemPage** — 機關生態圈分析
- **TenderBattleRoomPage** — 戰情室 (雷達圖+對手排行)
- **TenderPriceAnalysisPage** — 底價分析
- **TenderCompanyProfilePage** — 廠商分析整合頁
- **CategoryPieChart** — 共用圓餅圖元件 (全標案頁面複用)
- **ClickableStatCard** — 可點擊互動統計卡片共用元件

#### 派工 Kanban + 進度追蹤
- **Kanban Tab** — 派工列表頁新增看板視圖 + 快速狀態切換
- **Progress** — 進度百分比 + 截止日倒計時
- **Correspondence Matrix** — 1:n 公文配對 rowspan 分組
- **Unsaved Warning** — 未儲存變更警告

#### 服務拆分 + 效能
- **project_service** — 421L 拆分 (+ project_analytics_service)
- **invoice_recognizer** — 485L 拆分 (+ invoice_ocr_parser + invoice_qr_decoder)
- **code_graph_service** — 拆分 ingest + ast_endpoint_extractor
- **perf** — introspection Redis cache + ETag + agent dashboard memo + prefetch

#### 其他
- **Code Wiki** — Gemma 4 語意文件自動生成
- **Engineering Diagram** — Vision 服務 (experimental P3)
- **Digital Twin** — 進化指標儀表板 (EvolutionMetricsCard)
- **tool_executor_kg_search** — KG 搜尋工具拆分自 search

## [5.5.2] - 2026-04-07~08

### 標案模組全面重構 + ezbid 即時爬蟲 + UI 統一 (45 commits)

#### 品質修復
- **75 failing tests → 0** — 12 test files mock 更新 + proactive_triggers bug
- **file upload path** — DB 存 relative_path，download 拼接 UPLOAD_BASE_DIR

#### 架構重構
- **tool_executor_domain** — 826L → 3 files (219+166+458)
- **tender_analytics_service** — 722L → 283L facade + battle(108L) + price(184L)
- **TenderSearchPage** — 515L → 247L + 3 子元件 (SearchTab/SubscriptionTab/BookmarkTab)

#### UI 統一
- **ClickableStatCard** — 14 頁面統一互動統計卡片
- **valueStyle → styles.content** — Ant Design v6 相容
- **bodyStyle → styles.body** — deprecated 修正

#### 標案搜尋 v3.1
- 三模式搜尋 (標案/機關/廠商) + 招標類型篩選
- 訂閱 → 搜尋 Tab 自動切換 (含 category 同步)
- 收藏導航模式 Table + toggle 星星
- 推薦: 訂閱關鍵字驅動 + 業務/今日分區
- 30 天篩選 (移除 2016 等舊資料)

#### ezbid 即時爬蟲
- **ezbid_scraper.py** — cf.ezbid.tw HTML 解析 (當日即時資料)
- **雙軌整合** — search/recommend/dashboard 全整合 g0v + ezbid
- **POST /tender/realtime** — ezbid 即時 API 端點

#### Dashboard v2
- 6 統計卡片 (實際日期範圍) + 標案經費規模 + 得標廠商 + 機關 Top 10
- 採購類別/公告類型圓餅圖 + 資料來源狀態列
- 效能: 24.7s → 7.7s (asyncio.gather 並行)

#### 標案詳情 5 Tab 整合
- **POST /tender/detail-full** — 並行取得詳情+戰情+機關生態+底價 (避免重複 API)
- **Tab 4 投標戰情**: 相似標案去重 + 競爭強度表 (出現/得標/得標率/金額)
- **Tab 5 底價分析**: 預算/底價/決標 + 差異率 + 歷史折率推估
- **機關生態**: 短名 fallback (機關改名相容) + Top 15 廠商
- 訂閱 diff tracking: +N 新增 Tag + 標題去重

#### 頁面整合
- TenderBattleRoomPage → 重導向至 DetailPage Tab4
- TenderPriceAnalysisPage → 重導向至搜尋頁
- TenderCompanyPage → 重導向至 CompanyProfilePage
- TenderDetailPage 524L → 拆分 BattleTab + PriceTab 子元件
- **CompanyBookmark** — 廠商關注收藏 (competitor/partner)

#### 資料持久化 + 排程更新
- **tender_records** — 標案 DB 快取 (303+ 筆自動增長)
- **tender_company_links** — 廠商關聯 (149+ 家)
- **tender_cache_service** — save/search/refresh/stats
- **搜尋自動入庫** — 每次搜尋結果寫入 DB
- **ezbid 排程入庫** — 每小時爬取 → DB
- **狀態定期更新** — 每日 06:00 重查等標期→決標
- **tender.py 拆分** — 844L → 12L + 4 子模組 (search/graph_case/subscriptions/analytics)

#### 資料一致性修復
- 競爭對手統計: 每筆標案每家廠商只計一次 (union dedup)
- 統計基數與顯示一致 (8 筆相似 = 8 筆統計)
- 搜尋移除 30 天強制篩選 (推薦才篩)

---

## [5.4.0] - 2026-04-04

### 型別重構 + ERP 費用增強 + Gemma 4 + 服務層拆分 (9 commits)

#### 型別系統重構
- **api.ts v3.0** — 1338L barrel → 132L re-export，新增 5 個領域型別檔 (api-user/entity/project/calendar/knowledge)
- **pm.ts / erp.ts** — 從 api.ts 提取為獨立 SSOT，re-export 維持向後相容

#### ERP 費用報銷增強
- **三輸入新增頁** — ERPExpenseCreatePage v2.0 (手動/智慧掃描/財政部發票，396L)
- **案件分組視圖** — grouped-summary API + 金額佔比 Progress bar + attribution_type 三面向
- **智慧掃描** — invoice_recognizer 統一辨識器 (QR Head+Detail+OCR)
- **PM Case 費用 Tab** — ExpensesTab 子元件 (統計卡片+列表)
- **費用分類 AI** — suggest-category (Gemma 4, 15 類選項)
- **attribution_type migration** — project/operational/none 三面向核銷歸屬
- **ERP Hub 重組** — 5+5 主要/進階佈局

#### 資產管理升級
- **photo_path** — migration + upload-photo + Gemma 4 Vision 自動描述
- **project_code 映射** — 匯出入改用成案編號 (fallback case_code)
- **相機拍照** — capture=environment 支援行動裝置

#### AI/推理引擎
- **Gemma 4 P0** — inference-profiles v2.0 切換本地主力 (Ollama GPU)
- **LINE 圖片辨識** — line_image_handler 升級統一辨識器
- **ai_connector** — thinking mode 修正

#### 服務層重構
- **expense_invoice_service** — 625L → 3 模組 (facade 207L + approval 228L + import 265L)
- **expenses.py endpoint** — 551L → crud 194L + io 316L

#### 測試
- **+15 test cases** — 標案排程 6 + 費用分組 4 + 審核流程 5 (total: 3,108)

#### 基礎設施
- **.gitattributes** — 源碼 LF / Windows CRLF / 二進制標記
- **invoice-watcher** — PM2 Watchdog 資料夾監控
- **vite proxy** — 新端點轉發

---

## [5.3.22] - 2026-04-01~02

### 標案檢索模組 + 品質優化 + 資料標準化 (46 commits)

#### 標案模組 (全新, 16 commits)
- **搜尋頁** — 3-Tab (搜尋/收藏/訂閱) + 關鍵字+分類+推薦
- **詳情頁** — 4-Tab (總覽/生命週期/得標/同機關) + 截止倒數 + 預算卡片
- **廠商歷史** — 投標統計+得標率+類別/年度圓餅圖 + 互動廠商連結
- **知識圖譜** — 力導引視覺化 (機關→標案→廠商) + 節點點擊跳轉
- **訂閱排程** — APScheduler 08:00/12:00/18:00 + LINE/Discord 通知
- **Agent #29** — search_tender 政府標案搜尋
- **Agent #30** — auto_tender_to_case Multi-Agent 自動建案
- **一鍵建案** — 標案→PM Case + ERP Quotation
- **DB** — tender_subscriptions + tender_bookmarks (Alembic 20260401a002)
- **API** — 17 端點 (search/detail/graph/recommend/create-case/subscriptions/bookmarks)

### 品質優化 + 資料標準化 + 安全加固

#### Bug Fix
- **公文刪除 409** — entity/chunk backref 加 `passive_deletes=True`，精確 `isinstance(IntegrityError)` 判斷
- **導覽路徑 400** — 補齊 28 路由 + `_matches_dynamic_route()` 動態匹配 + **自動同步** init_navigation_data
- **年度民國/西元不一致** — DB 遷移 erp_quotations.year 114→2025 + 源頭 `date.today().year`
- **client-accounts 顯示 draft** — inner join + `project_code IS NOT NULL` 過濾

#### 資料標準化
- **NFKC 正規化** — `StringCleaners.clean_string()` + csv_processor + dispatch_import + expense + asset (5 服務)
- **千分位數字** — `StringCleaners.clean_number()` 支援 "NT$1,234,567" → Decimal
- **統一 Excel 讀取** — `load_workbook_any()` 自動偵測 .xls/.xlsx (magic bytes)，xlrd 轉 openpyxl + NFKC

#### 架構優化
- **endpoints.ts 域拆分** — 1309L → 8 files (core/users/projects/taoyuan/ai/erp/admin/index), max 261L
- **硬編碼 API 清理** — secureApiService 11 處 → SECURE_SITE_MANAGEMENT_ENDPOINTS
- **導覽白名單自動同步** — `_build_valid_paths()` 從 init_navigation_data 動態收集
- **Context budget -33%** — skills-inventory.md 875→180L (版本歷史移至 CHANGELOG)

#### 功能新增
- **報價 Excel 匯出/匯入** — export-excel + import + import-template (3 API + 前端按鈕)
- **ERP 資料補錄** — 48 billings + 48 invoices + 35 ledgers + 3 operational + 10 expenses
- **報價列表預設 confirmed** — 排除 draft

#### 安全加固
- **根目錄 .dockerignore** — 排除 .env / OAuth JSON / .claude/settings.local.json
- **前端 .dockerignore** — .env 不再保留於 Docker image

#### Memory 精簡
- 5 nemoclaw 檔合併為 1 | 已完成 spec 移除 | 37→31 檔

---

## [5.3.17] - 2026-03-31

### 廠商/委託帳款→案件管理式展示

#### 帳款詳情頁重構 (案件管理風格)
- VendorAccountDetailPage: 3 Tab (基本資訊+案件帳款+付款紀錄) — 186L
- ClientAccountDetailPage: 3 Tab (基本資訊+案件應收+收款紀錄) — 189L
- Tab 1: Statistic 卡片 + Descriptions + 簡易案件列表
- Tab 2: 可展開案件明細 (合約金額+狀態+報價連結)
- Tab 3: 跨案件付款/收款時間軸 (flatMap 所有記錄)

#### 跨模組導覽修正
- vendor/client detail 案號→報價詳情 (clickable)
- 財務儀表板/發票總覽→報價詳情 (erp_quotation_id)
- vendor detail total_price/quotation_status 修正 (重啟生效)

---

## [5.3.16] - 2026-03-31

### ERP 跨模組資訊關聯整合

#### 跨模組導覽連結
- 廠商/委託帳款 Detail: 案號 → 報價詳情 (clickable link)
- 財務儀表板: 案號 → 報價詳情 (erp_quotation_id)
- 發票總覽: 案號 → 報價詳情

#### 帳款展開增強 (contract-cases 風格)
- VendorAccountDetailPage: 展開顯示合約金額+年度+報價狀態+報價詳情連結
- ClientAccountDetailPage: 展開顯示合約金額+年度+狀態+連結
- 後端: vendor_payable_repo 增傳 total_price + quotation_status

#### ERP Hub 快速統計
- POST /erp/financial-summary/erp-overview — 7 模組記錄數
- Hub 各卡片顯示「N 筆記錄」

#### 請款開票流程
- POST /erp/invoices/create-from-billing — billing→invoice 銷項發票
- BillingsTab「開立發票」按鈕 + Modal

---

## [5.3.15] - 2026-03-31

### ERP Hub 統計 + 請款開票流程 + UI 完善

#### Hub 頁快速統計
- 新增 `POST /erp/financial-summary/erp-overview` — 7 模組記錄數統計
- ERPHubPage 各卡片顯示「N 筆記錄」

#### 請款→開票流程整合
- 新增 `POST /erp/invoices/create-from-billing` — 從 billing 建立銷項 invoice
- `CreateFromBillingRequest` schema + 雙向 FK 更新 (invoice↔billing)
- BillingsTab 新增「開立發票」按鈕 + Modal (發票號碼+日期)

---

## [5.3.14] - 2026-03-31

### ERP 模組 UI/UX 統一 + 入口頁 + 匯入功能

#### ERP 財務管理中心入口頁
- 新增 `ERPHubPage.tsx` (133L) — 9 模組卡片式導覽
- ROUTES: ERP_HUB (/erp)

#### UI/UX 統一審查修正 (9 頁面)
- 7 頁面補齊 `isError` + Alert 錯誤處理
- 3 頁面 static `message` → `App.useApp()` 上下文
- 2 頁面硬編碼路徑 → ROUTES 常數
- 1 頁面移除 `as any`

#### 資產 Excel 匯入
- 新增 `POST /erp/assets/import` — upsert by asset_code
- 前端 Upload 按鈕 + useImportAssets hook
- 中文類別/狀態自動映射

#### 品質指標
| 維度 | 值 |
|------|-----|
| ERP 頁面數 | **14** (含 Hub + 5 子模組) |
| ERP 路由數 | **27** |
| TypeScript | **0 errors** |
| 所有頁面 <500L | **確認** (max 433L) |
| isError 覆蓋 | **100%** |
| ROUTES 覆蓋 | **100%** (0 硬編碼) |
| `as any` | **0** |

---

## [5.3.13] - 2026-03-31

### 資產匯入匯出 + 盤點流程 + 發票整合

#### 資產 Excel 匯入
- 新增 `POST /erp/assets/import` — openpyxl upsert by asset_code
- 中文類別/狀態自動映射 (設備→equipment 等)
- 前端 Upload 按鈕 + useImportAssets hook

#### 資產盤點流程
- 新增 `POST /erp/assets/batch-inventory` — 批次建立 inspect log
- 新增 `POST /erp/assets/export-inventory` — 盤點報表 (含最近盤點日)
- 前端 Table row selection + 批次盤點 Modal + 盤點報表匯出按鈕

#### 發票→資產反向查詢
- 新增 `POST /erp/assets/by-invoice` — 從發票找關聯資產
- ERPExpenseDetailPage 新增「關聯資產」區塊
- ERPExpenseDetailPage 新增「關聯電子發票」按鈕 (auto-link-einvoice)

#### 前端整合按鈕
- ERPAssetListPage: 匯出+匯入+盤點報表+批次盤點 (4 按鈕)
- ERPExpenseDetailPage: 關聯電子發票+關聯資產顯示

---

## [5.3.12] - 2026-03-31

### 發票跨案件查詢頁面 + 電子發票自動關聯 + 資產匯出

#### 發票跨案件查詢頁面
- 新增 `ERPInvoiceSummaryPage.tsx` (168L) — 銷項/進項分類列表 + 統計
- ROUTES: ERP_INVOICE_SUMMARY (/erp/invoices/summary-view)
- 導覽: 發票總覽 (sort_order=14)

#### 電子發票自動關聯
- 新增 `POST /erp/expenses/auto-link-einvoice` — inv_num 匹配 einvoice_sync_logs
- `useAutoLinkEinvoice` mutation hook

#### 資產匯出 Excel
- 新增 `POST /erp/assets/export` — openpyxl 14 欄位 + 自動寬度
- `useExportAssets` mutation hook (postBlob + download)

---

## [5.3.11] - 2026-03-31

### 資產管理整合 + 發票跨案件查詢 + 案件財管連結

#### 資產表單頁面
- 新增 `ERPAssetFormPage.tsx` (221L) — 新增/編輯共用表單 (導航模式)
- ROUTES: ERP_ASSET_CREATE + ERP_ASSET_EDIT

#### 資產-發票關聯整合
- 新增 `POST /erp/assets/detail-full` — 資產完整詳情 (含關聯 ExpenseInvoice + ERPQuotation)
- `ERPAssetDetailPage.tsx` 關聯發票 Tab 增強 — 顯示發票明細 + 案件報價資訊
- `useAssetDetailFull` hook + `AssetDetailFull` interface

#### 發票跨案件查詢
- 新增 `POST /erp/invoices/summary` — 跨案件發票彙總 (銷項/進項分類)
- `InvoiceSummaryRequest` + `InvoiceSummaryItem` schema/type
- `useInvoiceSummary` hook

#### Pydantic v2 model 欄位衝突修正
- `asset_model` (alias="model") 取代保留字 `model`
- `validation_alias="model"` for ORM→Response 映射
- Service 層 `model_dump()` + 手動欄位映射

---

## [5.3.10] - 2026-03-31

### 資產管理模組 + 端點拆分 Phase 2

#### 資產管理 (新模組)
- 新增 `Asset` + `AssetLog` ORM 模型 (asset.py)
- 新增 `AssetRepository` + `AssetLogRepository` (asset_repository.py)
- 新增 `AssetService` with AuditMixin (asset_service.py)
- 新增 8 API 端點: list/create/detail/update/delete/stats/logs-list/logs-create
- 新增 `ERPAssetListPage.tsx` (237L) — 資產列表 + 統計 + 篩選
- 新增 `ERPAssetDetailPage.tsx` (249L) — 資訊 + 行為紀錄 + 關聯發票 (3 Tab)
- Alembic migration: `20260331a001_add_asset_tables`
- Schema: AssetCreateRequest/UpdateRequest/ListRequest + LogCreate + Response
- Types + Endpoints + 8 Hooks (queries + mutations)
- 路由 + 導覽註冊完成

#### 端點拆分 Phase 2 (4 檔案)
- `events.py` (684L) → events (296L) + events_create (273L) + events_batch (172L)
- `document_numbers.py` (562L) → document_numbers (376L) + document_numbers_crud (231L)
- `documents/crud.py` (554L) → crud (363L) + delete (220L)
- `ai/ai_stats.py` (532L) → ai_stats (218L) + ai_monitoring (342L)

#### api/client.ts 拆分
- `client.ts` (648L) → client (326L) + interceptors (340L)

#### vendor_id 批次配對
- `batch_link_vendor_payables.py` — 11 家廠商全部關聯 (4 匹配 + 7 新建)

#### 品質指標
| 維度 | 值 |
|------|-----|
| TypeScript | **0 errors** |
| Python 語法 | **0 errors** |
| 端點 >500L | **3** (526/513/501 — 接近閾值不拆) |
| 新增端點 | 8 (資產管理) |
| 新增頁面 | 2 |

---

## [5.3.9] - 2026-03-31

### ERP 廠商/委託帳款跨案件查詢 + 後端端點拆分 + 帳齡分析

#### 廠商帳款跨案件查詢 (AP)
- 新增 `vendor_accounts.py` — 2 API 端點 (summary + detail)
- 新增 `ERPVendorAccountsPage.tsx` (209L) — 廠商列表 + 統計 + 搜尋
- 新增 `ERPVendorAccountDetailPage.tsx` (198L) — 廠商跨案件應付明細

#### 委託單位帳款跨案件查詢 (AR)
- 新增 `client_accounts.py` — 2 API 端點 (summary + detail)
- 新增 `client_receivable_repository.py` — 跨案件應收 Repository
- 新增 `ERPClientAccountsPage.tsx` (212L) — 委託單位列表 + 統計
- 新增 `ERPClientAccountDetailPage.tsx` (212L) — 委託單位跨案件應收明細

#### 帳齡分析
- 新增 `POST /erp/financial-summary/aging` — 應收/應付帳齡分析 (0-30/31-60/61-90/90+ 天)
- 儀表板增強: AR vs AP 帳齡對比柱狀圖 + 應收帳齡明細表 (431L)

#### 後端端點拆分 (3 檔案, 消除 >500L)
- `graph_query.py` (886L) → `graph_entity.py` (229L) + `graph_admin.py` (286L) + `graph_unified.py` (428L)
- `dispatch_document_links.py` (736L) → `dispatch_doc_link_crud.py` (250L) + `document_dispatch_links.py` (227L) + `dispatch_correspondence.py` (287L)
- `user_management.py` (721L) → `user_management.py` (235L) + `user_permissions.py` (292L) + `role_permissions.py` (236L)

#### 廠商 vendor_id 批次配對
- `scripts/fixes/batch_link_vendor_payables.py` — 11 家廠商全部關聯 (4 匹配 + 7 新建)
- ERPVendorPayable.vendor_id NULL → PartnerVendor FK 完整

#### 追加端點拆分 (4 檔案)
- `document_calendar/events.py` (684L) → `events.py` (296L) + `events_create.py` (273L) + `events_batch.py` (172L)
- `document_numbers.py` (562L) → `document_numbers.py` (376L) + `document_numbers_crud.py` (231L)
- `documents/crud.py` (554L) → `crud.py` (363L) + `delete.py` (220L)
- `ai/ai_stats.py` (532L) → `ai_stats.py` (218L) + `ai_monitoring.py` (342L)

#### 前端 api/client.ts 拆分
- `client.ts` (648L) → `client.ts` (326L) + `interceptors.ts` (340L)

#### SSOT 修正
- `AccountRecordTab.tsx` — 8 個硬編碼 API 路徑 → ERP_ENDPOINTS 常數
- 4 頁面 `as any` → hook 層 typed unwrap (0 殘留)

#### 路由與導覽同步
- `ROUTES` — 新增 4 路由 (vendor-accounts + client-accounts + details)
- `AppRouter.tsx` — 4 新頁面路由註冊
- `init_navigation_data.py` — 2 導覽項目 (協力廠商帳款 + 委託單位帳款)

---

## [5.3.8] - 2026-03-30

### ERP 成本結構整合 + 作業性質管理 + 里程碑匯出入

#### 作業性質代碼管理
- 新增 `CaseNatureManagementPage.tsx` — 作業性質 DB 驅動管理 CRUD (取代硬編碼)
- 新增 `backend/app/repositories/case_nature_repository.py` — Repository
- 新增 `backend/app/schemas/pm/case_nature.py` — Schema
- 新增 `backend/app/api/endpoints/pm/case_nature.py` — 5 API 端點

#### 里程碑 XLS 匯出入
- `milestones.py` — 新增 export-xlsx + import-xlsx 端點
- `MilestonesTab.tsx` — 匯出/匯入按鈕 UI

#### ERP 請款流程整合
- `billings.py` — billing_id FK + 期別展開
- `BillingsTab.tsx` — 關聯請款期別

#### 統一 AR/AP 帳款紀錄
- 新增 `AccountRecordTab.tsx` — 應收/應付共用 Tab (294L)
- `ERPQuotationDetailPage.tsx` — Tab 結構重組 (成本結構 + 應收 + 應付)
- 應收: billing 數據轉統一格式
- 應付: vendor_payable 數據轉統一格式

#### 成本結構與損益分析
- 成本結構 Tab: 合約概況 + 應收概況 + 應付概況 + 損益分析 + 合約資訊
- 應收總額修正: 使用合約價 (total_price) 非已請款金額
- 損益分析: 營收含稅/稅額/未稅/淨利 + 費用明細

#### contract-cases 改善
- 里程碑/ERP Tab 改為永遠顯示 (不論是否成案)

#### 影響範圍
- `backend/app/api/endpoints/pm/case_nature.py` — 新增
- `backend/app/api/endpoints/pm/milestones.py` — 擴充 export/import
- `backend/app/api/endpoints/erp/billings.py` — 擴充 billing_id FK
- `backend/app/repositories/case_nature_repository.py` — 新增
- `frontend/src/pages/CaseNatureManagementPage.tsx` — 新增
- `frontend/src/pages/erpQuotation/AccountRecordTab.tsx` — 新增
- `frontend/src/pages/ERPQuotationDetailPage.tsx` — 重組 Tab
- 25 files changed, ~1,248 insertions

---

## [5.3.7] - 2026-03-30

### project_code 格式重構 + PM 成案自動化

#### 格式調整
- project_code 格式: `CK{年度}_{類別}_{性質}_{流水號}` → `{年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}`
- 移除 CK 前綴，相容舊格式查詢
- 範例: `2026_01_01_001`

#### 類別/性質重新定義
- 計畫類別: 01委辦招標(政府機關)、02承攬報價 (原 4 類簡化為 2 類)
- 作業性質: 擴展至 11 類 (地面測量/LiDAR掃描/UAV空拍/航空測量/安全檢測/建物保存/建築線測量/透地雷達/資訊系統/技師簽證/其他)

#### PM 成案自動化
- PM case 狀態變更為「已承攬」(contracted) 時自動觸發成案
- 自動產生 project_code + 建立 ContractProject + 同步 ERP Quotation
- PM model 新增 case_nature 欄位

#### 影響範圍
- `backend/app/core/constants.py` — 類別/性質常數
- `backend/app/services/case_code_service.py` — 格式生成 + promote 邏輯
- `backend/app/api/endpoints/pm/cases.py` — 自動成案觸發
- `backend/app/extended/models/pm.py` — +case_nature 欄位
- `backend/app/schemas/pm/case.py` — +case_nature schema
- `frontend/src/pages/contractCase/tabs/constants.ts` — 前端選項
- `frontend/src/pages/contractCase/tabs/CaseInfoTab.tsx` — tooltip
- `frontend/src/types/api.ts` — PMCase +case_nature
- `frontend/src/types/pm.ts` — PMCaseListParams +case_nature

---

## [5.3.6] - 2026-03-30

### Agent 進化報告推送 + 文件整合

#### Phase 2F: 進化報告推送
- `agent_evolution_scheduler.py` — 新增 `_push_evolution_report()` 方法
  - evolve() + LLM 摘要完成後 → NotificationDispatcher.broadcast_to_all()
  - 環境變數配置: `EVOLUTION_PUSH_LINE_USERS`, `EVOLUTION_PUSH_DISCORD_CHANNELS`
  - 推送格式: 進化摘要 + 信號/動作統計

#### 文件整合
- `SESSION_20260329_SUMMARY.md` — 完整 session 統整 (11 章節)
- `tech_debt_20260329.md` — 更新描述 (3 CRITICAL 已解消)

---

## [5.3.5] - 2026-03-29

### Document AI 多模態 — OCR + LLM 混合架構

#### 附件內容索引管線
- 新增 `attachment_content_indexer.py` — PDF/DOCX/TXT → OCR → chunk → embedding
  - 混合策略: pdfplumber (文字型) + Tesseract OCR (掃描型, 400字/頁門檻)
  - 複用現有 DocumentChunker + EmbeddingManager
  - 50 頁上限 + [附件:xxx] 前綴標記
- 新增 API 端點: `POST /ai/embedding/attachment-index` (單筆/批次)
- 新增 API 端點: `POST /ai/embedding/attachment-stats` (覆蓋統計)

#### Document AI 架構文件
- 新增 `docs/DOCUMENT_AI_ARCHITECTURE.md`
  - OCR + LLM 混合策略圖解
  - Document AI 技能圖譜 (8 大技能域)
  - 多模態發展路線圖 (Phase 1-4)

---

## [5.3.4] - 2026-03-29

### Agent 自主學習報告

#### Phase 2D: LLM 進化摘要
- `agent_evolution_scheduler.py` — 新增 `_generate_evolution_summary()` 方法
  - evolve() 完成後用 LLM 生成自然語言進化描述 (第一人稱, 2-3 句話)
  - 摘要存入 Redis `agent:evolution:latest_summary` (7 天 TTL)
- `get_evolution_status()` — 回傳時自動附加最新摘要

#### Phase 2E: 前端進化報告
- `EvolutionTab.tsx` — QualityTrendCard 新增摘要區塊 (綠底卡片, LLM 生成文字)

---

## [5.3.3] - 2026-03-29

### 數位分身預測洞察

#### Phase 2A: 預測引擎
- `digital_twin_service.py` — 新增 `get_predictive_insights()` 方法
  - 品質趨勢預測: eval_history 線性迴歸斜率計算 → improving/stable/declining
  - 工具降級預警: tool_monitor 成功率 → critical/high/medium 風險分級
  - 進化信號摘要: Redis 隊列深度監控
- `digital_twin.py` — 新增 `POST /ai/digital-twin/insights` 端點

#### Phase 2B: 前端洞察面板
- `DashboardTab.tsx` — 新增 InsightsSection 子元件 (298L, <500L)
  - 品質趨勢指標 (箭頭 + 預測分數)
  - 工具風險計數 + Tag 預警
  - 洞察列表

#### 品質指標
- TypeScript: **0 errors**
- Python: **0 errors**
- DashboardTab: 298L (<500L)

---

## [5.3.2] - 2026-03-29

### Agent 閉環強化 + 多代理激活

#### Phase 1A: 回饋閉環
- `ai_feedback.py` — 負面回饋 (score=-1) 自動注入 `agent:evolution:signals` Redis 隊列
- EvolutionScheduler 下一輪進化時會消費人類回饋信號，自動降級相關模式
- 信號格式: `{type: "user_negative_feedback", severity: "HIGH", ...}`

#### Phase 1B: Conductor 多代理激活
- `agent_supervisor.py` — dispatch 不再歸併到 doc，保持獨立域
- 新增跨域觸發短語偵測 (regex): 公文+進度, 案件+廠商, 派工+公文 等 10 組
- 多域查詢 (PM+ERP, Doc+Dispatch) 現在真正觸發 Supervisor 並行工具補充

#### 品質指標
- Python: **0 errors**
- 回饋→進化路徑: 使用者 👎 → Redis signal → EvolutionScheduler → 模式降級

---

## [5.3.1] - 2026-03-29

### 全棧重構 + RolePermission API + 新指令 + 復盤

#### 程式碼重構 (5 檔案拆分)
- `useDocumentCreateForm.ts` 676→364L — 拆分 useDocumentFormData (190L) + useDocumentFileUpload (126L)
- `types/ai.ts` 1535→28L — barrel re-export + 4 領域檔 (ai-document/ai-search/ai-knowledge-graph/ai-services)
- `AIStatsPanel.tsx` 473→320L — 提取 SearchStatsDashboard (188L)
- `DispatchWorkflowTab.tsx` 493→380L — 提取 useDispatchDocLinking (164L)
- `ContractCaseDetailPage.tsx` 478→263L — 提取 useContractCaseHandlers (264L)

#### 新增功能
- RolePermission 後端 API — 3 端點 (roles/{role}/permissions/detail, update, roles/list)
- RolePermissionDetailPage 前端整合 — 移除 TODO，接入 API
- `/health-dashboard` 指令 — 系統健康一鍵報告
- `/refactor-scan` 指令 — 超閾值檔案掃描 + 拆分建議

#### 文件同步
- CHANGELOG 補入 v5.3.0 完整記錄
- architecture.md 新增 digitalTwin/skillEvolution/profile 模組 + 後端服務 + 型別結構
- skills-inventory.md 新增 v5.3.0 段落 + 2 新指令
- MEMORY.md 修正 Layer 3 (已運作非 0%) + Inference Profiles (已就緒)

#### 復盤
- 復盤報告 `docs/reports/SYSTEM_REVIEW_20260329.md` — 技能樹 + 發展藍圖
- 新增 11 檔 + 修改 13 檔，淨減 1,900L (3,474→1,574L, -55%)

#### 品質指標
- TypeScript: **0 errors**
- Python: **0 errors**
- 所有 hooks <500L | 所有元件 <500L | 所有服務 <600L
- 指令數: 28→30 (新增 health-dashboard + refactor-scan)

---

## [5.3.0] - 2026-03-28

### 資安管理中心 + Agent 效能優化 + 表格強化

#### 資安管理中心 (SecurityCenterPage)
- 新增 `SecurityCenterPage.tsx` — OWASP Top 10 儀表板 + 問題追蹤 + 掃描 + 通知 + 模式庫
- 新增 `security_scanner.py` — 自動安全掃描排程 (每日 02:00 + 手動觸發, 15 條 OWASP 規則)
- 新增 `security.py` endpoint — 掃描/問題追蹤/通知 API
- 新增 Security ORM model — 掃描結果 + 安全問題持久化
- 即時安全分數計算 (scanner + API 統一基於 open issues)
- 通知去重 + 掃描分數修正 + 欄位比例統一
- 資安問題全部清零 — 51 筆 resolved + 1 筆 accepted risk
- pip 依賴漏洞修復 52→1 — 26 套件升級

#### Agent 效能優化 (效能 64%↑)
- 派工單查詢 13.7s→8.6s — 規則引擎 + 跳過 auto_correct
- chitchat 保守策略 — 預設走 Agent 工具查詢，不幻覺回答
- tool_loop 強制移除派工單後冗餘搜尋 — 程式碼層攔截
- auto_corrector 派工單已找到時跳過所有修正
- dispatch summary 完整列出關聯公文 — 解決 LLM 合成遺漏
- groq 合成路由 + pattern 門檻調低 + redis 工具快取

#### 表格欄位強化
- 新增 `tableEnhancer.ts` — enhanceColumns 工具，一行加入排序篩選
- 新增清單 Z-9 表格篩選排序 + Z-10 共用元件強制規範

#### Bug 修復
- 契金管控 MissingGreenlet — 列表查詢補齊 selectinload(payment)
- self_awareness SSE 事件顯示擅長領域
- 密碼安全修復 + 假陽性排除 + 認證偵測強化

#### 文件更新
- 新增清單 Y — agent/AI 服務開發 11 條強制規範 (v1.20.0)
- 新增清單 Z — 資安開發強制規範 8 條 (v1.21.0)
- v5.3.0 版本升級 — CLAUDE.md 同步

#### 品質指標
- TypeScript: **0 errors**
- Backend Tests: **2,881 passed** (2 flaky)
- 安全分數: **100/100** (51 issues resolved)
- Agent 效能: **+64%** (派工單場景)

---

## [5.1.17] - 2026-03-23

### SSOT 修復 + 覆盤儀表板 + 系統文件同步

#### SSOT 型別遷移 (前端 8 型別 + 後端 3 型別)
- `VoiceTranscriptionResult` → `types/ai.ts` (從 `api/ai/adminManagement.ts`)
- `DelegateRequest` + `DigitalTwinStreamCallbacks` → `types/ai.ts` (從 `api/digitalTwin.ts`)
- `TaskJobRecord` → `types/ai.ts` (從 `api/digitalTwin.ts`)
- `AgentNode` + `AgentEdge` + `AgentTopologyResponse` → `types/ai.ts` (從 `api/digitalTwin.ts`)
- `DigitalTwinQueryRequest` → `schemas/ai/digital_twin.py` (從 endpoint)
- `TaskApprovalRequest` + `TaskRejectionRequest` → `schemas/ai/digital_twin.py` (從 endpoint)

#### 覆盤儀表板 UI
- 新增 `ReviewDashboardPanel.tsx` — 6 子系統狀態 + 排程器面板
- 整合至 `ServiceStatusTab` (AI 助理管理 > 服務狀態)

#### 系統文件同步
- CLAUDE.md 版本號 v5.1.15 → v5.1.17
- CHANGELOG 補完 v5.1.16~v5.1.17

#### 全系統覆盤結果
- 後端: SSOT A+ / Repository A / 服務模組化 A- / API POST 一致性 A+
- 前端: SSOT A+ / React Query A+ / antd v6 A+ / 元件 <500L A
- 測試: 後端 1,685 / 前端 2,962 / 頁面覆蓋 89%
- 遷移: 78 migrations, 單一 HEAD

---

## [5.1.16] - 2026-03-23

### gstack 深度整合 v2.0 — 安全護欄 + 指令升級

#### 新增安全護欄 (gstack /careful + /freeze + /guard 理念)
- `careful-guard.ps1` — PreToolUse hook 攔截危險 Bash 命令 (CRITICAL 10 + WARNING 14 模式)
- `freeze-scope.ps1` — PreToolUse hook 限制 Edit/Write 範圍 (freeze-scope.json 配置)
- `/careful` 指令 — 查看攔截規則與狀態
- `/freeze` 指令 — 設定編輯範圍鎖定
- `/unfreeze` 指令 — 解除鎖定
- `/guard` 指令 — careful + freeze 合一模式
- `settings.json` 新增 2 個 PreToolUse hooks (Bash matcher + Write|Edit matcher)

#### 指令升級 (v1→v2)
- `/security-audit` v2.0 — 8 階段 CSO 等級審計 (OWASP Top 10 + STRIDE + 資料分級 + 信心閾值 8/10 + 假陽性過濾 10 規則)
- `/code-review` v2.0 — Scope Drift 偵測 (on-scope/adjacent/drift 分類) + Fix-First 模式 (AUTO-FIX vs ASK 分類審查)
- `/ship` v2.0 — 測試失敗歸因 (in-branch/pre-existing/flaky) + Review 就緒檢查 + 13 層 bisectable commit 分組
- `/retro` v2.0 — Per-author 貢獻分析 + Compare 趨勢模式 + Session 偵測 (deep/medium/micro) + 版本範圍回顧

#### 新增指令
- `/document-release` — 發布後文件同步 (6 類文件自動檢查: architecture/skills-inventory/hooks-guide/CHANGELOG/checklist/types)

#### 文件同步
- `skills-inventory.md` 更新 — 新增 5 指令、3 升級記錄
- `hooks-guide.md` 更新 — 新增 2 PreToolUse hooks

---

## [5.1.15] - 2026-03-23

### ERP 財務模組 Phase 4 前端 + LINE 整合 + 系統優化

#### ERP 財務前端 (Phase 4 完成)
- 費用報銷列表/詳情頁面 (ERPExpenseListPage, ERPExpenseDetailPage)
- 統一帳本頁面 (ERPLedgerPage)
- 財務儀表板 (ERPFinancialDashboardPage) — Recharts 月趨勢+預算排名
- 電子發票同步頁面 (ERPEInvoiceSyncPage)
- 4 API 模組 (expensesApi, ledgerApi, financialSummaryApi, einvoiceSyncApi)
- useERPFinance hook — 費用/帳本/儀表板/電子發票完整 hooks
- ERP 型別定義 (+452L in types/erp.ts)
- 路由三處同步完成 (types.ts / AppRouter.tsx / init_navigation_data.py)

#### LINE Login 整合 (v5.1.14~v5.1.15)
- LINE OAuth 2.1 callback 端點 (line_login.py)
- StrictMode 雙重 mount 防護 (processedRef)
- id_token email 解碼 (LINE Verify API)
- 前端 scope 加入 `email`
- LINE bind/unbind 管理端點
- 公網域名議題延緩 (私有 IP 不支援 LINE OAuth redirect_uri)

#### 後端服務拆分 (v5.1.13)
- document_service 866→613L (拆出 dispatch_linker + import_logic)
- system_health_service 拆分優化
- canonical_entity_service 拆分

#### 系統優化 (v5.1.10~v5.1.12)
- ERP Phase 3.6~7-E: 安全加固 + dashboard + nightly scanner
- CORS 修復 + HTTPS proxy (自簽憑證 SAN)
- userform 拆分 + AuthProvidersTab (LINE/Google 管理)
- Knowledge Graph 載入優化 (limit 300→150, staleTime 5min)
- antd v6 deprecation 修正 (Steps direction→orientation)
- React Query staleTime 30s→2min (減少頁面切換重載)

#### 測試修復
- vendor_payable auto-ledger 測試修復 (FakePayable 新增 vendor_id)
- quotation_service RuntimeWarning 清理 (async mock _validate_case_code)

#### 系統指標
| 維度 | 數值 |
|------|------|
| 後端測試 | 2,666+ passed |
| 前端測試 | 2,837+ passed |
| ERP 端點 | 45 (8 sub-routers) |
| 前端頁面 | 183 files |
| 前端元件 | 177 files |

---

## [5.0.0] - 2026-03-20

### v5.0 NemoClaw 代理人正式版

#### 里程碑摘要
NemoClaw 代理人正式發布，歷經 70+ commits 從 v1.84.3 升級：
- **乾坤智能體**: 41 模組、74 工具 (23 手動 + 51 auto-discovered)
- **自覺層**: 5 Phase 完成 (self-talk → journal → transparency → capability → mirror)
- **vLLM 本地推理**: Qwen2.5-7B-AWQ, RTX 4060 8GB, 月費 $0
- **多專案架構**: CK_Missive + CK_NemoClaw (監控塔) + CK_OpenClaw (通用引擎)

#### 前端品質 (antd v6 全面合規)
- antd List → Flex: 19 檔案替換，保留 4 正當用法
- Card `size="default"` → `"medium"`: 全域修正
- Select `dropdownRender` → `popupRender`
- InputNumber `addonBefore` → `prefix`: 5 處
- 0 TSC errors, 2,837 tests passed

#### 承攬案件管理
- 詳情頁新增刪除功能 (Popconfirm 二次確認 + 級聯解除 FK)
- 建立端點 `POST /projects/` → `/projects/create` (修正 redirect_slashes 404)

#### OpenClaw 聯邦協議
- federation_client: endpoint `/reason`, 標準化 payload (agent_id + action + payload)

#### 系統指標
| 維度 | 數值 |
|------|------|
| 後端測試 | 2,568+ passed |
| 前端測試 | 2,837 passed |
| Skills | 23 project + 48 shared |
| Agents | 5 project + 8 shared |
| Commands | 23 |
| AI 模組 | 74 |
| 工具 | 74 (23 + 51 auto) |
| DB 索引 | 253 (optimized) |
| NER | 100% (5,915 entities) |
| 文件 | 1,638 (100% chunked) |

---

## [1.84.3] - 2026-03-19

### 全系統優化 — 十二輪深度重構 + NIM 整合

#### 資料匯入
- 851 筆公文匯入 (541 新增 + 310 更新), 0 錯誤
- 733 PDF 附件批次上傳 (173 → 906), 112 磁碟缺檔
- NER 100% 完成 (5,915 entities, 0 pending), KG 全量入圖
- 機關代碼回補: 0 → 47/93 有代碼
- 匯入腳本: `scripts/fixes/import_112_documents.py`, `batch_attach_documents.py`

#### 後端服務拆分 (5 服務 → 12 新模組)
- document_service: 866→613L (+dispatch_linker +import_logic)
- graph_query_service: 853→351L (+graph_entity_graph_builder)
- agent_orchestrator: 929→700L (+post_processing +streaming_helpers)
- agent_planner: 902→613L (+auto_corrector +learning_injector)
- project_service: 544→411L (遷移至 Repository)

#### Repository 遷移 (5 服務, 50+ 查詢 → 0 繞過)
- dispatch_link_service, statistics_service(新建), agency_matching_service, project_service, case_code_service

#### 前端元件拆分 (16 元件, 18→0 個 >500L)
- 最大: CorrespondenceBody 638→179L (-72%), UserManagementPage 501→157L (-69%)

#### 新功能 (9 項)
- KB 內容全文搜尋: `POST /knowledge-base/search` + 前端 Search UI
- Graph-RAG 融合: RAG v2.4.0, KG 實體擴展 (synonyms+canonical+aliases)
- Agent 工具動態發現: ToolRegistry v1.2.0, 3 層評分 (query type+entity+KG context)
- 跨圖譜聯合查詢: `POST /ai/graph/unified-search` (KG+Code+DB 並行)
- 自適應上下文窗口: simple(2)/medium(4)/complex(6) turns
- ExcelImportService upsert 模式
- ProjectMatcher 強化 (min 8 chars + 3x ratio)
- Agent 策略 YAML: `config/agent-policy.yaml`
- 推理 Profile: `config/inference-profiles.yaml` (6 profiles)

#### 效能優化
- DB 索引: 274→253 (-21 重複, +11 新增), idle_in_transaction 5min
- three.js lazy-load (~600KB 延遲載入), antd List→Flex (9), Collapse→items (1)
- 連接池救援: 6 個 idle-in-transaction 連線終止 (最長 57min)
- 後端整合測試 event loop 修復 (2568 全通過)
- 前端 flaky 測試修復 (16 files, 2837 全通過)

#### NIM 整合 (部分完成)
- NGC Docker 登入: OK
- NIM 映像下載: latest + 1.8.3 (10.4GB)
- docker-compose nim profile: 配置完成
- NVIDIA API Key: 已配置 (.env)
- **受阻**: CUDA 12.8+ / Driver 580.95+ 尚未公開發布

#### 最終指標
- 後端測試: 2,568 passed (0 failures)
- 前端測試: 2,837 passed (0 flaky)
- TypeScript: 0 errors
- SSOT: 0 violations
- >500L 前端元件: 0
- Repository 繞過: 0
- Chunk/Embed/NER: 100%
- 全 4 服務 healthy

---

## [1.84.1] - 2026-03-18

### 系統復盤與架構優化

#### SSOT 修復
- PM/ERP endpoints 本地 BaseModel 遷移至 schemas/ (6 檔案, 8+ 違規)
- 新增共用 schema: `CaseIdRequest`, `IdRequest` 等

#### 文件同步更新
- skills-inventory.md: 更新模組統計 (66 AI modules, 31 agent modules)
- architecture.md: 補充 PM/ERP endpoints/schemas 結構
- directory-structure.md: 補登 review-checklist.md
- MEMORY.md: 精簡歷史段落，控制 200 行以內

#### 復盤發現
- 前端 SSOT/React Query/Endpoint 常數化: 零違規
- 後端 Repository 層缺口: PM/ERP 模組直接 DB 存取待改善
- 前端大元件待拆分: 23 個超 500L (top: KnowledgeGraph 922L)
- 後端 Service 膨脹: 10 個超 500L (top: agent_orchestrator 928L)

---

## [1.84.0] - 2026-03-16

### 乾坤智能體 v4.0.0 — 全 Phase 完成 (多模態+聯邦+並行)

#### Phase 10.2: OCR 圖像辨識
- tool_executor_document 增強: pytesseract OCR (chi_tra+eng)
- 支援格式: PNG/JPG/JPEG/TIFF/BMP
- Image-only PDF 偵測: < 50 chars/page → 自動 OCR
- 優雅降級: Tesseract 未安裝時回傳提示訊息

#### Phase 10.3: 語音轉文字
- 新增 `voice_transcriber.py`: Groq Whisper API (主) + Ollama (備)
- LINE 語音訊息: webhook 自動轉文字 → agent 處理
- Redis 快取 24h TTL (避免重複轉錄)

#### Conductor 並行 Agent
- 新增 `agent_conductor.py`: asyncio.gather 並行子任務
- 角色分配: DOC/DISPATCH/PM/ERP/GRAPH
- 錯誤隔離: 單一子任務失敗不阻塞其他
- 結果合併: 去重 + 關聯度排序

#### MCP Server 評估
- mcp>=1.0.0 依賴已存在, agent_query_sync 已提供 MCP 相容介面
- 結論: 現有架構已具 MCP 能力, 暫不需額外標準化

#### 統計
- AI 服務模組: 62→66 (+4: voice_transcriber, agent_conductor, OCR增強, federation)
- 後端測試: 2315→2347 (+32)
- 後端測試檔案: 116→120 (+4)

---

## [1.83.9] - 2026-03-16

### 乾坤智能體 Phase 10.1 + Phase 11 + 最終生產就緒掃描

#### Phase 10.1: PDF/DOCX 文件解析工具
- 新增 `tool_executor_document.py`: PDF (pdfplumber) + DOCX (python-docx) + TXT 文字提取
- 新增 `parse_document` 工具 (第 19 個): 解析公文附件供 RAG 問答使用
- 新增 `pdfplumber>=0.10.0` 依賴

#### Phase 11: 聯邦智能介面
- 新增 `federation_client.py`: CK_OpenClaw 雙向查詢介面 (httpx async, 30s timeout)
- 新增 `ask_external_system` 工具 (第 20 個): 委派超出領域的查詢到外部 AI 系統
- 支援系統: openclaw (URL + Token via env vars)
- 12 個新測試通過

#### 工具系統擴充
- ToolRegistry: 18→20 工具 (+parse_document, +ask_external_system)
- ToolResultGuard: 新增 2 個回退模板
- 測試更新: tool count assertions 18→20

---

## [1.83.8] - 2026-03-16

### 乾坤智能體 Phase 9.3 主動推薦 + 最終架構驗證

#### Phase 9.3: 主動推薦服務
- 新增 `proactive_recommender.py`: 掃描近 24h 新公文 × 使用者興趣匹配
- 新增 `POST /ai/stats/recommendations` 端點 (個人化推薦)
- 整合 ProactiveTriggerService → 新增 `recommendation` 警報類型
- AI 服務模組: 62 個 (含 proactive_recommender, user_query_tracker)

#### 最終架構驗證
- 後端 .py 檔案: 376 個
- 前端 .tsx 檔案: 407 個, .ts 檔案: 321 個
- 後端測試: 116 files / 2289 passed
- 前端測試: 201 files / 2754 passed
- AI 服務模組: 62 個 (文件記載 57→62, +5 新模組)

---

## [1.83.7] - 2026-03-16

### 乾坤智能體 Phase 8-9 + Embedding Backfill + Page Split R4

#### Phase 8: 階層化評估信號
- agent_self_evaluator: 信號分級 CRITICAL/HIGH/MEDIUM/LOW (取代二值 needs_improvement)
- agent_orchestrator: 自適應超時 base + tool_count*2 + question_length/100 (cap 30s)
- 27 個新測試通過

#### Phase 9.1-9.2: 使用者查詢圖譜
- 新增 `user_query_tracker.py`: Redis HINCRBY 原子計數 + 30 天 TTL
- 5 類興趣標記: agency/project/document_type/entity/topic
- orchestrator 非阻塞整合: `asyncio.create_task(tracker.track_query(...))`

#### Chunk Embedding Backfill
- backfill 腳本就緒 (`scripts/fixes/backfill_chunk_embeddings.py`)
- pgvector 未安裝 → embedding 列不存在 → 需先安裝 pgvector

#### Page Split Round 4
- NavigationTreePanel: 614L → ~350L, 提取 NavigationTree/NavigationFormModal/constants

#### 前後端清理
- 移除 3 個 legacy GET fallback (vendors/documents/agencies API)
- health.py HTTPException detail dict → string

---

## [1.83.6] - 2026-03-16

### 乾坤智能體 Phase 6-7 + 前後端架構清理

#### Phase 6: 生產數據基礎設施
- DB 遷移驗證: agent_traces/tool_call_logs/learnings/chunks 全部就緒
- document_chunks: 1092 筆已存在 (backfill 已完成)
- search_vector (BM25): 1091/1088 筆已填充
- agent_learnings: 1 筆初始學習記錄

#### Phase 7.1: 學習注入語意篩選
- agent_planner: 學習注入前 fetch 3x candidates → cosine similarity 篩選 top-5
- 避免不相關學習干擾規劃品質

#### 前後端架構清理
- 移除 3 個 GET API fallback (vendorsApi/documentsApi/agenciesApi) — POST-only 下永不觸發
- 清除 unused imports (ApiException, normalizePaginatedResponse, LegacyListResponse)
- 移除 4 個對應的 GET fallback 測試
- 後端安全掃描: 0 個 GET endpoint, 0 個 str(e) 洩漏至客戶端
- 前端掃描: 0 個生產 `as any`, 0 個 apiClient.get (生產代碼)

#### 測試結果
- 前端: 201 files / 2754 passed / 0 failed
- 後端: 2262 passed / 0 failed

---

## [1.83.5] - 2026-03-16

### 系統全面審查 + SSOT 違規修正 + 架構優化建議

#### 系統審查結果
- 全面掃描 57 AI 模組 + 34 Repository + 50+ 前端頁面 + 186 測試檔案
- 架構合規等級: **A 級** (SSOT/DI/Repository/React Query 全面遵循)
- TypeScript 嚴格模式: 0 errors, 0 `as any`, 全開啟
- ESLint: 0 errors, 7 warnings (不可避免 fast-refresh)

#### 發現 & 修正 — SSOT 違規 (P0)
- ⚠️ 3 個 endpoint 檔案定義了本地 BaseModel (違反 SSOT):
  - `ai_stats.py`: 4 個 BaseModel → 應建立 `schemas/ai/stats.py`
  - `line_webhook.py`: 1 個 BaseModel → 應搬至 `schemas/line.py`
  - `dispatch_document_links.py`: 1 個 BaseModel → 應搬至 `schemas/taoyuan/`
- `requirements.txt`: httpx 重複 (line 35 & 78)

#### 規範文件更新
- `CHANGELOG.md`: 新增 v1.83.5 全面審查記錄
- `DEVELOPMENT_GUIDELINES.md`: 新增第 15 項常見錯誤 (endpoint 本地 BaseModel)
- `skills-inventory.md`: 前端頁面拆分成果數據更新
- `architecture.md`: AI 服務直接 ORM 查詢清單補充

#### P1 測試覆蓋率大幅提升
- AI Management 元件測試: 0% → 100% (11 test files, 135 tests)
  - OverviewTab, HistoryTab, EmbeddingTab, KnowledgeGraphTab
  - OllamaManagementTab, ServiceMonitorTab, AgentPerformanceTab
  - PromptManagementPanel, SynonymManagementPanel, statusUtils, ManagementTabs
- System hooks 測試: 23% → 77% (7 new test files, 72+ tests)
  - useCalendar, useDashboard, useAdminUsers, useAIPrompts
  - useAISynonyms, useDepartments, useDocumentStats
- Business/Utility hooks 測試: (7 new test files)
  - useDocumentCreateForm, useDocumentsWithStore, useProjectsWithStore
  - useAgenciesWithStore, useVendorsWithStore, usePermissions, usePerformance
- 前端測試總數: 186 → **201 files**, 2512 → **2758 tests** (+246)
- 後端單元測試: 1728 → **2262 tests** (+534, 含新增服務測試)

#### P2-1: Page Splitting Round 3 (4 頁面)
- `ProfilePage.tsx`: 593L → 280L (-53%), 提取 ProfileInfoCard/AccountInfoCard/PasswordChangeModal
- `AdminDashboardPage.tsx`: 567L → 247L (-56%), 提取 UserStatsCards/SystemAlertsCard/PendingUsersCard/QuickActionsPanel/DocumentStatsSection/RoleStatusReference
- `StaffDetailPage.tsx`: 614L → 257L (-58%), 提取 StaffDetailHeader/StaffBasicInfoTab/StaffCertificationsTab
- `SimpleDatabaseViewer.tsx`: 623L → 250L (-60%), 提取 DatabaseStatsCards/OverviewTable/RelationView/ApiMappingView/TableDetailModal

#### P2-2: Tool Monitor 儀表板
- 後端新增 `POST /ai/stats/tool-registry` 端點 (18 工具元資料+即時狀態)
- 新增 `ToolRegistryItem`/`ToolRegistryResponse` schema (SSOT)
- 前端 AgentPerformanceTab 新增 "工具清單" 表格 (名稱/描述/類別/優先序/上下文/狀態)

#### 緊急修復: 資料庫遷移未套用
- **根因**: ORM 定義 `ner_pending` 欄位但資料庫無此欄 → 所有 SELECT 查詢 500 錯誤被 catch 吞掉
- 套用 5 個缺失遷移: ner_pending + agent_traces + agent_learnings + document_chunks + BM25 tsvector
- Alembic 版本: `20260313a002` → `20260315a003`
- 公文列表 (1088 筆) 和派工列表 (123 筆) 恢復正常

#### 修復: 405 Method Not Allowed
- `calendarApi.getGoogleStatus()`: GET → POST (符合 POST-only 政策)
- `SystemHealthDashboard`: GET → POST

#### 修復: antd v6 Deprecation 警告 (60+ 處)
- `Drawer width` → `styles.wrapper.width` (3 處: Layout/DatabaseManagement/PreviewDrawer)
- `Spin tip` → `Spin description` (20 處, 18 檔案)
- `Card bodyStyle` → `styles.body` (2 處)
- `notification({ message:` → `notification({ title:` (15+ 處, 8 檔案)

---

## [1.83.4] - 2026-03-16

### TypeScript Strict Mode + 測試覆蓋率提升 + 服務修復

#### TypeScript Strict Unused 正式啟用
- `noUnusedLocals: true` + `noUnusedParameters: true` 正式啟用
- 修復 43 個 src/ 檔案 + 4 個 shared-modules/ 檔案的 unused imports/variables
- 生產程式碼: `_` 前綴模式用於保留變數，`void` 抑制用於未來使用的值
- 測試程式碼: 移除 unused `React`/`screen`/`waitFor`/`fireEvent` imports

#### 測試覆蓋率提升
- 新增 8 個元件 smoke tests: PaymentsTab, ProjectsTab, DispatchOrdersTab, EventFormModal, LoginHistoryTab, MFASettingsTab, SimpleDatabaseViewer, DocumentPagination
- 前端測試檔案: 133 → **186 個** (+53)
- 類別分布: 56 pages + 63 components + 22 hooks + 13 API + 7 config + 2 utils

#### 服務修復
- Ollama healthcheck: `curl` → `wget` (容器無 curl 導致 unhealthy)
- PM2 ck-backend: 停止 restart loop (port 8001 已被 uvicorn 佔用)
- Review Checklist 外部化: `.claude/review-checklist.md`
- QA Route Map: `.claude/qa-route-map.json` (8 E2E spec, 50+ trigger patterns)
- 首個工程回顧基線: `.claude/retros/2026-03-16.json`

---

## [1.83.3] - 2026-03-16

### gstack 啟發 — 認知模式分離 + 工作流強化

> 參考: [garrytan/gstack](https://github.com/garrytan/gstack) — 8 種認知模式的開發工具

#### 新增 Slash Commands (3 個)
- **`/ship`** — 統一發布工作流 (5 階段: pre-flight → merge+test → pre-landing review → commit → PR)
- **`/retro`** — 工程回顧指標追蹤 (commit 統計/LOC/測試比率/熱點/趨勢/JSON 持久化)
- **`/qa-smart`** — Diff-Aware 智慧測試 (4 模式: diff/full/quick/regression + 8 維度健康度評分)

#### 增強既有 Skills (2 個)
- **`/code-review`** 升級為兩階段結構化審查 — Critical pass (安全+正確性) → Informational pass (品質+規範) + CK_Missive 專案規範檢查
- **`/plan`** 加入 gstack Scope 模式 — Step 0 前提挑戰 + 3 種 Scope 模式 (EXPANSION/HOLD/REDUCTION) + 9 條 Prime Directives

#### gstack 對照分析結論
- 採納: 認知模式分離、統一發布管線、diff-aware 測試、結構化審查
- 不採納: 持久化瀏覽器 (使用 Playwright E2E 替代)、Cookie 導入 (macOS 專用)
- Commands 總數: 18 → 21 個

---

## [1.83.2] - 2026-03-16

### 系統規範全面審計 + 文件同步 + 測試覆蓋率提升

#### 規範文件全量更新
- `architecture.md`: AI 服務模組數修正 44→57 (13 個缺漏模組補齊)
- `architecture.md`: 新增後端 Repository 層結構 (34 類別: 21 ORM + 7 關聯 + 3 QueryBuilder + 3 桃園)
- `architecture.md`: 新增前端 Hooks 完整結構 (39 檔, 150+ hooks, 4 目錄分類)
- `architecture.md`: 新增 3 個 ORM 模型 (agent_trace, agent_learning, document_chunk)
- `skills-inventory.md`: Agent 模組清單更新至 24 個 (含 user_preference_extractor, document_chunker)
- `skills-inventory.md`: 新增 AI 服務全量分類表 (7 大類, 57 模組)
- `skills-inventory.md`: 新增 AI Management Tabs 完整清單 (14 個 Tab + API 端點對照)
- `ci-cd.md`: 新增 `bundle-size-check` Job (10 → 10 Jobs 完整記錄)

#### 測試覆蓋率提升
- 新增 17 個頁面 smoke tests (覆蓋率缺口 30% → 0%)
- 新增 7 個關鍵 Hooks 測試 (useDocuments/useProjects/useVendors/useCalendar 等)
- 前端測試檔案: 80 → 97+ 檔

#### Memory 修正
- AI 服務模組數: 44→57
- 前端頁面檔案數: 89→57 (修正統計錯誤)
- Bundle chunks: 22→23
- Config version: 1.83.0→1.83.1

#### 系統審計發現
- AI Management 3 個 wrapper Tab (ServiceStatus/DataAnalytics/DataPipeline) API 端點全部正確對應
- Repository 層 34 類別完整運作 (含 3 個 Fluent Query Builder)
- 前端 Hooks 三層架構: React Query → WithStore → 業務特定

---

## [1.83.1] - 2026-03-15

### 乾坤智能體 v3.1.0 — 自主成長能力強化 + NexusMind 對標分析

#### 自主成長能力 (對標 OpenClaw / NexusMind)
- **Chain-of-Tools**: `tool_chain_resolver.py` (175L) — 自動從前輪結果萃取 entity_id/dispatch_id/document_id 注入後續工具參數，19 tests
- **Cross-session Learning**: AgentPlanner 查詢時從 DB 載入歷史學習，注入 LLM planning prompt，11 tests
- **Pattern Learner Seeds**: `pattern_seeds.py` 29 個冷啟動模式 (7 類別)，首次查詢自動載入，13 tests
- **Agent Benchmark Suite**: `test_agent_benchmark.py` 50 標準問答 (8 類別, 14 工具)，21 回歸測試

#### 模組拆分重構
- `agent_tools.py` 1215L → 260L (-79%): 拆為 SearchToolExecutor(540L) + AnalysisToolExecutor(405L) + DomainToolExecutor(105L)
- `agent_synthesis.py` 745L → 518L (-30%): 提取 citation_validator(85L) + thinking_filter(187L)
- Agent 模組 15→22 個，總計 491 tests 通過

#### RAG 管線升級 (NexusMind 借鑑)
- **Document Chunking**: `DocumentChunk` 模型 + `document_chunker.py` (段落分割+滑動窗口+合併) + Alembic migration
- **BM25 全文搜尋**: `tsvector` + GIN index + 觸發器自動更新 + chunk retrieval BM25 boost
- **雙層使用者記憶**: `user_preference_extractor.py` — 規則式偏好萃取 (topic/format) + Redis+DB 雙寫 + planner 注入
- RAG pipeline: doc-level → chunk-level retrieval (graceful fallback)

#### 前後端架構全面複查
- 後端 391 API 端點, 37 Repository, 24 Agent 模組
- 後端大服務待拆: graph_query_service(1416L), code_graph_service(1262L), dispatch_order_service(990L)
- 前端 14 頁面 >500L (已完成 Top 4 拆分，Round 2 待續)
- 前端測試覆蓋率 39% (目標 80%)
- 無循環匯入、無 console.log 汙染、型別 SSOT 合規

#### NexusMind 對標結論
- 我方優勢: 自我學習、Chain-of-Tools、多域協調、工具監控、品質基準 (NexusMind 均無)
- 已採納: 文件分段 Embedding (P0)、BM25 混合搜尋 (P1)、雙層使用者記憶 (P1)

---

## [1.83.0] - 2026-03-15

### 乾坤智能體統整 + 大頁面拆分 + Phase 5 重構

#### 乾坤智能體 (OpenClaw Agent) 架構統整
- 完成 15 模組清單盤點 (5,554 行, 327 測試)
- Phase 1-3 全部完成: ReAct loop, 角色系統, Trace, 工具監控, 模式學習, 對話壓縮, 路由, 多域協調
- `ai_config.py` 升級至 v3.0.0 (48 配置參數)
- `tool_registry.py` 管理 18 工具 (含 PM/ERP 擴充)
- `agent_pattern_learner.py` 升級 v2.0.0: Jaccard → Embedding cosine similarity
- `agent_summarizer.py` 升級 v2.0.0: 3-Tier Adaptive Compaction + 學習萃取持久化

#### 前端大頁面模組化拆分 (Top 4)
- `CodeGraphManagementPage` 921L → 526L (-43%): 拆出 CodeGraphSidebar, ModuleConfigPanel, ArchitectureOverviewTab
- `BackupManagementPage` 920L → 404L (-56%): 拆出 5 Tab 元件 + StatsCards
- `KnowledgeGraphPage` 812L → 326L (-60%): 拆出 GraphLeftPanel, ShortestPathFinder, MergeEntitiesModal 等 5 元件
- `TaoyuanDispatchDetailPage` 912L → 545L (-40%): 拆出 DispatchDetailHeader + 2 hooks
- 總計: 3,565L → 1,801L (-49%), 新增 18 個模組化檔案

#### Phase 5 重構進度
- `agent_tools.py`: 1512L → 1215L (提取 agent_diagram_builder.py 323L)
- `agent_orchestrator.py`: 920L → 804L (提取 agent_conversation_memory.py 137L)
- LINE Push Scheduler: ProactiveTriggerService → LineBotService 整合
- Agent Performance: daily-trend API + LineChart (14 天查詢/延遲趨勢)

#### 系統文件更新
- `architecture.md`: 新增 44 模組 AI 服務結構 + 頁面模組化目錄
- `skills-inventory.md`: 新增 v1.83.0 智能體完整清單 + 配置參數 + 拆分成果
- Memory: 更新乾坤智能體發展進度與優化事項

---

## [1.82.0] - 2026-03-13

### 收發文正規化 + 知識圖譜強化 + 資料品質監測

#### 收發文單位正規化 (Receiver/Sender Normalization)
- 新增 `receiver_normalizer.py` — 6 種正規化模式：統編前綴移除、機關代碼括號格式、多受文者分割、換行正規化、代表人後綴移除、協力廠商後綴移除
- NFKC Unicode 雙向正規化 + 公文字號 → 機關名稱推斷 (如 `府工用字第` → `桃園市政府工務局`)
- `backfill_normalized_fields.py` 回填腳本 (200 筆/批次，支援 dry-run)
- 14 個單元測試覆蓋所有正規化模式

#### 資料庫 Schema 擴充 (+8 欄位, +3 FK)
- `documents`: `normalized_sender`, `normalized_receiver` (indexed), `cc_receivers` (JSON), `keywords` (JSON)
- `government_agencies`: `tax_id` (unique), `is_self`, `parent_agency_id` (自參照 FK)
- `canonical_entities`: `linked_agency_id` (FK), `linked_project_id` (FK) — NER 實體自動連結業務記錄
- 2 支 Alembic 遷移：`20260313a001`, `20260313a002`

#### 知識圖譜查詢強化
- `graph_query_service` 重構 (835 → 1700+ 行)：7-Phase 公文知識圖譜 Pipeline
- 三階段同源實體合併：完全匹配 → 包含匹配 (40% 閾值) → 文件共現配對
- 新增參數：`year` (民國年度篩選)、`collapse_agency` (同源合併開關)
- Redis 快取 (TTL=5min, key 含 entity_types/mentions/limit/year/collapse)

#### NER 提取排程器升級 (事件驅動)
- `extraction_scheduler` 升級為混合模式 (polling 60min + event-driven)
- `notify_new_documents()` — 文件建立時立即觸發 NER，無需等待排程
- `canonical_entity_service` 新增自動連結：org → agency, project → project

#### Tool Registry (工具註冊中心)
- 新增 `tool_registry.py` (v1.0.0) — Singleton 集中管理 9 個 Agent 工具
- LLM Schema + Few-shot 範例 + 上下文感知篩選 (doc/dev/all)
- `agent_tools.py` 工具數 6 → 9 (新增 navigate_graph, summarize_entity, draw_diagram)

#### 前端知識圖譜 UI 升級
- 視圖模式切換 (`entity` / `full`)
- `GraphToolbar` 新增年度篩選 Slider + 同源合併開關
- GraphNode 新增 `fullLabel`, `dispatch_nos` 屬性
- ChatMessage / AgentStepInfo SSOT 型別定義

#### 系統健康監測擴充
- 資料品質指標面板：發文機關 FK 覆蓋率 / 受文機關 FK 覆蓋率 / NER 覆蓋率
- `SystemHealthDashboard` 新增 data_quality 區塊

#### 文件匯入增強
- Excel 匯入自動呼叫 `receiver_normalizer.normalize_unit()`
- 公文 CRUD 自動回填 normalized 欄位 + 觸發 NER 排程

---

## [1.81.0] - 2026-03-11

### 知識庫瀏覽器 + Bundle 優化 + 程式碼品質強化

#### 知識庫瀏覽器 (Knowledge Base Viewer)
- 新增 `/admin/knowledge-base` 路由 — 三分頁：知識地圖、ADR、架構圖
- 後端 4 個 POST API: tree/file/adr-list/diagrams-list (3 層路徑穿越防護)
- 前端 `KnowledgeBasePage` + `KnowledgeMapTab` (樹狀 + Markdown) + `AdrTab` (表格 + 狀態標籤) + `DiagramsTab` (Segmented + Mermaid)
- `MarkdownRenderer` 通用元件：react-markdown + remark-gfm + Mermaid 委派

#### 知識圖譜實體配對 API
- `POST /dispatch/{id}/entity-similarity` — Jaccard 相似度計算
- 公文對照矩陣 Phase 2: 複合評分 (關鍵字 60% + 實體 40%)
- `useDispatchWorkData` 整合實體配對數據 (靜默失敗, retry:false)

#### Bundle 優化
- `KnowledgeGraph` chunk: **741KB → 34KB** (-95%)
- 新增 6 個 manualChunks: three, react-force-graph-2d/3d, cytoscape, mermaid, markdown
- `NaturalSearchPanel` lazy-load 化 (AIAssistantButton)

#### ESLint 修復
- 13 errors → **0 errors, 3 warnings** (不可消除的 fast-refresh 限制)
- 移除死檔案 `frontend/src/index.js`
- 修復: 未使用 import, Hook 依賴, displayName, useMemo 穩定性

#### 後端清理
- `app/schemas/ai/__init__.py` re-export 移除 (v3.0.0) — 20 個消費者已改用子模組路徑
- 22 個 endpoint 檔案 unused imports 清除
- 知識圖譜垃圾實體清理 (1 筆重複合併)
- MCP server shutdown logging error 修復
- `module-mappings` endpoint GET → POST (資安合規)

#### 端點 SSOT 更新
- `KNOWLEDGE_BASE_ENDPOINTS` (4 個端點) 加入 API_ENDPOINTS
- 端點群組測試: 25 → 26
- 導航項目新增: 知識庫瀏覽器 (AI 智慧功能子項)

---

## [1.80.0] - 2026-03-10

### 專案遷移 + 架構清理 + GitHub Actions 停用

#### 路徑遷移 (C:\GeminiCli → D:\CKProject)
- 全專案路徑替換：mcp_server.py、scripts、settings.local.json、docs 等
- 修復 `.env` 中 `POSTGRES_HOST_PORT=5434` 被註解導致 DB 連線失敗

#### 硬編碼消除
- `scripts/check_consistency.py` → `Path(__file__)` 相對路徑
- `backend/scripts/enrich_dispatch_from_master.py` → 相對路徑
- `backend/execute_missing_tables.py` → `dotenv` + `os.getenv`
- `backend/scripts/fix_doc_number_format.py` → `os.environ["DATABASE_URL"]`
- `backend/scripts/regenerate_project_codes.py` → `os.environ["DATABASE_URL"]`
- `backend/mcp_server.py` → `<YOUR_PROJECT_ROOT>` 佔位符

#### GitHub Actions 停用（收費問題）
- `ci.yml`：PR/排程觸發 → 僅 `workflow_dispatch` 手動觸發
- `cd.yml`、`ci-e2e.yml`、`deploy-production.yml`：確認均已停用自動觸發

#### 根目錄清理（18 個散落檔案）
- SQL 備份 → `docs/archive/sql/`
- 圖片資產 → `docs/archive/assets/`
- 過時工具/文件 → `docs/archive/`
- 臨時檔案 → 刪除 (openapi_temp.json, monitoring_config.json 等)

#### Backend 腳本整理（27 個散落腳本）
- 管理腳本 → `backend/scripts/admin/`
- 修復腳本 → `backend/scripts/fixes/`
- 過時腳本 → `backend/scripts/archive/`
- 重複腳本 → 刪除 (setup_admin_fixed.py, setup_admin_simple.py)

#### Scripts 目錄重組（31 個扁平腳本 → 6 個子目錄）
- `scripts/dev/` — 開發工具 (dev-start, dev-stop, start-backend)
- `scripts/checks/` — 驗證檢查 (verify_architecture, api-endpoints, skills-sync)
- `scripts/health/` — 系統健康 (health_check, system_monitor)
- `scripts/deploy/` — 部署腳本 (deploy-nas)
- `scripts/init/` — 初始化/配置 (database-init, config-manager, port-manager)
- `scripts/archive/` — 過時腳本存檔

#### 垃圾清理
- 刪除工件：`backend/=2.8.0`、`=2.0.32`、`nul`×3
- 刪除異常目錄：`backend/C:/`、`backend/backend/`
- 日誌清理：343MB → 10MB（釋放 333MB）

#### 配置修復
- `vite.config.ts`：OpenAPI 代理 8002 → 8001
- `package.json`：npm scripts 路徑同步至新目錄結構
- `.env`：移除 UTF-8 BOM 編碼
- `.gitignore`：新增 archive 目錄、ruff cache、pip 工件規則

#### 文件更新
- `CLAUDE.md`：scripts 路徑更新
- `.claude/rules/architecture.md`：scripts 目錄結構描述
- `.claude/rules/ci-cd.md`：GitHub Actions 停用說明
- `.claude/rules/skills-inventory.md`：verify_architecture 路徑
- `.claude/MANDATORY_CHECKLIST.md`：腳本路徑同步
- `.claude/DEVELOPMENT_GUIDELINES.md`：腳本路徑同步
- `.claude/commands/db-backup.md`：備份路徑更新

---

## [1.79.0] - 2026-03-06

### API 端點 SSOT 強化 — 零硬編碼 + 自動防護測試

**Fix: AI 端點重複值導致測試失敗 (P0)**:
- `AI_ENDPOINTS.ANALYSIS_GET` / `ANALYSIS_TRIGGER` 從靜態字串改為函數型端點
- `adminManagement.ts` 消費者改用函數呼叫（消除字串拼接）

**Fix: PROJECT_STAFF_ENDPOINTS 定義與後端不符 (P1)**:
- `DELETE` 從單參數改為雙參數 `(projectId, userId)`
- 新增 `PROJECT_LIST(projectId)` 和 `UPDATE(projectId, userId)`

**Fix: 端點定義缺失 (P1)**:
- `AUTH_ENDPOINTS` 新增 `GOOGLE`、`REGISTER`、`CHECK` 三個端點
- `ADMIN_USER_MANAGEMENT_ENDPOINTS` 新增 `PERMISSIONS_CHECK`

**Refactor: 消除全部硬編碼 API 路徑 (21 處 → 0 處)**:
- `authService.ts` 7 處 → 改用 `AUTH_ENDPOINTS` / `ADMIN_USER_MANAGEMENT_ENDPOINTS`
- `projectStaffApi.ts` 5 處 → 改用 `PROJECT_STAFF_ENDPOINTS`
- `projectVendorsApi.ts` 5 處 → 改用 `PROJECT_VENDORS_ENDPOINTS`
- `useDropdownData.ts` 2 處 → 改用 `PROJECTS_ENDPOINTS` / `USERS_ENDPOINTS`
- `adminManagement.ts` 2 處 → 改用函數型端點

**Test: 端點自動防護測試**:
- 新增 AI 分析持久化端點動態路徑測試
- 更新 `PROJECT_STAFF_ENDPOINTS` 測試（雙參數驗證）
- 新增 `AUTH_ENDPOINTS` GOOGLE/REGISTER/CHECK 測試
- 新增 `ADMIN_USER_MANAGEMENT_ENDPOINTS.PERMISSIONS_CHECK` 測試
- 新增 12 個 API 服務檔案匯入驗證測試

**Doc: 系統文件同步**:
- `CHANGELOG.md` 新增 v1.79.0 記錄
- `MANDATORY_CHECKLIST.md` 清單 L 新增函數型端點規範 + authService 注意事項
- `DEVELOPMENT_GUIDELINES.md` 新增常見錯誤 #15（硬編碼 API 路徑）
- `architecture.md` 更新全域錯誤處理區塊（新增 429 + CircuitBreaker）
- `skills-inventory.md` 新增 v1.79.0 元件清單
- `memory/MEMORY.md` 同步更新版本里程碑

**異動檔案**: 13 個檔案 (1 endpoints + 5 api/service + 1 hooks + 6 docs)

**驗證結果**: 端點測試 99 passed (↑13), TypeScript 0 errors, 生產碼零硬編碼

---

## [1.78.0] - 2026-03-05

### 系統規範更新 + 文件同步 + 架構盤點

**Doc: 系統規範文件同步**:
- `skills-inventory.md` 新增 v1.77.0 作業歷程共用模組區塊（WorkRecordStatsCard, useWorkRecordColumns, useDeleteWorkRecord, workCategoryConstants）
- `architecture.md` 新增 workflow/ 前端元件結構（16 檔完整清單）
- `code-review.md` agent 新增 str(e) 洩漏審查項目、架構規範引用更新
- `MANDATORY_CHECKLIST.md` v1.16.0、`DEVELOPMENT_GUIDELINES.md` 新增安全快速檢查步驟

**Security Fix #1: str(e) 殘留洩漏 (7 處使用者可見)**:
- `files/upload.py` 3 處：讀取/儲存/附件記錄失敗 → 通用訊息 + logger.error
- `files/storage.py` 2 處：write_error/network_error → 通用訊息 + logger.error
- `documents/crud.py` 1 處：附件刪除錯誤 → 通用訊息 + logger.error
- `taoyuan_dispatch/attachments.py` 1 處：上傳失敗 → 通用訊息 + logger

**Security Fix #2: SSE 認證統一 (XSS 風險降低)**:
- `coreFeatures.ts` streamSummary() — 移除 localStorage.getItem('access_token')
- `adminManagement.ts` streamRAGQuery() + streamAgentQuery() — 同上
- 統一使用 `credentials: 'include'` 自動傳送 httpOnly cookie

**Security Fix #3: python-jose CVE 遷移**:
- `requirements.txt` python-jose[cryptography]==3.3.0 → PyJWT>=2.8.0
- `auth_service.py` from jose import → import jwt + PyJWTError
- `oauth.py` + `mfa.py` from jose import jwt → import jwt
- 51 個認證測試全部通過

**Test: 新增單元測試 (59 tests)**:
- `test_doc_number_parser.py` — 21 tests (clean_doc_number + parse_doc_numbers)
- `test_dispatch_enrichment.py` — 38 tests (parse_roc_date + parse_sequence_no + parse_amount + safe_cell + parse_doc_line)

**異動檔案**: 17 個檔案 (7 backend endpoints + 3 auth + 2 frontend SSE + 2 test + 3 docs)

---

## [1.77.0] - 2026-03-04

### 作業進度多類型顯示 + 公文對照矩陣統一 + 統計卡片重構

**Feature: 作業進度按作業類別分組顯示**:
- 新增 `WorkTypeStageInfo` 型別（workType + stage + status + total + completed）
- `useProjectWorkData.ts` 改為派工單維度統計（非紀錄維度），避免多類別共用紀錄計數重複
- 工程總覽 `ProjectWorkOverviewTab` 統計區重構為三區塊：作業紀錄 / 關聯公文 / 作業進度
- 派工詳情 `StatsCards` 同步重構，顯示每個作業類別的進度與狀態

**Feature: 公文對照矩陣統一**:
- `CorrespondenceMatrix.tsx` 標題改用 `dispatch_no + work_type`（取代 `sub_case_name`）
- 工程總覽的公文對照改用 `buildCorrespondenceMatrix()` 三階段匹配（與派工詳情一致）
- `DispatchCorrespondenceGroup` 新增 `matrixRows` 屬性，傳遞至 `CorrespondenceBody`

**Refactor: 統計卡片分區佈局**:
- 作業紀錄：合併總數 + 完成/進行中/暫緩/逾期 Tag
- 關聯公文：來文/發文計數 + 未指派警示（含 Tooltip 說明）
- 作業進度：逐類別顯示 `作業類別 → 當前階段 → 狀態`

**異動檔案**: `useProjectWorkData.ts`, `ProjectWorkOverviewTab.tsx`, `CorrespondenceMatrix.tsx`,
`StatsCards.tsx`, `DispatchWorkflowTab.tsx`, `TaoyuanDispatchDetailPage.tsx`, `workflow/index.ts`

---

## [1.76.1] - 2026-03-03

### 全端點錯誤訊息洩漏修復 + 導覽認證強化

**Security Fix #1: str(e) 錯誤訊息洩漏 (30 檔 57+ 處)**:
- 全面掃描後端 API 端點，移除所有 `str(e)` 暴露至客戶端的模式
- 統一替換為通用錯誤訊息 + `logger.error(f"...: {e}", exc_info=True)` 伺服器端記錄
- 涵蓋：HTTPException detail、JSON response message、StreamingResponse 錯誤回傳
- 受影響模組：documents/, document_calendar/, taoyuan_dispatch/, ai/, files/, auth/, agencies/, deployment, system_health, navigation, debug 等

**Security Fix #2: 導覽端點認證缺口 (navigation.py)**:
- `POST /navigation/action` 原僅有 CSRF 驗證無認證 → 新增 `require_auth()`
- `POST /navigation/valid-paths` 原無任何保護 → 新增 `require_auth()`
- 兩端點同時移除 `"error": str(e)` 洩漏

**Bug Fix #1: debug.py 殘留引用**:
- `get_dynamic_api_mapping()` 中 `elif base_name == "cases"` → `"contract_cases"` 修正
- 對應 service 參考從 `case_service.py` 更新為 `project_service.py`

**Bug Fix #2: useMenuItems 選單群組鍵同步**:
- 前端 `useMenuItems.tsx` 的 `/cases` 群組鍵 → `project-management`，與後端導覽資料一致

**異動檔案**: 30 個後端 endpoint 檔案 + `useMenuItems.tsx`
143 insertions(+), 104 deletions(-)

---

## [1.76.0] - 2026-03-03

### ForeignKey ondelete 修復 + 安全審計 + 死碼清理

**Bug Fix: FK ondelete 約束 (公文刪除 500 錯誤)**:
- `TaoyuanDispatchOrder.agency_doc_id/company_doc_id` 缺少 `ondelete='SET NULL'`
- PostgreSQL 預設 RESTRICT → 刪除被引用公文時 IntegrityError 500
- ORM 模型 + Alembic migration `20260303a001` 同步修正

**Security Fix: CircuitBreaker 閾值**:
- 前端 `RequestThrottler` GLOBAL_MAX 從 50 調至 100（防正常操作誤觸熔斷）

**Dead Code Cleanup**:
- 移除 `cases.py`（全部回傳 mock 資料的永未實作存根）
- 移除 3 個 `*ListResponseLegacy` schema（零引用）
- 移除 `backup_service.py`（已被 `backup/` 套件取代）
- 更新 `.env.example`：新增 `MCP_SERVICE_TOKEN`、`PYTHONUTF8`

**異動檔案**: `models.py`, `alembic/versions/20260303a001_*.py`, `cases.py`(刪除),
`schemas/`(清理), `backup_service.py`(刪除), `.env.example`, `RequestThrottler.ts`

---

## [1.75.0] - 2026-03-02

### MCP Server + OpenClaw LINE 整合

**Phase 1: CK_Missive MCP Server (backend/mcp_server.py)**:
- 建立 MCP Server，包裝 7 個工具（6 個 Agent 工具 + ask_question 問答）
- 使用 FastMCP SDK，standalone 獨立程序連接同一 PostgreSQL
- 支援 Claude Desktop 直接配置使用
- 新增 `ck-missive://system/info` MCP Resource
- 新增 `mcp>=1.0.0` Python 依賴

**Phase 1b: Agent 同步問答 API (agent_query_sync.py)**:
- 新增 `POST /api/ai/agent/query` 非串流端點
- 收集完整 SSE 事件後回傳 JSON（供 OpenClaw、LINE Bot、MCP 呼叫）
- X-Service-Token header 認證（MCP_SERVICE_TOKEN 環境變數）
- 未設定 token 時為開放存取（開發模式）

**Phase 2: OpenClaw ck-missive-bridge 技能**:
- 新增 `~/.openclaw/workspace/skills/ck-missive-bridge/` 技能
- SKILL.md 定義公文查詢、派工單搜尋、期限提醒、週報等使用情境
- `references/api-guide.md` — CK_Missive API 完整參考
- `references/line-templates.md` — 5 種 LINE 訊息模板（期限提醒、逾期警報、搜尋結果、週報、系統狀態）
- 複用 OpenClaw 既有 LINE 頻道（小花貓Aroan @349lcsbb）

**Phase 3: OpenClaw cron 排程整合**:
- `ck-missive-deadline-check` — 平日 8:30 公文期限 → LINE 推送
- `ck-missive-overdue-alert` — 平日 12:00 派工單逾期 → LINE 推送
- `ck-missive-weekly-summary` — 週五 16:30 公文週報 → LINE 推送

**異動檔案**: `backend/mcp_server.py`(新增), `backend/app/api/endpoints/ai/agent_query_sync.py`(新增),
`backend/app/api/endpoints/ai/__init__.py`, `backend/requirements.txt`,
`~/.openclaw/workspace/skills/ck-missive-bridge/`(新增), `~/.openclaw/cron/jobs.json`

---

## [1.74.0] - 2026-03-02

### 備份系統修復 — Docker 容器汙染 + 清理安全閥 + SMB 長路徑

**Bug Fix #1: Docker 容器名稱汙染 (db_backup.ps1 + utils.py)**:
- PS 腳本 `--filter "name=postgres"` 子字串匹配 → 選到 `ck-tunnel-postgres-1`
- 修正為精確比對，白名單 `_dev`、`_1` 後綴變體
- Python `_get_running_container()` 移除 fallback 到第一筆結果，統一白名單邏輯

**Bug Fix #2: 備份清理安全閥 (scheduler.py + attachment_backup.py + db_backup.ps1)**:
- 清理邏輯新增「至少保留 1 個」安全下限，防止備份失敗期間全部清空
- PS: `Select-Object -Skip 1`；Python: `db_backups[1:]`
- 備份失敗時完全跳過清理（Python + PS 雙系統一致）
- `_safe_mtime()` 靜態方法防止 `stat()` OSError 中斷排序

**Bug Fix #3: SMB/NAS WinError 123 長中文路徑 (scheduler.py)**:
- `shutil.copy2()` 在 SMB 網路磁碟對 UTF-8 中文長檔名（>180 字元路徑）拋出 WinError 123
- 新增 `_safe_copy2()` 靜態方法：自動截斷檔名 + MD5 hash 前 6 碼防碰撞
- `sync_to_remote()` 改為逐檔 try/except，單檔失敗不中斷整體同步
- 回傳 `failed_files` / `failed_count` 供前端顯示

**Security Fix: Path Traversal 防護 (schemas/backup.py)**:
- `DeleteBackupRequest` / `RestoreBackupRequest` 新增 `field_validator`
- 禁止 `..`、`/`、`\` 路徑穿越字元

**異動檔案**: `scripts/backup/db_backup.ps1`, `backend/app/services/backup/scheduler.py`,
`backend/app/services/backup/attachment_backup.py`, `backend/app/services/backup/utils.py`,
`backend/app/schemas/backup.py`, `backend/config/remote_backup.json`

---

## [1.73.0] - 2026-02-26

### 系統優化 — SSE 強化 + 串流防護 + 文件規範

**前端 Agent 步驟排序 (B3)**:
- `AgentStepInfo` 新增 `step_index` 欄位，對應後端 SSE `step_index`
- `onThinking` / `onToolCall` / `onToolResult` 回調接收並存儲 `stepIndex`
- `AgentStepsDisplay` 按 `step_index` 排序步驟顯示

**工具圖示差異化 (B4)**:
- `find_similar`: `FileTextOutlined` → `CopyOutlined`（相似公文）
- `get_statistics`: `DatabaseOutlined` → `BarChartOutlined`（統計資訊）

**開發規範文件更新 (C1/C2)**:
- `DEVELOPMENT_STANDARDS.md` v1.4.0 — 新增 §8 Agent 服務開發規範
  - SSE 事件協議表（7 種事件 + 4 種錯誤碼）
  - 工具註冊規範（後端 TOOLS + 前端 ICONS/LABELS 同步）
  - 合成品質控制（thinking 過濾 + 閒聊路由 + 迭代上限）
  - 前端串流防護（timeout + buffer + abort）
- `DEVELOPMENT_GUIDELINES.md` — 新增 Agent 開發前置檢查清單
  - 新增工具 5 項 + SSE 事件 4 項 + 合成品質 4 項

---

## [1.72.0] - 2026-02-26

### Agent 智慧對話模式 + 合成品質強化

**Agent Orchestrator v1.8.0 — 閒聊模式 + 合成答案提取**:

**閒聊路由（反向偵測策略）**:
- 新增 `_is_chitchat()` — 反向偵測法：檢查 `_BUSINESS_KEYWORDS` (55+ 關鍵字)
  - 有業務關鍵字 → Agent 工具流程（完整 4 層意圖解析 + LLM 規劃）
  - 無業務關鍵字 + 短句 ≤40 字 → 閒聊模式（僅 1 次 LLM 呼叫）
  - 精確匹配 `_CHITCHAT_EXACT` (25 個問候詞) + 前綴匹配 `_CHITCHAT_PREFIXES`
- 新增 `_stream_chitchat()` — 非串流 LLM 呼叫 + 後處理
  - `_CHAT_SYSTEM_PROMPT` 明確定義能力邊界（僅公文相關功能）
  - 超範圍請求回覆「這個我幫不上忙」+ 引導可用功能
  - `_clean_chitchat_response()` 3 策略提取：引號回覆 → 回覆開頭行 → 智慧預設
  - `_get_smart_fallback()` 10 組問題類型預設回覆（Ollama 回退時使用）
- 效果：問候/閒聊 13 步驟 → 3 步驟 (thinking + token + done)，延遲 <1s (Groq)

**合成答案提取（v1.8.0 核心改進）**:
- `_strip_thinking_from_synthesis()` 完全重寫 — 從「逐行過濾（黑名單）」改為「答案提取（白名單）」
  - Phase 1: `<think>` 標記移除
  - Phase 2: 短回答快速通過（<300 字元 + 無引用 + 無推理特徵）
  - Phase 3: **答案邊界偵測** — 從末尾向前找「如下：」「可能的回應：」等標記
  - Phase 3.5: **結尾「：」+ 下行結構化引用** — 通用 intro + 列表模式
  - Phase 4: **最後區塊提取** — 多段 `[公文N]`/`[派工單N]` 區塊時取最末段
  - Phase 5: 逐行過濾（最後手段，無引用的純文字回答）
- 合成 system prompt 強化：禁止推理 + 輸出格式範例
- 修正 `AgentQueryRequest.question` min_length 2→1（支援「嗨」單字輸入）

**前端工具標籤**:
- `RAGChatPanel.tsx` 新增 `search_dispatch_orders` 圖示 (`FileTextOutlined`) + 標籤（搜尋派工單）

---

## [1.71.0] - 2026-02-26

### Agent 派工單整合 + 編碼全域防護

**Agent Orchestrator v1.5.0 — 派工單工具 + 空計劃修復**:
- 新增 `search_dispatch_orders` 工具：支援 dispatch_no / search / work_type 三種搜尋策略
- 自動查詢關聯公文：透過 `taoyuan_dispatch_document_link` 帶出派工單關聯的公文
- 空計劃 hints 強制注入：qwen3:4b 回傳無效 JSON 時，用 SearchIntentParser hints 建構 tool_calls
  - 正則提取派工單號 `r"派工單[號]?\s*(\d{2,4})"` → 精確填入 dispatch_no 參數
  - 無 keywords 時使用原始問題文字作為 search 條件
- 自動修正策略 2.5：search_documents 0 結果 → 自動嘗試 search_dispatch_orders
- Few-shot 規劃範例新增 2 個派工單場景
- Planning prompt 規則強化：涉及「派工單」時必須使用 search_dispatch_orders
- `_build_synthesis_context` 派工單區塊含關聯公文資訊
- `_summarize_tool_result` 摘要含關聯公文數量

**Windows 編碼全域防護**:
- `.env` 新增 `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`
- `ecosystem.config.js` PM2 env 新增 `PYTHONUTF8: '1'`
- `startup.py` 新增 `PYTHONUTF8=1` 環境變數
- `deployment.py` 2 處 subprocess.run 加 `encoding="utf-8", errors="replace"`
- 全面審計：18+ open() + 20+ json.dumps 均已使用 UTF-8 ✓

---

## [1.70.0] - 2026-02-26

### 智能體品質強化 — 自我修正 + Hybrid Reranking + AI 機關匹配

**Phase C3: Agent 自我修正 (agent_orchestrator.py v1.2.0)**:
- `_auto_correct()` 規則式自我修正引擎 (4 策略, 不需 LLM):
  - 策略 1: 文件搜尋空結果 → 放寬條件 (移除篩選器) + 觸發實體搜尋
  - 策略 2: 實體搜尋空結果 → 改用公文全文搜尋
  - 策略 3: 所有工具均無結果 → 取得系統統計概覽
  - 策略 4: find_similar 失敗 → 降級為關鍵字文件搜尋
- `_evaluate_and_replan()` 整合: 先跑規則修正，再走 LLM 評估

**Hybrid Reranking 整合至 RAG 服務 (rag_query_service.py v2.2.0)**:
- `_retrieve_documents()` 增加 `query_terms` 參數
- 多取 2x 候選文件 → 向量+關鍵字混合重排 → 截取 top_k
- `_extract_query_terms()` 從問題提取有效查詢詞 (過濾停用詞)
- `query()` 和 `stream_query()` 自動傳遞 query_terms

**安全與品質修復 (Code Review 後)**:
- C1: 錯誤訊息不再洩漏內部異常詳情，改為通用使用者提示
- C2: Agent 端點整合服務層速率限制器 (BaseAIService.RateLimiter)
- I1: 自我修正防重複觸發：同一工具 0 結果超過 2 次不再重試
- I3: find_similar 來源補齊 category/receiver 欄位
- I4: AgencyMatchInput unmount 時清理 debounce 計時器
- I6: AgentQueryRequest 搬至 schemas/ai.py (SSOT)
- S1: done 事件 iterations 改為真實迴圈迭代次數

**Phase 4: AgencyMatchInput 智慧機關匹配元件 (v1.0.0)**:
- 新增 `AgencyMatchInput.tsx` — Ant Design Select + AI 匹配
  - 基本行為同 Select showSearch (向下相容)
  - 搜尋文字無精確匹配時，自動 debounce (600ms) 呼叫 `aiApi.matchAgency()`
  - AI 建議插入下拉頂部，帶紫色 AI 標籤 + 匹配信心度
  - 匹配結果提示欄: 高信心 (>=80%) 綠色勾、中信心黃色問號
- 整合至 `DocumentCreateInfoTab`:
  - 收文模式: 發文單位 Select → AgencyMatchInput
  - 發文模式: 受文單位 Select → AgencyMatchInput
- `useDocumentCreateForm`: 新增 `agencyCandidates` 計算欄位
- 收/發文建立頁面: 傳遞 `agencyCandidates` prop

---

## [1.69.0] - 2026-02-26

### Agentic 文件檢索引擎 — 借鑑 OpenClaw 智能體模式

**Phase A: Tool Registry + Agent Loop 核心引擎**:
- 新增 `agent_orchestrator.py` (AgentOrchestrator) — 多步工具呼叫引擎
  - 5 個工具: search_documents, search_entities, get_entity_detail, find_similar, get_statistics
  - LLM 規劃 → 工具執行 → 評估 → 最多 3 輪迭代 → 合成回答
  - 複用現有服務 (DocumentQueryBuilder, GraphQueryService, EmbeddingManager)
  - JSON 容錯解析 (直接/code-block/braces 三策略)
  - 單工具 15 秒超時保護，整體韌性降級至基本 RAG
- 新增 `agent_query.py` — `POST /ai/agent/query/stream` SSE 端點
- 路由註冊: AI `__init__.py` v1.6.0

**Phase B: 前端 Agentic Chat UI**:
- `RAGChatPanel.tsx` v3.0.0: 雙模式 (RAG / Agent)
  - 新增 `agentMode` prop (預設 true)
  - 推理步驟即時視覺化 (Steps 元件, thinking/tool_call/tool_result)
  - 工具呼叫圖示 + 標籤 (搜尋公文/搜尋實體/實體詳情/相似公文/統計)
  - Metadata 顯示: 延遲、模型、引用數、工具數
  - 串流中自動展開推理過程，完成後可摺疊
- `adminManagement.ts`: 新增 `streamAgentQuery()` + `AgentStreamCallbacks` 介面
- `endpoints.ts`: 新增 `AGENT_QUERY_STREAM` 端點常數
- `aiApi` index: 註冊 `streamAgentQuery`

**SSE 事件協議 (向下相容)**:
- 新增事件: `thinking`, `tool_call`, `tool_result`
- 保留事件: `sources`, `token`, `done`, `error`
- `done` 擴展: 新增 `tools_used[]`, `iterations` 欄位

---

## [1.68.0] - 2026-02-26

### 智能化語言查詢服務 — AI 助理統一整合

**Phase 1: 浮動面板搜尋/問答模式切換**:
- `AIAssistantButton.tsx` v3.0.0: 加入 `Segmented` 切換（搜尋 / 問答）
- RAG 問答從管理員專屬提升為全站使用者可用
- `RAGChatPanel.tsx` v2.1.0: 新增 `embedded` prop（省略 Card 外框，flex 填充父容器）
- Lazy load `RAGChatPanel`（僅切換至問答模式時載入，減少初始 bundle）
- 浮動按鈕 Tooltip 更新為「AI 智慧助理」

**Phase 2: 公文詳情頁 AI 分析 Tab**:
- 新增 `DocumentAITab` 元件（`pages/document/tabs/DocumentAITab.tsx`）
- 整合三項零掛載 AI 功能：
  - `AISummaryPanel` — AI 摘要生成（SSE 串流）
  - 語意相似公文推薦（`getSemanticSimilar`，顯示 8 筆，可點擊跳轉）
  - 單篇實體提取（`extractEntities`，顯示實體/關係數量）
- 註冊為 DocumentDetailPage 第 5 個 Tab「AI 分析」

**Phase 3: 公文建立表單 AI 分類建議**:
- 收文/發文建立表單在主旨欄下方嵌入 `AIClassifyPanel`
- 主旨輸入 >= 5 字後自動顯示分類建議面板
- 收文: `onSelect` 自動填入 `doc_type` + `category`
- 發文: `onSelect` 自動填入 `doc_type`（category 固定為發文）
- 使用 `Form.useWatch('subject', form)` 監聽主旨即時變化

**前端 AI 服務覆蓋率提升**: 61% → 87%（46 個 API 中 40 個有 UI）

---

## [1.67.0] - 2026-02-26

### 圖譜服務前端整合 — 5 個後端 API 納入 UI

**前端整合審計結果**: 9 個圖譜 API 中 5 個缺少前端 UI 使用，本次全數補齊。

**已整合服務**:
1. `getTopEntities` → KnowledgeGraphPage 左側面板「高頻實體排行」（Top 10，含類型色點 + 提及次數）
2. `findShortestPath` → KnowledgeGraphPage 左側面板「最短路徑」搜尋（兩個 Select + 路徑視覺化）
3. `mergeGraphEntities` → KnowledgeGraphPage 管理動作「合併實體」按鈕 + Modal
4. `getEntityTimeline` → EntityDetailSidebar v1.1.0 時間軸（Promise.all 平行載入，顯示 15 筆）
5. `findShortestPath` API 層: types/ai.ts + api/ai/types.ts + api/ai/knowledgeGraph.ts + endpoints.ts

**保留不整合**: `getEntityNeighbors` — 圖譜視覺化已透過 `getRelationGraph` 顯示鄰居，獨立 UI 冗餘。

**技術細節**:
- 實體搜尋共用 300ms debounced `handleEntitySearch`（Select `onSearch`）
- 合併 Modal 含方向說明（保留 vs 被合併），合併後自動重載統計
- Top Entities 與覆蓋率統計合併至 `Promise.allSettled` 平行載入
- TypeScript 0 錯誤

---

## [1.66.0] - 2026-02-26

### Phase C 閾值集中化 + 圖譜查詢 Redis 快取

**C1: 殘餘硬編碼閾值遷移**:
- `ai_config.py` v2.1.0: 新增 6 個可配置欄位
  - `agency_match_threshold` (0.7) — 機關名稱匹配最低信心度
  - `hybrid_semantic_weight` (0.4) — 混合搜尋語意權重
  - `graph_cache_ttl_detail/neighbors/search/stats` — 圖譜快取 TTL
- `document_ai_service.py`: 3 處硬編碼遷移
  - `confidence >= 0.7` → `get_ai_config().agency_match_threshold`
  - `weight=0.4` → `get_ai_config().hybrid_semantic_weight`
  - `timeout=20.0` → `get_ai_config().search_query_timeout`
- `relation_graph_service.py`: 2 處 `confidence >= 0.6` → `get_ai_config().ner_min_confidence`
- 所有閾值均支援環境變數覆寫

**C2: 圖譜查詢 Redis 快取 (graph_query_service.py v1.1.0)**:
- 共用 `RedisCache(prefix="graph:query")` 實例（模組級單例）
- 4 個高頻查詢方法加入快取層:
  - `get_entity_detail()` — TTL 300s (可配置)
  - `get_neighbors()` — TTL 300s (含 max_hops/limit 作為快取 key)
  - `search_entities()` — TTL 120s (含 query/entity_type/limit 作為快取 key)
  - `get_graph_stats()` — TTL 1800s (全域統計)
- Redis 不可用時靜默降級（RedisCache 內建 fallback）
- 預估: 重複查詢場景減少 ~90% DB 壓力

**架構複查修正**:
- `embedding_manager.py`: `_max_cache_size`, `_cache_ttl` 改從 AIConfig 讀取（原硬編碼 500/1800）
- `graph_query_service.py`: 清除未使用 imports (`literal_column`, `GraphIngestionEvent`, `List`, `and_`)
- `document_ai.py` (端點): 配置資訊回報中的 `0.7` → `config.agency_match_threshold`
- `graph_query.py` (端點): 7 處函數內 lazy import → 頂層 import（消除重複）
- `types/ai.ts`: `RAGStreamRequest` 從 `api/ai/adminManagement.ts` 遷移至 SSOT（含 re-export 鏈更新）
- AIConfig 集中化覆蓋率: 11/17 AI 服務模組使用 `get_ai_config()`（其餘 6 個無閾值需求）
- SSOT 驗證: API 層無業務型別定義違規（查詢參數型別 `*ListParams` 屬 API 關注點，合理留在 API 層）
- 驗證通過: 15/15 服務 + 10/10 端點 py_compile OK, TypeScript 0 錯誤

---

## [1.65.0] - 2026-02-26

### Phase B 效能優化 — NER 批次寫入 + 入圖管線 N+1 消除 + 元件拆分

**NER 批次寫入優化 (canonical_entity_service.py v1.1.0)**:
- 新增 `resolve_entities_batch()` 方法：批次精確匹配 + 延遲 flush + 批次建立
- Stage 1: 1 次 IN 查詢取代 N 次 per-entity 精確匹配
- Stage 2: 模糊匹配後批次去重別名（1 次查詢 vs N 次）
- Stage 3: 新實體批次 `db.add()` → 2 次 flush（建實體 + 建別名）取代 2N 次
- 預估效能提升: 10 實體文件 ~20 次 DB round-trip → ~5 次（50-75% 減少）

**入圖管線 N+1 消除 (graph_ingestion_pipeline.py v1.1.0)**:
- 使用 `resolve_entities_batch()` 取代 per-entity `resolve_entity()` 迴圈
- 關係預載: 1 次 IN 查詢取代 N 次 per-relation EXISTS 查詢
- 公文預載: 1 次 `db.get()` 取代 per-new-relation 重複查詢
- 同批次關係去重: `rel_lookup` 字典避免 INSERT 重複
- 預估批次入圖效能提升: 50 文件 batch ~50-100x 加速

**元件拆分 (AIAssistantManagementPage.tsx)**:
- 1522 行 → ~120 行（主頁面）+ 6 個獨立 Tab 元件
- 新增 `components/ai/management/` 目錄：
  - `OverviewTab.tsx` — 搜尋總覽統計
  - `HistoryTab.tsx` — 搜尋歷史與篩選
  - `EmbeddingTab.tsx` — Embedding 管理
  - `KnowledgeGraphTab.tsx` — 知識圖譜與實體提取
  - `ServiceMonitorTab.tsx` — AI 服務健康監控
  - `OllamaManagementTab.tsx` — Ollama 模型管理
  - `index.ts` — Barrel export

**Deprecated 清理**:
- 移除 `backend/app/models/calendar_event.py`（已 deprecated since v2.0.0, 零引用）

---

## [1.64.0] - 2026-02-26

### AI 閾值集中管理 + RAG Prompt DB 可配置 + 搜尋信心度色彩分級

**AIConfig v2.0.0 (ai_config.py)**:
- 新增 24 個可配置閾值，涵蓋 RAG / NER / Embedding / 知識圖譜 / 語意搜尋
- 所有閾值支援環境變數覆寫（`RAG_TOP_K`, `NER_MIN_CONFIDENCE`, `KG_FUZZY_THRESHOLD` 等）
- 移除 4 個服務中的硬編碼常數，統一讀取 AIConfig singleton

**RAG Prompt 可配置化 (rag_query_service.py v2.1.0)**:
- system prompt 改由 `AIPromptManager.get_system_prompt("rag_system")` 管理
- 優先順序: DB active 版本 > YAML (prompts.yaml) > 內建 fallback
- 新增 `rag_system` prompt 至 prompts.yaml v1.3.0（含 7 條回答規則）
- 所有生成參數（temperature, max_tokens, top_k, context_chars）讀取自 AIConfig
- 新增 embedding 向量維度執行時驗證（768D check）

**閾值統一遷移**:
- `entity_extraction_service.py`: MIN_CONFIDENCE → `AIConfig.ner_min_confidence`
- `canonical_entity_service.py`: FUZZY_SIMILARITY_THRESHOLD → `AIConfig.kg_fuzzy_threshold`
- `search_intent_parser.py`: VECTOR_SIMILARITY_THRESHOLD → `AIConfig.search_vector_threshold`

**搜尋信心度 UI 色彩分級 (NaturalSearchPanel.tsx)**:
- AI 解析信心度標籤改為三級色彩：Green (≥80%) / Orange (60-80%) / Red (<60%)

---

## [1.63.0] - 2026-02-25~26

### RAG 問答服務 v2.0 — SSE 串流 + 多輪對話 + 前端 Chat UI

**RAG Query Service (rag_query_service.py v2.0.0)**:
- 新增 `RAGQueryService`：基於現有 pgvector (728 篇 768D) + Ollama LLM 的輕量 RAG 管線
- 流程: 查詢 embedding → cosine_distance 向量檢索 → 上下文建構 → Ollama LLM 回答生成
- `query()` 同步問答 + `stream_query()` SSE 串流回答
- SSE 事件協議: `sources` → `token`* → `done`（前端先收來源再逐字回答）
- 多輪對話: history 陣列傳遞，`_build_messages()` 限制最近 4 輪 (MAX_HISTORY_TURNS)
- 來源引用追蹤（[公文N] 格式），上下文截斷 6000 字

**API 端點 (rag_query.py v2.0.0)**:
- `POST /api/ai/rag/query` — RAG 同步問答端點（需認證）
- `POST /api/ai/rag/query/stream` — RAG SSE 串流問答（含多輪對話歷史）
- StreamingResponse: `text/event-stream` + no-cache + keep-alive

**Schema (ai.py)**:
- `RAGQueryRequest`, `RAGSourceItem`, `RAGQueryResponse`

**前端 RAG Chat UI (RAGChatPanel.tsx v2.0.0)**:
- SSE 逐字串流顯示: `aiApi.streamRAGQuery()` + ReadableStream 解析
- 多輪對話記憶: 自動建構 history 陣列傳遞後端
- AbortController: 元件卸載/清除對話時自動取消串流
- 來源引用展開面板（Collapse）：doc_number / subject / sender / similarity
- 串流指示器 (LoadingOutlined)、快捷問題按鈕、回答元資料
- 整合至 AI 助理管理頁面首個 Tab（defaultActiveKey="rag-chat"）

**前端 API 整合**:
- `api/endpoints.ts`: `RAG_QUERY` + `RAG_QUERY_STREAM` 端點
- `api/ai/adminManagement.ts`: `ragQuery()` + `streamRAGQuery()` (SSE fetch + callback)
- `api/ai/index.ts`: aiApi 物件新增 ragQuery + streamRAGQuery
- `api/ai/types.ts` + `api/aiApi.ts`: re-export RAG 型別

**LlamaIndex 基礎建設**:
- 安裝 `llama-index-core`, `llama-index-vector-stores-postgres`, `llama-index-embeddings-ollama`, `llama-index-llms-ollama`
- pydantic 2.9.2 → 2.12.5（LlamaIndex 依賴升級，相容性已驗證）

**AI API 端點現況 (46 個)**:
- 公文 AI: 8 個（摘要/分類/關鍵字/搜尋/圖譜/匹配/語意相似）
- 知識圖譜: 8 個（搜尋/鄰居/最短路徑/詳情/時間軸/排名/統計/入圖）
- RAG 問答: 2 個（query + stream）
- Embedding: 2 個（stats/batch）
- NER: 3 個（extract/batch/stats）
- 搜尋歷史: 5 個
- 同義詞: 5 個
- Prompt: 4 個
- Ollama: 3 個
- 統計: 2 個
- 管理: 2 個（health/config）
- 圖譜管理: 2 個（merge-entities/ingest）

---

## [1.62.0] - 2026-02-25

### NER Ollama-First 修復 + 向量維度修正 + HNSW 索引 + 圖譜多跳查詢

**NER 實體提取修復 (entity_extraction_service.py)**:
- 重寫 `EXTRACTION_SYSTEM_PROMPT`：改用英文指令 + 嚴格 JSON-only 要求，提高 Ollama llama3.1:8b JSON 輸出率
- User prompt 改為英文（`Extract entities and relations...`）避免 Ollama 語境切換
- 新增 `_extract_json_from_text()` 四策略 JSON 解析器：
  1. 直接 json.loads() — 純 JSON
  2. Markdown code block 提取 — ```json 包裹
  3. 最大 JSON 物件搜尋 — bracket 計數找完整 `{...}`
  4. Regex 散落物件收集 — 從敘述文字收集個別 entity/relation JSON
- 拆分 `_validate_entities()` 和 `_validate_relations()` 獨立驗證函數
- **成效**: NER 成功率從 0% 提升至 100%，已批次處理 300+ 筆公文

**Ollama 狀態修復 (前端)**:
- `adminManagement.ts`: 移除 `getOllamaStatus()` 等 3 個函數的 try/catch null 回傳，改為錯誤傳播
- `AIAssistantManagementPage.tsx`: 新增 `isError` 狀態處理 + 重試按鈕

**導覽系統修復 (init_navigation_data.py)**:
- 修復 sort_order 衝突（system-management 子項、backup-management）
- AI 助理管理移至 AI 智慧功能分組
- 新增「統一表單示例」導覽項目
- 導覽覆蓋率：26/26 頁面（100%）

**向量維度修正 + HNSW 索引升級**:
- ORM 模型 `Vector(384)` → `Vector(768)` 匹配 nomic-embed-text 實際輸出（document.py, system.py, knowledge_graph.py）
- Alembic migration: `canonical_entities.embedding` 從 vector(384) → vector(768)
- 全部 3 張向量表索引從 IVFFlat 升級為 HNSW（m=16, ef_construction=64）
- Embedding 覆蓋率 97.66% → **100%**（修正維度後 17 筆卡住的公文成功入庫）
- `embedding_manager.py` docstring 修正 384 → 768

**知識圖譜多跳查詢強化 (graph_query_service.py)**:
- `get_neighbors()` 重寫為 Recursive CTE（單次 SQL 取代 N+1 Python BFS）
- 新增 `find_shortest_path()` — 兩實體間最短路徑查詢（Recursive CTE BFS）
- 新增 API 端點 `POST /ai/graph/entity/shortest-path`
- 新增 Schema: `KGShortestPathRequest`, `KGShortestPathResponse`, `KGPathNode`

**系統文件全面更新**:
- `skills/ai-development.md` v2.0.0 → **v3.0.0**：補充 NER/知識圖譜/CanonicalEntity/Ollama-First/4策略解析
- `rules/architecture.md`：ORM 模型新增 AI 模組（8 個新模型），Service 層 AI 目錄從 4 → 17 個模組
- `rules/skills-inventory.md`：ai-development 觸發關鍵字擴充 + 版本更新
- `ai_connector.py` docstring：修正 embedding 維度 384 → 768

---

## [1.61.0] - 2026-02-24

### 備份系統核心強化 + 知識圖譜修復 + CVE 漏洞修補

**備份系統 — 500 錯誤修復**:
- 修復 5 個 backup 端點 slowapi 參數命名衝突（`http_request` → `request`，body `request` → `body`）
- 修復 `uploads_dir` 雙重 backend 路徑（`project_root / "backend" / "uploads"` → `project_root / "uploads"`）
- 修復 `.env` 讀取路徑（`project_root / ".env"` → `project_root.parent / ".env"`）
- 修復 BackupManagementPage `useForm` 警告（`setFieldsValue` 從 queryFn 移至 useEffect）

**備份系統 — 核心強化 (v2.0.0)**:
- 備份失敗通知機制：首次失敗 warning、連續 ≥2 次 critical，透過 `SystemNotification` 廣播
- 自動異地同步排程：根據 `sync_interval_hours` 自動觸發 `sync_to_remote()`
- 健康檢查整合：新增 `GET /health/backup` 端點 + `build_summary()` 包含備份狀態
- `_consecutive_failures` 計數器從日誌載入，服務重啟不歸零

**知識圖譜修復**:
- NER `project` 映射為 `ner_project` 避免與業務 project 類型衝突
- `EntityDetailSidebar` 查詢時反向映射 `ner_project` → `project`
- `visibleTypes` 工具列勾選與 `GraphNodeSettings` 面板設定同步（`configVersion` 觸發）
- Drawer `mask={false}` 防止圖譜互動阻擋
- `graphNodeConfig.ts` 新增 `ner_project` 配置

**CVE 漏洞修補**:
- lodash 升級至 4.17.23 (CVE-2021-23337, High)
- requests 升級至 >=2.32.4 (CVE-2023-32681)
- `npm audit fix` 減少漏洞 35 → 24

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| Backup 500 錯誤 | 5 端點 | 0 |
| 備份失敗通知 | 無 | warning/critical |
| 異地自動同步 | 手動 | 自動排程 |
| 健康檢查含備份 | 否 | `/health/backup` |
| npm 漏洞 | 35 | 24 |
| CVE (High) | 2 | 0 |

---

## [1.60.0] - 2026-02-24

### SSOT 全面強化 + 架構優化 + 安全修復

基於系統全面架構審查，分 4 階段執行 9 項優化任務。

**P0 — 安全緊急修復**:
- SQL Injection 修復：`document_statistics_service.py` + `document_numbers.py` 的 `text(f"...")` 替換為 ORM `func.cast(func.substring(...), Integer)` 查詢
- asyncio.gather 注釋修正：`documents/list.py` 的誤導性 "asyncio.gather 並行" 註解更正
- 硬編碼 API 路徑修復：`useDocumentCreateForm.ts` 的 `/projects/list`, `/users/list` 遷移至 `API_ENDPOINTS` 常數

**P1 — 型別 SSOT 遷移**:
- AI 型別集中化：新增 `types/ai.ts` (SSOT, 757 行)，`api/ai/types.ts` 改為 re-export 相容層
- 9 個元件檔案 import 路徑更新至 `types/ai`
- 7 個 API 檔案型別清理：15 個本地 interface 定義遷移至 `types/api.ts`
- `types/document.ts` 合併 `doc_word`, `doc_class`, update-only 欄位
- `ProjectVendor`, `ProjectStaff` 基礎型別合併 API 擴展欄位

**P1 — Service 層遷移**:
- `search_history.py` 直接 `db.execute(update(...))` → `AISearchHistoryRepository.submit_feedback()`
- `synonyms.py` 直接 ORM mutation → `AISynonymRepository.update_synonym()`
- `entity_extraction.py` 計數查詢 → `get_pending_extraction_count()` service 函數
- `embedding_pipeline.py` 統計查詢 → `EmbeddingManager.get_coverage_stats()` class method

**P2 — 端點重構**:
- `agencies.py` fix_parsed_names 業務邏輯遷移至 `AgencyService.fix_parsed_names()`
- 移除 5 個 deprecated 重複路由 (agencies 2 + document_numbers 3)
- `document_numbers.py` 630→557 行, `agencies.py` 507→375 行

**P3 — 架構規範化 (二次優化)**:
- `health.py`, `relation_graph.py` 的本地 `_get_service()` 統一改用 `get_service()` 工廠模式
- `SystemHealthService._startup_time` 從模組級全域變數改為 class variable（保留向後相容函數）
- `AISynonymRepository.update_synonym()` 的 `commit()` 改為 `flush()`，commit 交由端點統一管理
- Docker Compose Ollama GPU 配置文件化（無 GPU 環境 fallback 說明）

**新增前端元件**:
- `GlobalApiErrorNotifier` — 全域 API 錯誤自動通知 (403/5xx/網路)，`ApiErrorBus` 事件匯流排
- `GraphNodeSettings` — 知識圖譜節點設定面板 (顏色/標籤/可見度，localStorage 持久化)
- `useAIPrompts` / `useAISynonyms` — AI 管理 React Query hooks

**文件同步更新**:
- `CLAUDE.md` 版本號 1.59.0 → 1.60.0
- `architecture.md` 補充 Service 層目錄結構、前端型別 SSOT 結構、全域錯誤處理架構
- `DEVELOPMENT_STANDARDS.md` §2.4 補充 `SystemHealthService` 和 `RelationGraphService`
- `DEVELOPMENT_GUIDELINES.md` 核心服務表格補充 2 項
- `TYPE_CONSISTENCY.md` §2.3 補充 `ProjectVendor` / `ProjectStaff` 擴展欄位
- `skills-inventory.md` 更新 AI 開發 skill 版本、新增 v1.60.0 元件清單

**BREAKING CHANGES**:
- `health.py` 部分端點權限從 `require_auth` 提升為 `require_admin`（detailed, metrics, pool, tasks, audit, summary）
- 移除 5 個 deprecated 路由 (agencies 2 + document_numbers 3)

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| SQL Injection 漏洞 | 2 | 0 |
| API 層本地型別定義 | 15+ | 0 (全部 re-export) |
| AI 端點直接 DB 操作 | 8 | 0 (Phase 1+2) |
| Deprecated 重複路由 | 5 | 0 |
| agencies.py 行數 | 507 | 375 |
| 本地 `_get_service()` | 2 | 0 (統一 `get_service()`) |

---

## [1.59.0] - 2026-02-21

### 全面優化 v1.59.0 — 安全強化 + 架構精煉 + 測試擴充

基於四維度審計結果（測試 4.5→7.0、前端 7.5→8.5、後端 8.7→9.2、文件 8.5→9.0），
系統性修復 15 項識別問題，分 3 個 Sprint 執行完成。

**Sprint 1: 安全 + 品質基線**:
- SQL 注入防禦加深：`audit.py` 白名單驗證 + bind parameters + rate limiting
- Rate Limiting 擴展：6 → **70** 個端點覆蓋 `@limiter.limit`（認證/寫入/AI/管理）
- `useDocumentDetail.ts` 18 處 `any` 型別修復（全部替換為具體型別）
- Form 型別 SSOT：8 個頁面本地定義集中至 `types/forms.ts`

**Sprint 2: 架構重構 + 測試擴充**:
- `DispatchWorkflowTab` 拆分：1,024 行 → **618 行** + 4 子元件
- Repository 層新增：`StaffCertificationRepository` + `ContactRepository` + agencies 遷移
- 後端測試新增：`test_auth_service.py`, `test_backup_service.py`, `test_notification_service.py`
- 前端 Hook 測試新增 7+ 檔案：useProjects, useAgencies, useCalendarEvents, useAuthGuard, useIdleTimeout 等
- Specification 文件版本標頭：13 個 docs 文件添加 `> Version: x.x.x | Last Updated`

**Sprint 3: 精煉 + 清理**:
- NaturalSearchPanel WCAG 2.1 AA 修復：role/tabIndex/aria-expanded/aria-label/onKeyDown
- Deprecated 服務清理：agency(5) + project(3) + vendor(8) 方法移除 + navigation_service 刪除
- `backup_service.py` 拆分：1,055 行 → 4 模組 (utils/db_backup/attachment_backup/scheduler)
- 部署文件整合：3 個分散文件 → 統一 `DEPLOYMENT_GUIDE.md` v2.0.0
- 覆蓋率門檻提升：60% → **70%**（pyproject.toml + CI）

**數據摘要**:
| 指標 | 修改前 | 修改後 |
|------|--------|--------|
| Rate Limiting 端點 | 6 | 70 |
| Deprecated 方法 | 16 | 0 |
| DispatchWorkflowTab | 1,024 行 | 618 行 |
| backup_service.py | 1,055 行 | 4 模組 (~960 行) |
| 覆蓋率門檻 | 60% | 70% |
| Hook 測試檔案 | 3 | 12 |
| 後端服務測試 | 2 | 7 |
| Repository | 5 | 7 |

---

## [1.58.0] - 2026-02-21

### 全面優化 — CI 覆蓋率門檻 + Hooks 自動化 + Skills 擴充

**文件同步與清理 (Step 1)**:
- CHANGELOG.md 回填 v1.34→v1.57 (24 版本, +269 行)
- `pyproject.toml` 覆蓋率門檻 `fail_under=60`
- Architecture 文件更新服務遷移/Repository 狀態
- 10 個陳舊文件歸檔至 `docs/archive/`

**CI 覆蓋率門檻強制化 (Step 2)**:
- `test-coverage` job 移除 `continue-on-error`
- pytest 加入 `--cov-fail-under=60`

**Hooks 自動化擴展 (Step 3)**:
- `api-serialization-check.ps1` 升級 v2.0.0 (stdin JSON 協議)
- `performance-check.ps1` 升級 v2.0.0 (stdin JSON 協議)
- 兩者加入 PostToolUse 自動觸發
- 新增 `migration-check` prompt hook (ORM 修改提醒遷移)

**新增 Skills (Step 4)**:
- `accessibility.md` v1.0.0 — WCAG 2.1 AA + ARIA + axe-core
- `alembic-migrations.md` v1.0.0 — 遷移流程 + pgvector 檢查
- `caching-patterns.md` v1.0.0 — Redis fallback + React Query

**配置更新 (Step 5)**:
- CLAUDE.md 版本更新至 v1.58.0
- `hooks-guide.md` 新增 3 個 PostToolUse hooks
- `skills-inventory.md` 新增 3 個 Skills

**檔案統計**: 23 個檔案, +1,087 / -256 行

---

## [1.57.0] - 2026-02-21

### CLAUDE.md 模組化拆分 + Hooks 升級至官方格式

- CLAUDE.md 從 2,437 行縮減至 89 行 (96% 精簡)
- 新增 7 個 `.claude/rules/` 自動載入規範檔案
- 升級 3 個現有 hook scripts 至 stdin JSON 協議 (v2.0.0)
- 新增 SessionStart / PermissionRequest / Stop 三種 hooks
- settings.json 遷移至官方三層巢狀格式
- 新增 `hooks-development.md` skill
- 修復 PowerShell 5.1 UTF-8 BOM 編碼問題 (8 個 .ps1 檔案)
- 修復 python-lint.ps1 Push-Location 路徑前綴問題

---

## [1.56.0] - 2026-02-19

### SSOT 全面強化 + Schema-ORM 對齊 + 型別集中化

- 後端 26 個本地 BaseModel 遷移至 `schemas/` (ai, deployment, calendar, links)
- Schema-ORM 對齊：ContractProject 14 欄位 + UserResponse.email_verified
- 前端 8 個頁面本地型別集中至 `types/admin-system.ts` + `types/api.ts`
- SSOT 合規率：後端 95%→100%, 前端 85%→95%, Schema-ORM 87%→98%
- 57 個檔案修改 (+1,032 / -1,833 行，淨減少 801 行)

---

## [1.55.0] - 2026-02-19

### 全面健康檢查 + 修復執行 + Phase 6 規劃

- system_health.py SQL 注入修復 (6 個 raw SQL → ORM 白名單)
- DocumentDetailPage 拆分：897 → 204 行 (-77%)
- NaturalSearchPanel Hook 提取：774 → 274 行 (-64%)
- 24 個元件新增 ARIA 可訪問性語意屬性
- Phase 6 規劃 (6A 可訪問性 / 6B 服務拆分 / 6C 測試擴充 / 6D Repository)
- 系統健康度：9.5 → 9.6/10

---

## [1.54.0] - 2026-02-17

### 鏈式時間軸 + 架構審查修復 + 測試擴充

- ORM 模型拆分 `extended/models.py` → 7 個模組
- ChainTimeline 鏈式時間軸元件 (chain + correspondence + table 三種視圖)
- InlineRecordCreator Tab 內 Inline 新增表單
- 架構審查修復 10 項 (CRITICAL 權限檢查、分頁上限、複合索引)
- 49 個新測試 (chainUtils 31 + work_record_service 18)
- 新增 `workflow-management.md` skill

---

## [1.53.0] - 2026-02-09

### Docker+PM2 混合開發環境優化與系統韌性強化

- 新增 `docker-compose.infra.yml` (僅 PostgreSQL + Redis)
- 重寫 `dev-start.ps1` v2.0.0 支援 -FullDocker/-Stop/-Status/-Restart
- 新增 `dev-stop.ps1` 支援 -KeepInfra/-All
- 資料庫連線韌性：statement_timeout 30s + pool event listeners
- Feature Flags 架構 (PGVECTOR_ENABLED, MFA_ENABLED)

---

## [1.52.0] - 2026-02-09

### Phase 4 審查修復：SSOT 一致性 + 安全強化 + 自動回填

- 24 個 AI 端點路徑集中至 `endpoints.ts` 的 `AI_ENDPOINTS`
- MFA 型別集中至 `types/api.ts`
- Session 端點限流 (30/10/5 per minute)
- Embedding 自動回填背景任務 (main.py lifespan)

---

## [1.51.0] - 2026-02-08

### Phase 4 全面完成：RWD + AI 深度優化 + 帳號管控

- Phase 4A RWD：Sidebar Drawer + ResponsiveTable/FormRow/Container
- Phase 4B AI：SSE 串流 + pgvector 語意搜尋 + Prompt 版控 + 同義詞管理
- Phase 4C 帳號：密碼策略 + 帳號鎖定 + MFA + Email 驗證 + Session 管理
- 32 個新增檔案、105 個修改檔案 (+10,312 / -1,752 行)
- 系統健康度：9.9 → 10.0/10

---

## [1.50.0] - 2026-02-08

### Phase 4 規劃文件

- 系統文件全面更新 (已被 v1.51.0 實作取代)

---

## [1.49.0] - 2026-02-07

### 全面架構優化：安全遷移 + Redis 快取 + 測試擴充

- httpOnly Cookie 認證遷移 + CSRF 防護 (Double Submit Cookie)
- Redis 非同步連線 + AI 結果快取 + 統計持久化
- AI 回應驗證層 `_call_ai_with_validation()`
- 搜尋歷史 localStorage + 結果快取 5 分鐘 TTL
- Refresh Token 速率限制 10/minute
- 測試擴充：認證整合 8 個 + Repository 24 個 + E2E 認證 5 個

---

## [1.48.0] - 2026-02-07

### 認證安全全面強化 + 管理後台優化

- CRITICAL: 移除明文密碼回退 + Refresh Token Rotation (SELECT FOR UPDATE)
- 診斷路由保護 → admin-only
- 強制 SECRET_KEY + 啟動 Token 驗證 + 閒置 30 分鐘超時
- 跨分頁 token 同步 (storage event)
- 系統健康度：9.9 → 10.0/10

---

## [1.47.0] - 2026-02-06

### AI 助理公文搜尋全面優化

- 提示注入防護：XML 標籤隔離 + 特殊字元清理
- RLS 權限篩選 `with_assignee_access()`
- asyncio.gather 並行取得附件與專案
- 前端 AbortController 防競態 + 30 秒超時
- AI 搜尋遷移至 DocumentQueryBuilder

---

## [1.46.0] - 2026-02-06

### Repository 層全面採用

- 5 個端點模組遷移至 Repository (users, user_management, profile, config, navigation)
- 新增 NavigationRepository
- UserRepository 新增 `get_users_filtered()`
- Repository 採用率：44% → 65%

---

## [1.45.0] - 2026-02-06

### 服務層工廠模式全面遷移 + AI 管理統一

- AgencyService v3.0.0 + ProjectService v4.0.0 工廠模式遷移
- UnitOfWork 移除 4 個 Adapter 類別
- 新增 UserRepository + ConfigurationRepository
- AI 管理頁面統一至 `/admin/ai-assistant` Tab 分頁
- CSRF AUTH_DISABLED 修復
- 架構驗證腳本 `verify_architecture.py` (7 項檢查)

---

## [1.44.0] - 2026-02-06

### 連鎖崩潰防護機制

- 事故：useEffect 無限迴圈 → 請求風暴 → 後端 OOM → PM2 重啟 421 次
- 五層防護：編碼規範 + RequestThrottler + slowapi 限流 + CI 驗證 + 部署驗證
- RequestThrottler：同 URL 1s 間隔、20/10s、全域 50/10s
- 3 個高頻端點限流 (documents/list, statistics, unread-count)

---

## [1.43.0] - 2026-02-06

### Phase 2 架構優化：Query Builder 擴展

- 新增 ProjectQueryBuilder (RLS 權限控制、多條件篩選)
- 新增 AgencyQueryBuilder (智慧模糊匹配)
- VendorService 合併為工廠模式 v2.0.0

---

## [1.42.0] - 2026-02-06

### 服務層架構優化與規範建立

- 新增 DocumentQueryBuilder 流暢介面查詢
- AI 自然語言搜尋 `/ai/document/natural-search`
- NaturalSearchPanel + AIAssistantButton 搜尋整合
- 前端 AI 元件配置集中化 `aiConfig.ts`

---

## [1.41.0] - 2026-02-05

### 派工安排 work_type 欄位修復

- 修復公文詳情頁 `work_type` 多選陣列 → 逗號分隔字串轉換

---

## [1.40.0] - 2026-02-05

### AI 助手 Portal 架構重構

- 移除 Drawer 抽屜模式，改用 Card 浮動面板
- createPortal 渲染與主版面 CSS 隔離
- 可拖曳面板 + 縮合/展開 + 漸層設計

---

## [1.39.0] - 2026-02-05

### AI 助理 UI 優化與配置集中化

- 新增 `aiConfig.ts` 集中 AI 配置
- 修復 FloatButton z-index 顯示問題

---

## [1.38.0] - 2026-02-05

### AI 服務優化與測試擴充

- RateLimiter 速率限制 (30 req/min) + SimpleCache 記憶體快取 (TTL 1h)
- E2E 測試擴充：documents 12 + dispatch 14 + projects 13
- 新增 mypy.ini Python 型別檢查配置

---

## [1.37.0] - 2026-02-04

### AI 語意精靈

- 整合 Groq API (免費方案 30 req/min) + Ollama 離線備援
- 公文摘要生成 + 分類建議 + 關鍵字提取 + 機關匹配
- 後端 7 個新檔案 + 前端 4 個新檔案
- 5 個 AI API 端點

---

## [1.36.0] - 2026-02-04

### 系統效能全面優化

- asyncio.gather 並行查詢 (API 響應 -40%)
- 5 個投影查詢方法 (資料傳輸 -30%)
- 4 個新索引 (複合 + 部分索引)
- 前端 12 個 useMemo 記憶化

---

## [1.35.0] - 2026-02-04

### 前端錯誤處理系統性修復

- 修復 6 處 catch 區塊錯誤清空列表的問題
- 7 個回歸測試 (useDocumentRelations)
- 新增錯誤處理規範：catch 中保留現有資料

---

## [1.34.0] - 2026-02-04

### E2E 測試框架與 Bug 修復

- 安裝 Playwright + 10 個 E2E 煙霧測試
- 修復派工安排存檔後紀錄消失 (重複 linkDispatch)
- 新增 E2E CI 工作流 `ci-e2e.yml`
- 前端覆蓋率門檻 50% → 80%

---

## [1.33.0] - 2026-02-03

### 派工單多對多關聯一致性修復與 GitOps 評估

**關鍵修復** 🔧:
- 修復派工單-公文關聯的資料一致性問題
- 建立/更新派工單時自動同步公文到關聯表
- 刪除派工單時清理孤立的公文-工程關聯
- 解除工程-派工關聯時反向清理自動建立的關聯

**新增檔案**:
- `backend/app/scripts/sync_dispatch_document_links.py` - 資料遷移腳本
- `docs/GITOPS_EVALUATION.md` - GitOps 評估與實施計畫
- `docs/MANUAL_DEPLOYMENT_GUIDE.md` - 手動部署指引
- `docs/OPTIMIZATION_REPORT_v1.32.md` - 系統優化報告

**修改檔案**:
- `backend/app/services/taoyuan/dispatch_order_service.py` - 新增 `_sync_document_links()` 方法
- `backend/app/api/endpoints/taoyuan_dispatch/project_dispatch_links.py` - 新增反向清理邏輯
- `.github/workflows/deploy-production.yml` - 修復 secrets 語法錯誤

**整合項目**:
- Everything Claude Code 配置（5 Commands, 2 Agents, 2 Rules, 1 Skill）
- Skills 目錄重構（移除重複，統一 shared/ 結構）

**測試修復**:
- `frontend/src/utils/logger.ts` - 匯出 LogLevel 型別
- `frontend/src/config/__tests__/queryConfig.test.ts` - 修正 calendar 測試
- `frontend/src/services/__tests__/navigationService.test.ts` - 修正 undefined 錯誤

**系統健康度**: 8.8/10 → **8.9/10** (提升 0.1 分)

**待完成**:
- ⏳ 生產環境部署（SSH 連線問題待解決）
- ⏳ Self-hosted Runner 安裝（GitOps 實施）

---

## [1.29.0] - 2026-02-02

### 資安強化與 CI/CD 優化

**資安強化**:
- 新增 `security_headers.py` - 安全標頭中間件 (OWASP 建議)
- 新增 `password_policy.py` - 密碼策略模組 (12 字元、複雜度要求)
- 整合密碼驗證至 `auth_service.py`
- SQL 注入風險評估完成 (7/8 處已修復)

**CI/CD 優化**:
- 移除 ESLint continue-on-error (強化品質檢查)
- 新增 Bandit Python 安全掃描

**系統健康度**: 9.6/10 → **9.7/10** (提升 0.1 分)

---

## [1.28.0] - 2026-02-02

### 部署架構優化與系統文件更新 (原 1.27.0)

---

## [1.27.0] - 2026-02-02

### 部署架構優化與系統文件更新

**部署優化完成**:
- ✅ 統一依賴管理：移除 poetry.lock，改用 pip + requirements.txt
- ✅ 部署前置腳本：pre-deploy.sh/ps1 + init-database.py
- ✅ Alembic 遷移文檔：ALEMBIC_MIGRATION_GUIDE.md
- ✅ Docker Compose 改進：添加註解和 logging 配置

**CI/CD 管線完整性**:
- 8 個 CI jobs 全部運作正常
- Docker 建置驗證整合
- 測試覆蓋率報告整合

**文件更新**:
- `SYSTEM_OPTIMIZATION_REPORT.md` 升級至 v7.0.0
- `OPTIMIZATION_ACTION_PLAN.md` 同步更新
- `CLAUDE.md` 升級至 v1.27.0

**系統健康度**: 9.5/10 → **9.6/10** (提升 0.1 分)

---

## [1.26.0] - 2026-02-02

### 派工-工程關聯自動同步功能

**新功能實現**：
當派工單關聯工程時，自動在派工關聯的所有公文中建立相同的工程關聯。

**修改檔案**：
- `backend/app/api/endpoints/taoyuan_dispatch/project_dispatch_links.py`
- `frontend/src/api/taoyuan/projectLinks.ts`
- `frontend/src/pages/TaoyuanDispatchDetailPage.tsx`

**業務邏輯**：
```
派工單 A 關聯工程 X
  ↓
查詢派工單 A 關聯的公文（如公文 B, C）
  ↓
自動建立：公文 B ↔ 工程 X
自動建立：公文 C ↔ 工程 X
  ↓
返回同步結果
```

**用戶體驗**：
- 關聯成功後顯示「已自動同步 N 個公文的工程關聯」提示
- 無需手動在公文頁面再次關聯工程

---

## [1.25.0] - 2026-02-02

### 系統檢視與待處理項目識別

**新識別優化項目** 🆕:

1. **前端 console 使用清理**
   - 數量: 165 處
   - 分布: 30+ 個檔案
   - 建議: 遷移至 `utils/logger.ts`

2. **前端測試覆蓋擴充**
   - 現況: 3 個測試檔案
   - 目標: 10+ 個測試檔案
   - 框架: Vitest (已配置)

**文件更新**:
- `SYSTEM_OPTIMIZATION_REPORT.md` v5.1.0
- `OPTIMIZATION_ACTION_PLAN.md` v4.1.0
- `CLAUDE.md` v1.25.0

**系統健康度維持**: 9.2/10

---

## [1.24.0] - 2026-02-02

### any 型別最終清理

**DocumentDetailPage.tsx 型別修復** ✅:
- 修復 5 處 any 型別
- 新增 `ProjectStaff`, `Project`, `User` 型別導入
- API 響應 `{ staff?: any[] }` → `{ staff?: ProjectStaff[] }`
- API 響應 `{ projects?: any[] }` → `{ projects?: Project[] }`
- API 響應 `{ users?: any[] }` → `{ users?: User[] }`

**any 型別最終統計**:
| 指標 | 數值 |
|------|------|
| 原始 | 44 檔案 |
| 最終 | 3 檔案 16 處 |
| 減少 | **93%** |

**剩餘 any (合理使用)**:
- `logger.ts` (11 處) - 日誌工具 `any[]`
- `ApiDocumentationPage.tsx` (3 處) - Swagger UI 第三方庫
- `common.ts` (2 處) - 泛型函數簽名

**文件更新**:
- `OPTIMIZATION_ACTION_PLAN.md` v4.0.0
- `SYSTEM_OPTIMIZATION_REPORT.md` 驗證結果更新
- `CLAUDE.md` v1.24.0

**驗證**:
- TypeScript 編譯: 0 錯誤 ✅

---

## [1.23.0] - 2026-02-02

### 全面優化完成

**any 型別清理** ✅:
- 從 24 檔案減少至 5 檔案 (減少 79%)
- 修復 19 個檔案的型別定義
- 新增 MenuItem、DocumentFormValues 等接口

**路徑別名配置** ✅:
- tsconfig.json 新增 @/api、@/config、@/store 別名
- vite.config.ts 同步更新 resolve.alias

**測試框架完善** ✅:
- 新增 `frontend/src/test/setup.ts`
- 前端 51 個測試全部通過
- 後端 290 個測試配置完善

**CI/CD 安全掃描** ✅:
- 新增 `.github/workflows/ci.yml` security-scan job
- npm audit + pip-audit 整合
- 硬編碼密碼檢測
- 危險模式掃描

**系統健康度**: 8.8/10 → **9.2/10** (提升 0.4 分)

**受影響檔案**:
- 19 個前端型別修復
- `tsconfig.json`、`vite.config.ts` 路徑配置
- `frontend/src/test/setup.ts` 新增
- `.github/workflows/ci.yml` 安全掃描

---

## [1.22.0] - 2026-02-02

### 系統檢視與文件同步更新

**文件更新**:
- `OPTIMIZATION_ACTION_PLAN.md` 升級至 v3.0.0 - 同步修復進度
- `CHANGELOG.md` 補齊 v1.20.0, v1.21.0 歷史記錄
- `CLAUDE.md` 確認版本 v1.21.0

**建議議題整理**:
1. 剩餘 any 型別 (24 檔案) - 低優先級
2. 路徑別名配置 - 可選
3. 測試覆蓋率提升 - 長期目標
4. CI/CD 安全掃描整合 - 建議加入

---

## [1.21.0] - 2026-02-02

### 中優先級任務完成

**後端架構優化**:
- 移除 `schemas/__init__.py` 中 9 個 wildcard import
- 改用具體導入，提升程式碼可追蹤性
- Alembic 遷移狀態健康 (單一 HEAD)

**前端型別優化**:
- any 型別減少 45% (44 → 24 檔案)
- 定義具體介面替代 any
- TypeScript 編譯 0 錯誤

**大型元件評估**:
- 評估 11 個大型檔案 (>600 行)
- 多數使用 Tab 結構，各 Tab 已獨立
- 建議後續針對 PaymentsTab、DispatchOrdersTab 細化

**系統健康度**: 7.8/10 → **8.8/10** (提升 1.0 分)

---

## [1.20.0] - 2026-02-02

### 全面安全與品質修復

**安全漏洞完全修復**:
- 🔐 硬編碼密碼：10 處移除（config.py, docker-compose, 備份腳本, setup_admin.py）
- 🔐 SQL 注入：關鍵路徑改用 SQLAlchemy ORM
- 🔐 CVE 漏洞：lodash (>=4.17.21), requests (>=2.32.0)

**程式碼品質修復**:
- ✅ print() 語句：61 → 0 (替換為 logging)
- ✅ 赤裸 except：11 → 0 (改為 `except Exception as e`)
- ✅ @ts-ignore：7 → 1 (新增 `google-oauth.d.ts`)

**新增模組**:
- `backend/app/core/security_utils.py` - 安全工具模組
- `frontend/src/types/google-oauth.d.ts` - Google OAuth 型別

**系統健康度提升**: 7.8/10 → **8.5/10** (提升 0.7 分)

---

## [1.19.0] - 2026-02-02

### 系統全面檢視與優化

**系統健康度評估**:
- 文件管理: 7.5/10 → 改善中
- 前端品質: 7.6/10
- 後端品質: 7.5/10

**文件更新**:
- CLAUDE.md 日期同步修正
- CHANGELOG.md 補齊 v1.7.0 至 v1.18.0 歷史記錄
- 系統優化報告升級至 v2.0.0

**識別的優化項目**:

| 類別 | 問題 | 數量 |
|------|------|------|
| 前端 | @ts-ignore 標記 | 7 個 |
| 前端 | any 型別使用 | 42 個 |
| 前端 | 大型元件 (>600行) | 5 個 |
| 後端 | print() 語句 | 44 個 |
| 後端 | 赤裸 except 語句 | 11 個 |
| 後端 | wildcard import | 10 個 |

**新增文檔**:
- 系統優化報告 v2.0.0 - 完整程式碼品質分析

---

## [1.18.0] - 2026-01-29

### 型別一致性修正

**前後端型別同步**:
- 移除前端 `TaoyuanProject` 中不存在於後端的欄位：`work_type`, `estimated_count`, `cloud_path`, `notes`
- 強化後端 `DispatchOrder.linked_documents` 型別：`List[dict]` → `List[DispatchDocumentLink]`

**TextArea 欄位優化**:
- `DispatchFormFields.tsx` v1.3.0：分案名稱、履約期限、聯絡備註等改為 TextArea

**驗證通過**: TypeScript ✅ | Python ✅ | 前端建置 ✅ | 後端導入 ✅

---

## [1.17.0] - 2026-01-29

### 共用表單元件架構

**派工表單共用元件重構**:
- 新增 `DispatchFormFields.tsx` 共用表單元件 (448 行)
- 統一 3 處派工表單：新增頁面、詳情編輯、公文內新增
- 支援三種模式：`create`、`edit`、`quick`

**AutoComplete 混合模式**:
- 工程名稱/派工事項欄位支援「選擇 + 手動輸入」混合模式

**Tab 順序調整**:
- `/taoyuan/dispatch` 頁面 Tab 順序：派工紀錄 → 函文紀錄 → 契金管控 → 工程資訊

**Skills 文件更新**:
- `frontend-architecture.md` v1.4.0 - 新增「共用表單元件架構」章節
- `calendar-integration.md` v1.2.0 - 新增 MissingGreenlet 錯誤解決方案

---

## [1.16.0] - 2026-01-29

### Modal 警告修復與備份優化

**Antd Modal + useForm 警告修復**:
- 修復 8 個 Modal 組件的 `useForm not connected` 警告
- 新增 `forceRender` 屬性確保 Form 組件始終渲染

**導航模式規範強化**:
- `DocumentPage.tsx` 完全移除 Modal，採用導航模式
- `DocumentsTab.tsx` 移除死程式碼

**備份機制優化**:
- 實作增量備份（Incremental Backup）機制
- 新增 `attachments_latest` 目錄追蹤最新狀態
- 修復 Windows 環境路徑檢測問題

---

## [1.15.0] - 2026-01-29

### CI 自動化版

**CI/CD 整合**:
- 整合 GitHub Actions CI 流程
- 新增 `skills-sync-check` job
- 支援 Push/PR 自動觸發檢查

**驗證腳本**:
- 新增 `scripts/skills-sync-check.ps1` (Windows)
- 新增 `scripts/skills-sync-check.sh` (Linux/macOS)
- 檢查 42 項配置（Skills/Commands/Hooks/Agents）

**文檔完善**:
- 新增 `.claude/skills/README.md` v1.0.0
- 更新 `.claude/hooks/README.md` v1.2.0

---

## [1.14.0] - 2026-01-28

### UI 規範強化版

**UI 設計規範強化**:
- 日曆事件編輯改用導航模式，移除 Modal
- 新增 `CalendarEventFormPage.tsx` 頁面
- 路由新增 `/calendar/event/:id/edit`

**派工單功能改進**:
- 返回導航機制 (returnTo Pattern) 完善
- 契金維護 Tab 編輯模式統一

**文件更新**:
- `UI_DESIGN_STANDARDS.md` 升級至 v1.2.0
- 新增 `SYSTEM_OPTIMIZATION_REPORT.md`

---

## [1.13.0] - 2026-01-26

### 架構現代化版

**依賴注入系統**:
- 新增 `backend/app/core/dependencies.py` (355 行)
- 支援 Singleton 模式與工廠模式兩種依賴注入方式

**Repository 層架構**:
- 新增 `backend/app/repositories/` 目錄 (3,022 行)
- `BaseRepository[T]` 泛型基類
- `DocumentRepository`, `ProjectRepository`, `AgencyRepository`

**前端元件重構**:
- `DocumentOperations.tsx`：1,229 行 → **327 行** (減少 73%)
- 新增 `useDocumentOperations.ts` (545 行)
- 新增 `useDocumentForm.ts` (293 行)

**程式碼精簡**:
- 總計減少約 **18,040 行**程式碼

---

## [1.12.0] - 2026-01-25

### 桃園派工模組完善

**新增功能**:
- 契金管控 CRUD 完整實作
- 派工單與公文關聯管理
- 函文紀錄 Tab 整合

**API 端點**:
- `POST /taoyuan_dispatch/payments` - 新增契金
- `PUT /taoyuan_dispatch/payments/{id}` - 更新契金
- `DELETE /taoyuan_dispatch/payments/{id}` - 刪除契金

---

## [1.11.0] - 2026-01-24

### 前端狀態管理優化

**Zustand Store 整合**:
- 新增 `taoyuanDispatchStore.ts`
- 新增 `taoyuanProjectStore.ts`

**React Query 整合**:
- 統一 API 快取策略
- 樂觀更新實作

---

## [1.10.0] - 2026-01-23

### 關聯記錄處理規範

**LINK_ID 規範制定**:
- 區分「實體 ID」與「關聯 ID」
- 禁止危險的回退邏輯

**新增規範文件**:
- `LINK_ID_HANDLING_SPECIFICATION.md` v1.0.0
- `MANDATORY_CHECKLIST.md` 升級至 v1.4.0

---

## [1.9.0] - 2026-01-21

### 架構優化版

**架構優化**:
- 前端 DocumentOperations.tsx: 1421 → 1229 行 (減少 13.5%)
- 後端 ORM models.py: 664 → 605 行 (減少 9%)
- 根目錄整理：21 個腳本移至 scripts/

**一致性驗證**:
- 新增 backend/check_consistency.py
- 前後端路由一致性驗證通過

---

## [1.8.0] - 2026-01-20

### 前端狀態管理架構

**雙層狀態管理**:
- React Query (Server State)
- Zustand (UI State)

**整合 Hook 模式**:
- `useDocumentsWithStore`
- `useProjectsWithStore`

---

## [1.7.0] - 2026-01-19

### 序列化規範版

**API 序列化規範**:
- 新增 `api-serialization.md` Skill v1.0.0
- 新增 `api-serialization-check.ps1` Hook

**Python 常見陷阱規範**:
- 新增 `python-common-pitfalls.md` Skill v1.0.0
- 涵蓋 Pydantic forward reference、async MissingGreenlet 等

---

## [1.6.0] - 2026-01-18

### 重大變更：型別定義統一整合 (SSOT 架構)

**背景**: 消除前後端型別重複定義問題，建立單一真實來源

### 新增
- `type-management.md` Skill - 型別管理規範 v1.0.0
- `MANDATORY_CHECKLIST.md` 清單 H - 型別管理開發檢查
- 11 個新 Schema 檔案整合至 `backend/app/schemas/`
- 前端 OpenAPI 自動生成機制 (`npm run api:generate`)
- 型別變更日誌生成器 (`scripts/type-changelog.js`)
- Pre-commit TypeScript 編譯檢查

### 改進
- `type-sync.md` 升級至 v2.0.0 - 完整 SSOT 架構驗證
- `api-development.md` 新增 SSOT 規範說明
- `MANDATORY_CHECKLIST.md` 升級至 v1.3.0

### 整合的 Schema 檔案

| Schema 檔案 | 整合的類別數量 | 來源 |
|------------|--------------|------|
| `notification.py` | 11 | system_notifications.py, project_notifications.py |
| `document_query.py` | 10 | documents_enhanced.py |
| `document_number.py` | 10 | document_numbers.py |
| `document_calendar.py` | +2 | ConflictCheckRequest, SyncIntervalRequest |
| `reminder.py` | 6 | reminder_management.py |
| `backup.py` | 3 | backup.py |
| `case.py` | 3 | cases.py |
| `secure.py` | 2 | secure_site_management.py |
| `agency.py` | +2 | FixAgenciesRequest, FixAgenciesResponse |
| `project.py` | +1 | ProjectListQuery |
| `user.py` | +1 | UserListQuery |
| `vendor.py` | +2 | VendorListQuery, VendorStatisticsResponse |
| `project_staff.py` | +1 | StaffListQuery |
| `project_vendor.py` | +1 | VendorAssociationListQuery |
| `project_agency_contact.py` | +1 | UpdateContactRequest |

### 成果指標
- endpoints 本地 BaseModel：62+ → 0 (100% 減少)
- 新增欄位修改位置：6+ → 2 (僅後端 Schema + 前端自動生成)

---

## [1.5.0] - 2026-01-15

### 新增
- `PUT /auth/profile` - 更新個人資料 API 端點
- `PUT /auth/password` - 修改密碼 API 端點
- `ProfileUpdate` schema 定義
- 共享 Skills 庫文檔化至 CLAUDE.md
- 本 CHANGELOG.md 變更日誌

### 改進
- `useAuthGuard.ts` v1.3.0 - superuser 角色現在擁有所有角色權限
- `auth.py` v2.2 - 新增個人資料與密碼管理端點
- `SiteManagementPage.tsx` - 修復 ValidPath 型別錯誤
- CLAUDE.md 升級至 v1.5.0

### 修復
- 修復 superuser 無法訪問管理員頁面的權限問題
- 修復 ProfilePage 的 404 錯誤 (缺失 API 端點)

---

## [1.4.0] - 2026-01-12 ~ 2026-01-14

### 新增
- `/security-audit` 資安審計檢查指令
- `/performance-check` 效能診斷檢查指令
- `navigation_validator.py` 路徑白名單驗證機制
- 導覽路徑下拉選單自動載入功能
- `route-sync-check.ps1` 路徑同步檢查 Hook
- API Rate Limiting (slowapi)
- Structured Logging (structlog)
- 擴展健康檢查端點 (CPU/Memory/Disk/Scheduler)

### 改進
- `route-sync-check.md` 升級至 v2.0.0 - 新增白名單驗證
- `api-check.md` 升級至 v2.1.0 - POST-only 安全模式檢查
- `MANDATORY_CHECKLIST.md` 升級至 v1.2.0 - 新增導覽系統架構說明
- `frontend-architecture.md` 新增至 Skills (v1.0.0)
- `EntryPage.tsx` 修復快速進入未設定 user_info 問題

### 修復
- bcrypt 版本降級至 4.0.1 (解決 Windows 相容性)
- 動態 CORS 支援多來源
- 統一日誌編碼 (UTF-8)
- 進程管理腳本優化

---

## [1.3.0] - 2026-01-10 ~ 2026-01-11

### 新增
- 環境智慧偵測登入機制 (localhost/internal/ngrok/public)
- 內網 IP 免認證快速進入功能
- Google OAuth 登入整合
- 新帳號審核機制
- 網域白名單檢查

### 改進
- `EntryPage.tsx` 升級至 v2.5.0 - 三種登入方式
- `useAuthGuard.ts` v1.2.0 - 支援內網繞過認證
- `config/env.ts` 集中式環境偵測

---

## [1.2.0] - 2026-01-08 ~ 2026-01-09

### 新增
- `/db-backup` 資料庫備份管理指令
- `/csv-import-validate` CSV 匯入驗證指令
- `/data-quality-check` 資料品質檢查指令
- 備份排程器 (每日凌晨 2:00)

### 改進
- 公文管理 CRUD 完善
- 行事曆 Google Calendar 雙向同步

---

## [1.1.0] - 2026-01-05 ~ 2026-01-07

### 新增
- `/pre-dev-check` 開發前強制檢查指令
- `/route-sync-check` 前後端路由檢查指令
- `/api-check` API 端點一致性檢查指令
- `/type-sync` 型別同步檢查指令
- `MANDATORY_CHECKLIST.md` 強制性開發檢查清單
- `DEVELOPMENT_GUIDELINES.md` 開發指引

### 改進
- Hooks 系統建立 (typescript-check, python-lint)
- Agents 建立 (code-review, api-design)

---

## [1.0.0] - 2026-01-01 ~ 2026-01-04

### 初始版本
- 專案架構建立
- FastAPI + PostgreSQL 後端
- React + TypeScript + Ant Design 前端
- 基本公文管理功能
- 基本認證系統

---

## 版本號說明

採用語義化版本 (SemVer):
- **Major (主版本)**: 重大架構變更或不相容更新
- **Minor (次版本)**: 新增功能，向後相容
- **Patch (修補版本)**: Bug 修復，向後相容

---

*維護者: Claude Code Assistant*
