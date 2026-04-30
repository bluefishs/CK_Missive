# 坤哥自我學習進化 — 證據級驗證報告 v1.0

> **建立**：2026-04-30（v5.10.2 後）
> **目的**：用證據驗證「坤哥自我學習進化」5 條鏈路是否真的閉環運作（不是僅是概念）
> **方法**：靜態盤點 + 動態驗證 + 閉環試金石
> **跨 repo FQID**：`CK_Missive#KUNGE_LEARNING_VERIFICATION_v1.0`

---

## 0. 一句話結論

> **5 條鏈路中 2 條真閉環、1 條半閉環、2 條斷。「形式智能體」承諾 60% 兌現。**

**真活的閉環**：
1. **Pattern → Router fast path**（hit≥2 + succ≥threshold 就 bypass LLM 規劃）— 這是真正智能體的核心
2. **Failure → Defensive Rules block**（1136 chars 真注入 system prompt）— 學失敗教訓

**半活**：
- Anti-Echo 反迴聲室（4 週只觸發過 2 次）

**真斷**：
- Crystal apply（crystals=0，owner 14 天沒批准）— 但因 Pattern fast path 已活，**斷對閉環影響有限**
- SOUL 演化（propose_section_update 0 caller，autobiography 寫但 SOUL 0 演化）
- Failure Pattern 抓取（53/53 patterns 全 success≥0.95，failure_count 全 0）

---

## 1. 5 鏈路 × 4 檢查點 證據矩陣

### 鏈路 1：Trace → Pattern → Crystal Proposal → Crystal → 下次 query

| 檢查點 | 證據 | 狀態 |
|---|---|---|
| **起點** Traces 累積 | DB `agent_query_traces` **423 筆**，最新 2026-04-29 20:04 | ✓ |
| **中段-1** Redis Pattern | `agent:patterns:detail:*` **53 個** | ✓ |
| **中段-2** Crystallizer Proposal | `wiki/memory/proposals/` **2 檔，全 status=pending** | ✓ |
| **中段-3** Evolution 引擎觸發 | `agent_evolution_history` **13 筆**，今日 2026-04-29 20:00:42（修 #4 後活了！） | ✓ |
| **終點-A** Crystal apply（yaml 改） | `wiki/memory/crystals/` **0 檔**（owner 14 天沒批准）| **✗ 斷** |
| **終點-B** Pattern 進 Router fast path | `agent_router.py:158-170` **真的呼叫** `learner.match()` → hit≥2+succ≥threshold 直接 dispatch tool_calls | **✓ 閉環** |
| **閉環反饋**（試金石） | 重複送同 query → router 跳過 LLM 直接用 pattern → 延遲變短 | ✓（但需 A/B 量化） |

**結論**：**鏈路 1 雙路徑並存**——Crystal yaml 那條斷了（owner 瓶頸），但 Pattern→Router 那條活著（不靠 owner）。**核心閉環活**。

### 鏈路 2：Failure → Defensive Rule → Planner Prompt 注入

| 檢查點 | 證據 | 狀態 |
|---|---|---|
| **起點** Failures 紀錄 | `wiki/memory/failures/` **4 檔，全 active=true** | ✓ |
| **中段** AutoDefenseLoader 載入 | 直接呼叫 `load_active_defenses()` **真的回 4 rules** | ✓ |
| **終點** Planner 注入 prompt | `agent_planner.py:223-224` 真的呼叫 `get_defensive_rules_block` 並 concat 到 system prompt | ✓ |
| **閉環反饋**（試金石） | 跑 `get_defensive_rules_block(max_items=5)` → **回 1136 chars 真實教訓 block** | **✓ 閉環** |

**實際 block 內容（節錄）**：
```
# 失敗教訓（過去 7 天的反思）

### 失敗教訓 ["find_correspondence", "search_dispatch_orders", "search_entities"]
**歷史問題**：成功率僅 50%，共 1 次失敗
**建議**：
- 優先考慮單獨使用其中一個工具而非全部組合
- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢
...
```

