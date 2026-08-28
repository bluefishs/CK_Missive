---
type: agent_memory
memory_type: failure
signature: 8c06ac7053
tool_sequence: ["get_financial_summary"]
hit_count: 2
failure_count: 2
failure_rate: 1.000
active: false
expired_reason: stale >21d (last_seen 2026-08-06)
first_seen: 2026-08-06
last_seen: 2026-08-06
tags: [memory, failure, defensive]
---

# Failure Mode 8c06ac7053

## Tool sequence（問題組合）

`get_financial_summary`

## 失敗統計

- **觸發次數**：2
- **失敗次數**：2
- **失敗率**：100.0%
- **症狀**：成功率僅 0%，共 2 次失敗

## 典型問法

- 顯示財務彙總（get_financial_summary）含科目分類

## 🛡️ Defensive Rule（planner 將自動注入）

**觸發**：規劃包含 `get_financial_summary` 的組合

**歷史問題**：成功率僅 0%，共 2 次失敗

**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
- 必要時先 `get_statistics` 確認資料存在再深入查詢

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
