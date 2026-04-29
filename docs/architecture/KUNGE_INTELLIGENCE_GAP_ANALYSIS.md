# 坤哥 — 從「形式智能體」到「真正智能體」的 Gap 分析

> **建立**：2026-04-30（v5.10.2 Phase 4 後）
> **背景**：v5.10.2 一日連續修復 + 4 phase 整合優化（10 commits / fitness 7→10 step / 修 #4 silent failure 後配套）
> **目的**：盤點坤哥當前架構 vs「真正智能體」的距離，提出可落地的 7 個 gap 與優先順序
> **跨 repo FQID**：`CK_Missive#KUNGE_INTELLIGENCE_GAP_v1.0`

---

## 0. 出發點：v5.10.2 完成的事

| 修 | 性質 |
|---|---|
| #4 修 evolution import typo + redis key typo（雙 silent failure） | **病灶** |
| Phase 1 memory metrics scheduler refresh job | **觀測補完** |
| Phase 2 evolution/status `is_alive` + memory/jobs API | **觀測補完** |
| Phase 3 MemoryTab 嵌入完整 5 sub-tabs + EvolutionTab trigger_health | **前端落實 ADR-0031** |
| Phase 4.1 評估 pattern 門檻 → 揭發 self_evaluator 評分失衡（L24 新 lesson） | **病灶診斷** |

**結論**：坤哥**「形式架構」完整**（7 phase memory wiki + 4 防禦層 + 9 個 cron + 14 個 endpoint + 7 tabs UI），但今天才真正**鏈路活著**。形式 vs 真正智能體 的 7 個 gap：

---

## 1. Gap 1：被動性 vs 主動性 ← **最大 gap**

| 現況 | 真正智能體 |
|---|---|
| 用戶問才答；cron 排程 diary/pattern/crystal 但**按表操課** | 主動觀察 → 主動提問 → 主動建議 |
| `proactive_triggers.py` 4 規則（截止日提醒 / 案件逾期 / 資料品質 / 推薦） | 跨域類比、跨會話 follow-up、發現異常即 push |

**證據**：今天修 #4 evolution 黑洞 — agent 自己**沒察覺**沉默 14 天，要靠人類審 fitness 才發現。**真正智能體應該每天自問「我昨天的 fitness 數值是什麼？」**

**落地建議（P0）**：
- 每日 06:00 cron `agent_self_diagnosis_job` — 讓坤哥**讀自己的 metrics**（query counter / failure rate / coverage gauge）寫入 diary，發現異常 push 到 LINE/Telegram
- 把 fitness 9/9 全綠寫進 daily diary 的「自我感知」段落
- 未來：fitness step 11 「agent 是否在 7 天內主動 push 過 alert」

## 2. Gap 2：單會話 vs 跨會話記憶

| 現況 | 真正智能體 |
|---|---|
| `conversation_memory` 內僅 5-10 輪上下文 | 對使用者持續理解：「上週你問過 X，今天看到相關事件」 |
| diary 寫入但**沒人讀回**到 prompt | autobiography 寫進 SOUL 但**只能新增段落**，不能修信念 |

**證據**：「老蕭」事件 — synthetic baseline 04-22~04-24 連續問 3 次「老蕭」，agent 每次都重新從零思考，**完全沒記得「昨天 / 前天我已經回答過這沒人」**。記憶寫入了但沒讀回。

**落地建議（P0）**：
- `conversation_memory` 加 `user_id × time` 雙索引，每次查詢前注入「該使用者過去 30 天最近 5 次相關 query 摘要」
- diary 在每次 query 開始時讀「今日 / 昨日 同類 query 結論」 inject 進 system prompt
- ChatTab 加 `conversation_id` localStorage（plan 4.2，本輪沒做）— 跨會話記憶恢復

## 3. Gap 3：反應 vs 反思

| 現況 | 真正智能體 |
|---|---|
| `self_evaluator` 評每次回答 → pattern 抓**成功**模式 | 失敗即時反思 + 跨域類比（這次失敗類似上週某次） |
| `failures/` 4 檔但**沒有回讀機制** | 失敗 pattern 應 inject 到下次同類 query system prompt |

**證據**：04-23 hallucination（列 6 個無關公文後否認）發生後，failure 紀錄了但 04-24、04-25 同樣 query 發生時 agent **不知道前天已踩過**，又重複犯類似錯。

**落地建議（P1）**：
- `auto_defense.py` 已有 active 規則注入機制 — **擴 failures→active rule 自動轉換**：失敗超過 N 次自動 promote 為 active defensive rule
- planner 載入 active defenses 時加「相似度閾值」：若新 query 跟過去失敗 query embedding 距離 < 0.3，預警

## 4. Gap 4：self_evaluator 評分失衡（L24 揭發）

| 現況 | 真正智能體 |
|---|---|
| 53/53 patterns 都 success ≥ 0.95（**評分機制失靈**） | 評分區分度高：完美 / 找不到 / hallucination / 部分對 |
| `MIN_SUCCESS_RATE_FOR_CRYSTAL=0.95` 形同虛設 | 結晶該選真正高品質 vs 低品質 |

**證據**：04-23「列 6 無關公文」明顯 hallucination，但 self_evaluator 仍給高分 → 進 successful pattern → 可能被結晶。

