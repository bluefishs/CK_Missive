---
type: agent_memory
memory_type: pattern
template_hash: 1c8217069c
tool_sequence: [get_statistics, search_documents]
domains: [analysis, doc]
wiki_topics: [wiki/topics/公文管理系統總覽.md]
hit_count: 7
success_count: 7
failure_count: 0
success_rate: 1.0
avg_latency_ms: 35498
first_seen: '''2026-05-10'''
last_seen: '2026-05-30'
crystallization_candidate: true
tags: [memory, pattern, analysis, doc]
---

# Pattern 1c8217069c

## Tool sequence

`get_statistics`, `search_documents`

## 統計

- **觸發次數**：7（累計）
- **成功率**：100.0%
- **平均延遲**：35498ms
- **涉及領域**：analysis, doc
- **相關 Wiki**：[[wiki/topics/公文管理系統總覽.md]]

## 典型問法

- 顯示財務彙總（get_financial_summary）含科目分類
- 列出所有資產（list_assets）並顯示資產統計

## 結晶候選

✅ 符合結晶門檻（hit >= 5, success >= 95%），等待 Phase 3 crystallizer 掃描。

---

_由 pattern_extractor 自動產生，最後更新：2026-05-30_
