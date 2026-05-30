# 圖譜生態系整體性複查與建議事項 — 2026-05-31

> **Owner 訴求**：知識地圖 + 公文 + 標案 + 資料庫 + 技能 + 知識文庫 應同步檢視
> **資料源**：KG 4 graph_domain × entity_type 矩陣 + Wiki 370+ pages + Skills 108 + DB 71 表
> **核心**：揭發圖譜生態系 5 大斷層 + 5 大整合建議

---

## 1. 圖譜生態系全面盤點

### 1.1 KG 四 graph_domain（24535 entities）

| Domain | Total | 占比 | 主要 entity_type |
|---|---|---|---|
| **code** | 9091 | 37% | py_function 4409 / py_class 1165 / ts_interface 826 / ts_module 748 |
| **tender** | 7804 | 32% | tender_record 5973 / tender_agency 1831 |
| **knowledge** | 7556 | 31% | **org 3791** / py_function 2042 / py_module 306 / project 206 / dispatch 127 / location 185 |
| **erp** | **84** | **0.3%** | quotation 69 / vendor 11 / expense 3 / asset 1 |

### 1.2 LLM Wiki（370+ pages）

| Type | Count |
|---|---|
| entities/ | 221（業務實體 narrative）|
| memory/ | 111（內部記憶 + lessons + diary）|
| synthesis/ | 20（綜合知識）|
| topics/ | 17（主題彙整）|
| SOUL/SCHEMA/index | 3（meta）|

### 1.3 Skills 庫（108 SKILL.md）

`.claude/skills/` 含 22 專案 skills + 86 共享 skills，**完全不在 KG 內**。

### 1.4 DB 真實 schema（71 tables）

含 documents / projects / agencies / tender_orders / canonical_entities / ai_* 等 7 大業務群組。

---

## 2. 揭發 5 大架構斷層

### 斷層 1 — **ERP graph_domain 嚴重不符規模** 🔴

**現況**：ERP 業務有 30+ 表 + 150+ endpoint（PM/ERP 模組），但 KG 只 **84 entities**。

**影響**：
- AI agent 查 ERP 業務找不到 entity
- 跨域 query「某廠商對某報價」無法走 KG
- ERP 模組功能與 KG 觀測脫鉤

**對齊 5/31 早 KG 建議 #3**：ingest 至 ~500+。

### 斷層 2 — **Knowledge graph 重複 code entity 嚴重** 🔴

**現況**：knowledge domain 內含 **py_function 2042 / py_module 306 / py_class 282 / api_endpoint 267 / service 68** = **2965** (39%) 是 code entity 重複到 knowledge。

**影響**：
- KG 7556 entities 看似豐富，**實際業務 entity 僅 ~4591** (61%)
- 雙寫造成 storage 浪費 + query 混淆
- knowledge graph 變「code graph 副本」失去業務 narrative 屬性

**建議**：knowledge domain 去重 code entity（移至 code-only），knowledge 純留業務 entity（org/project/dispatch/location 等）。

### 斷層 3 — **Skills 庫 108 完全不在 KG** 🟡

**現況**：`.claude/skills/` 內 108 SKILL.md 文件 / 22 專案 + 86 共享 skills，**0 KG entity**。

**影響**：
- AI agent 無法查「有哪些 skill 可用」
- skill 演進 / drift 無法 metric 化
- skill ↔ code 關聯無法追蹤（哪些 skill 對應 code module）

**建議**：加 skill graph_domain（或 entity_type=skill），ingest 108 skills。

### 斷層 4 — **Tender ↔ Wiki ↔ Knowledge 跨域連結率未量化** 🟡

**現況**：tender 7804 / knowledge 7556 / wiki 221 entity pages，但**三者之間連結率**未 audit。

**問題範例**：
- tender_agency 1831 是否與 knowledge.org 3791 對應？
- tender_record 5973 是否有 wiki narrative page？
- Wiki entity 是否真連到 KG canonical_entity？

**建議**：加 fitness step `cross_domain_link_audit.py`，量化三者跨域連結率。

