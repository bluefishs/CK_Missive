# KG + LLM Wiki + Memory Wiki — 三層 Wiki 系統整合覆盤 v1.0

> **建立**：2026-05-01（v6.2 階段性覆盤）
> **目的**：釐清三層 wiki 角色定位，找出整合機會 vs 該獨立的部分
> **跨 repo FQID**：`CK_Missive#KG_WIKI_INTEGRATION_REVIEW_v1.0`

---

## 0. 一頁式三層定位

| 層級 | 名稱 | 儲存 | 規模 | 服務對象 | 核心價值 |
|---|---|---|---|---|---|
| **L1** | KG（Knowledge Graph） | PostgreSQL + pgvector | 22,851 entities / 22,370 embedded / 2,145 edges / 29 types | LLM 工具（vector search / path）| **結構化關係 + 語意檢索** |
| **L2** | LLM Wiki | wiki/{entities,topics,synthesis}/ | 243 pages（219 entities + 4 topics + 20 synthesis） | LLM / owner 閱讀 | **敘事化業務知識**（給人讀懂）|
| **L3** | Memory Wiki | wiki/memory/{...}/ | 38 檔（diary 13 + patterns 6 + failures 5 + proposals 2 + critiques 4 + evolutions 2 + ...）| 坤哥意識體（自我記憶）| **agent 內在心智**（每天回看自己）|

**核心結論**：**三層各有不可取代的價值，不該合併**。但層間連結需治理。

---

## 1. 三層當前健康度

### L1 KG（最厚實）

```
22,851 entities × 29 types：
  py_function   6,125  ← 程式碼結構
  tender_record 5,973  ← 標案
  org           2,652  ← 機關/廠商
  tender_agency 1,831  ← 標案機關
  py_class      1,385
  py_module       915
  ts_interface    864
  ts_module       789
  api_endpoint    573
  ts_hook         323
  ...
embedded: 22,370 / 22,851 = 97.9%
```

**狀態**：✓ 真活，KG 是平台最厚實的知識層，貫穿 agent 工具呼叫。

### L2 LLM Wiki（中等發展）

```
wiki/entities/   219 pages（業務 entity，含 org / project / dispatch）
wiki/topics/       4 pages（極少）
wiki/synthesis/   20 pages（跨 entity 綜合）
wiki/sources/      0 pages（空 — 待調查）

Wiki↔KG 連結：208/219 = 94.9%（v5.9.8 backfill 後從 30% → 86% → 95%）
```

**狀態**：✓ entities 真活、⚠ topics 略少、✗ sources/ 完全空。

### L3 Memory Wiki（v5.10.2~v6.1 主要建設）

```
diary/        13 篇（每日寫，✓ 真活）
patterns/      6 篇（pattern_extractor cron 04:00）
failures/      5 篇（active=true 真接 auto_defense）
critiques/     4 篇（v6.0 新增，agent_critic 寫）
evolutions/    2 篇（autobiography 週日 18:00）
proposals/     2 篇（crystallizer 寫，等 owner 批）
crystals/      0 篇（owner 未批，鏈路 1B 半活原因）
preferences/   0 篇（crystallization apply 後寫，連動 crystals/）
```

**狀態**：6/8 子目錄真活，2 個空（owner 瓶頸，已記錄為 v5.13 backlog）。

---

## 2. 三層連結現況

### L1 KG ↔ L2 LLM Wiki：94.9% 連結率 ✓

```
wiki/entities/{slug}.md → frontmatter kg_entity_id: <UUID>
208 / 219 wiki entities 有 kg_entity_id
```

**狀態**：✓ 健康。剩 11 個 wiki entities 無 kg_entity_id（新增的 wiki 待 backfill）。

### L1 KG ↔ L3 Memory Wiki：弱連結 ⚠

```
diary/patterns/critiques 直接寫 query 內容，不引用 KG entity
僅 evolutions（autobiography）frontmatter 含 wiki_topics（連 L2）
```

**狀態**：⚠ 設計上 Memory Wiki 是 agent 自我記憶，不直接引用 KG。但若 critique 涉及具體 entity（如「老蕭」），目前是純文字無 KG 連結 → 統計分析時只能 grep 不能 join。

### L2 LLM Wiki ↔ L3 Memory Wiki：稀疏連結 ⚠

```
autobiography frontmatter 含 wiki_topics（top 3 wiki 命中）
diary entries 沒引用 wiki page
```

**狀態**：⚠ autobiography 連 L2，但 diary 不連。導致「agent 每天回看 diary」時無法主動展開到 wiki 補背景。

---

## 3. 整合機會 vs 該獨立的部分

### 該整合（提升 ROI）

| 整合點 | 內容 | 收益 |
|---|---|---|
| **I1** | wiki/sources/ 是空目錄 — 確認是 dead 還是設計待用 | 若 dead 直接刪；若待用要寫 cron 填 |
| **I2** | diary entries 加 entity 自動連結（grep KG entities → 自動 link） | agent 回看時可一鍵展開 entity |
| **I3** | critique 寫入時自動 tag 涉及 entity（4 篇都涉及「老蕭」這 case，但無 KG 標記） | 統計「哪些 entity 最常觸發 hallucination」變可能 |
| **I4** | Wiki↔KG 95% 連結率，補完剩 5%（11 entities） | 一致性提升 |
| **I5** | LLM Wiki topics 只 4 篇（vs entities 219），補主題綜合 | wiki RAG 時能覆蓋更多 query 維度 |

