# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-06-09 02:30:00
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
  governance_fitness_report_freshness_hours                  23.3
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                    0.0
  governance_wiki_freshness_hours                             6.2
  governance_wiki_pages_total                               408.0
  kg_entities_total                                       26578.0
  memory_crystals_total                                       2.0
  memory_diary_days_total                                    48.0
  scheduler_job_last_run_age_seconds{job_id="agent_self_diagnosis"}      73194.4
  scheduler_job_last_run_age_seconds{job_id="cf_tunnel_verify"}      72900.4
  scheduler_job_last_run_age_seconds{job_id="code_graph_incremental"}      84596.2
  scheduler_job_last_run_age_seconds{job_id="critique_health_audit"}     173699.4
  scheduler_job_last_run_age_seconds{job_id="cron_outcome_freshness"}      70200.1
  scheduler_job_last_run_age_seconds{job_id="cron_self_health_alert"}      72000.4
  scheduler_job_last_run_age_seconds{job_id="crystal_review_overdue"}     147600.4
  scheduler_job_last_run_age_seconds{job_id="daily_self_reflection_line_push"}      16200.4
  scheduler_job_last_run_age_seconds{job_id="daily_self_retrospective"}      85498.3
  scheduler_job_last_run_age_seconds{job_id="db_graph_refresh"}      82499.8
  scheduler_job_last_run_age_seconds{job_id="embedding_warmup"}      78291.1
  scheduler_job_last_run_age_seconds{job_id="erp_graph_ingest"}      82800.2
  scheduler_job_last_run_age_seconds{job_id="ezbid_cache_refresh"}       2570.2
  scheduler_job_last_run_age_seconds{job_id="fitness_weekly"}     172791.8
  scheduler_job_last_run_age_seconds{job_id="governance_dashboard_regen"}      86399.6
  scheduler_job_last_run_age_seconds{job_id="health_check_broadcast"}        175.5
  scheduler_job_last_run_age_seconds{job_id="health_snapshot_log"}      73500.4
  scheduler_job_last_run_age_seconds{job_id="integration_e2e_validation"}       1487.7
  scheduler_job_last_run_age_seconds{job_id="kb_coverage_check"}      81000.3
  scheduler_job_last_run_age_seconds{job_id="kg_embedding_backfill"}      79200.4
  scheduler_job_last_run_age_seconds{job_id="kunge_weekly_learning_summary"}     142200.0
  scheduler_job_last_run_age_seconds{job_id="ledger_reconciliation"}      77399.8
  scheduler_job_last_run_age_seconds{job_id="line_weekly_pulse"}     145800.2
  scheduler_job_last_run_age_seconds{job_id="llm_quota_check"}      20575.1
  scheduler_job_last_run_age_seconds{job_id="memory_anti_echo_scan"}      73800.3
  scheduler_job_last_run_age_seconds{job_id="memory_crystallization_scan"}      78900.3
  scheduler_job_last_run_age_seconds{job_id="memory_pattern_extract"}      80700.3
  scheduler_job_last_run_age_seconds{job_id="memory_weekly_autobiography"}     116986.6
  scheduler_job_last_run_age_seconds{job_id="morning_report"}      66578.3
  scheduler_job_last_run_age_seconds{job_id="optimization_pipeline"}      84568.0
  scheduler_job_last_run_age_seconds{job_id="pcc_today_scrape"}       6174.9
  scheduler_job_last_run_age_seconds{job_id="proactive_trigger_scan"}       7198.1
  scheduler_job_last_run_age_seconds{job_id="process_reminders"}        175.5
  scheduler_job_last_run_age_seconds{job_id="proposal_aging_alert"}     173400.1
  scheduler_job_last_run_age_seconds{job_id="soul_mirror_sync"}      78000.4
  scheduler_job_last_run_age_seconds{job_id="synthetic_baseline_inject"}      23164.0
  scheduler_job_last_run_age_seconds{job_id="tender_business_recommend"}      63000.3
  scheduler_job_last_run_age_seconds{job_id="tender_dashboard_warm"}        160.2
  scheduler_job_last_run_age_seconds{job_id="tender_pcc_enrichment"}      82580.2
  scheduler_job_last_run_age_seconds{job_id="tender_refresh_pending"}      73790.8
  scheduler_job_last_run_age_seconds{job_id="tender_subscription"}      30599.8
  scheduler_job_last_run_age_seconds{job_id="weekly_evolution_generator"}     174558.4
  scheduler_job_last_run_age_seconds{job_id="wiki_compile"}      77395.3
  scheduler_job_last_run_age_seconds{job_id="wiki_lint"}      75599.5
  scheduler_job_success_created{job_id="agent_self_diagnosis"} 1780611005.8
  scheduler_job_success_created{job_id="cf_tunnel_verify"} 1780611300.0
  scheduler_job_success_created{job_id="code_graph_incremental"} 1780599604.3
  scheduler_job_success_created{job_id="critique_health_audit"} 1780769701.0
  scheduler_job_success_created{job_id="cron_outcome_freshness"} 1780614000.5
  scheduler_job_success_created{job_id="cron_self_health_alert"} 1780612200.0
  scheduler_job_success_created{job_id="crystal_review_overdue"} 1780795800.0
  scheduler_job_success_created{job_id="daily_self_reflection_line_push"} 1780668000.0
  scheduler_job_success_created{job_id="daily_self_retrospective"} 1780685102.2
  scheduler_job_success_created{job_id="db_graph_refresh"} 1780601700.4
  scheduler_job_success_created{job_id="embedding_warmup"} 1780605907.9
  scheduler_job_success_created{job_id="erp_graph_ingest"} 1780601400.9
  scheduler_job_success_created{job_id="ezbid_cache_refresh"} 1780602426.3
  scheduler_job_success_created{job_id="fitness_weekly"} 1780770608.6
  scheduler_job_success_created{job_id="governance_dashboard_regen"} 1780684200.8
  scheduler_job_success_created{job_id="health_check_broadcast"} 1780599124.8
  scheduler_job_success_created{job_id="health_snapshot_log"} 1780610700.0
  scheduler_job_success_created{job_id="integration_e2e_validation"} 1780682712.7
  scheduler_job_success_created{job_id="kb_coverage_check"} 1780603200.0
  scheduler_job_success_created{job_id="kg_embedding_backfill"} 1780605000.0
  scheduler_job_success_created{job_id="kunge_weekly_learning_summary"} 1780801200.4
  scheduler_job_success_created{job_id="ledger_reconciliation"} 1780606800.1
  scheduler_job_success_created{job_id="line_weekly_pulse"} 1780797600.2
  scheduler_job_success_created{job_id="llm_quota_check"} 1780620424.9
  scheduler_job_success_created{job_id="memory_anti_echo_scan"} 1780869600.1
  scheduler_job_success_created{job_id="memory_crystallization_scan"} 1780605300.1
  scheduler_job_success_created{job_id="memory_pattern_extract"} 1780603500.0
  scheduler_job_success_created{job_id="memory_weekly_autobiography"} 1780826413.8
  scheduler_job_success_created{job_id="morning_report"} 1780617613.7
  scheduler_job_success_created{job_id="optimization_pipeline"} 1780599632.2
  scheduler_job_success_created{job_id="pcc_today_scrape"} 1780606026.6
  scheduler_job_success_created{job_id="proactive_trigger_scan"} 1780677001.7
  scheduler_job_success_created{job_id="process_reminders"} 1780599124.8
  scheduler_job_success_created{job_id="proposal_aging_alert"} 1780770000.3
  scheduler_job_success_created{job_id="soul_mirror_sync"} 1780606200.0
  scheduler_job_success_created{job_id="synthetic_baseline_inject"} 1780621378.1
  scheduler_job_success_created{job_id="tender_business_recommend"} 1780621201.0
  scheduler_job_success_created{job_id="tender_dashboard_warm"} 1780598839.8
  scheduler_job_success_created{job_id="tender_pcc_enrichment"} 1780601593.2
  scheduler_job_success_created{job_id="tender_refresh_pending"} 1780610419.5
  scheduler_job_success_created{job_id="tender_subscription"} 1780617600.5
  scheduler_job_success_created{job_id="weekly_evolution_generator"} 1780768841.9
  scheduler_job_success_created{job_id="wiki_compile"} 1780866005.1
  scheduler_job_success_created{job_id="wiki_lint"}  1780608600.9
  scheduler_job_success_total{job_id="agent_self_diagnosis"}          4.0
  scheduler_job_success_total{job_id="cf_tunnel_verify"}          4.0
  scheduler_job_success_total{job_id="code_graph_incremental"}          4.0
  scheduler_job_success_total{job_id="critique_health_audit"}          1.0
  scheduler_job_success_total{job_id="cron_outcome_freshness"}          4.0
  scheduler_job_success_total{job_id="cron_self_health_alert"}          4.0
  scheduler_job_success_total{job_id="crystal_review_overdue"}          1.0
  scheduler_job_success_total{job_id="daily_self_reflection_line_push"}          4.0
  scheduler_job_success_total{job_id="daily_self_retrospective"}          3.0
  scheduler_job_success_total{job_id="db_graph_refresh"}          4.0
  scheduler_job_success_total{job_id="embedding_warmup"}          4.0
  scheduler_job_success_total{job_id="erp_graph_ingest"}          4.0
  scheduler_job_success_total{job_id="ezbid_cache_refresh"}         95.0
  scheduler_job_success_total{job_id="fitness_weekly"}          1.0
  scheduler_job_success_total{job_id="governance_dashboard_regen"}          3.0
  scheduler_job_success_total{job_id="health_check_broadcast"}       1147.0
  scheduler_job_success_total{job_id="health_snapshot_log"}          4.0
  scheduler_job_success_total{job_id="integration_e2e_validation"}          4.0
  scheduler_job_success_total{job_id="kb_coverage_check"}          4.0
  scheduler_job_success_total{job_id="kg_embedding_backfill"}          4.0
  scheduler_job_success_total{job_id="kunge_weekly_learning_summary"}          1.0
  scheduler_job_success_total{job_id="ledger_reconciliation"}          4.0
  scheduler_job_success_total{job_id="line_weekly_pulse"}          1.0
  scheduler_job_success_total{job_id="llm_quota_check"}         15.0
  scheduler_job_success_total{job_id="memory_anti_echo_scan"}          1.0
  scheduler_job_success_total{job_id="memory_crystallization_scan"}          4.0
  scheduler_job_success_total{job_id="memory_pattern_extract"}          4.0
  scheduler_job_success_total{job_id="memory_weekly_autobiography"}          1.0
  scheduler_job_success_total{job_id="morning_report"}          4.0
  scheduler_job_success_total{job_id="optimization_pipeline"}          4.0
  scheduler_job_success_total{job_id="pcc_today_scrape"}         47.0
  scheduler_job_success_total{job_id="proactive_trigger_scan"}          4.0
  scheduler_job_success_total{job_id="process_reminders"}       1147.0
  scheduler_job_success_total{job_id="proposal_aging_alert"}          1.0
  scheduler_job_success_total{job_id="soul_mirror_sync"}          4.0
  scheduler_job_success_total{job_id="synthetic_baseline_inject"}         12.0
  scheduler_job_success_total{job_id="tender_business_recommend"}          4.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}       1149.0
  scheduler_job_success_total{job_id="tender_pcc_enrichment"}          4.0
  scheduler_job_success_total{job_id="tender_refresh_pending"}          4.0
  scheduler_job_success_total{job_id="tender_subscription"}         12.0
  scheduler_job_success_total{job_id="weekly_evolution_generator"}          1.0
  scheduler_job_success_total{job_id="wiki_compile"}          1.0
  scheduler_job_success_total{job_id="wiki_lint"}             4.0
  shadow_baseline_call_total{provider="gemma-hermes"}          1.0
  shadow_baseline_call_total{provider="gemma-local"}         58.0
  shadow_baseline_call_total{provider="unknown"}              3.0
  shadow_baseline_latency_p95_ms{provider="gemma-hermes"}       4757.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      48262.0
  shadow_baseline_latency_p95_ms{provider="unknown"}      30888.0
  shadow_baseline_rows_total{lookback_hours="24"}            58.0
  shadow_baseline_success_ratio{provider="gemma-hermes"}          1.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_success_ratio{provider="unknown"}           1.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="get_statistics"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="draw_diagram"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="find_correspondence"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_entity_detail"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_expense_overview"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_financial_summary"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}         14.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_unpaid_billings"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_dispatch_orders"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}         21.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          7.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_projects"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_tender"}          1.0
  shadow_baseline_tool_use_count{provider="unknown",tool="get_statistics"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                         100.0
  v7_reference_density_diary_pct                             13.3
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
| 4 | error rate | < 5% | 0.0% | ✅ |
| 5 | p95 latency | < 8s | 48.3s | ❌ |
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
| `weekly_evolution_generator` | 48.5h | 1 | 0 | 🔴 |
| `critique_health_audit` | 48.2h | 1 | 0 | 🔴 |
| `proposal_aging_alert` | 48.2h | 1 | 0 | 🔴 |
| `fitness_weekly` | 48.0h | 1 | 0 | 🟡 |
| `crystal_review_overdue` | 41.0h | 1 | 0 | 🟡 |
| `line_weekly_pulse` | 40.5h | 1 | 0 | 🟡 |
| `kunge_weekly_learning_summary` | 39.5h | 1 | 0 | 🟡 |
| `memory_weekly_autobiography` | 32.5h | 1 | 0 | 🟡 |
| `governance_dashboard_regen` | 24.0h | 3 | 0 | 🟢 |
| `daily_self_retrospective` | 23.7h | 3 | 0 | 🟢 |
| `code_graph_incremental` | 23.5h | 4 | 0 | 🟢 |
| `optimization_pipeline` | 23.5h | 4 | 0 | 🟢 |
| `erp_graph_ingest` | 23.0h | 4 | 0 | 🟢 |
| `tender_pcc_enrichment` | 22.9h | 4 | 0 | 🟢 |
| `db_graph_refresh` | 22.9h | 4 | 0 | 🟢 |
| `kb_coverage_check` | 22.5h | 4 | 0 | 🟢 |
| `memory_pattern_extract` | 22.4h | 4 | 0 | 🟢 |
| `kg_embedding_backfill` | 22.0h | 4 | 0 | 🟢 |
| `memory_crystallization_scan` | 21.9h | 4 | 0 | 🟢 |
| `embedding_warmup` | 21.7h | 4 | 0 | 🟢 |
| `soul_mirror_sync` | 21.7h | 4 | 0 | 🟢 |
| `ledger_reconciliation` | 21.5h | 4 | 0 | 🟢 |
| `wiki_compile` | 21.5h | 1 | 0 | 🟢 |
| `wiki_lint` | 21.0h | 4 | 0 | 🟢 |
| `memory_anti_echo_scan` | 20.5h | 1 | 0 | 🟢 |
| `tender_refresh_pending` | 20.5h | 4 | 0 | 🟢 |
| `health_snapshot_log` | 20.4h | 4 | 0 | 🟢 |
| `agent_self_diagnosis` | 20.3h | 4 | 0 | 🟢 |
| `cf_tunnel_verify` | 20.3h | 4 | 0 | 🟢 |
| `cron_self_health_alert` | 20.0h | 4 | 0 | 🟢 |
| `cron_outcome_freshness` | 19.5h | 4 | 0 | 🟢 |
| `morning_report` | 18.5h | 4 | 0 | 🟢 |
| `tender_business_recommend` | 17.5h | 4 | 0 | 🟢 |
| `tender_subscription` | 8.5h | 12 | 0 | 🟢 |
| `synthetic_baseline_inject` | 6.4h | 12 | 0 | 🟢 |
| `llm_quota_check` | 5.7h | 15 | 0 | 🟢 |
| `daily_self_reflection_line_push` | 4.5h | 4 | 0 | 🟢 |
| `proactive_trigger_scan` | 2.0h | 4 | 0 | 🟢 |
| `pcc_today_scrape` | 1.7h | 47 | 0 | 🟢 |
| `ezbid_cache_refresh` | 0.7h | 95 | 0 | 🟢 |
| `integration_e2e_validation` | 0.4h | 4 | 0 | 🟢 |
| `process_reminders` | 0.0h | 1147 | 0 | 🟢 |
| `health_check_broadcast` | 0.0h | 1147 | 0 | 🟢 |
| `tender_dashboard_warm` | 0.0h | 1149 | 0 | 🟢 |

**統計**：44 真活 cron / 36 GREEN / 5 YELLOW / 3 RED

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