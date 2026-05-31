---
type: critique_health_marker
verdict: silent_dormant
created_at: 2026-05-31T14:09:55
window_days: 7
critiques_in_window: 0
query_traces_in_window: 37
generator: critique_health_audit
tags: [critique, silent-dormant, health-check]
---

# Critique Health Marker — 揭發 silent dormant

**揭發時間**: 2026-05-31 14:09:55

## 訊號

- 最近 7 天 critique 數: **0**
- 最近 7 天 query trace 數: **37**

## 可能含義

⚠️ 有 37 個 query 但 0 critique → agent 完全無質性反省

## 設計意圖

critique 只在 critic 偵測到以下情況才 persist:
1. entity_alignment < 0.5 (hallucination 警示)
2. completeness < 0.3 且 answer < 100 字
3. 所有工具失敗但 answer > 200 字
4. tools ≥ 3 但 entity_alignment < 0.5

→ 0 critique 不一定壞，但長期 silent 是異常訊號

## 建議

- 檢查 agent_query_traces.eval_score 分佈
- 若 entity_alignment 都 ≥ 0.5 → 質性反省機制太嚴 (downgrade threshold?)
- 若 query 數量本來就少 → 推 owner 多互動

---

> 對齊 owner「日誌與周報成為實質平臺靈魂」
> 此 marker 本身即一條反省 (auto-generated 但有意義)
