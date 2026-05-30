# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT

> **Generated**: 2026-05-30 22:32:15
> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)
> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照
> **生成器**: `scripts/checks/generate_governance_dashboard.py`

---

## 1. 規範清單盤點

| 類別 | 數量 | 位置 |
|---|---|---|
| ADR | active=21 / archived=14 | `docs/adr/` |
| Lessons | 12 | `wiki/memory/lessons/L*.md` |
| SOPs | 13 | `.claude/rules/*.md` |
| Fitness checks | 88 | `scripts/checks/*.py` |
| Architecture docs | 64 | `docs/architecture/*.md` |
| **Total** | **212** | 5 處散落 |

## 2. 現況真活 metric (從 /metrics 即時抓)

```
  governance_fitness_report_freshness_hours                  10.5
  governance_lessons_l4x_family_count                        12.0
  governance_lessons_total                                   28.0
  governance_pipeline_red_consecutive_days                   10.0
  governance_wiki_freshness_hours                             0.2
  governance_wiki_pages_total                               366.0
  kg_entities_total                                       24535.0
  memory_crystals_total                                       0.0
  memory_diary_days_total                                    39.0
  scheduler_job_success_total                                 2.0
  shadow_baseline_rows_total                                  2.0
  v7_channel_diversity                                        1.0
  v7_reference_density_critique_pct                           0.0
  v7_reference_density_diary_pct                             25.0
  v7_soul_drift_lines                                         0.0
```

## 3. 最近 8 commits (進化執行軌跡)

- `db405433 fix(scheduler): w1 #2 移除 shadow_baseline_export cron (對齊 l59 自我優先)`
- `6edc1252 docs(meta): l59 治理架構倒置 + 平衡策略 (owner 兩日連續反思第 3 案)`
- `48d63b3d docs(meta): l58 治理範本污染風險 — owner 反思最深刻 lesson (第 6 句立法)`
- `b5f19826 docs(governance): l57 lesson + step 69 paths sub-path mount audit (l4x family 9 案)`
- `5ca1d720 fix(shadow): 真因 #4 — l52 family 第七案 shadow_trace.db path 漂移 (l51 同型)`
- `a5a2328c fix(shadow): hermes baseline 真因 #1 populate gauge 重複註冊 + 3 重真因報告`
- `2b1d2ab7 feat(governance): sprint 3.p3.14/p3.15 — kunge ux redesign + hermes baseline reset`
- `8ac1d85d docs(ops): orphan volume cleanup sop 供 owner 分階段 approve`

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
- **L54** — cross repo apply vs commit gap
- **L57** — backend dir logs vs mount drift
- **L58** — governance template pollution
- **L59** — governance architecture inversion

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