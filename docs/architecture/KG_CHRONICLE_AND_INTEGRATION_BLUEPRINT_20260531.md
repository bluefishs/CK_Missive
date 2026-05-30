# 知識地圖歷程議題 + 整合應用架構藍圖 — 2026-05-31

> **Owner 訴求**：複查統整知識地圖相關歷程議題 + 整合應用架構規劃
> **資料源**：60+ KG/Wiki/graph commits（4 月底起）+ 本日 dedup 後新 KG 狀態
> **核心**：5 段歷程 + 5 大整合應用 + 6 階段執行藍圖

---

## 1. 知識地圖歷程議題（5 階段）

### 階段 1 — KG 初建（v6.7 之前）

- 基礎 entity ingest（document / project / agency）
- `canonical_entities` 表 schema 立基
- 初始無 graph_domain 分流

### 階段 2 — KG 對齊治理（v6.7-v6.8, ~5/04）

| Commit | 主題 |
|---|---|
| `dd0ce4db` | get_statistics summary 加 kg 權威數字（解 q2 llm 誤回 3 entities）|
| `47cb33c6` | f25 補完 overdue_docs + kg_top_degree |
| `fa855369` | v6.7 e1+e2 fidelity log + kg alias backfill |
| `5dc9e31e` | v6.7 phase e 收尾 e2 kg backlog + wiki backfill |

**議題**：KG 與業務分開、AI 誤回答 entities 數量錯誤。
**修法**：權威數字注入 + alias backfill。

### 階段 3 — Wiki 整合（v6.9, ~5/16）

| Commit | 主題 |
|---|---|
| `3966bec1` | v6.6 phase b1 wiki 5 個聚合 topic |
| `90e0f895` | i5+ wiki topics 9→20 backlog |
| `e1827e42` | step 35/36 autobiography freshness |
| `b8cef209` | autobiography wiki silent fix |
| `31597a3c` | wire wiki/ into docker container（mount fix）|

**議題**：Wiki / Memory / Autobiography 寫入 silent fail（mount drift）。
**修法**：docker mount + fitness step 35/36 偵測 silent dormant。

### 階段 4 — Wiki↔KG link 治理（v5.9.8 → v6.10, ~5/20-25）

| Commit | 主題 |
|---|---|
| `ec2bee63` | karpathy 4-phase wiki + memory critique/diary/pattern (247 files) |
| `f1bd68df` | 5/26-27 wiki memory + autobiography + diary updates |
| `0f7f4ec8` | fitness tier 2 weekly + kg metric name fix |
| `0851bf64` | wiki metric export + metric() endpoint health |

**議題**：
- Wiki↔KG 連結率不足
- KG metric name `ck_missive_kg_entities_total` 錯誤
- Wiki pages 缺 `kg_entity_id` frontmatter

**修法**：
- v5.9.8 wiki_kg_link_audit fitness step 4
- KG metric name 修正
- Wiki frontmatter backfill 開始

### 階段 5 — KG 整體性複查 + dedup（5/31 本日）

| Commit | 主題 |
|---|---|
| `3c335da8` | KG 圖譜+架構整體性複查（5 大建議）|
| `8aec4d78` | 程式圖譜+wiki 對應規範現況 fitness step 63 |
| `befcc750` | step 70 repository:db_table 覆蓋率 audit |
| `e463c087` | step 71 cross-domain link + step 72 dedup audit |
| `1908b54e` | effectiveness report + dedup script |
| `984fc780` | dedup 5 層備份 + erp ingest dry-run |
| `560848ad` | LINE timeout fix + dedup 紀錄 |

**議題**：
- repository:db_table 1:3.5 覆蓋不足
- knowledge 41.8% code entity 雙寫
- ERP graph 84 嚴重不符規模
- Skills 108 完全不在 KG
- Document 1809 無獨立 entity

