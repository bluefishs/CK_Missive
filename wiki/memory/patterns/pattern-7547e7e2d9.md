---
type: agent_memory
memory_type: pattern
template_hash: 7547e7e2d9
tool_sequence: [get_unpaid_billings]
domains: [erp]
wiki_topics: [wiki/topics/案件索引.md]
hit_count: 15
success_count: 15
failure_count: 0
success_rate: 1.0
avg_latency_ms: 19486
first_seen: '''''''''''''''''''''''''''''''2026-06-08'''''''''''''''''''''''''''''''
last_seen: '2026-07-02'
crystallization_candidate: true
tags: [memory, pattern, erp]
---

# Pattern 7547e7e2d9

## Tool sequence

`get_unpaid_billings`

## 統計

- **觸發次數**：15（累計）
- **成功率**：100.0%
- **平均延遲**：19487ms
- **涉及領域**：erp
- **相關 Wiki**：[[wiki/topics/案件索引.md]]

## 典型問法

- 查詢廠商應付帳款（get_vendor_detail），到期日近者優先
- 未付請款清單（get_unpaid_billings）

## 結晶候選

✅ 符合結晶門檻（hit >= 5, success >= 95%），等待 Phase 3 crystallizer 掃描。

---

_由 pattern_extractor 自動產生，最後更新：2026-07-02_