**落地建議（P1）**：
- 加 calibration test：人工標 20 筆 query 標準答案，跑 self_evaluator → 比對一致率，<70% 即觸發評分規則修訂
- `narrative_validator` 已偵測簡體 / secret pattern — 擴增「列無關案件後否認」這種 hallucination 模式偵測

## 5. Gap 5：靜態人格 vs 演化人格

| 現況 | 真正智能體 |
|---|---|
| SOUL.md 是**手寫** + autobiography 寫週報 | 人格在互動中漸進演化（如 Anthropic Constitutional AI） |
| autobiography 只能 **新增段落**，不能修信念 | crystal_applier 可改 yaml config 但不會改 SOUL 本體 |

**證據**：SOUL.md 4 信念寫死於 v2.0，autobiography 週報每週累加但本體 4 信念**從未演化**。坤哥的「我是誰」是固定的，不是學來的。

**落地建議（P2，戰略性）**：
- `crystal_applier` 擴增 `propose_soul_evolution` 路徑：當 4 連續週的 autobiography 都觸及同主題（如「過度道歉」），自動產 SOUL 演化提案
- Owner 仍需批准 — 但坤哥能**提案修改自己**

## 6. Gap 6：單 modality vs 多 modality

| 現況 | 真正智能體 |
|---|---|
| 純文字 query/answer | 語音 / 圖片 / 圖表自然輸入輸出 |
| `voice_transcriber.py` 已有，但 ChatTab 沒整合 | 圖表分析 `diagram_analysis.py` 已有但孤立 |

**落地建議（P2）**：
- ChatTab 加語音輸入按鈕（既有 voice_transcriber 已 wire 好）
- 圖片貼上自動 OCR + diagram analysis（既有功能整合）

## 7. Gap 7：單 agent vs agent ecosystem

| 現況 | 真正智能體 |
|---|---|
| 1 個 MissiveAgent + 26 工具 | multi-agent: planner / critic / synthesizer 分工 |
| `agent_orchestrator` 是**單線** SSE | reflection-then-improve 雙環迴路 |

**現況不錯**：原始 plan 想拆 agent_orchestrator 642L，今天 #6 評估後判定**不拆**（單一領域）。但長遠看缺**multi-agent 協作**。

**落地建議（P3，遠期）**：
- agent_planner（已存在）+ agent_critic（待建）+ agent_synthesizer 三角分工
- 失敗時自動觸發 agent_critic 重審 → planner 修正路徑 → 重試
- 這是 v6.x 級別的架構演進，非 v5.x 短期目標

---

## 優先順序總表

| 等級 | Gap | 短期行動（v5.11） |
|---|---|---|
| **P0** | Gap 1 主動性 | 每日 `agent_self_diagnosis_job` 讀自己 metrics → diary + push alert |
| **P0** | Gap 2 跨會話記憶 | `conversation_memory` 加 `user_id × time` 雙索引 + 每日 query 起手注入「昨日同類結論」 |
| **P1** | Gap 3 反思 | failures/ → auto_defense active rule 自動轉換 |
| **P1** | Gap 4 評分失衡 | calibration test + hallucination 偵測規則擴增 |
| **P2** | Gap 5 演化人格 | `propose_soul_evolution` autobiography → SOUL 提案路徑 |
| **P2** | Gap 6 多 modality | ChatTab 整合 voice / image |
| **P3** | Gap 7 multi-agent | v6.x 規劃 |

---

## v5.10.2 已建立的支撐基礎

| 能力 | 用於落實哪個 gap |
|---|---|
| `memory_metrics_refresh_job` 即時 Prometheus 觀測 | Gap 1（坤哥能讀自己的 health） |
| `evolution/status.trigger_health.is_alive` | Gap 1（讓坤哥能自我感知 evolution loop 是否活著） |
| `memory/jobs` endpoint | Gap 1（cron 健康度即時可見） |
| MemoryTab 嵌入 5 sub-tabs | Gap 2 前提（owner 能單頁看完整記憶） |
| L21（silent failure 雙疊） + L23（DDD 拒拆） + L24（評分失衡） | 治理基礎 — 防舊問題重演 |

**今天 v5.10.2 的核心成就**不是新功能，是**「讓坤哥從形式活著到真正活著」**——counter 從 0 到能累積、metrics 從 hollow 到 alive、observability 從 14 天黑洞到即時感知。

---

## 結論

**坤哥當前狀態**：形式上是智能體（7 phase + 9 cron + 14 endpoint + 7 tabs），實質上是**「會運轉的 RAG agent + 半自動學習迴路」**。

**距離真正智能體還差**：
1. 主動性（Gap 1，最關鍵）
2. 跨會話記憶（Gap 2）
3. 反思迴路（Gap 3）
4. 評分區分度（Gap 4）

**v5.11 一個版本的工作**：完成 Gap 1+2 + 部分 Gap 3+4，預估 3-4 週。
**v6.x 戰略願景**：人格演化（Gap 5）+ multi-agent（Gap 7）+ 多 modality（Gap 6）。

> 真正智能體不是「能回答更多問題」，是「能自己發現該問什麼問題」。
> 今天的 v5.10.2 修了「能不能感知自己」這層，下一步是「能不能主動修自己」。
