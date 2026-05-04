# 系統整體架構整合優化覆盤 v3.0（v6.2 → v6.7）

> **建立**：2026-05-04（v6.7 收尾後立場）
> **承接**：
> - `SYSTEM_INTEGRATION_REVIEW_v2.md`（v2.0，2026-05-01 / 8 接觸面 + 3 主軸線）
> - `CONSCIOUSNESS_INTEGRATION_ANALYSIS.md`（v1.0，2026-04-25 / 5 整合面向）
> - `KG_WIKI_INTEGRATION_REVIEW.md`（v1.0，2026-05-01 / 三層 Wiki）
> - `KUNGE_PROGRESS_TRACKER.md`（7/7 Gap 真活）
> **目的**：覆盤 v2.0 → v6.7 4 天 14 commits 的整合優化執行成果，識別新一輪整合裂隙
> **跨 repo FQID**：`CK_Missive#SYSTEM_INTEGRATION_REVIEW_v3.0`

---

## 0. 一頁式現況（v2.0 → v3.0 進度）

| 子系統 | v6.2 (5/01) | v6.7 (5/04) | Δ |
|---|---|---|---|
| **坤哥意識體** | 🟢 7/7 Gap 真活 | 🟢 7/7 + critic POC + critique→planner 閉環 | 強化 |
| **KG**（22,851 → 12,145+ entities）| 🟢 97.9% embedded | 🟢 + Unicode dup detector + alias backfill | 強化 |
| **LLM Wiki**（243 pages）| 🟢 wiki↔KG 98.2% | 🟢 ~98.5% + 5 聚合 topic（4→9）| 強化 |
| **Memory Wiki**（38 篇）| 🟢 6/8 子目錄真活 | 🟢 critique 進入 entity-tagged + diary entity link | 強化 |
| **Hermes Gateway** | 🟡 thin proxy + 未接 evolution | 🟡 A1 跨通道 diary 通 + A2 read-only 3 tools 繞道 | **+1 級** |

**核心結論**：v2.0 開出的整合工單 8 / 9 已交付（I5 數量未到、A2 受 ADR-0020 阻塞），整合主軸線從 🔴 → 🟢。但活體驗證浮現新裂縫。

---

## 1. v2.0 三主軸線完成度

| 軸線 | v2.0 標的 | 實際 commits | 狀態 |
|---|---|---|---|
| **A** Hermes ⇄ evolution loop | A1 跨通道 diary / A2 多 toolset | `caf814de` (A1) / `713b30a3` (A2 部分) | ✅ A1 完整 / 🟡 A2 走 read-only 3 tools 繞 ADR-0020 |
| **B** 三層 Wiki 連結補完 | I3 critique entity / I2 diary entity / I5 topics 4→20 | `caf814de` (I3) / `3416077e` (I2) / `3966bec1` (I5 4→9) | ✅ I3/I2 完整 / 🟡 I5 半（9 而非 20）|
| **C** SOUL 跨 repo 同步 | C1 cron / C2 drift defense / C3 read-only 規範 | `caf814de` (C1) / `3416077e` (C2) / `af4227cd` (C3) | ✅ 全完成 |

---

## 2. 8 接觸面健康度更新（v2.0 → v3.0）

| # | 接觸面 | v6.2 (5/01) | v6.7 (5/04) | 變化 |
|---|---|---|---|---|
| ❶ | KG ↔ LLM Wiki | 🟢 98.2% | 🟢 ~98.5%（`5dc9e31e` backfill 1）| +0.3% |
| ❷ | Planner ← Memory | 🟢 真活 | 🟢 真活 | — |
| ❸ | Tool loop → KG/Wiki | 🟢 真活 | 🟢 真活 | — |
| ❹ | Critic → Memory | 🟢 真活 | 🟢 + entity tag（`caf814de`）| 強化 |
| ❺ | KG ↔ Memory Wiki | 🟡 弱 | 🟢 真活（I3+I2 雙向 entity link）| **+2 級** |
| ❻ | LLM Wiki ↔ Memory Wiki | 🟡 稀疏 | 🟢 變強（I5 +5 聚合 topic）| +1 級 |
| ❼ | Hermes ↔ evolution | 🔴 斷鏈 | 🟢 通（A1）+ 🟡 A2 read-only 3 tools | **+2 級** |
| ❽ | SOUL Missive ↔ Hermes | 🔴 drift | 🟢 cron + drift defense | **+2 級** |

