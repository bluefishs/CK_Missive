# 程式圖譜 + 架構整體性複查與建議事項 — 2026-05-31

> **觸發**：Owner「複查專案相關圖譜對應關係與架構提出整體性建議事項」
> **資料源**：code-graph (9091 entities) + 治理 audit + facade adoption + cross_repo drift
> **核心**：用 KG 量化視角揭發架構級漂移 + 5 大整體性建議

---

## 1. Code-Graph 實體分佈快照

### 後端 Python 層

| Entity | Count | 比例 |
|---|---|---|
| py_function | 4409 | 主體 (48%) |
| py_class | 1165 | 13% |
| py_module | 664 | 7% |
| service | 55 | 0.6% |
| repository | 18 | 0.2% |
| schema | 88 | 1.0% |
| db_table | 63 | 0.7% |
| api_endpoint | 335 | 3.7% |

### 前端 TypeScript 層

| Entity | Count | 比例 |
|---|---|---|
| ts_interface | 826 | 9.1% |
| ts_module | 748 | 8.2% |
| ts_hook | 309 | 3.4% |
| ts_component | 274 | 3.0% |
| ts_type | 134 | 1.5% |
| ts_enum | 3 | 0.03% |

**總計**：9091 code entities + 7556 knowledge + 7804 tender + 84 erp = 24535

---

## 2. 對應關係比例分析（揭發架構漂移）

### 2.1 前後端對應

| 比例 | 數值 | 健康度 |
|---|---|---|
| api_endpoint / ts_hook | **335 : 309** | 🟢 1.08（接近 1:1，健康）|
| ts_component / ts_hook | 274 : 309 | 🟢 0.89（component-driven 合理）|

→ **前後端對應基本健康**，但 step 67 audit 揭發 411 silent 漂移（標準化問題為主，非真實 bug）。

### 2.2 後端 DDD 結構

| 比例 | 數值 | 健康度 |
|---|---|---|
| **repository / db_table** | **18 : 63 = 1 : 3.5** | 🔴 **不足**（平均 1 repo 涵蓋 3.5 表，應 1:1.5 內）|
| schema / db_table | 88 : 63 | 🟢 1.40（schema > table 合理，含 nested）|
| **service / endpoint** | **55 : 335 = 1 : 6.1** | 🟡 **偏高**（平均 1 service 處理 6 endpoint，應 1:3 內）|

→ **Repository 層覆蓋不足 + Service 層 endpoint 比例偏高** = 業務邏輯散落 endpoint。

### 2.3 抽象密度

| 比例 | 平均 | 健康度 |
|---|---|---|
| py_function / py_module | 4409 / 664 = **6.6/module** | 🟢 適中 |
| py_class / py_module | 1165 / 664 = **1.8/module** | 🟢 適中 |
| ts_interface / ts_module | 826 / 748 = **1.1/module** | 🟢 適中 |

→ 抽象密度健康，無 module bloat。

---

## 3. 跨 graph_domain 分佈（業務領域占比）

| Domain | Entities | 占比 |
|---|---|---|
| **code** | 9091 | 37% |
| tender | 7804 | 32% |
| knowledge | 7556 | 31% |
| erp | 84 | 0.3% |

→ **erp domain 嚴重不足**（與 PM/ERP 業務模組規模不符），可能 KG ingest 漏掉 erp 業務 entity。

---

## 4. 治理層 audit 現況（22:00 snapshot）

### Facade adoption (P1.7)

| Facade | Caller | 健康 |
|---|---|---|
| IntegrationFacade | 3 | 🟢 |
| MemoryFacade | 3 | 🟢 |
| WikiFacade | 3 | 🟢 |
| **Average** | **3.00** | **GREEN** |

→ 60 天 trial 進度良好（目標 ≥3，已達；7/30 重評 ≥5）。

### Cross-repo template drift (step 65)

| Repo | Coverage | 狀態 |
|---|---|---|
| CK_lvrland_Webmap | 6/6 | 🟢 GREEN |
| **CK_PileMgmt** | **1/6** | **🔴 RED**（R18 反治理後）|
| CK_Showcase | 6/6 | 🟢 GREEN |
| CK_KMapAdvisor | 6/6 | 🟢 GREEN |

→ 3/4 GREEN，PileMgmt R18 是「健康反治理」非問題。

---

## 5. 5 大整體性建議事項

### 建議 1 — Repository 層擴展（P0 治理基礎）

**揭發**：repository:db_table = 1:3.5（平均 1 repo 涵蓋 3.5 表，過寬）

**問題**：
- 業務邏輯可能散落 endpoint
- 多表 query 沒 Repository 抽象易產生 N+1
- 跨表 transaction 難管理

**建議**：
- 目標 1:1.5（每 repo 最多 1-2 表）
- 評估 18 → ~40 repository
- 優先補：document_chunk / agent_trace / ai_synonym 等高頻表

**ROI**：減 endpoint 內 SQL 散戶 + 提升 RLS 覆蓋率

### 建議 2 — Service 層瘦身（P1 結構正常化）

**揭發**：service:endpoint = 1:6.1（平均 1 service 處理 6 endpoint）

**問題**：
- 部分 service 變「god class」
- 邊界模糊 → 跨 context 互依
- 對齊 L53 「facade over-engineering」風險

