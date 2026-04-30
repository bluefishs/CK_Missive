# 坤哥意識體進化進度追蹤 SSOT v1.0

> **建立**：2026-05-01（v5.13 Phase 4，「全部完成並持續追蹤」訴求）
> **目的**：單點追蹤坤哥從「形式智能體」到「真正智能體」的演進
> **更新機制**：
> - **手動**：每次 minor version（v5.10 → v5.11 → ...）發布後人工更新
> - **自動**：每日 06:00 `agent_self_diagnosis_job` 自動跑 Gap 健康度檢查 + 寫 diary
> **跨 repo FQID**：`CK_Missive#KUNGE_PROGRESS_TRACKER_v1.0`

---

## 0. 一頁式現況（看這裡就夠）

| 維度 | 當前狀態 |
|---|---|
| **5 條鏈路真活率** | 5/5 (100%) ✓（v5.12 達成）|
| **斷鏈** | 0 ✓ |
| **孤兒 signal** | 0 完全孤兒 ✓ |
| **Fitness step** | 12/12 全綠 |
| **7 個 Gap 解決度** | 4 真活、2 部分、1 戰略保留 |
| **下一里程碑** | v5.14 跨會話 query history（深層 Gap 2）|

---

## 1. 7 個 Gap 演進矩陣

| Gap | 主題 | v5.10.2 | v5.11 | v5.12 | **v5.13** | 計畫 |
|---|---|---|---|---|---|---|
| **1** 主動性 | 從被動 → 主動 | ✗ | 部分（auto_apply 邏輯）| ✓ part（owner endpoint）| ✓ **真活**（self_diagnosis cron）| done |
| **2** 跨會話記憶 | 從單次 → 連續 | ✗ | ✗ | ✗ | ⚠ partial（learnings 跨 session）| ✓ **v5.14 真活**（query history user×time 雙索引）|
| **3** 反思迴路 | 從反應 → 反思 | ✗ | 部分 | ✓ **真活**（hallucination signal 真消費）| ✓ | done |
| **4** 評分區分度 | 從鬆 → 區分 | ✗ | 部分 | ✓ **真活**（entity_alignment 進 success 判定）| ✓ | done |
| **5** 演化人格 | 從靜 → 動 | ✗ | ✓ part（agent_writable）| ✓ part | ✓ part | ⚠ **v5.15「我的能力自評」真活**（self_diagnosis 自動更新）/ 4 信念演化 v5.16+ |
| **6** 多 modality | 從文字 → 多媒 | ✗ | ✗ | ✗ | ⚠ partial（後端齊備前端缺）| ⚠ **v5.14 voice 真活** + **v5.15 後端 /vision/describe** / 前端 paste v5.16 |
| **7** Multi-agent | 單 agent → 生態 | ✗ | ✗ | ✗ | ✗ | **v6.x** 戰略 |

**Score**（v5.14 後）：
- 真活：4.5/7（Gap 1/2/3/4 完整 + Gap 5 part）
- 部分：1.5/7（Gap 5 信念 / Gap 6 image）
- 戰略保留：1/7（Gap 7）

v5.13 → v5.14 進步：Gap 2 從 partial → 真活（+1）、Gap 6 部分強化（voice 真活）
v5.14 → v5.15 進步：Gap 5「我的能力自評」producer 真活、Gap 6 後端 image endpoint 真活

---

## 2. v5.13 Phase 1 實證（self_diagnosis）

每日 06:00 自動跑 6 健康指標 + 寫 diary：

| 指標 | 當前值 | 狀態 |
|---|---|---|
| evolution counter | 31 | ✓ alive（修 #4 後真累積） |
| memory diary days | 12 | ✓ |
| 待批 proposals | 2 | ✓（< 5 不報警） |
| Telegram 連續失敗 | 0 | ✓ |
| SOUL「我的成長」 | alive | ✓ |
| 近 7 天反迴聲室 | 1 次 | ✓ |
| **6/6 alerts** | 0 | **全綠** |

「自我感知」段落 2026-04-30 16:17:07 已寫入 diary ✓。

---

## 3. v5.13 Phase 2 評估（Gap 2 跨會話記憶）