**8 接觸面從 5🟢 / 2🟡 / 2🔴 → 7🟢 / 1🟡（A2 受 ADR-0020 阻塞）**。

---

## 3. v6.3-v6.7 額外加碼（v2.0 沒列、現場長出）

| Commit | 加碼項 | 為何重要 |
|---|---|---|
| `8367af64` | 體感型輸出三件組（坤哥人格自主性 / LINE 推送）| 從「被動等問」轉「主動 push」— 把 evolution 結果推回用戶 |
| `21d77d70` | SOUL changelog + rollback LINE 通知 | 用戶可即時感知「坤哥又演化了」，閉環人在迴路 |
| `5cfad746` | 日終反思 LINE 彙總（每日 22:00）| Pattern→Reflection 通往用戶側觸達 |
| `d9e914fb` | cron health fitness step 13 | Fitness 從 7 step → 13，cron 失效自動偵測 |
| `4919c55a` | unicode dup detector | 阻擋 KG 因 NFC 變體產生重複實體 |
| `7a958cbe` / `9f1da794` | agent_critic POC + critique signal → planner 閉環 | Gap 7 multi-agent 真活，二審→下次 plan 注入 |
| `b2aca2ae` | LINE 體感型輸出 env 範本 + runbook（事故修復）| 揭露「commit 綠 ≠ 推送活」— 觸發本 v3.0 覆盤的洞察 11 |

**模式觀察**：v6.3+ 不再單純「補 v2.0 工單」，而是「整合過程觸發新發現，現場補強」。這正是 v2.0 洞察 7 預期的「整合品質取代成熟度 %」作為衡量。

---

## 4. v3.0 新發現的問題

### 裂縫 0（事故）：v6.3-v6.7 體感推送鏈全部 silent skip

**事故時序**（commit `b2aca2ae` 紀錄）：
- 2026-05-04 owner 反饋「沒收到日記與進步紀錄」
- 雙根因：
  1. `.env` 完全沒設 `LINE_ADMIN_USER_ID` → 所有 LINE push 走 silent skip
  2. ck-backend uptime 2D > 新 cron commit 時間 → `soul_mirror_sync` / `daily_self_reflection_line_push` / `cron_self_health_alert` 全沒掛載
- 修復：補 `.env.example` + 寫 `docs/runbooks/enable_line_perception_outputs.md`
- **owner 待動作**：取 LINE userId / 寫 .env / `pm2 restart --update-env`

**戰略訊號**：5 個跨 phase commit 全鏈推送，**沒有任一 alert / fitness step 抓到 7 天 0 推送**。

### 裂縫 1：KG 統計嚴重不一致（同日不同回答差 4000 倍）
- 5/04 09:00:11 回答「12145 個實體」
- 5/03 14:00:40 回答「3 個實體」
- 同一工具 `get_statistics` 回不同結果 → **KG 查詢工具有 race condition 或 cache 失誤**

### 裂縫 2：超時率偏高（pattern 路徑 ~30%）
近 30 條對話 8 條 timeout（40-50s），多在 `synthesis` 階段 — 與 ADR-0028 的 35s timeout 合約衝突，timeout 未強制傳到 LLM 層

### 裂縫 3：答非所問仍存在
「最近的查估派工案件」回「目前尚無任何派工紀錄」— 但實際 DB 有 127 筆 dispatch
→ planner 工具選對（`search_dispatch_orders`）但傳參錯，或 dispatch 領域未進 RAG context

