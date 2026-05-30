# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-05-30 19:25:24
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 8 | `wiki/memory/lessons/L*.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 84 | `scripts/checks/*.py` |
| Architecture docs | 56 | `docs/architecture/*.md` |
| **Total** | **196** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                   7.4
  governance_lessons_l4x_family_count                         8.0
  governance_lessons_total                                   24.0
  governance_pipeline_red_consecutive_days                   10.0
  governance_wiki_freshness_hours                             1.7
  governance_wiki_pages_total                               362.0
  kg_entities_total                                       24535.0
  memory_crystals_total                                       0.0
  memory_diary_days_total                                    39.0
  scheduler_job_success_total                                22.0
  shadow_baseline_rows_total                                  2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             16.7
  v7_soul_drift_lines                                         0.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `ba59b020 fix(L51): google_client_id/secret env 注入 (fitness step 1 RED → GREEN)`
- `ec6f65a4 docs(governance): cross-repo install-template 預覽報告供 owner 決策`
- `b2d10d94 feat(governance): dashboard §9 整合跨 repo 漂移摘要 (對齊 step 65)`
- `43f30cb2 feat(governance): cross-repo template drift audit step 65 + adr parser regex fix`
- `0ca34a07 docs(governance): reference for other systems + install-template v6.12 補完 4 新類別`
- `ba82e8fe feat(governance): session-start hook 接 dashboard + fitness step 64 freshness 防 cron silent fail`
- `5c9e012c fix(contracts): adapters/__init__.py 對齊 b 方案 (移除 audit/cache import)`
- `9ec7c8d6 feat(scheduler): governance dashboard regen cron 每日 06:00 (整合 ssot 接通)`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260530_v6_12_full_day.md
- session_20260530_v6_12_governance_4principles.md
- session_20260528_l49_family_closure_pre_reboot.md
- session_20260527_continuation_loop_sweep.md
- session_20260527_v6_11_complete_pre_reboot.md

## 5. Facade B 方案 60 天 trial 進度 (重評日 2026-07-30)

| Facade | 現 caller | 60 天目標 | 達標 |
|---|---|---|---|
| IntegrationFacade | 3 | ≥5 | 🟡 |
| MemoryFacade | 3 | ≥5 | 🟡 |
| WikiFacade | 3 | ≥3 | ✅ |

## 6. Lesson 索引 (L4x family 為主)

- **L41** — jwt secret drift silent fail
- **L43** — volume mount drift silent fail
- **L44** — sso session lock cross subdomain
- **L45** — compose dockerfile healthcheck drift
- **L49** — container host dependency family
- **L50** — multi source identifier link
- **L52** — paths compose mount drift
- **L53** — facade over engineering 30day pruning

## 7. v6.12 進化 4 原則狀態

| # | 原則 | 落地證據 | 狀態 |
|---|---|---|---|
| #1 | 修法掃全範圍 audit | fitness step 60 container image freshness | ✅ |
| #2 | observability 分層 forcing | Tier 1 daily 7 + Tier 2 weekly 14 + Tier 3 monthly | ✅ |
| #3 | 治理本身 metric 化 | 7 governance_* gauge + scheduler_job_* | ✅ |
| #4 | 元覆盤 cron | daily_self_retrospective 7 aspects (06:30) | ✅ |

## 8. 漂移看板 (audit 結果統一)

- ⚠ Pipeline 連續 10 天 RED (> 3 天門檻)

## 9. 跨 repo 範本漂移 (4 子專案 v6.12 治理採用度)

| Repo | 跟進度 | Verdict | 修法建議 |
|---|---|---|---|
| CK_lvrland_Webmap | 6/6 | 🟢 GREEN | — |
| CK_PileMgmt | 6/6 | 🟢 GREEN | — |
| CK_Showcase | 6/6 | 🟢 GREEN | — |
| CK_KMapAdvisor | 6/6 | 🟢 GREEN | — |


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