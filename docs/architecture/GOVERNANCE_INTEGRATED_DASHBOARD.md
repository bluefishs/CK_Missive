# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-05-30 15:54:42
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
| Fitness checks | 82 | `scripts/checks/*.py` |
| Architecture docs | 54 | `docs/architecture/*.md` |
| **Total** | **192** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                   3.8
  governance_lessons_l4x_family_count                         8.0
  governance_lessons_total                                   24.0
  governance_pipeline_red_consecutive_days                   10.0
  governance_wiki_freshness_hours                             0.9
  governance_wiki_pages_total                               362.0
  kg_entities_total                                       24535.0
  memory_crystals_total                                       0.0
  memory_diary_days_total                                    39.0
  scheduler_job_success_total                                15.0
  shadow_baseline_rows_total                                  7.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             18.2
  v7_soul_drift_lines                                         0.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `8aec4d78 feat(governance): 程式圖譜+wiki 對應規範現況 fitness step 63 + 補 l43/l44/l45 stale lesson`
- `12ae5d7e refactor(facade): caller +3 補強 60 天 trial 達標 healthy ≥3`
- `36351cc4 docs(governance): l53 lesson + adr-0036 superseded by b 方案 (60 天 trial)`
- `d0d24639 refactor(contracts): b 方案 facade 13→3 收口 + ports 4→2 (l31 roi)`
- `4bd27997 feat(governance): l52 lesson + paths/compose mount audit step 62`
- `8842e8a2 fix(L51.7): shadow_baseline 真活恢復 — mount target drift + token env fallback`
- `7023b971 feat(governance): cron silent dormant 偵測 — prometheus expose + fitness daily step 7`
- `0851bf64 feat(governance): wiki metric export + metric() endpoint health + facade ABC decision`

## 4. 最近 5 session 覆盤 (memory/)

- session_20260530_v6_12_governance_4principles.md
- session_20260528_l49_family_closure_pre_reboot.md
- session_20260527_continuation_loop_sweep.md
- session_20260527_v6_11_complete_pre_reboot.md
- session_20260526_27_8_root_causes_complete.md

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

## 9. Owner action 待辦 (不可委任)

- ADR-0020 + ADR-0035 proposed 收斂
- 4 pending crystal 審批 (`/admin/crystals`)
- Hermes GO/NO-GO baseline 重評
- CK_KMapAdvisor CLAUDE.md STALE 32 天 (跨 repo)
- Task Scheduler 重建 / sync_enabled=true

---

## 整合視角結論

> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。
> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。
> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`