**修法**：
- **dedup 執行 ✅**：knowledge 7556→4399（純業務）
- Step 70/71/72 audit 落地
- ERP ingest dry-run 完成（129 entity 待補）

---

## 2. 當下 KG 狀態（dedup 後）

| Domain | Total | Embedded | Pct |
|---|---|---|---|
| **code** | 9091 | 9091 | **100%** ✅ |
| **tender** | 7804 | 7804 | **100%** ✅ |
| **knowledge** | 4399 | 3100 | 70% 🟡（純業務後）|
| **erp** | 84 | 84 | 100% ✅ |
| **總計** | **21378** | **20079** | **94%** |

**改善**：
- 整體 KG 24535 → **21378**（-3157 雙寫）
- knowledge 純業務 4399（vs 7556 含 41.8% code）
- 整體 embedded 86% → **94%**

---

## 3. 整合應用架構藍圖（6 層）

### 3.1 層級設計

```
┌─────────────────────────────────────────────────────┐
│ Layer 6 — User Interface                            │
│   /kunge web UI / LINE bot / Telegram / Discord    │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 5 — AI Agent Orchestrator                     │
│   - agent_planner (task_type=planning)              │
│   - agent_synthesis (chat)                          │
│   - tool_registry (45 tools)                        │
│   - sender_context (channel-aware routing)          │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 4 — Knowledge Sources (3 source)              │
│   ┌───────────┬─────────────┬──────────────────┐   │
│   │ KG (KG)   │ LLM Wiki    │ Skills           │   │
│   │ 21378     │ 359 pages   │ 108 SKILL.md     │   │
│   │ 4 domain  │ 4 type      │ 22 專案 + 86 共享 │   │
│   └───────────┴─────────────┴──────────────────┘   │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 3 — Embedding Layer (pgvector 768D)           │
│   - 20079 embedded (94% coverage)                   │
│   - nomic-embed-text Ollama                         │
│   - semantic search 跨 4 domain                     │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 2 — Data Sources (DB + File System)           │
│   - PostgreSQL 71 tables                            │
│   - File: wiki/ docs/ scripts/                      │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 1 — Business Domain                           │
│   公文 / 標案 / PM/ERP / 派工 / 機關 / 廠商         │
└─────────────────────────────────────────────────────┘
```

### 3.2 5 大整合應用

| # | 應用 | 入口 | 涉及 source |
|---|---|---|---|
| 1 | **AI 問答** | /kunge chat / LINE bot | KG + Wiki + tool |
| 2 | **公文推薦** | dashboard 推送 | KG (knowledge) + ERP |
| 3 | **晨報生成** | cron 06:00 | KG + Wiki memory |
| 4 | **標案分析** | /tender pages | KG (tender) + 業務 |
| 5 | **Agent 自省** | /kunge ops | KG + skill + lesson |

### 3.3 跨域連結率（v5.9.8 + 本日驗證）

| 連結 | 狀態 | 目標 |
|---|---|---|
| Wiki↔KG（frontmatter） | 38.5% 🔴 | ≥80% |
| Wiki↔KG（v5.9.8 業務 entity）| 86% ✅ | ≥80% |
| tender_agency↔knowledge.org | **92.8%** ✅ | ≥80% |
| Knowledge dedup | ✅ 100% (本日完成) | — |
| ERP↔code | 待 ingest | — |

---

## 4. 6 階段執行藍圖（下批優先級）

### Phase 1（本批已完成 5/31）

- ✅ KG 整體性複查（5 大建議）
- ✅ Step 70/71/72 audit 落地
- ✅ knowledge dedup --apply (7556→4399)
- ✅ LINE timeout 修法 (25→28s)
- ✅ effectiveness report + 14 lesson 索引

### Phase 2（下批 P0）

- ERP 欄位校正 + ingest --apply（C 方案 A，129 entity 待補）
- wiki kg_entity_id backfill（38.5%→80%）

### Phase 3（P0 中期）

