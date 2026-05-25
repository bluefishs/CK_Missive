---
type: agent_memory
memory_type: failure
signature: bbd8990563
tool_sequence: ["get_statistics", "search_dispatch_orders"]
hit_count: 7
failure_count: 5
failure_rate: 0.714
active: true
first_seen: 2026-05-06
last_seen: 2026-05-13
tags: [memory, failure, defensive]
---

# Failure Mode bbd8990563

## Tool sequence（問題組合）

`get_statistics`, `search_dispatch_orders`

## 失敗統計

- **觸發次數**：7
- **失敗次數**：5
- **失敗率**：71.4%
- **症狀**：成功率僅 33%，共 2 次失敗

## 典型問法

- 查估專區目前有幾件進行中？
- 在標案系統搜尋桃園市測量相關標案（tender search）

## 🛡️ Defensive Rule（planner 將自動注入）

**觸發**：規劃包含 `get_statistics` + `search_dispatch_orders` 的組合

**歷史問題**：成功率僅 33%，共 2 次失敗

**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
- 必要時先 `get_statistics` 確認資料存在再深入查詢

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
