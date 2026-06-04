---
type: agent_memory
memory_type: failure
signature: 1c8217069c
tool_sequence: ["get_statistics", "search_documents"]
hit_count: 11
failure_count: 7
failure_rate: 0.636
active: true
first_seen: 2026-05-05
last_seen: 2026-06-03
tags: [memory, failure, defensive]
---

# Failure Mode 1c8217069c

## Tool sequence（問題組合）

`get_statistics`, `search_documents`

## 失敗統計

- **觸發次數**：11
- **失敗次數**：7
- **失敗率**：63.6%
- **症狀**：成功率僅 20%，共 4 次失敗

## 典型問法

- 狀態
- 顯示財務彙總（get_financial_summary）含科目分類
- 列出所有資產（list_assets）並顯示資產統計

## 🛡️ Defensive Rule（planner 將自動注入）

**觸發**：規劃包含 `get_statistics` + `search_documents` 的組合

**歷史問題**：成功率僅 20%，共 4 次失敗

**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
- 必要時先 `get_statistics` 確認資料存在再深入查詢

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
