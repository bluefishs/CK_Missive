---
type: agent_memory
memory_type: failure
signature: a18f229167
tool_sequence: ["get_statistics", "search_across_graphs"]
hit_count: 3
failure_count: 3
failure_rate: 1.000
active: true
first_seen: 2026-05-20
last_seen: 2026-05-20
tags: [memory, failure, defensive]
---

# Failure Mode a18f229167

## Tool sequence（問題組合）

`get_statistics`, `search_across_graphs`

## 失敗統計

- **觸發次數**：3
- **失敗次數**：3
- **失敗率**：100.0%
- **症狀**：成功率僅 0%，共 3 次失敗

## 典型問法

- 查詢標案決標資訊（tender award lookup）
- 在 wiki 知識庫搜尋「派工流程」相關內容

## 🛡️ Defensive Rule（planner 將自動注入）

**觸發**：規劃包含 `get_statistics` + `search_across_graphs` 的組合

**歷史問題**：成功率僅 0%，共 3 次失敗

**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
- 必要時先 `get_statistics` 確認資料存在再深入查詢

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