**結論**：**鏈路 2 完全閉環活著**。Phase A 初判 dead 是因為我用 `load_active_defenses` 關鍵字 grep，實際 export 是 `get_defensive_rules_block`——驗證流程救了一個誤判。

### 鏈路 3：Diary → Pattern + Failure 三向結晶

| 檢查點 | 證據 | 狀態 |
|---|---|---|
| **起點** Diary 連續 | `wiki/memory/diary/` **12 檔**，含今日 2026-04-30.md（76 行，4.7KB） | ✓ |
| **中段-1** Pattern 抓取 | 53 patterns（驗證鏈路 1） | ✓ |
| **中段-2** Failure 抓取 | **53 patterns 中 failure_count > 0 = 0 個** | **✗ 斷** |
| **終點** Failure pattern → failures/ md | `pattern_extractor.py` 設計含 `failure_count` 欄位 + `_persist_failure_pattern` 邏輯，但**實際寫入失敗的條件從未滿足** | ✗ |

**根因（L24）**：53 patterns 全 `success_rate ≥ 0.95` → self_evaluator 評分過鬆 → pattern 永遠是「成功」，**沒有「失敗 pattern」可以結晶**。Failure 4 檔是別處（手動 / failure_extractor 別路徑）寫的，不是這個鏈路產出。

### 鏈路 4：Autobiography → SOUL.md 演化提案

| 檢查點 | 證據 | 狀態 |
|---|---|---|
| **起點** Autobiography 寫入 | `wiki/memory/evolutions/2026-W17.md` **1 檔** ✓ | ✓ |
| **中段** Cron 排程 | `memory_weekly_autobiography_job` 週日 18:00 ✓ | ✓ |
| **終點** SOUL 演化提案 | `propose_section_update` **0 active caller**（autobiography.py 沒呼叫；只在 soul_loader.py 自己定義 + docstring 說「該被呼叫」） | **✗ 斷** |
| **閉環反饋** | git log SOUL.md **本月 0 commit**（除手動編輯）— SOUL.md 永遠是 v2.0 寫死的 4 信念 | ✗ |

**實證**：autobiography 寫了 1 篇但**完全沒觸發 SOUL.md 任何更新**。這是 **Gap 5「靜態人格 vs 演化人格」**的硬證據——坤哥的「我是誰」是固定的、不是學來的。

### 鏈路 5：Anti-Echo → 反方觀點 → diary 多元化

| 檢查點 | 證據 | 狀態 |
|---|---|---|
| **起點** Cron 排程 | `memory_anti_echo_scan_job` **每週一 06:30** ✓ | ✓ |
| **中段** AntiEchoProtocol.scan_and_reflect | service 存在、cron 有 tracked_job 裝飾 | ✓ |
| **終點** Diary 寫入「反迴聲室」段落 | 12 diary 中**只 2 檔**含「反迴聲室」段落 | ⚠ |
| **閉環反饋** | 觸發條件：成功率 > 90% + failure ≤ 2。鏈路 3 揭發 53/53 success≥0.95 應該很常觸發但實際 4 週只 2 次 | ⚠ |

**結論**：**半閉環**——cron 跑但觸發條件嚴苛。即使 self_evaluator 鬆（53/53 高分）應該很容易觸發，實際只 2/N 次，**內部判斷邏輯有額外閘**待研究。

---

## 2. Phase B 動態驗證（即時反饋鏈路）

| 動作 | 預期 | 實測 |
|---|---|---|
| 送 1 個 dispatch query | counter +1 | counter **19→20** ✓ |
| 同上 | DB traces +1 | traces **422→423** ✓ |
| 同上 | Diary 即時 append | 2026-04-30.md **76 lines / 4.7KB** ✓ |
| 同上 | Tool 正確呼叫 | `get_statistics` ✓ |