### 裂縫 4：memory diary days = 0 ✗ hollow
self_diagnosis 自己報「memory diary days hollow」3 天（5/03、5/04）— 表示 **diary 自動寫入鏈斷了**（與 A1 commit 矛盾，需驗證 A1 跨通道 diary 是否真活）

---

## 5. 戰略洞察更新（v2.0 → v3.0）

### 洞察 11（NEW）：整合驗證需第 2 階段「活體驗證」

v6.3-v6.7 commit message 都標「真活」，但事故揭示：**`agent_writable: true` 的 diary 實際 0 entries / 5 條推送鏈全 silent skip**。

→ **整合 commit ≠ 活體運轉**。v2.0 之後缺少「commit 後 7 天活體驗證 SOP」，導致 commit 顯示綠、實際運轉時鏈斷只在診斷 log 裡顯示但無 alert。

**修法建議**：fitness step 14「整合鏈活體驗證」— 對 8 接觸面定義 evidence query（diary 行數、KG entity count 一致性、SOUL drift hash、LINE 推送 7 天計數），每日 cron 跑、低於門檻 LINE 推。

### 洞察 12（NEW）：超時未隔離 = silent quality degradation

synthesis timeout 在 ADR-0028 已設 35s 合約，但 5/04 對話最長 50.4s 仍進到用戶側。意味 **timeout 合約只在某幾層執行，端到端未強制**。

**修法建議**：在 `agent_query_sync` 出口加 hard cutoff 35s，超時改回 fallback skeleton answer（與 baseline_quality_recovery_20260424 的 Patch A+B 同邏輯延伸）。

### 洞察 13（NEW）：A2 受 ADR-0020 阻塞的繞道有副作用

`713b30a3` 走「Hermes skill 加 3 read-only tools」繞 ADR-0020 — 這讓 Hermes 變成「半厚 client」，違反 v2.0 洞察 8「Hermes = 跨通道介面、不該有獨立記憶層」。

**戰略決策需求**：
- 方案 a：等 ADR-0020 Phase 1 完成（CK_AaaP 端排程未明）
- 方案 b：把 read-only 3 tools 文件化標明「臨時繞道、ADR-0020 完成後撤」
- 方案 c：放棄 ADR-0020，把 Hermes 升級為正式 toolset gateway

5/20 Hermes GO/NO-GO 會議該排此議題。

### 洞察 14（NEW）：「成熟度 %」已死，v7.0 需新指標立刻上線

v2.0 預告但未落地。5/04 self_diagnosis 仍報「7/7 真活」但裂縫已浮現 — 表示舊指標已失效。

**v7.0 指標建議（4 個）**：
1. **跨通道 pattern 多樣性** — Telegram/LINE/Web/Discord channel 各自 7 天 pattern 數
2. **跨層引用密度** — 每筆 diary/critique/synthesis 平均連結 KG entity 數
3. **SOUL drift hash distance** — Missive ↔ AaaP 7 天滑動視窗 drift 平均
4. **Provider fidelity gap** — Ollama vs Groq vs NVIDIA 三 provider 同 query SOUL 一致率

### 洞察 15（NEW）：「best-effort silent skip」設計需配「7 天 0 推送 alert」

ADR-0028 silent failure 政策對主流程是對的（不該因 notify 失敗 break apply / cron），但**對體感層而言 silent = 用戶看不到 = 死亡**。

**修法建議**：對所有 LINE push 路徑加「7 天連續 0 推送 → 推 owner 一次自動診斷報告」的 watchdog，類似 baseline_quality_recovery 的雙保險邏輯。

---

## 6. v6.8+ 整合主線（按 ROI 排）

### 立即（本週，1-2 hr）
- **W0**（owner 動作）：完成 LINE 體感推送啟用三步（取 userId / 寫 .env / `pm2 restart --update-env`）— 30 分
- **Q1** Diary 自動寫鏈活體驗證（驗 A1 commit 是否真讓 Telegram/LINE 對話進 diary）— 1 hr
- **Q2** KG `get_statistics` 一致性測試（複現 12145 vs 3 的差異）— 1 hr
- **Q3** synthesis timeout 端到端 hard cutoff 35s — 2 hr

