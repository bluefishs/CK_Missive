# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-06-04 02:30:00
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 0 | `wiki/memory/lessons/L*.md` |
| SOPs | 0 | `.claude/rules/*.md` |
| Fitness checks | 96 | `scripts/checks/*.py` |
| Architecture docs | 81 | `docs/architecture/*.md` |
| **Total** | **212** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  23.5
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             6.3
  governance_wiki_pages_total                               392.0
  kg_entities_total                                       26401.0
  memory_crystals_total                                       2.0
  memory_diary_days_total                                    43.0
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       1053.4
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        155.3
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}       1487.7
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       1051.2
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}       7198.9
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        155.3
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        140.3
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1780506760.4
  scheduler_job_success_created{job_id="health_check_broadcast"} 1780503445.0
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1780509912.6
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1780510349.2
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1780504201.4
  scheduler_job_success_created{job_id="process_reminders"} 1780503445.0
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1780503160.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}          2.0
  scheduler_job_success_total{job_id="health_check_broadcast"}         27.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          1.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}          1.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          1.0
  scheduler_job_success_total{job_id="process_reminders"}         27.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}         28.0
  shadow_baseline_call_total{provider="gemma-hermes"}          1.0
  shadow_baseline_call_total{provider="gemma-local"}         54.0
  shadow_baseline_call_total{provider="unknown"}              3.0
  shadow_baseline_latency_p95_ms{provider="gemma-hermes"}       4757.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      71352.0
  shadow_baseline_latency_p95_ms{provider="unknown"}      30888.0
  shadow_baseline_rows_total{lookback_hours="24"}            58.0
  shadow_baseline_success_ratio{provider="gemma-hermes"}          1.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_success_ratio{provider="unknown"}           1.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="get_statistics"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="find_correspondence"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         19.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="navigate_graph"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          5.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         15.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="summarize_entity"}          1.0
  shadow_baseline_tool_use_count{provider="unknown",tool="get_statistics"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             15.4
  v7_soul_drift_lines                                        -1.0
```

## 3. 最近 8 commits (進化執行軌跡)


## 4. 最近 5 session 覆盤 (memory/)


## 5. Facade B 方案 60 天 trial 進度 (重評日 2026-07-30)

| Facade | 現 caller | 60 天目標 | 達標 |
|---|---|---|---|
| IntegrationFacade | ? | ≥5 | 🔴 |
| MemoryFacade | ? | ≥5 | 🔴 |
| WikiFacade | ? | ≥3 | 🔴 |

## 6. Lesson 索引 (L4x family 為主)


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
| 1 | baseline rows | ≥ 30 | 58 | ✅ |
| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |
| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |
| 4 | error rate | < 5% | 1.2% | ✅ |
| 5 | p95 latency | < 8s | 71.4s | ❌ |
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
| `proactive_trigger_scan` | 2.0h | 1 | 0 | 🟢 |
| `integration_e2e_validation` | 0.4h | 1 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.3h | 2 | 0 | 🟢 |
| `pcc_today_scrape` | 0.3h | 1 | 0 | 🟢 |
| `process_reminders` | 0.0h | 27 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 27 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 28 | 0 | 🟢 |

**統計**：7 真活 cron / 7 GREEN / 0 YELLOW / 0 RED

**凌晨低干擾排程設計（v6.13）**：
- 02:00 fitness_daily / 02:30 dashboard_regen / 02:45 self_retrospective
- 03:00 optimization_pipeline / 03:35 db_schema
- 避開 06:00-22:00 用戶活躍時段 + 早報推播

**事件追溯**：每 scheduler tracker 含 `last_run` / `last_status` / `last_duration_ms` / `last_error`

## 9.6 Cron 執行歷史摘要 (jsonl event log)

**事件 log**：`backend/logs/cron_events.jsonl` (跨 backend restart 持久化)

⚪ cron_events.jsonl 不存在（待 backend rebuild 後 SchedulerTracker._append_event 啟動）

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