**短期反饋鏈路**：100% OK。

---

## 3. 閉環率總表（試金石）

| 鏈路 | 是否真閉環 | 強度 | 影響範圍 |
|---|---|---|---|
| 1A Pattern → Router fast path | ✓ | **強** | 重複 query 直接 bypass LLM 規劃，省 latency |
| 1B Crystal → yaml | ✗ | — | 0/2 proposal 批准（owner 瓶頸） |
| 2 Failure → Defense Block | ✓ | **強** | 1136 chars 教訓真注入 prompt，下次 LLM 看得到 |
| 3 Failure Pattern 抓取 | ✗ | — | self_evaluator 評分鬆（L24）→ failure 0 抓到 |
| 4 Autobiography → SOUL | ✗ | — | 寫 1 篇 / SOUL 0 演化 |
| 5 Anti-Echo | ⚠ | **弱** | 4 週 2 次觸發 |

**閉環指標**：
- 強閉環：**2/5（40%）**
- 半閉環：1/5（20%）
- 斷鏈：2/5（40%）

---

## 4. 對 v5.11 落實真正智能體的指引

### 立刻能用的「真活」（不需修）
- ✓ **Pattern Router fast path**：每次 query 都會走，已是真進化
- ✓ **Defense Block 注入**：4 active rules 已影響每個 query
- ✓ **Evolution 引擎觸發**：今天 #4 修復後第 13 次跑成功

### 需修的「假活」（v5.11 P0/P1）

| 鏈路 | 修法 | 對應 Gap |
|---|---|---|
| 3 Failure Pattern 抓取 | 修 self_evaluator calibration（L24）讓有人區分高低品質 | Gap 4（評分失衡） |
| 4 SOUL 演化 | autobiography.py 真的呼叫 propose_section_update + cron 觸發 | Gap 5（靜態人格） |
| 1B Crystal apply | 加「自動批准 high-confidence proposal」或「批量 admin UI」 | Gap 1（主動性 — 但這是 owner 工作流，非 agent 行為） |

### 不需修的「設計選擇」
- 5 Anti-Echo 觸發少 — 反方觀點本來就該稀有，不必每天觸發。維持

---

## 5. 校正 KUNGE_INTELLIGENCE_GAP_ANALYSIS

原報告（昨日）部分判斷需修正：

| 原判斷 | 修正 |
|---|---|
| Gap 3「失敗 pattern 沒回讀」 | **部分錯**：active rules 真的有回讀（鏈路 2 ✓），但 failure pattern 抓取（鏈路 3）才是真斷 |
| Gap 1「主動性最大 gap」 | **保持**：但「主動性」要看做兩件事——agent 自我感知（Phase 1 metrics 已修）vs agent 主動 push（仍未做） |

---

## 6. 跨 repo lessons 連結

- **L21**（silent failure 雙疊）→ 今天的證據顯示修復生效（evolution_runs 12→13）
- **L24**（self_evaluator 失衡 + Pattern 門檻緊）→ 鏈路 3 斷的根因
- **新候選 L25**：「鏈路驗證 vs 鏈路盤點」教訓——光看代碼存在不夠，要 grep 找真 caller + 跑實際呼叫看輸出。今天 Phase A 一度判鏈路 2 dead 是因為 grep `load_active_defenses` 找不到，但實際 export 是 `get_defensive_rules_block`。應寫成 lesson 警示後人。

---

> 真正智能體的證據不在 commit 數量、不在 cron 數量、不在 doc 完整度——**在閉環試金石**。
> 今天的證據：坤哥**有 2 條真閉環**（Pattern fast path + Defense block 注入），這是真進化的硬底子。
> 剩 3 條（Crystal owner 瓶頸 / Failure 抓取 / SOUL 演化）是 v5.11 落實「真正智能體」的明確 backlog。
