# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-08-30 02:45:21
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 97 | `docs/architecture/LESSONS_REGISTRY.md` |
| SOPs | 12 | `.claude/rules/*.md` |
| Fitness checks | 181 | `scripts/checks/*.py` |
| Architecture docs | 117 | `docs/architecture/*.md` |
| **Total** | **442** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  47.7
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   18.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             0.1
  governance_wiki_pages_total                               807.0
  kg_entities_total                                       50086.0
  memory_crystals_total                                       4.0
  memory_diary_days_total                                   130.0
  scheduler_job_last_run_age_seconds{job_id="cleanup_events"}       2576.3
  scheduler_job_last_run_age_seconds{job_id="critique_health_audit"}       1820.0
  scheduler_job_last_run_age_seconds{job_id="daily_self_retrospective"}         18.8
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       1984.9
  scheduler_job_last_run_age_seconds{job_id="fitness_daily"}       2575.8
  scheduler_job_last_run_age_seconds{job_id="fitness_weekly"}        920.9
  scheduler_job_last_run_age_seconds{job_id="governance_dashboard_regen"}        920.1
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        193.4
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}       2408.3
  scheduler_job_last_run_age_seconds{job_id="kg_metrics_refresh"}        183.4
  scheduler_job_last_run_age_seconds{job_id="memory_metrics_refresh"}        180.5
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       1993.3
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}       8120.1
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        193.4
  scheduler_job_last_run_age_seconds{job_id="proposal_aging_alert"}       1520.5
  scheduler_job_last_run_age_seconds{job_id="security_scan"}       2575.2
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        178.4
  scheduler_job_last_run_age_seconds{job_id="weekly_evolution_generator"}       2575.5
  scheduler_job_success_created{job_id="cleanup_events"} 1788026544.7
  scheduler_job_success_created{job_id="critique_health_audit"} 1788027301.1
  scheduler_job_success_created{job_id="daily_self_retrospective"} 1788029102.3
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1788023556.0
  scheduler_job_success_created{job_id="fitness_daily"} 1788026545.2
  scheduler_job_success_created{job_id="fitness_weekly"} 1788028200.1
  scheduler_job_success_created{job_id="governance_dashboard_regen"} 1788028200.9
  scheduler_job_success_created{job_id="health_check_broadcast"} 1788020227.6
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1788026712.7
  scheduler_job_success_created{job_id="kg_metrics_refresh"} 1788019937.6
  scheduler_job_success_created{job_id="memory_metrics_refresh"} 1788019940.3
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1788027127.7
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1788021000.9
  scheduler_job_success_created{job_id="process_reminders"} 1788020227.6
  scheduler_job_success_created{job_id="proposal_aging_alert"} 1788027600.5
  scheduler_job_success_created{job_id="security_scan"} 1788026545.9
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1788019942.6
  scheduler_job_success_created{job_id="weekly_evolution_generator"} 1788026545.5
  scheduler_job_success_total{job_id="cleanup_events"}          1.0
  scheduler_job_success_total{job_id="critique_health_audit"}          1.0
  scheduler_job_success_total{job_id="daily_self_retrospective"}          1.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}          2.0
  scheduler_job_success_total{job_id="fitness_daily"}          1.0
  scheduler_job_success_total{job_id="fitness_weekly"}          1.0
  scheduler_job_success_total{job_id="governance_dashboard_regen"}          1.0
  scheduler_job_success_total{job_id="health_check_broadcast"}         30.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          1.0
  scheduler_job_success_total{job_id="kg_metrics_refresh"}         11.0
  scheduler_job_success_total{job_id="memory_metrics_refresh"}         11.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}          1.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}         30.0
  scheduler_job_success_total{job_id="proposal_aging_alert"}          1.0
  scheduler_job_success_total{job_id="security_scan"}          1.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}         31.0
  scheduler_job_success_total{job_id="weekly_evolution_generator"}          1.0
  shadow_baseline_call_total{provider="gemma-local"}         55.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      69502.0
  shadow_baseline_rows_total{lookback_hours="24"}            55.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          8.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_financial_summary"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         16.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          5.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         25.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}         11.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_tender"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          6.0
  v7_channel_diversity                                        0.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             23.1
  v7_soul_drift_lines                                         3.0
