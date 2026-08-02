# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-08-03 07:58:28
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 69 | `docs/architecture/LESSONS_REGISTRY.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 123 | `scripts/checks/*.py` |
| Architecture docs | 102 | `docs/architecture/*.md` |
| **Total** | **342** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                   4.8
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             0.0
  governance_wiki_pages_total                               618.0
  kg_entities_total                                       49548.0
  memory_crystals_total                                       4.0
  memory_diary_days_total                                   104.0
  scheduler_job_last_run_age_seconds{job_id="agent_self_diagnosis"}       6501.6
  scheduler_job_last_run_age_seconds{job_id="case_finance_bridge_selfheal"}      18507.8
  scheduler_job_last_run_age_seconds{job_id="cf_tunnel_verify"}       6206.0
  scheduler_job_last_run_age_seconds{job_id="cleanup_events"}      21456.8
  scheduler_job_last_run_age_seconds{job_id="code_graph_incremental"}      17898.8
  scheduler_job_last_run_age_seconds{job_id="cron_outcome_freshness"}       3506.4
  scheduler_job_last_run_age_seconds{job_id="cron_self_health_alert"}       5307.8
  scheduler_job_last_run_age_seconds{job_id="daily_self_retrospective"}      18805.6
  scheduler_job_last_run_age_seconds{job_id="db_graph_refresh"}      15807.3
  scheduler_job_last_run_age_seconds{job_id="embedding_warmup"}      11607.8
  scheduler_job_last_run_age_seconds{job_id="erp_graph_ingest"}      16107.6
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}        715.6
  scheduler_job_last_run_age_seconds{job_id="fitness_daily"}      21454.9
  scheduler_job_last_run_age_seconds{job_id="governance_dashboard_regen"}      19707.2
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        117.6
  scheduler_job_last_run_age_seconds{job_id="health_snapshot_log"}       6807.8
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}      21195.1
  scheduler_job_last_run_age_seconds{job_id="kb_coverage_check"}      14307.8
  scheduler_job_last_run_age_seconds{job_id="kg_embedding_backfill"}      12506.2
  scheduler_job_last_run_age_seconds{job_id="ledger_reconciliation"}      10707.2
  scheduler_job_last_run_age_seconds{job_id="llm_quota_check"}      11517.2
  scheduler_job_last_run_age_seconds{job_id="memory_anti_echo_scan"}       7107.7
  scheduler_job_last_run_age_seconds{job_id="memory_crystallization_scan"}      12207.7
  scheduler_job_last_run_age_seconds{job_id="memory_pattern_extract"}      14007.7
  scheduler_job_last_run_age_seconds{job_id="optimization_pipeline"}      17851.0
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       4314.3
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}      26907.1
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        117.6
  scheduler_job_last_run_age_seconds{job_id="security_scan"}      21455.4
  scheduler_job_last_run_age_seconds{job_id="soul_mirror_sync"}      11307.8
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        102.1
  scheduler_job_last_run_age_seconds{job_id="tender_pcc_enrichment"}      14747.4
  scheduler_job_last_run_age_seconds{job_id="tender_refresh_pending"}       7098.7
  scheduler_job_last_run_age_seconds{job_id="wiki_compile"}      10701.8
  scheduler_job_last_run_age_seconds{job_id="wiki_lint"}       8904.7
  scheduler_job_success_created{job_id="agent_self_diagnosis"} 1785708606.3
  scheduler_job_success_created{job_id="case_finance_bridge_selfheal"} 1785696600.0
  scheduler_job_success_created{job_id="cf_tunnel_verify"} 1785708901.8
  scheduler_job_success_created{job_id="cleanup_events"} 1785693651.0
  scheduler_job_success_created{job_id="code_graph_incremental"} 1785697209.0
  scheduler_job_success_created{job_id="cron_outcome_freshness"} 1785711601.4
  scheduler_job_success_created{job_id="cron_self_health_alert"} 1785709800.0
  scheduler_job_success_created{job_id="daily_self_retrospective"} 1785696302.2
  scheduler_job_success_created{job_id="db_graph_refresh"} 1785699300.5
  scheduler_job_success_created{job_id="embedding_warmup"} 1785703500.0
  scheduler_job_success_created{job_id="erp_graph_ingest"} 1785699000.2
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1785685593.8
  scheduler_job_success_created{job_id="fitness_daily"} 1785693652.9
  scheduler_job_success_created{job_id="governance_dashboard_regen"} 1785695400.7
  scheduler_job_success_created{job_id="health_check_broadcast"} 1785682290.2
  scheduler_job_success_created{job_id="health_snapshot_log"} 1785708300.0
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1785693912.8
  scheduler_job_success_created{job_id="kb_coverage_check"} 1785700800.0
  scheduler_job_success_created{job_id="kg_embedding_backfill"} 1785702601.6
  scheduler_job_success_created{job_id="ledger_reconciliation"} 1785704400.6
  scheduler_job_success_created{job_id="llm_quota_check"} 1785703590.6
  scheduler_job_success_created{job_id="memory_anti_echo_scan"} 1785708000.1
  scheduler_job_success_created{job_id="memory_crystallization_scan"} 1785702900.1
  scheduler_job_success_created{job_id="memory_pattern_extract"} 1785701100.1
  scheduler_job_success_created{job_id="optimization_pipeline"} 1785697256.8
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1785689190.4
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1785688200.7
  scheduler_job_success_created{job_id="process_reminders"} 1785682290.2
  scheduler_job_success_created{job_id="security_scan"} 1785693652.4
  scheduler_job_success_created{job_id="soul_mirror_sync"} 1785703800.0
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1785682005.2
  scheduler_job_success_created{job_id="tender_pcc_enrichment"} 1785700360.4
  scheduler_job_success_created{job_id="tender_refresh_pending"} 1785708009.2
  scheduler_job_success_created{job_id="wiki_compile"} 1785704406.0
  scheduler_job_success_created{job_id="wiki_lint"}  1785706203.1
  scheduler_job_success_total{job_id="agent_self_diagnosis"}          1.0
  scheduler_job_success_total{job_id="case_finance_bridge_selfheal"}          1.0
  scheduler_job_success_total{job_id="cf_tunnel_verify"}          1.0
  scheduler_job_success_total{job_id="cleanup_events"}          1.0
  scheduler_job_success_total{job_id="code_graph_incremental"}          1.0
  scheduler_job_success_total{job_id="cron_outcome_freshness"}          1.0
  scheduler_job_success_total{job_id="cron_self_health_alert"}          1.0
  scheduler_job_success_total{job_id="daily_self_retrospective"}          1.0
  scheduler_job_success_total{job_id="db_graph_refresh"}          1.0
  scheduler_job_success_total{job_id="embedding_warmup"}          1.0
  scheduler_job_success_total{job_id="erp_graph_ingest"}          1.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}          9.0
  scheduler_job_success_total{job_id="fitness_daily"}          1.0
  scheduler_job_success_total{job_id="governance_dashboard_regen"}          1.0
  scheduler_job_success_total{job_id="health_check_broadcast"}        110.0
  scheduler_job_success_total{job_id="health_snapshot_log"}          1.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          1.0
  scheduler_job_success_total{job_id="kb_coverage_check"}          1.0
  scheduler_job_success_total{job_id="kg_embedding_backfill"}          1.0
  scheduler_job_success_total{job_id="ledger_reconciliation"}          1.0
  scheduler_job_success_total{job_id="llm_quota_check"}          1.0
  scheduler_job_success_total{job_id="memory_anti_echo_scan"}          1.0
  scheduler_job_success_total{job_id="memory_crystallization_scan"}          1.0
  scheduler_job_success_total{job_id="memory_pattern_extract"}          1.0
  scheduler_job_success_total{job_id="optimization_pipeline"}          1.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}          4.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}        110.0
  scheduler_job_success_total{job_id="security_scan"}          1.0
  scheduler_job_success_total{job_id="soul_mirror_sync"}          1.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}        111.0
  scheduler_job_success_total{job_id="tender_pcc_enrichment"}          1.0
  scheduler_job_success_total{job_id="tender_refresh_pending"}          1.0
  scheduler_job_success_total{job_id="wiki_compile"}          1.0
  scheduler_job_success_total{job_id="wiki_lint"}             1.0
  shadow_baseline_call_total{provider="gemma-hermes"}          6.0
  shadow_baseline_call_total{provider="gemma-local"}         58.0
  shadow_baseline_call_total{provider="unknown"}              2.0
  shadow_baseline_latency_p95_ms{provider="gemma-hermes"}      35449.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      54270.0
  shadow_baseline_latency_p95_ms{provider="unknown"}        123.0
  shadow_baseline_rows_total{lookback_hours="24"}            66.0
  shadow_baseline_success_ratio{provider="gemma-hermes"}          0.8
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_success_ratio{provider="unknown"}           1.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="document_search"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_expense_overview"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         23.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="list_assets"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         28.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}         15.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_tender"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          3.0
  shadow_baseline_tool_use_count{provider="unknown",tool="doc_search"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             25.5
  v7_soul_drift_lines                                         3.0
```

> ℹ️ **metric 範疇註記（消 SSOT 誤判）**：`wiki_pages_total` = 全 `wiki/**/*.md` 檔數（含 memory/diary/patterns）；
> self-retrospective 報告的「wiki 頁數」= LLM wiki 頁（`wiki/` 前兩層）。兩者同名不同範疇，差異屬定義非漂移。
> `v7_soul_drift_lines = -1` 為 sentinel（容器內 writer 盲視 host `CK_AaaP`，L73）；真值須 host fitness 寫入。

## 3. 最近 8 commits (進化執行軌跡)

- `207dcdc0 docs: v6.37 里程碑 + LESSONS_REGISTRY 標註 L42-L48 編號缺口`
- `dd2f181c feat(checks): 補上「測試套件跑不跑得起來」這一階，並修掉一個 flaky`
- `4d73195f test: 修三類過時測試（DDD 遷移後的 import 路徑、鎖死的版本號）`
- `88a87f36 fix(erp): finance_ledger 用了未 import 的 logger，刪除有帳本的請款單會 NameError`
- `7a3daa70 fix(tender): 封鎖偵測誤把 CSS class 當封鎖；ezbid fixture 補回改版後的回歸保護`
- `4366a2ed docs: v6.36 里程碑（測試庫隔離）`
- `bea53984 fix(tests): 測試套件改用獨立測試庫，整套從「不能安全執行」變成 9 分鐘跑完`
- `2dccea23 fix(checks): producer watchdog 區分「還沒做」與「做了沒產出」，且 SKIP 不算通過`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260730_silent_success_sweep.md
- session_20260729_post_restart_review.md
- session_20260725_arch_review.md
- session_20260723_24_frontend_shared_consolidation.md
- session_20260721_22_sso_modularization_verification.md

## 5. Facade B 方案 60 天 trial（**已到期 2026-07-30，待 owner 結案**）

| Facade | 現 caller | 60 天目標 | 達標 |
|---|---|---|---|
| IntegrationFacade | 3 | ≥5 | 🟡 |
| MemoryFacade | 3 | ≥5 | 🟡 |
| WikiFacade | 3 | ≥3 | ✅ |

> 到期判定與建議（全保留 + 停止設成長目標 + 往後新增 facade 須先有 ≥3 既存 caller）：
> `docs/architecture/RETRO_20260730_POST_SWEEP_REVIEW.md` §4。
> 註：此處 caller 數以 import 行 grep 計，可能低估（實測 Integration=4）。

## 6. Lesson 索引 (L4x family 為主)

- **L01** — SSOT 聲明 vs 實作斷鏈（Dead Doc 反模式）
- **L02** — Yaml config 聲明卻 0 reader（Dead Config）
- **L03** — Mock.patch 路徑遷移（Wave 1 sub-batch B）
- **L04** — Multi-line patch sed 失效（Wave 4 tender）
- **L05** — Class name collision（Wave 1 sub-batch C notification）
- **L06** — 內部循環 import → relative import（Wave 1 sub-batch A document）
- **L07** — Private function (`_` 開頭) re-export（Wave 2 ERP）
- **L08** — Production caller 路徑同步（Wave 3 integration）
- **L09** — Async mock 斷鏈（pre-existing test failures）
- **L10** — Dead UI（後端實作但前端缺 UI）
- **L11** — React Query staleTime + 0 invalidate = 60s 不刷新
- **L12** — Stub 算散戶 → entropy 短期不會降
- **L13** — sed 替換漏掃 cross-cutting test 檔（Wave 8）
- **L14** — GitHub Actions 自動觸發產生雲端費用
- **L15** — Telegram 個人號當主推播通道（ADR-0027）
- **L16** — 一個 dataclass 塞 100+ 設定欄位
- **L17** — DDD 遷移看職責邊界不看行數
- **L18** — Wiki dispatch backfill 不需 fuzzy match
- **L19** — KG embedding 維護需週期性 backfill
- **L21** — Agent evolution scheduler 整合斷鏈（redis counter 卡 0）
- **L24** — Self-evaluator 標準過鬆 / Pattern 門檻過緊（雙重失衡）
- **L25** — 鏈路驗證 vs 鏈路盤點（grep 關鍵字陷阱）
- **L20** — Lessons 散落 commit/ADR/PLAYBOOK → 需 SSOT
- **L23** — 領域驅動拆分 vs 行數驅動拆分（拒拆判準）
- **L26** — Half-Wired Anti-Pattern Stacking（多層 bug 疊加遮蔽）
- **L27** — Dev Mode Override Trap（VITE_AUTH_DISABLED 強制覆蓋真實用戶）
- **L29** — Domain score 寫入鏈再次中斷（dict key bug + 涵蓋率不足）
- **L28** — JSON-as-TEXT Schema Drift（DB Text 存 JSON 但忘 parse）
- **L30** — Pipeline Integration as Priority（環節不連通就是浪費）
- **L31** — ROI = entities × usage_rate（建表不等於用表）
- **L32** — Frontend UI Component 不適合 packaging（LR-015 終局教訓 / 2026-05-18）
- **L33** — Transitive Deps 缺失必致 Half-Wired（LR-015/016 配套）
- **L34** — 業務 specific 不可進 shared package（lvrland LR-020 對應 / 2026-05-18）
- **L35** — 採納前必過 baseline TS check（lvrland LR-019 對應 / 2026-05-18）
- **L36** — Repo Structure Assumption（install.sh 寫死目標路徑 / 2026-05-18）
- **L22** — 範本資產缺跨 repo 引用治理規範
- **L37** — 覆盤報告自身也是「真活宣告 vs 真接通」候選（2026-05-19）
- **L39** — QueryKey Drift（React Query invalidate silent dead）（2026-05-20）
- **L38** — 平時保險（cron / 異地備份）也是 LR-015 反模式高發區（2026-05-19）
- **L41** — JWT Secret Drift Silent Fail（4 重疊加 / 2026-05-21）
- **L77** — 標案 enrichment 死結：openfun 需 org_id、org_id 只在被反爬限流的 PCC 詳情頁（勿重試爬蟲路徑 / 2026-06-17）
- **L76** — Windows Docker backend recreate/restart 易留殭屍埠轉發 socket → 公網 502（部署後必驗 host→8001 / 2026-06-16）
- **L75** — 推薦相關性：機關關係 ≠ 工項相關；粗放機關信號 + 粗粒度（府級）比對＝噪音源（標案業務推薦 / 2026-06-16）
- **L74** — 單一狀態欄被多個 async 來源 last-writer-wins 競寫 + 破壞性副作用＝經典 race（SSO「第一次停 entry、重刷才好」/ 2026-06-16）
- **L80** — SSO 反覆回歸的底層＝「後端 token 生命週期層」：SSO 沒有可用的透明 refresh 路徑（前端不變式救不了 / 2026-07-21）
- **L79** — Session 收尾不完整＝功能「存在於硬碟但不存在於系統」：寫好＋測試綠 ≠ commit ≠ 部署（2026-07-08）
- **L78** — 「今日 OK、明日又壞」＝復原路徑有多入口且散落破壞性副作用，happy-path 驗證必漏（SSO 反覆回歸元覆盤 / 2026-07-03）
- **L73** — In-container writer 盲視 host/cross-repo 資源 → silent 寫錯值（治理工具自身亦中招 / 2026-06-12）
- **L72** — 排程「註冊 ≠ 真在跑」：scheduler liveness 對賬揪 silent dormant cron（擴大治理至坤哥/Hermes/排程 / 2026-06-12）
- **L71** — 程式圖譜是「結構地圖」抓不到 config/語意/runtime 三類問題 → 用 AST 橋接治理（2026-06-11）
- **L70** — GOOGLE_CALENDAR_ID config-drift：1044 事件靜默推進「服務帳號私人日曆」無人可見（L51 同族 / 2026-06-11）
- **L69** — secureApiService single-flight 讓並發共用「單次」CSRF token → nav 選單 403（修 L49 反效果 / 2026-06-11）
- **L68** — CSRF refresh 死結：csrf cookie 過期→refresh 被 CSRF 擋→全站 403「權限不足」（OWASP / 2026-06-10）
- **L66** — 跨子域 SSO 消費端 self-heal gate 漏掉 cookie-session（顯示「訪客」race / 2026-06-10）
- **L67** — 前端 baseURL 已含 `/api` 卻硬編 `/api` 前綴 → double-prefix 404（半接通 / 2026-06-10）
- **L64** — LINE 推播鏈交易污染復發（吞錯不 rollback + 缺方法 + 重複掃描 / 2026-06-03）
- **L63** — 學習閉環需 aging alert 才能突破 owner 健忘（2026-05-31）
- **L62** — 整合連通 = 持續驗證機制，不是一次性 endpoint（2026-05-31）
- **L61** — 下游反治理（PileMgmt R18 案例 / L60 真活驗證範本）（2026-05-31）
- **L60** — 平衡 = 結構正常化（非中間值）（2026-05-30，meta-治理第 8 句立法）
- **L59** — 治理架構倒置（上游 meta 缺 audit / 業務 source 反向 audit 子專案）（2026-05-30）
- **L58** — 治理範本污染風險（強推 132 檔 57% 為本專案特定）（2026-05-30）
- **L57** — BACKEND_DIR/logs vs compose mount 子路徑漂移（L52 family 第七案）（2026-05-30）
- **L54** — 跨 repo 套用 ≠ 落實（install-template apply vs commit gap）（2026-05-30）
- **L53** — Facade over-engineering 30 天實證裁判（ADR-0036 ROI 失敗）（2026-05-30）
- **L52** — paths.py PROJECT_ROOT vs compose mount target 漂移（L4x family 第六案）（2026-05-30）
- **L51** — Container image freshness family（L51.5/L51.7 系列，2026-05-30）
- **L50** — Multi-source identifier ≠ entity link（2026-05-28）
- **L49** — Container Host Dependency Family (PM2 → Docker 遷移 5 重 silent regression / 2026-05-27)

## 7. v6.12 進化 4 原則狀態

| # | 原則 | 落地證據 | 狀態 |
|---|---|---|---|
| #1 | 修法掃全範圍 audit | fitness step 60 container image freshness | ✅ |
| #2 | observability 分層 forcing | Tier 1 daily 7 + Tier 2 weekly 14 + Tier 3 monthly | ✅ |
| #3 | 治理本身 metric 化 | 7 governance_* gauge + scheduler_job_* | ✅ |
| #4 | 元覆盤 cron | daily_self_retrospective 7 aspects (06:30) | ✅ |

## 8. 漂移看板 (audit 結果統一)

✓ 所有 governance metric 在門檻內

## 8.5 Hermes Baseline GO/NO-GO 5 條件 (Sprint 3.P3.15)

| # | 條件 | 門檻 | 現況 | 達標 |
|---|---|---|---|---|
| 1 | baseline rows | ≥ 30 | 66 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 5.6% | ❌ |
| 5 | p95 latency | < 8s | 54.3s | ❌ |
| **Summary** | — | — | **1/5** | **🔴 NO-GO** |

> ℹ️ **#4 error rate / #5 p95 為已接受的結構性限制（accepted constraint）**：瓶頸坐實在本地模型強度
> （免費策略下 TPM 牆），非 prompt/管路可解；monorepo 已定調維持免費、勿再投 prompt 層 recall 強化。
> 維持免費策略期間此兩項不列為待辦，避免每次覆盤重觸發雜訊。升付費 tier 或換更強模型才重評。

詳見 `docs/architecture/HERMES_BASELINE_RESET_PLAN_20260530.md`

## 9. 跨 repo 範本漂移 (4 子專案 v6.12 治理採用度)

| Repo | 跟進度 | Verdict | 修法建議 |
|---|---|---|---|
| CK_lvrland_Webmap | 1/6 | 🔴 RED | `install-template-to.sh` |
| CK_PileMgmt | 0/6 | 🔴 RED-zero | `install-template-to.sh` |
| CK_Showcase | 6/6 | 🟢 GREEN | — |
| CK_KMapAdvisor | 6/6 | 🟢 GREEN | — |

⚠ **2/4 子專案 RED** — 範本對外採用度不足，owner approve 後執行:
```bash
bash scripts/install-template-to.sh ../<repo_name> \
  --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons
```

## 9.5 Cron 排程真活全表 (事件追溯依據)

**近期活躍 cron**（從 `/metrics scheduler_job_*` 即時抓 = 重啟後已 fire 的 job）：

> ⚠️ 此表只含「後端重啟後已執行過」的 job（metric 重啟歸零）；週級/月級 job 在重啟後
> 到下次 fire 前不會出現於此，**非代表中斷**。完整註冊×執行對賬（用持久 cron_events.jsonl，
> 涵蓋週自傳等低頻 job）以 `scheduler_liveness_audit.py` 為權威，silent dormant 由其偵測。

| Job ID | Age | Success | Failure | 狀態 |
|---|---|---|---|---|
| `proactive_trigger_scan` | 7.5h | 1 | 0 | 🟢 |
| `cleanup_events` | 6.0h | 1 | 0 | 🟢 |
| `security_scan` | 6.0h | 1 | 0 | 🟢 |
| `fitness_daily` | 6.0h | 1 | 0 | 🟢 |
| `integration_e2e_validation` | 5.9h | 1 | 0 | 🟢 |
| `governance_dashboard_regen` | 5.5h | 1 | 0 | 🟢 |
| `daily_self_retrospective` | 5.2h | 1 | 0 | 🟢 |
| `case_finance_bridge_selfheal` | 5.1h | 1 | 0 | 🟢 |
| `code_graph_incremental` | 5.0h | 1 | 0 | 🟢 |
| `optimization_pipeline` | 5.0h | 1 | 0 | 🟢 |
| `erp_graph_ingest` | 4.5h | 1 | 0 | 🟢 |
| `db_graph_refresh` | 4.4h | 1 | 0 | 🟢 |
| `tender_pcc_enrichment` | 4.1h | 1 | 0 | 🟢 |
| `kb_coverage_check` | 4.0h | 1 | 0 | 🟢 |
| `memory_pattern_extract` | 3.9h | 1 | 0 | 🟢 |
| `kg_embedding_backfill` | 3.5h | 1 | 0 | 🟢 |
| `memory_crystallization_scan` | 3.4h | 1 | 0 | 🟢 |
| `embedding_warmup` | 3.2h | 1 | 0 | 🟢 |
| `llm_quota_check` | 3.2h | 1 | 0 | 🟢 |
| `soul_mirror_sync` | 3.1h | 1 | 0 | 🟢 |
| `ledger_reconciliation` | 3.0h | 1 | 0 | 🟢 |
| `wiki_compile` | 3.0h | 1 | 0 | 🟢 |
| `wiki_lint` | 2.5h | 1 | 0 | 🟢 |
| `memory_anti_echo_scan` | 2.0h | 1 | 0 | 🟢 |
| `tender_refresh_pending` | 2.0h | 1 | 0 | 🟢 |
| `health_snapshot_log` | 1.9h | 1 | 0 | 🟢 |
| `agent_self_diagnosis` | 1.8h | 1 | 0 | 🟢 |
| `cf_tunnel_verify` | 1.7h | 1 | 0 | 🟢 |
| `cron_self_health_alert` | 1.5h | 1 | 0 | 🟢 |
| `pcc_today_scrape` | 1.2h | 4 | 0 | 🟢 |
| `cron_outcome_freshness` | 1.0h | 1 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.2h | 9 | 0 | 🟢 |
| `process_reminders` | 0.0h | 110 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 110 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 111 | 0 | 🟢 |

**統計**：35 個近期活躍 cron / 35 GREEN / 0 YELLOW / 0 RED（完整對賬見 scheduler_liveness_audit）

**凌晨低干擾排程設計（v6.13）**：
- 02:00 fitness_daily / 02:30 dashboard_regen / 02:45 self_retrospective
- 03:00 optimization_pipeline / 03:35 db_schema
- 避開 06:00-22:00 用戶活躍時段 + 早報推播

**事件追溯**：每 scheduler tracker 含 `last_run` / `last_status` / `last_duration_ms` / `last_error`

## 9.6 Cron 執行歷史摘要 (jsonl event log)

**事件 log**：`backend/logs/cron_events.jsonl` (跨 backend restart 持久化)

**最近 30 個事件**：

| 時間 | Job | 狀態 | 耗時 |
|---|---|---|---|
| 07:56:45 | `tender_dashboard_warm` | ✅ success | 480ms |
| 07:56:30 | `health_check_broadcast` | ✅ success | 15ms |
| 07:56:30 | `process_reminders` | ✅ success | 4ms |
| 07:51:45 | `tender_dashboard_warm` | ✅ success | 1ms |
| 07:51:30 | `health_check_broadcast` | ✅ success | 36ms |
| 07:51:30 | `process_reminders` | ✅ success | 4ms |
| 07:46:45 | `tender_dashboard_warm` | ✅ success | 2ms |
| 07:46:32 | `ezbid_cache_refresh` | ✅ success | 2050ms |
| 07:46:30 | `health_check_broadcast` | ✅ success | 24ms |
| 07:46:30 | `process_reminders` | ✅ success | 17ms |

**統計** (最近 30 個事件): 30 成功 / 0 失敗 / 失敗率 0.0%

## 10. Owner action 待辦 (不可委任)

- ADR-0020 + ADR-0035 proposed 收斂
- 4 pending crystal 審批 (`/admin/crystals`)
- Hermes GO/NO-GO baseline 重評
- 跨 repo install-template 對 2 RED 子專案套用 (詳 §9)
- CK_KMapAdvisor CLAUDE.md STALE 32 天
- Task Scheduler 重建 / sync_enabled=true

---

## 整合視角結論

> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。
> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。
> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`