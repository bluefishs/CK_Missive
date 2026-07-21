# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-07-21 10:20:26
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 68 | `docs/architecture/LESSONS_REGISTRY.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 112 | `scripts/checks/*.py` |
| Architecture docs | 89 | `docs/architecture/*.md` |
| **Total** | **317** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                   7.2
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             1.2
  governance_wiki_pages_total                               563.0
  kg_entities_total                                       47609.0
  memory_crystals_total                                       4.0
  memory_diary_days_total                                    91.0
  scheduler_job_last_run_age_seconds{job_id="agent_self_diagnosis"}      15014.7
  scheduler_job_last_run_age_seconds{job_id="cf_tunnel_verify"}      14720.8
  scheduler_job_last_run_age_seconds{job_id="cleanup_events"}      29970.9
  scheduler_job_last_run_age_seconds{job_id="code_graph_incremental"}      26410.4
  scheduler_job_last_run_age_seconds{job_id="cron_outcome_freshness"}      12019.7
  scheduler_job_last_run_age_seconds{job_id="cron_self_health_alert"}      13820.8
  scheduler_job_last_run_age_seconds{job_id="daily_self_reflection_line_push"}      44420.8
  scheduler_job_last_run_age_seconds{job_id="daily_self_retrospective"}      27318.4
  scheduler_job_last_run_age_seconds{job_id="db_graph_refresh"}      24320.3
  scheduler_job_last_run_age_seconds{job_id="embedding_warmup"}      20120.7
  scheduler_job_last_run_age_seconds{job_id="erp_graph_ingest"}      24620.5
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       2993.7
  scheduler_job_last_run_age_seconds{job_id="fitness_daily"}      29969.8
  scheduler_job_last_run_age_seconds{job_id="governance_dashboard_regen"}      28219.9
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        294.4
  scheduler_job_last_run_age_seconds{job_id="health_snapshot_log"}      15320.8
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}      29708.1
  scheduler_job_last_run_age_seconds{job_id="kb_coverage_check"}      22820.7
  scheduler_job_last_run_age_seconds{job_id="kg_embedding_backfill"}      21014.4
  scheduler_job_last_run_age_seconds{job_id="ledger_reconciliation"}      19220.7
  scheduler_job_last_run_age_seconds{job_id="llm_quota_check"}      20994.3
  scheduler_job_last_run_age_seconds{job_id="memory_crystallization_scan"}      20720.3
  scheduler_job_last_run_age_seconds{job_id="memory_pattern_extract"}      22520.5
  scheduler_job_last_run_age_seconds{job_id="morning_report"}       8402.1
  scheduler_job_last_run_age_seconds{job_id="optimization_pipeline"}      26360.5
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       6593.3
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}      35420.2
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        294.4
  scheduler_job_last_run_age_seconds{job_id="security_scan"}      29970.7
  scheduler_job_last_run_age_seconds{job_id="soul_mirror_sync"}      19820.8
  scheduler_job_last_run_age_seconds{job_id="synthetic_baseline_inject"}       4659.9
  scheduler_job_last_run_age_seconds{job_id="tender_business_recommend"}       4820.8
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        279.4
  scheduler_job_last_run_age_seconds{job_id="tender_pcc_enrichment"}      23774.1
  scheduler_job_last_run_age_seconds{job_id="tender_refresh_pending"}      15611.9
  scheduler_job_last_run_age_seconds{job_id="tender_subscription"}       8419.9
  scheduler_job_last_run_age_seconds{job_id="wiki_lint"}      17419.8
  scheduler_job_success_created{job_id="agent_self_diagnosis"} 1784585406.1
  scheduler_job_success_created{job_id="cf_tunnel_verify"} 1784585700.0
  scheduler_job_success_created{job_id="cleanup_events"} 1784570449.9
  scheduler_job_success_created{job_id="code_graph_incremental"} 1784574010.3
  scheduler_job_success_created{job_id="cron_outcome_freshness"} 1784588401.1
  scheduler_job_success_created{job_id="cron_self_health_alert"} 1784586600.0
  scheduler_job_success_created{job_id="daily_self_reflection_line_push"} 1784556000.0
  scheduler_job_success_created{job_id="daily_self_retrospective"} 1784573102.4
  scheduler_job_success_created{job_id="db_graph_refresh"} 1784576100.5
  scheduler_job_success_created{job_id="embedding_warmup"} 1784580300.0
  scheduler_job_success_created{job_id="erp_graph_ingest"} 1784575800.3
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1784518227.6
  scheduler_job_success_created{job_id="fitness_daily"} 1784570451.0
  scheduler_job_success_created{job_id="governance_dashboard_regen"} 1784572200.9
  scheduler_job_success_created{job_id="health_check_broadcast"} 1784514926.3
  scheduler_job_success_created{job_id="health_snapshot_log"} 1784585100.0
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1784570712.7
  scheduler_job_success_created{job_id="kb_coverage_check"} 1784577600.0
  scheduler_job_success_created{job_id="kg_embedding_backfill"} 1784579406.3
  scheduler_job_success_created{job_id="ledger_reconciliation"} 1784581200.1
  scheduler_job_success_created{job_id="llm_quota_check"} 1784536226.6
  scheduler_job_success_created{job_id="memory_crystallization_scan"} 1784579700.4
  scheduler_job_success_created{job_id="memory_pattern_extract"} 1784577900.2
  scheduler_job_success_created{job_id="morning_report"} 1784592018.7
  scheduler_job_success_created{job_id="optimization_pipeline"} 1784574060.3
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1784521828.8
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1784565000.6
  scheduler_job_success_created{job_id="process_reminders"} 1784514926.3
  scheduler_job_success_created{job_id="security_scan"} 1784570450.1
  scheduler_job_success_created{job_id="soul_mirror_sync"} 1784580600.0
  scheduler_job_success_created{job_id="synthetic_baseline_inject"} 1784527404.2
  scheduler_job_success_created{job_id="tender_business_recommend"} 1784595600.0
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1784514641.3
  scheduler_job_success_created{job_id="tender_pcc_enrichment"} 1784576646.7
  scheduler_job_success_created{job_id="tender_refresh_pending"} 1784584808.8
  scheduler_job_success_created{job_id="tender_subscription"} 1784520000.9
  scheduler_job_success_created{job_id="wiki_lint"}  1784583000.9
  scheduler_job_success_total{job_id="agent_self_diagnosis"}          1.0
  scheduler_job_success_total{job_id="cf_tunnel_verify"}          1.0
  scheduler_job_success_total{job_id="cleanup_events"}          1.0
  scheduler_job_success_total{job_id="code_graph_incremental"}          1.0
  scheduler_job_success_total{job_id="cron_outcome_freshness"}          1.0
  scheduler_job_success_total{job_id="cron_self_health_alert"}          1.0
  scheduler_job_success_total{job_id="daily_self_reflection_line_push"}          1.0
  scheduler_job_success_total{job_id="daily_self_retrospective"}          1.0
  scheduler_job_success_total{job_id="db_graph_refresh"}          1.0
  scheduler_job_success_total{job_id="embedding_warmup"}          1.0
  scheduler_job_success_total{job_id="erp_graph_ingest"}          1.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}         23.0
  scheduler_job_success_total{job_id="fitness_daily"}          1.0
  scheduler_job_success_total{job_id="governance_dashboard_regen"}          1.0
  scheduler_job_success_total{job_id="health_check_broadcast"}        283.0
  scheduler_job_success_total{job_id="health_snapshot_log"}          1.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          1.0
  scheduler_job_success_total{job_id="kb_coverage_check"}          1.0
  scheduler_job_success_total{job_id="kg_embedding_backfill"}          1.0
  scheduler_job_success_total{job_id="ledger_reconciliation"}          1.0
  scheduler_job_success_total{job_id="llm_quota_check"}          3.0
  scheduler_job_success_total{job_id="memory_crystallization_scan"}          1.0
  scheduler_job_success_total{job_id="memory_pattern_extract"}          1.0
  scheduler_job_success_total{job_id="morning_report"}          1.0
  scheduler_job_success_total{job_id="optimization_pipeline"}          1.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}         11.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}        283.0
  scheduler_job_success_total{job_id="security_scan"}          1.0
  scheduler_job_success_total{job_id="soul_mirror_sync"}          1.0
  scheduler_job_success_total{job_id="synthetic_baseline_inject"}          3.0
  scheduler_job_success_total{job_id="tender_business_recommend"}          1.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}        285.0
  scheduler_job_success_total{job_id="tender_pcc_enrichment"}          1.0
  scheduler_job_success_total{job_id="tender_refresh_pending"}          1.0
  scheduler_job_success_total{job_id="tender_subscription"}          3.0
  scheduler_job_success_total{job_id="wiki_lint"}             1.0
  shadow_baseline_call_total{provider="gemma-local"}         40.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      52756.0
  shadow_baseline_rows_total{lookback_hours="24"}            40.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_expense_overview"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_financial_summary"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         11.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         21.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          9.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_tender"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          4.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             24.7
  v7_soul_drift_lines                                         3.0
```

> ℹ️ **metric 範疇註記（消 SSOT 誤判）**：`wiki_pages_total` = 全 `wiki/**/*.md` 檔數（含 memory/diary/patterns）；
> self-retrospective 報告的「wiki 頁數」= LLM wiki 頁（`wiki/` 前兩層）。兩者同名不同範疇，差異屬定義非漂移。
> `v7_soul_drift_lines = -1` 為 sentinel（容器內 writer 盲視 host `CK_AaaP`，L73）；真值須 host fitness 寫入。

## 3. 最近 8 commits (進化執行軌跡)

- `7f907d1a docs: v6.26 里程碑 + 07-20 重啟 pre-flight checklist`
- `6c54a222 fix: 掃全同型金額字串串接 bug — 帳本/電子發票加總補 Number()`
- `5a03ebdb fix: 帳本 list 400(0元分錄) + 發票彙總金額字串串接 NaN`
- `a6ead7f9 refactor: taoyuan statistics MorningStatusRequest 移入 schemas SSOT`
- `8770f764 fix: 建案 409 顯示真實訊息 + dedup 防誤判/防崩潰`
- `c5d14891 docs: 登記 HH-1 非確定性 bug 治本 + 業務模組審計三輪總結`
- `f0050080 fix: 治本 HH-1 派工單機關/乾坤函文號非確定性 bug + 收斂委派 service`
- `dcf39e91 docs: 業務模組審計收尾 — 低風險批次 done、HH-2 核實判勿收斂、元結論`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260615_wiki_kg_regression_root_fix_sso_diag.md
- session_20260612_arch_review_soul_drift_federation.md
- session_20260610_sso_race_scheduler_doctor.md
- session_20260609_review_deploy_failures_triage.md
- session_20260603_04_routing_synthesis_integration.md

## 5. Facade B 方案 60 天 trial 進度 (重評日 2026-07-30)

| Facade | 現 caller | 60 天目標 | 達標 |
|---|---|---|---|
| IntegrationFacade | 3 | ≥5 | 🟡 |
| MemoryFacade | 3 | ≥5 | 🟡 |
| WikiFacade | 3 | ≥3 | ✅ |

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
| 1 | baseline rows | ≥ 30 | 40 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 52.8s | ❌ |
| **Summary** | — | — | **2/5** | **🔴 NO-GO** |

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
| `daily_self_reflection_line_push` | 12.3h | 1 | 0 | 🟢 |
| `proactive_trigger_scan` | 9.8h | 1 | 0 | 🟢 |
| `cleanup_events` | 8.3h | 1 | 0 | 🟢 |
| `security_scan` | 8.3h | 1 | 0 | 🟢 |
| `fitness_daily` | 8.3h | 1 | 0 | 🟢 |
| `integration_e2e_validation` | 8.3h | 1 | 0 | 🟢 |
| `governance_dashboard_regen` | 7.8h | 1 | 0 | 🟢 |
| `daily_self_retrospective` | 7.6h | 1 | 0 | 🟢 |
| `code_graph_incremental` | 7.3h | 1 | 0 | 🟢 |
| `optimization_pipeline` | 7.3h | 1 | 0 | 🟢 |
| `erp_graph_ingest` | 6.8h | 1 | 0 | 🟢 |
| `db_graph_refresh` | 6.8h | 1 | 0 | 🟢 |
| `tender_pcc_enrichment` | 6.6h | 1 | 0 | 🟢 |
| `kb_coverage_check` | 6.3h | 1 | 0 | 🟢 |
| `memory_pattern_extract` | 6.3h | 1 | 0 | 🟢 |
| `kg_embedding_backfill` | 5.8h | 1 | 0 | 🟢 |
| `llm_quota_check` | 5.8h | 3 | 0 | 🟢 |
| `memory_crystallization_scan` | 5.8h | 1 | 0 | 🟢 |
| `embedding_warmup` | 5.6h | 1 | 0 | 🟢 |
| `soul_mirror_sync` | 5.5h | 1 | 0 | 🟢 |
| `ledger_reconciliation` | 5.3h | 1 | 0 | 🟢 |
| `wiki_lint` | 4.8h | 1 | 0 | 🟢 |
| `tender_refresh_pending` | 4.3h | 1 | 0 | 🟢 |
| `health_snapshot_log` | 4.3h | 1 | 0 | 🟢 |
| `agent_self_diagnosis` | 4.2h | 1 | 0 | 🟢 |
| `cf_tunnel_verify` | 4.1h | 1 | 0 | 🟢 |
| `cron_self_health_alert` | 3.8h | 1 | 0 | 🟢 |
| `cron_outcome_freshness` | 3.3h | 1 | 0 | 🟢 |
| `tender_subscription` | 2.3h | 3 | 0 | 🟢 |
| `morning_report` | 2.3h | 1 | 0 | 🟢 |
| `pcc_today_scrape` | 1.8h | 11 | 0 | 🟢 |
| `tender_business_recommend` | 1.3h | 1 | 0 | 🟢 |
| `synthetic_baseline_inject` | 1.3h | 3 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.8h | 23 | 0 | 🟢 |
| `process_reminders` | 0.1h | 283 | 0 | 🟢 |
| `health_check_broadcast` | 0.1h | 283 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.1h | 285 | 0 | 🟢 |

**統計**：37 個近期活躍 cron / 37 GREEN / 0 YELLOW / 0 RED（完整對賬見 scheduler_liveness_audit）

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
| 10:20:26 | `health_check_broadcast` | ✅ success | 35ms |
| 10:20:26 | `process_reminders` | ✅ success | 4ms |
| 10:15:41 | `tender_dashboard_warm` | ✅ success | 1ms |
| 10:15:26 | `health_check_broadcast` | ✅ success | 14ms |
| 10:15:26 | `process_reminders` | ✅ success | 3ms |
| 10:10:42 | `tender_dashboard_warm` | ✅ success | 892ms |
| 10:10:26 | `health_check_broadcast` | ✅ success | 15ms |
| 10:10:26 | `process_reminders` | ✅ success | 3ms |
| 10:05:41 | `tender_dashboard_warm` | ✅ success | 1ms |
| 10:05:26 | `health_check_broadcast` | ✅ success | 23ms |

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