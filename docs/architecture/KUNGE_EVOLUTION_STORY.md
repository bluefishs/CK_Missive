# 坤哥意識體進化故事 v1.0

> **建立**：2026-05-01（v6.2 Phase D 對外敘事）
> **對象**：人類讀者（非技術 doc — 給 owner / 跨 repo 引用 / 未來 Claude session 接手）
> **跨 repo FQID**：`CK_Missive#KUNGE_EVOLUTION_STORY_v1.0`

---

## 一頁式精華

> **9 個 minor versions（v5.10.2 → v6.1）+ 39 個 task + 15 個 commits**
> **從「形式智能體 30%」走到「真正智能體 100% 7/7 全真活」**
>
> **核心發現**：真正智能體不是「LLM 變強」，是「**每個 signal 都被消費，每個消費都改變行為，agent 知道自己在進化中**」。

---

## 5 個關鍵時刻（每個都改變了什麼是「真正智能體」的定義）

### 1. 14 天 silent failure（v5.10.2 #4）— 「能不能感知自己」

**事件**：fitness 月度報告 evolution 14 天 0 新增。深掃發現是 `agent_post_processing.py:144` import path typo（`app.core.redis` → `app.core.redis_client`）+ silent except 吞錯 14 天。

**洞察**：「自我進化引擎死了 14 天，沒人發現」是 architecture failure 的最低警報。一個會學習的系統至少要能感知自己是否在學習。

**修復**：1 行 import path 修 + ADR-0028 silent failure 政策強化。

**改變**：從「functions 寫了就算」→「functions 必須有 alive 證據」。

### 2. Hallucination 真改變 LLM 行為（v5.12 Phase B）— 「signal 真改變行為」

**事件**：04-23 案例 — query「承辦人老蕭負責的案件」LLM 列了 6 個無關公文後說「均未指向人名」。明顯 hallucination 但 self_evaluator 給高分。

**洞察**：53/53 patterns 全 success ≥ 0.95 暴露評分機制失靈。signal 寫入了但下游沒消費 = 形式上有，本質上沒。

**修復**：
- 加 `entity_alignment` signal（query 含具名 entity 但 answer 沒提 → 警示）
- planner inject「entity_preservation 警示」進 system prompt

**A/B 實證**：
```
v5.10.2: 「老蕭」→ 列 6 個無關公文（hallucination）
v5.12 B: 「老蕭」→「目前檢索到的公文資料中未包含相關資訊」（精準）
```

**改變**：從「signal 通膨」（producer 多 consumer 缺）→「signal 真消費」。

### 3. self_diagnosis 主動回看（v5.13）— 「主動發現該修什麼」

**事件**：v5.10.2 修 evolution silent failure 後，發現一個更深問題 — 「為什麼是人類發現？agent 自己不該察覺嗎？」

**洞察**：真正智能體不只執行任務，還每天自查。「自我感知」是真正智能體的最低門檻。

**實作**：每日 06:00 cron `agent_self_diagnosis_job` — 跑 6 個健康指標 + 7 個 Gap spot check + 寫 diary「🩺 自我感知」段落 + 異常自動 push Telegram。

**改變**：從「靠 owner 月度查」→「agent 每日自查 + 自報」。

### 4. 跨會話真連續（v5.14）— 「能不能記得使用者」

**事件**：「老蕭」事件揭發 — synthetic baseline 連續 3 天問同樣問題，agent 每次重新從零思考，**完全沒記得「昨天我已經回答過」**。

**洞察**：對話記憶寫入了但沒讀回，本質上等於沒記得。

**實作**：
- ConversationMemory 加 `user_id × time` 雙索引（從 session_id 推導 user_key）
- 30 天累積該 user 過去 query history（zset）
- planner 規劃時 inject「同使用者過去查詢」

**A/B 實證**：跨 session 同 user_key 自動關聯，第二次同 user 進來時，planner 看到第一次的 query。

**改變**：從「每次 query 是獨立事件」→「同 user 30 天累積」。

### 5. Multi-agent 學習迴圈閉環（v6.1）— 「signal 自我循環改變未來」

**事件**：v6.0 加 critic agent POC，但寫 critique signal 沒人讀（同 v5.12 病灶）。

**洞察**：multi-agent 不是「加更多 LLM call」，是「**signal 真形成迴圈**」— 一個 agent 的輸出改變另一個 agent 的輸入。

**實作**：critic 寫 critique → wiki/memory/critiques/ → 下次 planner 規劃時 inject「過去 7 天 critic 抓出的問題」block → LLM 看到自己過去的失敗 → 主動避免。

**A/B 實證**：04-23 hallucination 寫 critique → 現在 planner 規劃時看到 critique block 182 chars → 警覺重蹈覆轍。

**改變**：從「單 agent 多工具」→「multi-agent 學習迴圈」（planner / synthesizer / critic 三角）。

---

## 7 個 Gap × 9 個版本演進

