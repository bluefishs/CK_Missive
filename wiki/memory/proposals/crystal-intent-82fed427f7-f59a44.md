---
type: memory_proposal
proposal_kind: intent_rule
target_file: intent_rules.yaml
source_pattern: 82fed427f7
proposed_by: agent
proposed_at: 2026-04-21T10:03:39.814269+08:00
status: superseded
superseded_at: 2026-06-01T15:30:00+08:00
superseded_by: owner-jujuiacc
superseded_reason: "owner 裁定誠實 defer：(1) crystal_applier 安全閘擋空 pattern；(2) tool_preference 在 services/ai 無消費端，rule_engine 用 extract/confidence schema → 即使套用仍 inert；(3) crystallizer 只存 tool_sequence 未存來源 query 文字，無法生成有意義 regex。待 v6.14 升級 pattern_extractor 補捕 query 文字 + 建 tool_preference 消費端後，重新生成可真實 apply 的 proposal。不造假、不留 dead rule。"
reason: "Pattern 82fed427f7 已累積 6 次使用，成功率 100%，tool_sequence=['find_correspondence', 'get_statistics', 'search_dispatch_orders', 'search_projects']。建議結晶為 intent_rule 加速路由。"
---

# Crystal Proposal: crystal-intent-82fed427f7-f59a44

**Kind**: intent_rule  |  **Target**: `intent_rules.yaml`

## Reason

Pattern 82fed427f7 已累積 6 次使用，成功率 100%，tool_sequence=['find_correspondence', 'get_statistics', 'search_dispatch_orders', 'search_projects']。建議結晶為 intent_rule 加速路由。

## Payload

```yaml
  rule: {"name": "crystal_auto_82fed427f7", "pattern": "", "tool_preference": ["find_correspondence", "get_statistics", "search_dispatch_orders", "search_projects"], "priority": 50, "note": "由 pattern 82fed427f7 自動提議。hit=6 success_rate=100%"}
  stats: {"hit_count": 6, "success_rate": 1.0, "tool_sequence": ["find_correspondence", "get_statistics", "search_dispatch_orders", "search_projects"]}
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
`POST /api/ai/memory/proposals/approve` with `proposal_id=crystal-intent-82fed427f7-f59a44`