### 已部分實作（不是斷鏈）

`inject_cross_session_learnings()` (agent_learning_injector.py:158)：
- 從 DB `agent_learnings` 表讀歷史學習
- embedding cosine similarity 篩 top-5
- 注入 planner system prompt

**這是 Gap 2 的「learnings 跨 session」維度** ✓ 真活。

### 仍缺的維度（v5.14 補）

「query history 跨 session」— 同 user 上週問什麼今天記得：
- 需求：ConversationMemory 加 `user_id` 維度
- 實作：`agent:user_history:{user_id}` zset 累積該 user 所有 session 摘要
- inject：query 進來時找該 user 過去 30 天 5 個最相關 session

工作量估：1.5 天（schema 改 + retrieval 邏輯 + planner inject）。

---

## 4. v5.13 Phase 3 評估（Gap 6 多 modality）

### 後端已齊備

- ✓ `voice_transcriber.py`（OpenAI Whisper / 本地）
- ✓ `diagram_analysis.py`（v1.0.0 圖表分析）
- ✓ endpoint `/api/ai/voice/transcribe`、`/api/ai/diagram-analysis`

### 前端缺整合

- ChatTab 沒語音輸入按鈕
- 沒圖片貼上 OCR handler
- LINE/Telegram bot 已有 image_handler，但 web ChatTab 沒

工作量估：1 天（前端 MediaRecorder + paste handler + 接後端 endpoint）。

---

## 5. v5.13 已完成 commits

| Commit | Phase | 內容 |
|---|---|---|
| `bf3f33b0` | Phase 1 | agent self-diagnosis cron（Gap 1 真活）|
| (本輪) | Phase 4 | KUNGE_PROGRESS_TRACKER + self_diagnosis 升級含 Gap 進度 |

---

## 6. 持續追蹤機制

### 6.1 每日（自動）

`agent_self_diagnosis_job` 06:00 cron：
- 跑 6 個健康指標 + Gap 解決度 spot check
- 寫 diary「自我感知」段落
- 異常 → push Telegram

### 6.2 每月（半自動）

每月架構覆盤時：
1. 跑 `bash scripts/checks/run_fitness.sh` 看 12/12 step
2. 手動更新本檔 §1 演進矩陣（標 ✗ → part → 真活）
3. commit `chore: kunge_progress_tracker 同步 vM.X`

### 6.3 每 minor version（人工）

新 plan / verification 報告產出時：
- 對照本檔 §1 矩陣
- 更新「計畫」欄位
- 標出新 phase 對應的 Gap

---

## 7. 戰略路線圖

| 版本 | 主題 | 預計 Gap |
|---|---|---|
| v5.10.2 ✓ | 能不能感知自己 | observability baseline |
| v5.11 ✓ | 能不能主動修自己 | Gap 4 部分 + 鏈路 4 |
| v5.12 ✓ | signal 真改變行為 | Gap 3 真活 + Gap 4 真活 + 鏈路 5 |
| **v5.13 ✓** | **能不能主動發現問題** | **Gap 1 真活 + 持續追蹤 SSOT** |
| v5.14 | 能不能跨會話連續記憶 | Gap 2 + Gap 6 |
| v5.15 | 能不能演化核心信念 | Gap 5 信念 propose |
| v6.x | 從單 agent 到 multi-agent 生態 | Gap 7 |

---

## 8. 真正智能體成熟度分數

```
v5.10.2: 30%（observability + 0 真閉環）
v5.11:   55%（2 真閉環 + 部分 producer 接通）
v5.12:   75%（5 真閉環 + signal 真改行為 + 治理 SSOT）
v5.13:   85%（+ 主動 self_diagnosis + 持續追蹤）
v5.14:   92%（+ Gap 2 真活 + voice 真活）  ← 當前
v5.15:   95%（+ 信念演化 + image 補完）
v6.0:    100%（multi-agent 生態）
```

---

> **此檔每月人工更新 §1 矩陣，每日 self_diagnosis 自動補健康度。**
> **單一 SSOT，跨 repo 引用 `CK_Missive#KUNGE_PROGRESS_TRACKER_v1.0`。**
