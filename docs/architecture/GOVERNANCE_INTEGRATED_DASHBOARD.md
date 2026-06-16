# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-06-16 02:30:00
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 62 | `docs/architecture/LESSONS_REGISTRY.md` |
| SOPs | 0 | `.claude/rules/*.md`（容器未掛載 .claude/，host 端執行才計數） |
| Fitness checks | 105 | `scripts/checks/*.py` |
| Architecture docs | 84 | `docs/architecture/*.md` |
| **Total** | **286** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  23.3
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             6.2
  governance_wiki_pages_total                               439.0
  kg_entities_total                                       26934.0
  memory_crystals_total                                       2.0
  memory_diary_days_total                                    55.0
  scheduler_job_last_run_age_seconds{job_id="cleanup_events"}       1752.7
  scheduler_job_last_run_age_seconds{job_id="daily_self_reflection_line_push"}      16200.3
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       1644.3
  scheduler_job_last_run_age_seconds{job_id="fitness_daily"}       1751.6
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        144.8
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}       1487.7
  scheduler_job_last_run_age_seconds{job_id="llm_quota_check"}       8844.6
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       1641.1
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}       7198.4
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        144.9
  scheduler_job_last_run_age_seconds{job_id="security_scan"}       1752.5
  scheduler_job_last_run_age_seconds{job_id="synthetic_baseline_inject"}      23225.9
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        128.2
  scheduler_job_last_run_age_seconds{job_id="tender_subscription"}      30599.6
  scheduler_job_success_created{job_id="cleanup_events"} 1781546447.6
  scheduler_job_success_created{job_id="daily_self_reflection_line_push"} 1781532000.0
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1781499763.3
  scheduler_job_success_created{job_id="fitness_daily"} 1781546448.8
  scheduler_job_success_created{job_id="health_check_broadcast"} 1781496455.5
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1781546712.7
  scheduler_job_success_created{job_id="llm_quota_check"} 1781517755.8
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1781503357.5
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1781541002.0
  scheduler_job_success_created{job_id="process_reminders"} 1781496455.5
  scheduler_job_success_created{job_id="security_scan"} 1781546447.9
  scheduler_job_success_created{job_id="synthetic_baseline_inject"} 1781503621.3
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1781496177.9
  scheduler_job_success_created{job_id="tender_subscription"} 1781517600.7
  scheduler_job_success_total{job_id="cleanup_events"}          1.0
  scheduler_job_success_total{job_id="daily_self_reflection_line_push"}          1.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}         14.0
  scheduler_job_success_total{job_id="fitness_daily"}          1.0
  scheduler_job_success_total{job_id="health_check_broadcast"}        172.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          1.0
  scheduler_job_success_total{job_id="llm_quota_check"}          2.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}          7.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}        172.0
  scheduler_job_success_total{job_id="security_scan"}          1.0
  scheduler_job_success_total{job_id="synthetic_baseline_inject"}          2.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}        173.0
  scheduler_job_success_total{job_id="tender_subscription"}          1.0
  shadow_baseline_call_total{provider="gemma-local"}         60.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      49690.0
  shadow_baseline_rows_total{lookback_hours="24"}            60.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="find_correspondence"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_expense_overview"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         25.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          5.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         33.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}         12.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             24.1
  v7_soul_drift_lines                                        -1.0
```

## 3. 最近 8 commits (進化執行軌跡)

> ⚪ 容器內執行（非 git repo）無法取 commit 歷史；於 host 端手動 regenerate 可填。

## 4. 最近 5 session 覆盤 (memory/)

> ⚪ 容器內無 ~/.claude memory 存取；於 host 端手動 regenerate 可填。

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
| 1 | baseline rows | ≥ 30 | 60 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 49.7s | ❌ |
| **Summary** | — | — | **2/5** | **🔴 NO-GO** |

詳見 `docs/architecture/HERMES_BASELINE_RESET_PLAN_20260530.md`

## 9. 跨 repo 範本漂移 (4 子專案 v6.12 治理採用度)

| Repo | 跟進度 | Verdict | 修法建議 |
|---|---|---|---|
| CK_lvrland_Webmap | 0/6 | ⚪ N/A | — |
| CK_PileMgmt | 0/6 | ⚪ N/A | — |
| CK_Showcase | 0/6 | ⚪ N/A | — |
| CK_KMapAdvisor | 0/6 | ⚪ N/A | — |


## 9.5 Cron 排程真活全表 (事件追溯依據)

**所有 47 cron 真活狀態**（從 `/metrics scheduler_job_*` 即時抓）：

| Job ID | Age | Success | Failure | 狀態 |
|---|---|---|---|---|
| `tender_subscription` | 8.5h | 1 | 0 | 🟢 |
| `synthetic_baseline_inject` | 6.5h | 2 | 0 | 🟢 |
| `daily_self_reflection_line_push` | 4.5h | 1 | 0 | 🟢 |
| `llm_quota_check` | 2.5h | 2 | 0 | 🟢 |
| `proactive_trigger_scan` | 2.0h | 1 | 0 | 🟢 |
| `cleanup_events` | 0.5h | 1 | 0 | 🟢 |
| `security_scan` | 0.5h | 1 | 0 | 🟢 |
| `fitness_daily` | 0.5h | 1 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.5h | 14 | 0 | 🟢 |
| `pcc_today_scrape` | 0.5h | 7 | 0 | 🟢 |
| `integration_e2e_validation` | 0.4h | 1 | 0 | 🟢 |
| `process_reminders` | 0.0h | 172 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 172 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 173 | 0 | 🟢 |

**統計**：14 真活 cron / 14 GREEN / 0 YELLOW / 0 RED

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
| 02:27:52 | `tender_dashboard_warm` | ✅ success | 1679ms |
| 02:27:35 | `health_check_broadcast` | ✅ success | 52ms |
| 02:27:35 | `process_reminders` | ✅ success | 34ms |
| 02:22:50 | `tender_dashboard_warm` | ✅ success | 1ms |
| 02:22:35 | `health_check_broadcast` | ✅ success | 52ms |
| 02:22:35 | `process_reminders` | ✅ success | 46ms |
| 02:17:50 | `tender_dashboard_warm` | ✅ success | 1ms |
| 02:17:35 | `health_check_broadcast` | ✅ success | 53ms |
| 02:17:35 | `process_reminders` | ✅ success | 32ms |
| 02:12:51 | `tender_dashboard_warm` | ✅ success | 852ms |

**統計** (最近 30 個事件): 30 成功 / 0 失敗 / 失敗率 0.0%

## 10. Owner action 待辦 (不可委任)

- ADR-0020 + ADR-0035 proposed 收斂
- 4 pending crystal 審批 (`/admin/crystals`)
- Hermes GO/NO-GO baseline 重評
- 跨 repo install-template 對 0 RED 子專案套用 (詳 §9)
- CK_KMapAdvisor CLAUDE.md STALE 32 天
- Task Scheduler 重建 / sync_enabled=true

---

## 整合視角結論

> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。
> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。
> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`