# 圖譜治理覆盤 delta + 結構標準化建議 — 2026-06-12

> **觸發**：owner「覆盤各類主題圖譜、整合優化治理程序與架構、結構設計強化專案整合型與標準化」
> **基準**：更新 `KG_ARCHITECTURE_HOLISTIC_REVIEW_20260531.md` + `GRAPH_ECOSYSTEM_HOLISTIC_REVIEW_20260531.md`（12 天前 stale）為今日 live 數據
> **方法**：live DB（`ck_documents`）量化 + 跑 fitness audit 取真值，不憑印象

---

## 1. 五圖譜 live 快照（2026-06-12，26,837 entity / 2,158 edge）

| graph_domain | entity | embedding | mention>0 | 評 |
|---|---|---|---|---|
| knowledge | 9,727 | 6,796 (69.9%) | 4,989 (51%) | ⚠️ 見 §2 真因 |
| code | 9,091 | 9,091 (100%) | **0 (0%)** | 🔴 建表沒用表（L31）|
| tender | 7,804 | 7,804 (100%) | 7,804 (100%) | ✅ |
| erp | 215 | 215 (100%) | 84 (39%) | 🟡 業務量偏小 |

> 「DB 圖譜」= code domain 內 `db_table`(63) + `repository`(19)；非獨立 domain。

**邊密度**：2,158 edge / 26,837 node = **0.08 edge/node → 極稀疏**（多為孤立節點，非連通圖）。

---

## 2. 🔴 結構標準化缺陷 #1：graph_domain 誤標（最重要發現）

「knowledge embedding 僅 69.9%」是**假象**。真因＝**code 構件實體被誤標進 knowledge domain**：

| 證據 | 數字 |
|---|---|
| `py_function` 跨 domain 分裂 | knowledge **1,949** + code 4,409（同型實體兩個 domain）|
| code-type 實體誤標在 knowledge domain 總量 | **2,614**（py_function/module/class/ts_*/api_endpoint/db_table/repository）|
| 排除誤標後**真實** knowledge 語意 embedding | **6,693 / 7,113 = 94.1%** ✅（非 70%）|

**影響**：
1. 膨脹假性 embedding 缺口（70% vs 真 94%）→ 誤導「需 2,931 backfill」（真缺口僅 ~420 org/project）。
2. code 構件污染 knowledge domain（語意搜尋混入函式名）。
3. **根因＝code-graph ingest 與 knowledge ingest 各自建 py_function 實體，無統一 domain-tagging SSOT**。

---

## 3. 與 5/31 藍圖的 delta（12 天）

| 5/31 建議 | 5/31 狀態 | 今日 live | delta |
|---|---|---|---|
| 建議 1 Repository 擴展 1:3.5→1:1.5 | 🔴 18:63 | **49:71 = 1:1.45** | ✅ **比例達標**（repo 18→49）|
| ↑ 但 name-coverage（每表有同名 repo）| — | 46/71 ≈ 65% | 🔴 RED（25 表無同名 repo）— **指標歧義：比例 vs 覆蓋** |
| 建議 3 ERP KG ingest 補完 | P0 | erp 215 entity | 🟡 仍小，待補 |
| 建議 5 cross-domain 連結 audit | P2 規劃 | **已實作 step 71** | ✅ 落地 |
| ↑ tender_agency↔knowledge.org | — | **92.9%** | ✅ GREEN |
| ↑ wiki entity↔KG canonical | v5.9.8 曾 86% | **85/222 = 38.3%** | 🔴 **回歸**（KG 成長稀釋 / wiki backfill 沒跟上）|

---

## 4. 治理程序優化（本輪已修 + 待辦）

### 已修（commit 本輪）
- **cross_domain_link_audit + repository_coverage_audit 直接 host 呼叫 cp950 崩潰**（↔/≥ 字元）→ 補 `sys.stdout.reconfigure`，讓 audit 不論調用方式都穩。
- ⚠️ 範圍校正：經 `run_fitness_weekly.sh` 跑**不會崩**（`run_step` 已帶 `PYTHONIOENCODING=utf-8`）；崩潰只發生在 **owner/debug 直接 `python xxx.py`** 時。故此修是「ad-hoc 直跑韌性」非「fitness 路徑救火」——但仍屬 v6.18 8-audit 硬化漏網的 L49.8 同型，補齊一致性。