```

> ℹ️ **metric 範疇註記（消 SSOT 誤判）**：`wiki_pages_total` = 全 `wiki/**/*.md` 檔數（含 memory/diary/patterns）；
> self-retrospective 報告的「wiki 頁數」= LLM wiki 頁（`wiki/` 前兩層）。兩者同名不同範疇，差異屬定義非漂移。
> `v7_soul_drift_lines = -1` 為 sentinel（容器內 writer 盲視 host `CK_AaaP`，L73）；真值須 host fitness 寫入。

## 3. 最近 8 commits (進化執行軌跡)

- `ca39ab30 docs(checks): 收窄判準之後得到的零要再查一次——我今天有四個那樣的零`
- `9dc83ec1 docs(checks): 為什麼不採用清單雜湊——錨點要對應「被斷言的是什麼」`
- `6bb9c86e fix(checks): 豁免必須是會被重驗的斷言——沒有到期日的豁免會變成永久盲點`
- `094ed14a fix(checks): 「沒有這 6 個檔」被當成「還沒跟進」——而 lvrland 有 43 支自己的檢核`
- `21581430 docs(checks): 幽靈條目——登記在錯名字下的東西不會顯示為漂移，會顯示為「不存在」`
- `ee7d0825 docs(checks): 記錄四個否定結果——因為否定結論會替後來的人決定「不必再查」`
- `f34b7e3d docs: pre-push 舊版已自行同步——但其餘 5 個 repo 仍是舊版（A36）`
- `24b2e5ad fix(checks): 基線再加一道下限守衛——本 repo 早有比我更強的形式`

> <!--host-captured:2026-08-30T02:45:21-->

## 4. 最近 5 session 覆盤 (memory/)

- session_20260730_silent_success_sweep.md
- session_20260729_post_restart_review.md
- session_20260725_arch_review.md
- session_20260723_24_frontend_shared_consolidation.md
- session_20260721_22_sso_modularization_verification.md

> <!--host-captured:2026-08-30T02:45:21-->

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
- **L90** — 一次異常關機讓 12 個排程整批沒跑，而三層存活稽核沒有一層問「這一次它跑了沒有」（2026-08-12）
- **L108** — 為了看見一種訊號而加的旗標，把另一種訊號整批關掉了（2026-08-29）
- **L107** — 外層 rollback 擋不住內部自己 commit 的函式，而我把「已回滾」寫進了回報（2026-08-29）
- **L106** — 公網探的那支 health 根本不查 DB，而 L43 的防禦做在另一條路徑上（2026-08-29）
- **L105** — 「我這條路徑找不到」不等於「資料不存在」，而那句結論寫進了文件（2026-08-29）
- **L104** — 註解指名了來源檔，不代表值是從那裡來的（2026-08-29）
- **L103** — 我把 runner 改壞、提交進版控，而它印著 GREEN 與退出碼 0（2026-08-29）
- **L101** — 量測工具的解析度比事件粗，而它交回的數字是對的（2026-08-29）
- **L102** — 修法的首版把「不存在」偽裝成「用錯」，正是它要修的東西的反面（2026-08-29）
- **L100** — 執行者在、腳本在、旗標也在，只是呼叫時少了那個旗標（2026-08-29）
- **L99** — 壞掉的腳本＋假的執行者宣告＋文件把它列為驗證命令（2026-08-29）
- **L97** — 判準命中的是註解不是程式碼，而註解寫得越用心它越容易被騙（2026-08-29）
- **L98** — 修一個共用元件不會讓它的同類變好，而它們的症狀一模一樣（2026-08-29）
- **L96** — 取走資料的動作與送出的動作之間，只要有失敗的可能，就必須有回填路徑（2026-08-29）
- **L95** — 排程紅燈有四種型態，而稽核上長得一模一樣（2026-08-29）
- **L94** — 把觀測者的回報路徑接到被觀測的系統上，就是讓它們共用失敗模式（2026-08-29）
- **L93** — ORM mapper 初始化失敗＝整個系統無法登入，而 /health 仍是 200（2026-08-16）
- **L92** — 檢核在「要報問題的那一刻」崩掉，而平常看起來好好的（2026-08-15）
- **L91** — 在 Windows 上執行帶容器絕對路徑的程式碼不會失敗，它會靜靜讀寫 `D:\app\`（2026-08-12）
- **L89** — 跨 repo 共用腳本帶著自己的退出碼約定進到別人的 runner，會被靜靜降級成「未驗完」（2026-08-09）
- **L87** — 「多給一種憑證」不是保險，是多開一條會失敗的路；而剛上線的檢核最不該被信任（2026-08-09）
- **L88** — 檢核把自己的退出碼判成異常：自我循環讓 weekly 永遠不可能綠（2026-08-09）
- **L86** — 連續猜錯五次之後：讓工具「說出它看到什麼」，比再猜第六次有效（2026-08-08）
- **L85** — 破壞性指令的作用範圍必須先確認；而且答案往往早就寫在文件裡（2026-08-08）
- **L84** — 「設定寫得很嚴謹」與「它跑得起來」是兩件事：從未啟動成功過的服務，會逼出一條更差的替代路徑（2026-08-08）
- **L83** — 「我送出了什麼」與「對方收到了什麼」是兩件事：中間層會靜靜改寫，而單元測試斷言的是前者（2026-08-07）
- **L81** — 換了出口就要換整條鏈：把通知從 A 管道改到 B 管道時，閘門、測試安全網、測試斷言都會留在 A（2026-08-04）
- **L82** — 「還沒到門檻」與「永遠到不了門檻」長得一模一樣：資料深度被保留期釘住，而腳本每次都禮貌地說資料不足（2026-08-04）
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
| 1 | baseline rows | ≥ 30 | 55 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 69.5s | ❌ |
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
| `proactive_trigger_scan` | 2.3h | 1 | 0 | 🟢 |
| `cleanup_events` | 0.7h | 1 | 0 | 🟢 |
| `fitness_daily` | 0.7h | 1 | 0 | 🟢 |
| `weekly_evolution_generator` | 0.7h | 1 | 0 | 🟢 |
| `security_scan` | 0.7h | 1 | 0 | 🟢 |
| `integration_e2e_validation` | 0.7h | 1 | 0 | 🟢 |
| `pcc_today_scrape` | 0.6h | 1 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.6h | 2 | 0 | 🟢 |
| `critique_health_audit` | 0.5h | 1 | 0 | 🟢 |
| `proposal_aging_alert` | 0.4h | 1 | 0 | 🟢 |
| `fitness_weekly` | 0.3h | 1 | 0 | 🟢 |
| `governance_dashboard_regen` | 0.3h | 1 | 0 | 🟢 |
| `process_reminders` | 0.1h | 30 | 0 | 🟢 |
| `health_check_broadcast` | 0.1h | 30 | 0 | 🟢 |
| `kg_metrics_refresh` | 0.1h | 11 | 0 | 🟢 |
| `memory_metrics_refresh` | 0.1h | 11 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 31 | 0 | 🟢 |
| `daily_self_retrospective` | 0.0h | 1 | 0 | 🟢 |

**統計**：18 個近期活躍 cron / 18 GREEN / 0 YELLOW / 0 RED（完整對賬見 scheduler_liveness_audit）

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
| 02:45:02 | `daily_self_retrospective` | ✅ success | 2248ms |
| 02:42:22 | `tender_dashboard_warm` | ✅ success | 1ms |
| 02:42:20 | `memory_metrics_refresh` | ✅ success | 970ms |
| 02:42:17 | `kg_metrics_refresh` | ✅ success | 18ms |
| 02:42:07 | `health_check_broadcast` | ✅ success | 21ms |
| 02:42:07 | `process_reminders` | ✅ success | 16ms |
| 02:37:28 | `tender_dashboard_warm` | ✅ success | 5974ms |
| 02:37:07 | `health_check_broadcast` | ✅ success | 51ms |
| 02:37:07 | `process_reminders` | ✅ success | 38ms |
| 02:32:22 | `tender_dashboard_warm` | ✅ success | 1ms |

**統計** (最近 30 個事件): 30 成功 / 0 失敗 / 失敗率 0.0%

## 10. Owner action 待辦 (不可委任)

- 跨 repo install-template 對 2 RED 子專案套用 (詳 §9)
- `CK_KMapAdvisor/CLAUDE.md` 已 123 天未更新
- `shared-modules/CLAUDE.md` 已 101 天未更新
- `FT_StorageTank/CLAUDE.md` 已 60 天未更新

> 其餘待決事項**不在這裡維護第二份清單** —— 單一入口是
> [`OPEN_ITEMS_20260819.md`](OPEN_ITEMS_20260819.md)（A 段＝需 owner 決定）。
> 2026-08-27 起本段只印算得出來的；寫死的字串已移除，
> 理由是它們在被發現前已經錯了 89 天而每天照印。

---

## 整合視角結論

> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。
> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。
> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`