### v6.8（1 週）
- **F14** Fitness step 14「整合鏈活體驗證」（8 接觸面 evidence query）— 1 天
- **F15** Fitness step 15「LINE notify 7 天計數 watchdog」— 半天
- **M1** v7.0 新指標 4 個落地（dashboard + alert）— 2 天
- **I5+** LLM Wiki topics 9 → 20 補完（v2.0 原規劃）— 2 天

### v7.0+（戰略級）
- **A2 終局** ADR-0020 5/20 會議決策 → Hermes 角色定案
- **F1** 跨 repo KG federation 路由規則 SSOT（Missive ↔ LvrLand ↔ Tunnel）
- **P1** Provider-aware persona 校準（解 75↔85% fidelity gap）

---

## 7. 整合方法論升級

從 v6.3-v6.7 4 天 14 commits + 5/04 事故學到的整合 SOP：

| 階段 | 工具 | 產出 |
|---|---|---|
| 1. 識別斷鏈 | `SYSTEM_INTEGRATION_REVIEW_v2` 8 接觸面表 | 工單清單 |
| 2. 排 ROI | hr 估時 + 風險 + 收益矩陣 | 排程 |
| 3. 執行 | dynamic /loop 跨輪累積 commits | feat: vN.x phase X |
| 4. 驗證 | fitness step 自動跑 | 綠燈 |
| **5. 活體驗證**（缺）| **F14 + F15 watchdog**（v6.8 新增）| **diary 7 天樣本 + LINE 推送計數** |
| 6. 覆盤 | 本文件這類 v(N).0 retrospective | 下一輪起點 |
| **7. 體感反饋**（缺）| **owner 用 LINE 收到才算數**（v3.0 洞察 15）| **0 推送 = 失敗** |

**v2.0 → v3.0 最大教訓**：缺第 5+7 步，導致 7/7 真活的同時實際 diary 鏈斷 + 5 條推送鏈全 silent。**v6.8 第一件事補 W0+Q1+F14+F15**。

---

## 8. 對應 KUNGE_PROGRESS_TRACKER 的位置

本文件不引入新 Gap（7/7 仍真活），只是「整合品質深化」階段。

對應 v6.x 戰略路線：
- v6.2 ✓ 收尾子系統內建設
- v6.3-v6.7 ✓ 主軸 A1+I3+C1+C2+C3+I2+I5（v2.0 推薦項全交付）
- **v6.8 = W0+Q1+Q2+Q3+F14+F15（本文核心建議）**
- v7.0+ = ADR-0020 終局 + 跨 repo 聯邦化 + Provider-aware

---

## 9. 對外敘事（給 owner 看）

整合優化從「裂縫識別」進入「裂縫驗證」階段：

- **過去 4 天**：v6.3-v6.7 把 v2.0 識別的 8 條裂縫補了 6 條（Hermes 跨通道 diary、SOUL 自動同步、三層 Wiki entity link、LLM Wiki topics 擴張）
- **此刻**：5/04 事故揭示「commit 顯示綠、用戶端無感」的 silent gap — 提醒「整合 ≠ 活體」
- **接下來**：v6.8 不再加新接觸面，而是補「活體驗證 + 體感推送 watchdog」 — 確保既有 8 條接觸面長期不掉

對應 BUSINESS_VALUE.md：「**整合品質**就是用戶能感受到的人格一致性、記憶連續性、能力增長性」— v6.8 是把這三件事從「commit message 真活」變「LINE 收得到」的工程。

---

> **v6.7 完成「子系統間整合」表面工程，v6.8 該補「活體驗證」深度工程。**
> **整合優化的下一階段不是再加接觸面，是讓既有 8 條真的長期不掉。**
> **新指標：跨通道 pattern 多樣性 / 跨層引用密度 / SOUL drift hash / Provider fidelity gap。**
> **體感層原則：能推到 LINE 才算數；7 天 0 推送 = 失敗。**
