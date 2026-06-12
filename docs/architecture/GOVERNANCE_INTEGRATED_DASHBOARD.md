# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-06-12 14:02:08
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 61 | `docs/architecture/LESSONS_REGISTRY.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 103 | `scripts/checks/*.py` |
| Architecture docs | 81 | `docs/architecture/*.md` |
| **Total** | **293** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  10.9
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             4.8
  governance_wiki_pages_total                               423.0
  kg_entities_total                                       26837.0
  memory_crystals_total                                       2.0
  memory_diary_days_total                                    52.0
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       3300.4
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}          2.9
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}          2.9
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        287.9
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1781240828.1
  scheduler_job_success_created{job_id="health_check_broadcast"} 1781237525.6
  scheduler_job_success_created{job_id="process_reminders"} 1781237525.6
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1781237240.6
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}          1.0
  scheduler_job_success_total{job_id="health_check_broadcast"}         23.0
  scheduler_job_success_total{job_id="process_reminders"}         23.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}         23.0
  shadow_baseline_call_total{provider="gemma-local"}         47.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      41510.0
  shadow_baseline_rows_total{lookback_hours="24"}            47.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="find_correspondence"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_expense_overview"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         19.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         12.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_tender"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          1.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             20.7
  v7_soul_drift_lines                                        -1.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `ea60f5cb chore(memory): 06-12 cron 副產物歸檔 + 治理儀表板重生`
- `d9e76fc1 docs(reboot): v6.18 CLAUDE delta + 06-12 重啟 pre-flight runbook`
- `c1435d73 fix(scheduler): 57f 收尾 — id 對齊 + audit 認 conditional/prefix/f-string`
- `2cf1c48e refactor(memory): 57e 收斂 — _parse_tools 抽 memory/_utils SSOT（9→8 真重複）`
- `c78151f4 refactor(schema): 57e 收斂 — normalize_name 抽 schemas/_text_utils SSOT（10→9 真重複）`
- `1ceb976a refactor(repo): 57e 收斂 — get_by_ids 抽 BaseRepository SSOT（11→10 真重複）`
- `e0470c41 refactor(governance): 57e audit 再精煉 — 跨檔同名才算真 copy-paste（11 精準目標）`
- `4f8a4723 refactor(repo): 57e 收斂 — 3 repo _get_grouped_count 抽 BaseRepository.grouped_count SSOT`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260610_sso_race_scheduler_doctor.md
- session_20260609_review_deploy_failures_triage.md
- session_20260603_04_routing_synthesis_integration.md
- session_20260530_v6_12_meta_governance_day.md
- session_20260530_v6_12_full_day.md

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
| 1 | baseline rows | ≥ 30 | 47 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 41.5s | ❌ |
| **Summary** | — | — | **2/5** | **🔴 NO-GO** |

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

**所有 47 cron 真活狀態**（從 `/metrics scheduler_job_*` 即時抓）：

| Job ID | Age | Success | Failure | 狀態 |
|---|---|---|---|---|
| `ezbid_cache_refresh` | 0.9h | 1 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.1h | 23 | 0 | 🟢 |
| `process_reminders` | 0.0h | 23 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 23 | 0 | 🟢 |

**統計**：4 真活 cron / 4 GREEN / 0 YELLOW / 0 RED

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
| 14:02:05 | `health_check_broadcast` | ✅ success | 21ms |
| 14:02:05 | `process_reminders` | ✅ success | 10ms |
| 13:57:20 | `tender_dashboard_warm` | ✅ success | 1ms |
| 13:57:05 | `health_check_broadcast` | ✅ success | 56ms |
| 13:57:05 | `process_reminders` | ✅ success | 50ms |
| 13:52:20 | `tender_dashboard_warm` | ✅ success | 2ms |
| 13:52:05 | `health_check_broadcast` | ✅ success | 50ms |
| 13:52:05 | `process_reminders` | ✅ success | 45ms |
| 13:47:28 | `tender_dashboard_warm` | ✅ success | 7496ms |
| 13:47:05 | `health_check_broadcast` | ✅ success | 55ms |

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