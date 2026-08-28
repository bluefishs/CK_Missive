---
type: agent_memory
memory_type: failure
signature: d93bd661a1
tool_sequence: ["search_documents"]
hit_count: 67
failure_count: 39
failure_rate: 0.582
active: true
first_seen: 2026-04-24
last_seen: 2026-08-27
tags: [memory, failure, defensive]
---

# Failure Mode d93bd661a1

## Tool sequence（問題組合）

`search_documents`

## 失敗統計

- **觸發次數**：67
- **失敗次數**：39
- **失敗率**：58.2%
- **症狀**：成功率僅 50%，共 1 次失敗

## 典型問法

- 最近有哪些收文？
- 桃園市政府的來文有幾封？

## 🛡️ Defensive Rule（planner 將自動注入）

**觸發**：規劃包含 `search_documents` 的組合

**歷史問題**：成功率僅 50%，共 1 次失敗

**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
- 必要時先 `get_statistics` 確認資料存在再深入查詢

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