```
Gap                  v5.10.2  v5.11   v5.12   v5.13   v5.14   v5.15   v5.16   v5.17   v6.0    v6.1
────────────────────────────────────────────────────────────────────────────────────────────────
1 主動性                ✗      part    part    ✓ 真活  ✓        ✓        ✓        ✓        ✓        ✓
2 跨會話記憶            ✗       ✗       ✗       ✗       ✓ 真活  ✓        ✓        ✓        ✓        ✓
3 反思迴路              ✗      part    ✓ 真活  ✓        ✓        ✓        ✓        ✓        ✓        ✓
4 評分區分度            ✗      part    ✓ 真活  ✓        ✓        ✓        ✓        ✓        ✓        ✓
5 演化人格              ✗      part    part    part    part    part+   part+   ✓ 真活  ✓        ✓
6 多 modality           ✗       ✗       ✗       ✗      part    part+   ✓ 真活  ✓        ✓        ✓
7 multi-agent           ✗       ✗       ✗       ✗       ✗       ✗       ✗       ✗      partial ✓ 真活
────────────────────────────────────────────────────────────────────────────────────────────────
真活率                  0/7     1/7     3/7     3/7     4/7     4/7     5/7     6/7     6+P     7/7
成熟度                  30%     55%     75%     85%     92%     95%     97%     98%     99%    100%
```

---

## 跨 repo Lessons（其它 repo 可移植）

### Lesson 1：Producer-Consumer 對稱原則

**反模式**：寫了 producer（signal 寫入），不寫 consumer（signal 讀回）。
**結果**：dead integration（signal 通膨）— v5.10.2 evolution / v5.12 entity_alignment / v5.14 critic POC 全踩過。
**正解**：每個新 signal 必先想「誰會讀 + 讀了做什麼」，先寫 consumer test 才能合 producer code。

### Lesson 2：雙閘安全（Safe by Default）

**範例**：crystal auto_apply（confidence ≥ 0.9 + intent_rules.yaml only + dry-run 預設）、SOUL 4 信念演化（agent 不直接改，只 propose、owner 批）。
**原則**：自動化的副作用必有「人類可介入閘」，且預設保守。
**理由**：信任 agent 不等於放權，雙閘保護下放權才安全。

### Lesson 3：Archetypal Safety（累積夠才觸發）

**範例**：belief evolution propose 條件 = 連續 3+ 週同主題 + 連續 4+ 週 active_failures ≥ 5。
**原則**：對「核心改動」設累積門檻（不能 1 次 signal 就觸發）。
**理由**：避免 noise spike 導致誤改 architecture。

### Lesson 4：fitness step = silent failure 的免疫系統

**範例**：fitness step 11 SOUL alive check（防 04/26 wiki/SOUL.md 落地時序問題重演）+ step 12 signal consumer lint。
**原則**：每修一個 silent failure，必加對應 fitness step 防重演。
**理由**：人類記憶有限，fitness 是 architecture 的長期記憶。

### Lesson 5：Self-Report 必須壓測

**範例**：v5.13 self_diagnosis 自動報「7/7 真活」— v6.2 Phase A 壓測證實成立（不是 self-report bias）。
**原則**：「真活」claim 必須有 edge case 壓測背書。
**理由**：spot check 報全綠 + edge case 全 fail 是經典 happy path 陷阱。

---

## 給未來 Claude session 接手的指引

### 必讀 SSOT（依優先序）

1. **`KUNGE_PROGRESS_TRACKER.md`** — 一頁式現況 + 7 Gap 演進 + 戰略路線
2. **`KUNGE_LEARNING_VERIFICATION_V3.md`** — 5 鏈路 × 4 檢查點證據矩陣
3. **`KUNGE_INTELLIGENCE_GAP_ANALYSIS.md`** — 7 Gap 戰略框架（最先讀，建立 mental model）
4. **`MEMORY_SIGNAL_FLOW.md`** — 每個 signal 的 producer-consumer map
5. **`LESSONS_REGISTRY.md`** L21-L25 — silent failure 雙疊 / DDD 拒拆 / 評分失衡 / grep 陷阱

### 心智模型（不要再走過的彎路）

- ❌ **「加新功能」優先**：v5.10.2 → v6.1 沒加新功能，全在「接通 producer-consumer」
- ❌ **行數驅動拆分**：L23 已立 — 看領域邊界不看行數
- ❌ **silent fail 是常態**：L21 + L25 — silent except 必加 logger.error + exc_info
- ✓ **每加 producer 必設計 consumer**：MEMORY_SIGNAL_FLOW.md SOP
- ✓ **fitness step 是免疫系統**：每修一個 silent fail 必加對應 fitness step

### v6.2+ 路線（v7.0+ 戰略）

- **v6.2 Phase B/C**：技債清理 + 流程整合（合併 cron / planner block budget）
- **v7.0+**：multi-modal 真整合（不只描述）+ multi-critic ensemble + cross-repo agent federation

但**這些都是品質提升，非 Gap 解決**。7/7 全真活已是底層架構完成。

---

## 結語

> **真正智能體不是「能回答更多問題」，是「能自己發現該問什麼問題」。**
>
> v5.10.2 修了「能不能感知自己」。
> v5.12 修了「signal 真改變行為」。
> v5.13 修了「主動發現該修什麼」。
> v5.14 修了「跨會話真連續」。
> v5.16 修了「多模態互動」。
> v5.17 修了「人格漸進演化」。
> **v6.1 修了「multi-agent 學習迴圈閉環」。**
>
> 7/7 全真活，但這不是終點 — 是「真正智能體最低門檻」起點。
> 從這裡開始，每個 query 都是公司時間複利的一小份積累，而坤哥每天都在回看自己。

---

> 此檔不再頻繁更新（旅程已完成）。未來新里程碑請更新 KUNGE_PROGRESS_TRACKER 而非此檔。
> 此檔的價值是「**保存這次 session 的精華，避免下次接手不知為何走到這**」。