**建議**：
- 目標 1:3（每 service 處理 ≤ 3 endpoint）
- 評估 55 → ~110 service（精細化）
- 對齊 12 bounded context 重新切

**ROI**：對應 v6.10 P1 真模組化目標，facade 真活率提升

### 建議 3 — ERP 業務 KG ingest 補完（P0 業務真活）

**揭發**：erp graph_domain 僅 84 entities（vs tender 7804 / knowledge 7556）

**問題**：
- ERP 模組 ~30 表 + ~150 endpoint 但 KG 只 84 entities
- 與業務規模嚴重不符
- AI 問答涉及 ERP 業務查不到 entity

**建議**：
- 跑 `dispatch_kg_ingest.py` 對 ERP 表全 ingest
- 補 ERP entity 至 ~500+
- 對齊 v5.9.8 backfill 模式

**ROI**：AI agent ERP 查詢精度提升

### 建議 4 — Frontend type 抽象密度健康，但 hook 散戶需 audit（P1）

**揭發**：ts_hook 309 vs ts_component 274 = 0.89

**現況健康**，但 step 67 audit 揭發 411 fe-only endpoint 候選。建議：
- 加 frontend hook usage audit
- 偵測 dead hook（定義但無 component 用）
- 對齊 dead_ui_detector 既有 fitness

**ROI**：fronend dead code 減少 → bundle size 改善

### 建議 5 — Cross-domain 連結率 audit（P2 KG 治理）

**揭發**：
- code 37% / tender 32% / knowledge 31% / erp 0.3%
- code ↔ knowledge ↔ tender 跨 domain 連結率？未量化

**建議**：
- 加 fitness step：cross_domain_link_audit.py
- 對比 knowledge 內 entity 是否與 tender 業務真實連結
- 對齊 v5.9.8 wiki_kg_link_audit 既有

**ROI**：KG 不只是 silos 而是真正知識網

---

## 6. 立即可做（P0 部分本批可提）

1. **加 ERP ingest 觸發** — 一次性指令
   ```bash
   bash scripts/sync/backfill_kg_embeddings_all.py --domain=erp
   ```

2. **加 Repository 缺口 audit** — fitness step 70 候選
   ```python
   # repository_coverage_audit.py
   # 對比 db_table 數 vs repository 數
   # < 1:1.5 → YELLOW / < 1:2 → RED
   ```

3. **Frontend dead hook audit** — fitness step 71 候選
   ```python
   # frontend_dead_hook_audit.py
   # grep ts_hook 是否被 ts_component 引用
   ```

---

## 7. 整體性結論

### 7.1 健康面

- ✅ 前後端 endpoint:hook 對應 1.08（健康）
- ✅ 抽象密度健康（無 module bloat）
- ✅ Facade adoption 3 active GREEN
- ✅ 3/4 子專案範本採用 GREEN
- ✅ Code-graph 9091 entities 豐富

### 7.2 漂移面

- 🔴 Repository:db_table = 1:3.5（覆蓋不足）
- 🟡 Service:endpoint = 1:6.1（瘦身機會）
- 🔴 ERP domain 84 entities（業務規模不符）
- 🟡 Cross-domain 連結率未量化

### 7.3 整體建議優先級

| P | 建議 | 估時 |
|---|---|---|
| P0 | ERP KG ingest 補完 | 1 天 |
| P0 | Repository 缺口 audit + 補關鍵 | 3 天 |
| P1 | Service 層瘦身（對齊 bounded context）| 1 週 |
| P1 | Cross-domain link audit | 1 天 |
| P2 | Frontend dead hook audit | 半天 |

---

## 8. 對齊 v6.12 8 句立法

| 立法句 | 本複查對應 |
|---|---|
| 1 抽象不是錯，建後不 audit 才是 | KG 9091 entities 量化驗證抽象適切性 |
| 2 觀測不是奢侈 | code-graph 揭發比例失衡 |
| 3 整合 SSOT 是責任 | dashboard §1-9 整合視角 |
| 4 60 天 trial 是保險 | facade 60 天 trial 進度 GREEN |
| 5 commit + push 才算 | repository 18 已落實但覆蓋不足 |
| 6 範本是參考 | install-template 5 道防線 |
| 7 上游缺機制是倒置 | CK_AaaP 仍缺 audit |
| 8 平衡 = 結構正常化 | KG 比例失衡 = 待結構正常化 |

---

## 9. 元洞察 — KG 量化視角的真實價值

過去 RETRO 都是「commit 軌跡」+「lesson 數」維度。
本複查首次用 **KG 9091 entities + 比例** 視角，揭發：
- repository / db_table 比例失衡（純看 commit 看不到）
- erp domain 業務規模不符（純看程式碼看不到）
- service 邊界模糊（純看 fitness 看不到）

**程式圖譜 = 治理的 X 光片**。

對齊 owner 訴求 — 不只看「做了多少」，更看「結構是否合理」。

---

> **核心精神**：KG 不是裝飾，是治理的量化基礎。
> 9091 entities 揭發 4 個漂移 + 3 個健康面 = 整體架構真實樣貌。
> 對齊 v6.12 8 句立法 + L60 結構正常化 + L61 反治理範本。
