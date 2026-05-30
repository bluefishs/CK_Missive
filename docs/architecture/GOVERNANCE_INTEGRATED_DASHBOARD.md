# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-05-30 23:49:08
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
| Fitness checks | 88 | `scripts/checks/*.py` |
| Architecture docs | 65 | `docs/architecture/*.md` |
| **Total** | **201** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  11.8
  governance_lessons_l4x_family_count                         0.0
  governance_lessons_total                                   16.0
  governance_pipeline_red_consecutive_days                   10.0
  governance_wiki_freshness_hours                             0.1
  governance_wiki_pages_total                               369.0
  kg_entities_total                                       24535.0
  memory_crystals_total                                       0.0
  memory_diary_days_total                                    39.0
  scheduler_job_success_total{job_id="health_check_broadcast"}          7.0
  scheduler_job_success_total{job_id="process_reminders"}          7.0
  scheduler_job_success_total{job_id="tender_dashboard_warm"}          8.0
  shadow_baseline_call_total{provider="gemma-hermes"}          3.0
  shadow_baseline_call_total{provider="gemma-local"}         10.0
  shadow_baseline_latency_p95_ms{provider="gemma-hermes"}      43746.0
  shadow_baseline_latency_p95_ms{provider="gemma-local"}      71226.0
  shadow_baseline_rows_total{lookback_hours="24"}            13.0
  shadow_baseline_success_ratio{provider="gemma-hermes"}          1.0
  shadow_baseline_success_ratio{provider="gemma-local"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="get_statistics"}          3.0
  shadow_baseline_tool_use_count{provider="gemma-hermes",tool="search_documents"}          1.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="get_statistics"}          4.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_across_graphs"}          2.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_documents"}          6.0
  shadow_baseline_tool_use_count{provider="gemma-local",tool="search_entities"}          2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             17.9
  v7_soul_drift_lines                                         0.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `2564543e feat(governance): lesson 命名分流 universal/missive-specific + .template-policy.yml.example`
- `d9a85d4c fix(ai): p0 p95 ollama keep_alive 24h 解 cold start (71s → 40s, -44%)`
- `08b2d089 feat(governance): install-template --tier flag (l58 配套分級 + opt-out 機制)`
- `73add1bf docs(retro): 5/30 核心議題覆盤統整 (owner 三段執行第 3 段)`
- `d368720f docs(meta): l60 結構正常化 lesson + pilemgmt r18 反治理真活驗證`
- `db405433 fix(scheduler): w1 #2 移除 shadow_baseline_export cron (對齊 l59 自我優先)`
- `6edc1252 docs(meta): l59 治理架構倒置 + 平衡策略 (owner 兩日連續反思第 3 案)`
- `48d63b3d docs(meta): l58 治理範本污染風險 — owner 反思最深刻 lesson (第 6 句立法)`

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

- ⚠ Pipeline 連續 10 天 RED (> 3 天門檻)

## 8.5 Hermes Baseline GO/NO-GO 5 條件 (Sprint 3.P3.15)

| # | 條件 | 門檻 | 現況 | 達標 |
|---|---|---|---|---|
| 1 | baseline rows | ≥ 30 | 13 | ❌ |
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