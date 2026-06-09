---
type: memory_proposal
proposal_kind: intent_rule
target_file: intent_rules.yaml
source_pattern: 82fed427f7
proposed_by: agent
proposed_at: 2026-06-02T04:35:00.092379+08:00
status: superseded
superseded_at: 2026-06-09T13:30:00+08:00
superseded_by: owner-jujuiacc
superseded_reason: "與 06-01 已 defer 的 sibling crystal-intent-82fed427f7-f59a44 同源同缺陷（payload pattern:\"\" 空 regex；tool_preference 無消費端；crystallizer 06-02 產生時尚未補來源 query 文字）。且 failure-82fed427f7 記 failure_rate=0.500（hit4/fail2），與本提案『成功率 100%』直接矛盾 → failure tracker 較誠實，pattern 非可靠。本份早於 06-04 crystallizer L1 修法（517cdd5f 從 example_questions 推導真 regex），屬修法前舊產物。退回，待新 crystallizer 產帶真 pattern 之提案再批。不留 dead rule。"
reason: "Pattern 82fed427f7 已累積 6 次使用，成功率 100%，tool_sequence=['find_correspondence', 'get_statistics', 'search_dispatch_orders', 'search_projects']。建議結晶為 intent_rule 加速路由。"
---

# Crystal Proposal: crystal-intent-82fed427f7-713394

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
`POST /api/ai/memory/proposals/approve` with `proposal_id=crystal-intent-82fed427f7-713394`
