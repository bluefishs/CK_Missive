# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-05-31 09:08:34
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 0 | `wiki/memory/lessons/L*.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 91 | `scripts/checks/*.py` |
| Architecture docs | 73 | `docs/architecture/*.md` |
| **Total** | **212** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                   6.0
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                   11.0
  governance_wiki_freshness_hours                             0.0
  governance_wiki_pages_total                               374.0
  kg_entities_total                                       21378.0
  memory_crystals_total                                       0.0
  memory_diary_days_total                                    40.0
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        151.4
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        151.4
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        136.5
  scheduler_job_success_created{job_id="health_check_broadcast"} 1780189562.8
  scheduler_job_success_created{job_id="process_reminders"} 1780189562.8
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1780189287.7
  scheduler_job_success_total{job_id="health_check_broadcast"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}          1.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}          2.0
  shadow_baseline_call_total{provider="gemma-hermes"}          3.0
  shadow_baseline_call_total{provider="gemma-local"}         13.0
  shadow_baseline_latency_p95_ms{provider="gemma-hermes"}      43746.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      71226.0
  shadow_baseline_rows_total{lookback_hours="24"}            16.0
  shadow_baseline_success_ratio{provider="gemma-hermes"}          1.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="get_statistics"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="search_documents"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}          5.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}          7.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             16.7
  v7_soul_drift_lines                                         0.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `336343d5 feat(scheduler): cron 06:00/06:30 → 02:30/02:45 凌晨化 + dashboard §9.5 cron 統計 + 前端頁面規劃`
- `94132f4e fix(scheduler): misfire_grace_time 7200s 防 cron silent dormant + 優先作業機制總表`
- `d28aefd9 docs(retro): 5/30-31 兩日整合覆盤 + v6.13 自我覆盤進化目標 6 維度`
- `187fed47 docs(retro): kg 歷程議題 + 整合應用架構藍圖 (5 階段+6 階段)`
- `560848ad fix(line): line bot 超時 25→28s (owner 報「查詢處理時間較長」)`
- `984fc780 feat(sync): erp ingest + dedup 強化 5 層備份 (對齊 owner 備份安全訴求)`
- `1908b54e feat(governance): effectiveness report + knowledge dedup script (owner approved)`
- `e463c087 feat(governance): step 71 cross-domain link + step 72 knowledge dedup audit`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260530_v6_12_meta_governance_day.md
- session_20260530_v6_12_full_day.md
- session_20260530_v6_12_governance_4principles.md
- session_20260528_l49_family_closure_pre_reboot.md
- session_20260527_continuation_loop_sweep.md

## 5. Facade B 方案 60 天 trial 進度 (重評日 2026-07-30)

| Facade | 現 caller | 60 天目標 | 達標 |
|---|---|---|---|
| IntegrationFacade | 3 | ≥5 | 🟡 |
| MemoryFacade | 3 | ≥5 | 🟡 |
| WikiFacade | 3 | ≥3 | ✅ |

## 6. Lesson 索引 (L4x family 為主)


## 7. v6.12 進化 4 原則狀態

| # | 原則 | 落地證據 | 狀態 |
|---|---|---|---|
| #1 | 修法掃全範圍 audit | fitness step 60 container image freshness | ✅ |
| #2 | observability 分層 forcing | Tier 1 daily 7 + Tier 2 weekly 14 + Tier 3 monthly | ✅ |
| #3 | 治理本身 metric 化 | 7 governance_* gauge + scheduler_job_* | ✅ |
| #4 | 元覆盤 cron | daily_self_retrospective 7 aspects (06:30) | ✅ |

## 8. 漂移看板 (audit 結果統一)

- ⚠ Pipeline 連續 11 天 RED (> 3 天門檻)

## 8.5 Hermes Baseline GO/NO-GO 5 條件 (Sprint 3.P3.15)

| # | 條件 | 門檻 | 現況 | 達標 |
|---|---|---|---|---|
| 1 | baseline rows | ≥ 30 | 16 | ❌ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 71.2s | ❌ |
| **Summary** | — | — | **1/5** | **🔴 NO-GO** |

詳見 `docs/architecture/HERMES_BASELINE_RESET_PLAN_20260530.md`

## 9. 跨 repo 範本漂移 (4 子專案 v6.12 治理採用度)

| Repo | 跟進度 | Verdict | 修法建議 |
|---|---|---|---|
| CK_lvrland_Webmap | 6/6 | 🟢 GREEN | — |
| CK_PileMgmt | 0/6 | 🔴 RED-zero | `install-template-to.sh` |
| CK_Showcase | 6/6 | 🟢 GREEN | — |
| CK_KMapAdvisor | 6/6 | 🟢 GREEN | — |

⚠ **1/4 子專案 RED** — 範本對外採用度不足，owner approve 後執行:
```bash
bash scripts/install-template-to.sh ../<repo_name> \
  --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons
```

## 9.5 Cron 排程真活全表 (事件追溯依據)

**所有 47 cron 真活狀態**（從 `/metrics scheduler_job_*` 即時抓）：

| Job ID | Age | Success | Failure | 狀態 |
|---|---|---|---|---|
| `process_reminders` | 0.0h | 1 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 1 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 2 | 0 | 🟢 |

**統計**：3 真活 cron / 3 GREEN / 0 YELLOW / 0 RED

**凌晨低干擾排程設計（v6.13）**：
- 02:00 fitness_daily / 02:30 dashboard_regen / 02:45 self_retrospective
- 03:00 optimization_pipeline / 03:35 db_schema
- 避開 06:00-22:00 用戶活躍時段 + 早報推播

**事件追溯**：每 scheduler tracker 含 `last_run` / `last_status` / `last_duration_ms` / `last_error`

## 10. Owner action 待辦 (不可委任)

- ADR-0020 + ADR-0035 proposed 收斂
- 4 pending crystal 審批 (`/admin/crystals`)
- Hermes GO/NO-GO baseline 重評
- 跨 repo install-template 對 1 RED 子專案套用 (詳 §9)
- CK_KMapAdvisor CLAUDE.md STALE 32 天
- Task Scheduler 重建 / sync_enabled=true

---

## 整合視角結論

> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。
> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。
> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`