### 治理整合現況（澄清「孤兒治理」疑慮）
KG audit **未孤兒、未 silent fail**：step 19/20/21（repository_coverage / cross_domain_link / knowledge_dedup）在 `run_fitness_weekly.sh`（帶 PYTHONIOENCODING）；57b config_settings_drift（AST 衍生，L71）在主 `run_fitness.sh`。治理整合是健全的。

### 待辦
- **指標歧義收斂**：repository「比例 1:1.45 ✅」vs「name-coverage 65% 🔴」是兩個指標。建議 SSOT 定義 = name-coverage（更嚴、防散戶），比例僅參考。
- **cp950 全域 sweep audit**：v6.18 硬化逐檔漏網（本輪又揪 2）→ 建議一個「python audit cp950 guard 覆蓋率」檢查（同 `powershell_bom_audit` 思路），一次性掃出所有含中文/符號卻缺 guard 的 audit（治本，免再逐檔漏）。

---

## 5. 結構標準化建議（整合型強化）

### 建議 A（P0 數據品質）— graph_domain tagging SSOT
**問題**：2,614 code 實體誤標 knowledge domain。
**修法**：
1. 定義 SSOT 規則：`entity_type ∈ {py_*, ts_*, api_endpoint, db_table, repository}` → `graph_domain='code'`（強制）。
2. 一次性 migration：`UPDATE canonical_entities SET graph_domain='code' WHERE entity_type IN (...) AND graph_domain='knowledge'`（2,614 筆；**需 owner 確認＋備份**，破壞性 DB 變更）。
3. 新 fitness audit `graph_domain_tagging_audit`：偵測 entity_type 與 graph_domain 不符（防回退）。
4. 修 ingest 源頭（code-graph + knowledge ingest）統一 domain 標記，避免再生。

### 建議 B（P1 連通性）— 邊稀疏 + wiki↔KG 回歸
**問題**：0.08 edge/node 極稀疏；wiki↔KG 38.3% 回歸。
**修法**：
1. wiki↔KG backfill 重跑（`scripts/sync/backfill_wiki_*.py`），把 38.3%→回 80%+。
2. 跨域邊補建（tender_record↔wiki narrative 「未實作」段補上）。
3. cross_domain_link_audit 門檻納 alert（回歸即 RED）。

### 建議 C（P2 ROI）— code 圖譜 mention=0 的用途定位
**問題**：9,091 code 實體 mention=0（建表沒用表，L31）。
**抉擇**：code-graph 的價值在「AST 橋接治理」（L71，餵 config_drift/命名 audit），**非語意搜尋**。建議明確定位：code domain **不追 mention/embedding ROI**，改追「被 fitness audit 消費的覆蓋率」當其 KPI（與 knowledge/tender 的 RAG ROI 分開計）。→ 避免用錯指標誤判 code 圖譜「死」。

---

## 6. 整體結論

- ✅ **健康**：tender 圖譜（100% emb/mention/92.9% 跨域連結）、repository 比例達標、KG audit 已整合進 weekly fitness。
- 🔴 **真問題（去除假象後）**：①graph_domain 誤標 2,614（標準化）②wiki↔KG 連結回歸 38.3% ③邊極稀疏 ④code 圖譜用錯 ROI 指標。
- 🟢 **假警報澄清**：knowledge embedding 真實 94.1%（非 70%）；code mention=0 是「指標用錯」非「圖譜死」。
- **本輪已修**：2 圖譜 audit cp950 host 韌性。
- **待 owner 拍板**：建議 A 的 2,614 筆 domain migration（破壞性 DB 變更，需備份＋確認）。

> 核心精神（呼應 L31/L71）：**圖譜是結構地圖，不同 domain 該用不同 ROI 指標**（knowledge/tender 用 RAG 連結率、code 用 fitness 消費覆蓋率）；用單一指標套全圖譜會製造假象（如 knowledge「70%」、code「mention 0」）。