### 斷層 5 — **Document graph 不獨立 graph_domain** 🟡

**現況**：公文（1809 documents）在 KG 內無獨立 graph_domain，而是分散在 knowledge 內：
- dispatch 127（派工 ≈ 公文派發）
- 但 documents 本身（1809 筆）無對應 entity

**影響**：
- 公文搜尋 / 推薦無法走 KG
- 公文 ↔ 機關 ↔ 案件三方關聯漏 KG 觀測

**建議**：加 `document` entity_type（或 graph_domain），對 1809 documents 全 ingest。

---

## 3. 5 大整合建議事項

### 建議 1 — ERP graph_domain ingest 補完（P0，1 天）

```bash
python scripts/sync/backfill_kg_embeddings_all.py --domain=erp
# 目標: 84 → ~500+
# 涵蓋: quotation / billing / invoice / vendor_payable / asset / expense
```

### 建議 2 — Knowledge graph 去重 code entity（P0，0.5 天）

```sql
-- 評估去重影響
SELECT entity_type, COUNT(*)
FROM canonical_entities
WHERE graph_domain='knowledge'
  AND entity_type LIKE 'py_%' OR entity_type LIKE 'ts_%'
        OR entity_type IN ('api_endpoint', 'service', 'schema', 'repository')
GROUP BY entity_type;

-- 預期 ~2965 重複 entity 待 archive/delete
```

對齊 v5.9.8 wiki ↔ KG link audit 既有機制。

### 建議 3 — Skill graph 加入（P1，1 天）

```python
# scripts/sync/skill_kg_ingest.py
# 對 .claude/skills/**/SKILL.md ingest:
#   entity_type='skill', graph_domain='knowledge'（或新建 graph_domain='skill'）
# canonical_name = skill name (frontmatter)
# description = SKILL.md 前 200 字
# 連結: code module(s) referenced in skill
```

### 建議 4 — Document graph_domain 獨立 + ingest（P1，1 天）

```python
# scripts/sync/document_kg_ingest.py (對齊 dispatch_kg_ingest 模式)
# 對 1809 documents ingest:
#   entity_type='document', graph_domain='knowledge' (或新 domain='document')
#   canonical_name = doc_number
#   linked_agency_id / linked_project_id 透過 ORM 關聯
```

### 建議 5 — Cross-domain link audit（P1，1 天）

```python
# scripts/checks/cross_domain_link_audit.py (fitness step 71 候選)
# 量化 3 對連結率:
#   1. tender_agency ↔ knowledge.org (應 80%+)
#   2. tender_record ↔ wiki narrative (應 ≥30%)
#   3. wiki entity ↔ KG canonical (應 ≥80%, v5.9.8 已 86%)
# RED: 任一 < 50% 觸發 LINE
```

---

## 4. 圖譜生態系整合架構（建議目標）