- Document graph_domain 加入（1809 documents → entity）
- Skill graph 加入（108 skills → entity）
- Cross-domain link audit 自動 weekly

### Phase 4（P1 結構優化）

- Repository 擴展（19 missing tables）
- Service 瘦身 55→110（對齊 12 bounded context）
- LINE channel groq fast-path（v6.13）

### Phase 5（P2 產品）

- /kunge UX Phase 1-3（1-2 週）
- Hermes 30 天累積 + 6/28 重評
- ADR-0035 GitNexus 收斂

### Phase 6（範本治理）

- CK_AaaP 加 audit 機制（L59 配套）
- PileMgmt R18 範本擴散至 lvrland/Showcase/KMap
- v6.13 治理立法（基於 v6.12 8 句立法演進）

---

## 5. 議題優先級總結

### P0（業務影響 / KG 完整性）

1. ERP ingest --apply（129 entity 待補，AI ERP 查詢精度）
2. wiki kg_entity_id backfill 38.5%→80%（SSOT 完整性）
3. LINE p95 改善（v6.13 groq fast-path）

### P1（結構正常化）

4. Document/Skill graph 加入
5. Repository 命名規約 enforce
6. Service 瘦身

### P2（產品+治理）

7. /kunge UX Phase 1-3
8. Hermes baseline 達標
9. CK_AaaP audit 配套（L59）

---

## 6. 對齊 v6.12 8 句立法

| 立法句 | KG 歷程對應 |
|---|---|
| 1 抽象不是錯，建後不 audit 才是 | knowledge 41.8% 雙寫 audit 揭發 |
| 2 觀測不是奢侈 | step 70/71/72 量化 KG 漂移 |
| 3 整合 SSOT 是責任 | 6 層整合應用藍圖 |
| 4 修法不可逆 → 60 天 trial | dedup 5 層備份 + 7 天 verify |
| 5 commit + push 才算 | dedup --apply 已執行 |
| 6 範本是參考 (L58) | Document/Skill 不外推 L3 |
| 7 上游缺機制 (L59) | KG 是 CK_AaaP audit 缺口之一 |
| 8 平衡 = 結構正常化 (L60) | KG 4 domain 比例平衡（94% embedded）|

---

## 7. 元洞察 — KG 從散戶到統一

**5 階段演進**：
1. 初建（裸 entity）
2. 治理對齊（修錯誤回答）
3. Wiki 整合（mount drift 修）
4. Wiki↔KG link 治理（連結率）
5. **整體性複查 + dedup**（本日達成）

**從散戶到統一**：
- 初期：4 domain 各自 ingest
- 中期：Wiki 連結但 silent fail
- 本日：dedup 後 knowledge 純業務 + 整體 94% embedded

**下一步**：6 階段執行藍圖，從「KG 結構優化」進化到「跨域應用整合」。

對齊 owner 訴求 — 不只看「有多少 entity」，更看「entity 如何在業務應用中發揮價值」。

---

## 8. 文件入口（整合）

| 文件 | 用途 |
|---|---|
| `GRAPH_ECOSYSTEM_HOLISTIC_REVIEW_20260531.md` | 圖譜生態系 5 大斷層揭發 |
| `KG_ARCHITECTURE_HOLISTIC_REVIEW_20260531.md` | code-graph 量化複查 |
| `REPOSITORY_NAMING_CONVENTION_20260531.md` | A+C 規範智能 |
| `GOVERNANCE_EFFECTIVENESS_REPORT_20260531.md` | 真活+效益驗證 |
| **`KG_CHRONICLE_AND_INTEGRATION_BLUEPRINT_20260531.md`** | **本文件 — 歷程+藍圖** |

---

> **核心精神**：KG 不是孤立 storage，是業務應用的脊椎。
> 5 階段歷程 + 6 階段藍圖 = 從「資料化」到「智能化」演進。
> 對齊 v6.12 8 句立法 + 整合 SSOT 是責任。