### 該保持獨立（不該合併）

| 理由 | 說明 |
|---|---|
| 三層 SoT 不同 | KG = 結構化事實 / Wiki = 敘事 / Memory = agent 主觀觀察 |
| 寫入頻率不同 | KG 即時（dispatch 建檔即入）/ Wiki 週期（compile cron）/ Memory 即時+每日批次 |
| 服務對象不同 | KG → tools / Wiki → human reading + RAG / Memory → agent self |
| 演化邏輯不同 | KG 不演化（只增加）/ Wiki 重編譯覆寫 / Memory 累積式不刪 |

---

## 4. 整合優化規劃

### 優先序

| 優先 | 動作 | 工作量 | ROI |
|---|---|---|---|
| **P0** | I1 wiki/sources/ 死活確認（grep wiki_compiler 看是否有人寫到此目錄） | 30 min | dead 即刪、活的補 cron |
| **P0** | I4 wiki↔KG 95→100% backfill（11 entities） | 30 min | 一致性 |
| **P1** | I2 diary entity auto-link（每日 cron 後處理）| 1 天 | agent 回看可展開 |
| **P1** | I3 critique entity tag（critic.review 結尾加 entity 抽取） | 半天 | 「哪些 entity 最常 hallucination」分析 |
| **P2** | I5 LLM Wiki topics 補編（4 → ~20） | 2 天 | wiki RAG 覆蓋面 |

### Phase B+C 既有 backlog（合併考量）

| Phase | 項目 | 與此規劃關係 |
|---|---|---|
| **B1** | KUNGE_PROGRESS_TRACKER 重整 | 獨立做 |
| **B3** | critic ADR-0028 silent fail 修 | 跟 I3 結合（同檔） |
| **C2** | fitness step 13 cron 健康度 | 獨立做 |
| **C1** | weekly_evolution_pipeline | 跟 I2 不衝突 |
| **C3** | 記憶寫入事件 bus | 整合三層連結時可順手做 |

---

## 5. 戰略性洞察

### 洞察 1：KG 是基礎層，不該往「敘事化」走

**反模式**：把 KG node 加長 description 欄位試圖「給人讀懂」。
**正解**：KG 保持結構化（id/type/name/embedding/edges），敘事化由 LLM Wiki 承擔。

### 洞察 2：LLM Wiki 是「業務領域翻譯層」

**核心價值**：把 KG 結構化資料翻譯成人讀的敘事。但**不該變成 agent 自我記憶**（混 layer）。
**範例**：wiki/entities/桃園市政府.md 寫該機關業務範圍 + 與本公司關係，但**不該寫**「上週坤哥跟此機關互動失敗 3 次」。

### 洞察 3：Memory Wiki 是 agent「主觀視角」

**核心價值**：坤哥從**第一人稱**寫自己的觀察、學習、信念。
**反模式**：把 Memory Wiki 當業務知識庫用。
**正解**：diary/patterns 內容可引用 KG entity（連結），但述說角度是「agent 怎麼看」非「事實是什麼」。

### 洞察 4：三層形成「客觀 → 描述 → 主觀」漸進光譜

```
KG（客觀事實）─→ LLM Wiki（敘事描述）─→ Memory Wiki（主觀觀察）
        ↑                ↑                    ↑
    工具呼叫           RAG / 閱讀          agent self
```

每層往下走，「主觀性」遞增、「機器可處理性」遞減。

### 洞察 5：v5.10.2~v6.1 是 L3 Memory Wiki 的建設期

之前 9 個 minor versions 主要在強化 L3（agent 主觀層），L1 KG 和 L2 LLM Wiki 變動極少。**v6.2+ 該往 L1↔L3 / L2↔L3 連結強化**（I2 / I3）。

---

## 6. 對應 KUNGE_PROGRESS_TRACKER 的位置

新整合優化項目 (I1-I5) 寫入 v6.2+ backlog，但**不算新 Gap**——是「已真活的 7 Gap 上的微調」。

對應戰略路線圖：
- v6.2 Phase B+C：技債 + 流程整合（既有）
- **v6.2 + I1+I4**（本次新增）：wiki/sources 死活 + wiki↔KG 補全 → 1 天可完
- v7.0+：I2/I3/I5（深度整合 vs 待 v6.2 看效果再決定）

---

## 7. 下一步建議

按 ROI 優先序：

**立即做（1 小時）**：
- I1 wiki/sources/ 死活確認 + I4 11 entities backfill

**v6.2 內做（半天-1 天）**：
- B1 tracker v2.0 重整（獨立）
- B3 critic ADR-0028（跟 I3 合併）
- C2 cron health fitness step 13（獨立）

**v6.3+ 觀察後決定**：
- I2 diary entity link
- I3 critique entity tag
- I5 LLM Wiki topics 擴充

---

> **三層 wiki 不是冗餘，是「客觀 → 描述 → 主觀」漸進光譜。**
> **整合機會在「層間連結」而非「合併同類項」。**
> **v6.2+ 重點：把 95% 連結補到 99%，把 dead 子目錄釐清，不做架構級重組。**