```
┌─────────────────────────────────────────────────────────┐
│ Unified Knowledge Graph (全域 SSOT)                     │
│                                                         │
│ graph_domain=                                           │
│   - code (9091, 純技術 — 去重後)                        │
│   - tender (7804, 標案業務)                             │
│   - knowledge (~4591, 純業務 — 去重 + 補 document)     │
│   - erp (500+, 補完後)                                  │
│   - skill (108, 新加)                                   │
│   - document (1809, 新加 或 入 knowledge)               │
│                                                         │
│ entity_type 跨域連結率：                                 │
│   tender_agency ↔ knowledge.org      (應 ≥80%)         │
│   tender_record ↔ wiki narrative     (應 ≥30%)         │
│   wiki entity ↔ KG canonical          (✅ 86% v5.9.8)  │
└─────────────────────────────────────────────────────────┘
        ↓ semantic search + AI query
┌─────────────────────────────────────────────────────────┐
│ LLM Wiki (370+ pages narrative layer)                   │
│   entities/ 221 + memory/ 111 + synthesis/ 20 +         │
│   topics/ 17                                            │
│   全部對應 KG canonical_entity_id                       │
└─────────────────────────────────────────────────────────┘
        ↓ 知識應用
┌─────────────────────────────────────────────────────────┐
│ AI Agent + Skills (108 skills)                          │
│   可查 KG / Wiki / Skill (3 source)                     │
│   Agent decision: which graph to query                  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 立即可做（P0 本批可提）

### 5.1 寫 cross_domain_link_audit.py（建議 5 落地）

可立即寫並接 weekly fitness。揭發三方連結率。

### 5.2 寫 knowledge_dedup_audit.py（建議 2 配套）

偵測 knowledge 內 code entity 數量 + 計算去重影響。

兩者皆純 audit 不動資料，可本批落地。

---

## 6. 整體性結論

### 6.1 圖譜健康面

- ✅ Code graph 9091 entities 豐富（最完整）
- ✅ Tender graph 7804 業務扎實（5973 record + 1831 agency）
- ✅ Wiki ↔ KG 86% 連結率（v5.9.8 已達）
- ✅ Knowledge org 3791（機關 entity 完整）

### 6.2 圖譜漂移面

- 🔴 ERP graph 84 嚴重不符（業務規模 ~500+ 預期）
- 🔴 Knowledge graph 39% 重複 code entity（雙寫浪費）
- 🟡 Skills 108 完全不在 KG（silo）
- 🟡 Document 1809 無獨立 entity（無法 KG 查）
- 🟡 Tender ↔ Knowledge ↔ Wiki 跨域連結率未量化

### 6.3 整合建議優先級

| P | 建議 | 估時 |
|---|---|---|
| **P0** | ERP graph ingest 84→500+ | 1 天 |
| **P0** | Knowledge 去重 code entity (2965 → 0) | 0.5 天 |
| **P1** | Document graph_domain 加入 + ingest | 1 天 |
| **P1** | Skill graph 加入 + 108 ingest | 1 天 |
| **P1** | Cross-domain link audit (step 71) | 1 天 |
| **總計** | **5 項，4.5 天** | — |

---

## 7. 對齊 v6.12 8 句立法

| 立法句 | 本複查對應 |
|---|---|
| 1 抽象不是錯 | KG 5 domain 抽象適切性檢核 |
| 2 觀測不是奢侈 | KG entity count 量化揭發 |
| 3 整合 SSOT 是責任 | 5 圖譜 + Wiki + Skills 整合架構 |
| 4 60 天 trial 是保險 | 新 graph_domain (skill/document) 30 天 audit |
| 5 commit + push 才算 | 5 個 ingest script 待寫 |
| 6 範本是參考 | 各圖譜不同 entity_type 命名分流 |
| 7 上游缺機制 | erp graph_domain ingest 缺機制 |
| 8 平衡 = 結構正常化 | 5 圖譜大小平衡（code/tender/knowledge/erp/document）|

---

## 8. 元洞察 — 圖譜生態系視角

過去 RETRO 只看「KG 總數 24535」，本複查首次按 **graph_domain 拆解** 並對應 Wiki + Skills + DB。

揭發 **5 大斷層**：
- 業務規模不符（ERP）
- 雙寫浪費（knowledge 重複 code）
- silo 孤立（Skills）
- 缺類別（Document）
- 跨域連結率未量化

**「程式圖譜 = 治理 X 光片」延伸到「圖譜生態系 = 業務 X 光片」**。

對應 owner「整體性建議」訴求 — 不只看「有多少 entity」，更看「entity 之間如何關聯」。

---

## 9. 下批執行建議

按 P0 → P1 順序：

1. **本批可立即做**：寫 cross_domain_link_audit.py（不動資料純 audit）
2. **下批 P0**：ERP ingest + knowledge 去重評估
3. **下下批 P1**：Document/Skill graph_domain 加入

---

> **核心精神**：圖譜不是孤立 silos，是業務的關聯網。
> 6 圖譜（KG 4 domain + Wiki + Skills）需要明確邊界 + 跨域連結 audit。
> 對齊 v6.12 第 3 句「整合 SSOT 是責任」+ 第 8 句「平衡 = 結構正常化」。
