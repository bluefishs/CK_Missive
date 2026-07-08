---
type: memory_proposal
proposal_kind: intent_rule
target_file: intent_rules.yaml
source_pattern: 82fed427f7
proposed_by: agent
proposed_at: 2026-07-07T04:35:00.141879+08:00
status: rejected
rejected_reason: 重複提案——同 pattern 已於 2026-07-07 00:36 批准結晶（crystal-20260707-003611，收窄版 regex 已入 intent_rules.yaml）；crystallizer 重複提案迴圈已修（_already_applied 檢查）
reason: "Pattern 82fed427f7 已累積 6 次使用，成功率 100%，tool_sequence=['find_correspondence', 'get_statistics', 'search_dispatch_orders', 'search_projects']。建議結晶為 intent_rule 加速路由。"
---

# Crystal Proposal: crystal-intent-82fed427f7-784432

**Kind**: intent_rule  |  **Target**: `intent_rules.yaml`

## Reason

Pattern 82fed427f7 已累積 6 次使用，成功率 100%，tool_sequence=['find_correspondence', 'get_statistics', 'search_dispatch_orders', 'search_projects']。建議結晶為 intent_rule 加速路由。

## Payload

```yaml
  rule: {"name": "crystal_auto_82fed427f7", "pattern": "進度|進度如|派工|派工單|度如", "tool_preference": ["find_correspondence", "get_statistics", "search_dispatch_orders", "search_projects"], "priority": 50, "note": "由 pattern 82fed427f7 自動提議。hit=6 success_rate=100%"}
  stats: {"hit_count": 6, "success_rate": 1.0, "tool_sequence": ["find_correspondence", "get_statistics", "search_dispatch_orders", "search_projects"], "example_questions": ["派工單 11301-001 的進度如何？", "派工單 11301-001 進度如何"]}
```

## 批准流程

這是一個**結晶提案** — 將高頻成功 pattern 固化為規則。需人批准才會實際改動
`intent_rules.yaml`。批准後 CrystalApplier 會：

1. Snapshot 原 yaml 到 `wiki/memory/evolutions/yaml-snapshots/`
2. 套用 diff（ruamel.yaml 保留註解）
3. Validate 新 yaml 語法
4. 失敗自動 rollback
5. 寫 crystal record 到 `wiki/memory/crystals/`

批准 API（待 Phase 5 UI 實作）:
`POST /api/ai/memory/proposals/approve` with `proposal_id=crystal-intent-82fed427f7-784432`
