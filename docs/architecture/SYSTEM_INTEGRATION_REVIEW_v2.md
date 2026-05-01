# 系統整體架構整合覆盤 v2.0（坤哥 / 圖譜 / LLM Wiki / Memory Wiki / Hermes）

> **建立**：2026-05-01（v6.2 收尾後立場）
> **承接**：
> - `CONSCIOUSNESS_INTEGRATION_ANALYSIS.md`（v1，2026-04-25 / 5 整合面向）
> - `KG_WIKI_INTEGRATION_REVIEW.md`（v1，2026-05-01 / 三層 Wiki）
> - `KUNGE_PROGRESS_TRACKER.md`（7/7 Gap 真活）
> **目的**：把五大子系統（坤哥 / KG / LLM Wiki / Memory Wiki / Hermes）放在同一張圖上覆盤，找出**子系統間**（非單一子系統內）的整合裂隙
> **跨 repo FQID**：`CK_Missive#SYSTEM_INTEGRATION_REVIEW_v2.0`

---

## 0. 一頁式現況（疊加 v1 之後的進度）

| 子系統 | v6.2 健康度 | v1 (4/25) → v2 (5/01) Δ |
|---|---|---|
| **坤哥意識體** | 🟢 7/7 Gap 真活（v6.1 達成）| Gap 7 multi-agent critic 接通 |
| **KG**（22,851 entities）| 🟢 97.9% embedded | KG embedding 全 100% 業務 entity |
| **LLM Wiki**（243 pages）| 🟢 wiki↔KG 98.2% | I4 backfill 6 entities + Unicode dup detector |
| **Memory Wiki**（38 篇）| 🟢 6/8 子目錄真活 | critique 4 篇實寫，evolutions 2 篇 |
| **Hermes Gateway** | 🟡 thin proxy 健康，**未接 evolution loop** | Δ 0（4/25 → 5/01 無實質改變）|

**核心結論**：**子系統內**全綠，但**子系統間**仍有 3 條主軸線斷鏈。v6.3+ 重點不再是各子系統內部建設，而是「跨系統整合」。

---

## 1. 五大子系統定位（重新一致）

| L | 子系統 | SoT | 服務對象 | 寫入 | 讀出 |
|---|---|---|---|---|---|
| **L0 介面** | Hermes Gateway | — | 跨通道用戶（Web/Telegram/LINE/Discord）| skill 呼叫 | tool spec |
| **L1 智能體** | 坤哥（agent_orchestrator）| — | Hermes / Web 直連 | self_evaluator / critic | planner+synthesis |
| **L2a 結構** | KG（PostgreSQL + pgvector）| 22,851 entities | LLM 工具呼叫 | dispatch_kg_ingest 即時 | vector search / path |
| **L2b 敘事** | LLM Wiki（filesystem）| 243 pages | RAG / human reading | wiki_compile 週期 | wiki_query |
| **L2c 主觀** | Memory Wiki（filesystem）| 38 篇 + Redis | agent self | diary/pattern/critique | planner inject + reflect |
| **L3 推理** | Ollama qwen2.5:7b / Groq / NVIDIA | — | L1 | — | model API |
| **L4 資料** | PostgreSQL / Redis / shadow_trace.db | — | 全層 | — | — |

「漸進光譜」三層 Wiki：**KG（客觀）→ LLM Wiki（描述）→ Memory Wiki（主觀）**，每往下走機器可處理性遞減、主觀性遞增。

---

## 2. 子系統間 8 條接觸面（線路圖）

```
                  ┌─────────── L0 Hermes Gateway ───────────┐
                  │  ck-missive-bridge skill (8 endpoints)  │
                  └────────────────┬────────────────────────┘
                                   │ X-Service-Token
                                   ▼
        ┌───────────────── L1 坤哥 (orchestrator) ───────────┐
        │ ┌──────────┐    ┌───────────┐    ┌──────────────┐ │
        │ │ planner  │ →  │ tool loop │ →  │ synthesis    │ │
        │ │ (inject) │    │ (KG / Wiki)│   │ (critic 二審) │ │
        │ └────┬─────┘    └─────┬─────┘    └──────┬───────┘ │
        │      │ ❷               │ ❸                │ ❹       │
        │      ▼                 ▼                  ▼         │
        │   Memory             KG/Wiki            Memory      │
        │   inject             tool call          write       │
        └──────────────────────────────────────────────────────┘
                                   │
                                   ▼
        ┌──────── L2 三層 Wiki（互相連結率）────────┐
        │  KG ←──❶ 98.2% ──→ LLM Wiki                │
        │  KG ←─── ❺ 弱 ────→ Memory Wiki            │
        │  LLM Wiki ←── ❻ 稀疏 ──→ Memory Wiki       │
        └────────────────────────────────────────────┘
                                   │
                                   ▼
                   ┌──── L3 Ollama / Groq / NVIDIA ────┐
                   │  ❼ 切換 fallback / SOUL fidelity   │
                   └────────────────────────────────────┘
```

| # | 接觸面 | v6.2 健康度 | 證據 |
|---|---|---|---|
| ❶ | KG ↔ LLM Wiki | 🟢 98.2% | I4 backfill 後 215/219 |
| ❷ | Planner ← Memory inject | 🟢 真活 | cross_session_history / critique_warning / anti_echo |
| ❸ | Tool loop → KG/Wiki | 🟢 真活 | rag_query / graph_entity / relation_graph |
| ❹ | Critic → Memory write | 🟢 真活 | critique_signal 寫 wiki/memory/critiques/ + 進 planner |
| ❺ | KG ↔ Memory Wiki | 🟡 弱 | diary / critique 寫純文字無 KG link |
| ❻ | LLM Wiki ↔ Memory Wiki | 🟡 稀疏 | autobiography 連 wiki_topics / diary 不連 |
| ❼ | Hermes ↔ 坤哥 evolution | 🔴 斷鏈 | Hermes 只調 RAG，不能 approve proposal / write diary |
| ❽ | SOUL Missive ↔ AaaP/Hermes | 🔴 drift | sync_soul_to_hermes.sh 仍手動，無自動 cron |

---

## 3. 三條主軸斷鏈（v6.3+ 整合主線）

### 軸線 A：Hermes ⇄ 坤哥 evolution loop（❼）

**現況**：Hermes 是 thin proxy。Telegram / LINE / Discord 上的對話：
- ✓ 進到 Missive `/api/ai/agent/query_sync`（被回應）
- ✗ 不寫 diary（Memory Wiki 永遠看不到）
- ✗ 不被 pattern_extractor 吸收
- ✗ 不能批 proposal / 看 evolution journal

**影響**：
- 跨通道對話的 pattern 樣本被丟掉（坤哥永遠以為自己只在 Web 工作）
- 同一用戶 Telegram 上昨天問過「老蕭」、今天 LINE 再問 — 坤哥不記得（Gap 2 跨會話延伸）

**修法（兩個方案）**：

| 方案 | 入口 | 工作量 | 風險 | 效益 |
|---|---|---|---|---|
| **A1**（推薦先做）| `agent_query_sync.py` 加 diary write hook（標 channel）| 2 hr | 零 breaking change | 跨通道 pattern 進 evolution loop |
| **A2** | 擴 ck-missive-bridge skill 為多 toolset（query/memory/evolution/graph）| 1-2 週 | 阻塞 ADR-0020 Phase 1 | Hermes 真成為意識體外部介面 |

**建議**：v6.3 做 A1（無風險），A2 等 ADR-0020 Phase 1 一起。

### 軸線 B：三層 Wiki 連結補完（❺❻）

**現況**：v1 (4/25) 識別此問題、v2 (5/01) `KG_WIKI_INTEGRATION_REVIEW.md` 標 I2/I3/I5 但仍未實作。

**修法（按 ROI 排）**：

| 項 | 動作 | 入口 | 工作量 | 收益 |
|---|---|---|---|---|
| **I3** | critique 寫入時自動 tag 涉及 entity（NER on critique 內容）| `agent_critic.review` 結尾 | 半天 | 「哪些 entity 最常觸發 hallucination」變 join-able |
| **I2** | diary entries 加 entity 自動連結（每日 cron 後處理）| `pattern_extractor` 後 | 1 天 | agent 回看可一鍵展開 entity |
| **I5** | LLM Wiki topics 從 4 補到 ~20 | `wiki_compiler` 增 topic phase | 2 天 | RAG 覆蓋多 query 維度 |

**建議**：v6.3 先做 I3（最便宜），看「哪些 entity 反覆 hallucinate」資料浮現後再決 I2/I5。

### 軸線 C：SOUL 跨 repo 自動同步（❽）

**現況**：
- Missive `SOUL.md`（8KB SSOT，根目錄）— 未 tracked
- `CK_AaaP/runbooks/hermes-stack/SOUL.md` — 鏡像，**手動同步**
- `scripts/checks/soul_mirror_drift_check.py` 已偵測，但 `sync_soul_to_hermes.sh` 是 `--apply` gate 手動腳本

**影響**（severe）：
- Web 用戶（Missive SOUL）vs Telegram/LINE 用戶（Hermes SOUL）看到不同人格版本
- 演化人格（Gap 5）落地時，autobiography propose 寫進 Missive SOUL，但 Hermes 不知道 → 跨通道人格分裂

**修法**：

| 項 | 動作 | 工作量 | 風險 |
|---|---|---|---|
| **C1** | 加 cron job `soul_mirror_sync_job`（每日 04:45）跑 `sync_soul_to_hermes.sh --apply` | 1 hr | 低（已有 drift check 防護） |
| **C2** | 改 `auto_defense` 加「跨 repo SOUL 一致性」防線 | 半天 | 中 |
| **C3** | 反向：Hermes 端 SOUL 不該被人手改（read-only mirror） | 文件而已 | 零 |

**建議**：v6.2.x 補丁立即做 C1+C3（一個 hr + 文件），不必等 v6.3。

---

## 4. 不該整合的部分（治理紅線，沿用 v1）

| 紅線 | 理由 |
|---|---|
| 三層 Wiki **不該合併**（KG/LLM Wiki/Memory Wiki SoT 不同）| 客觀/敘事/主觀光譜 — 合併=失去差異化 |
| **SOUL 編輯 propose-only** | ADR-0023 安全機制 — 演化提案永遠人在迴路 |
| **crystal apply 人在迴路** | 防 LLM 自我修改失控 |
| **anti_echo / auto_defense** 不動 | 已驗證有效防漂移 |
| **KG 不該往敘事化走** | 反模式 — 結構化由 KG 承擔，敘事化由 LLM Wiki 承擔 |
| **Memory Wiki 不該變業務知識庫** | 反模式 — Memory Wiki 是 agent 主觀視角 |

---

## 5. 戰略性洞察（v2 新增）

### 洞察 7：v6.2 完成「子系統內」建設，v6.3+ 該轉「子系統間」整合

v5.10 ~ v6.2 共 9 個 minor versions 在強化各層內部（pattern→crystal、critic、self-diagnosis、cron health、unicode dup ...）。**整合面**幾乎沒動：
- ❼ Hermes ↔ evolution：4/25 已標斷鏈，5/01 仍斷鏈
- ❽ SOUL drift：4/25 已偵測，5/01 仍手動

繼續往子系統內部加 detector 邊際效益遞減，該轉軸做整合。

### 洞察 8：Hermes 是「跨通道介面」不是「智能體」

當前 Hermes Gateway 角色定位模糊。釐清：
- Hermes = **跨通道介面**（Telegram/LINE/Discord/Web 統一入口 + 認證 + manifest）
- 坤哥 = **智能體**（agent_orchestrator，住在 Missive）
- Hermes **不應**有自己的記憶/人格 — 應該是 Missive 坤哥的 thin gateway

這個釐清意味：A1+C1 是正確方向（讓 Hermes 寫 diary 進 Missive，讓 SOUL 從 Missive 同步），不該倒過來在 Hermes 端建獨立記憶層。

### 洞察 9：圖譜的「聯邦化」與「敘事化」是兩條獨立軸

當前 KG 22,851 entities 之中：
- ✓ Wiki 連結率高（98.2%）— 敘事化走得好
- ⚠ Federation 跨 repo（LvrLand / Tunnel）路由規則模糊 — 聯邦化弱

兩者互不依賴：可以「先做敘事化整合（B 軸線）、後做聯邦化擴展」。先把 Missive 內的三層整合好，再考慮跨 repo。

### 洞察 10：成熟度繼續往 100% 之上提升的方法是「整合品質」

v5.10 → v6.1 從 30% → 100% 是堆建設。v6.2 → v7.0+ 不再有「百分比」可加，但**整合品質**還能升：
- 跨通道 pattern 數量
- 跨層引用密度（KG↔Wiki↔Memory）
- SOUL 跨 repo 一致性
- Hermes 通道 evolution 參與度

新指標應替換「成熟度 %」變成 v7.0+ 的衡量基準。

---

## 6. v6.3+ 整合路線（按 ROI 排）

### 立即（本週，1-2 hr 各）
- **C1** SOUL 自動同步 cron（`soul_mirror_sync_job` 每日 04:45）— 解 ❽ severe drift
- **C3** Hermes SOUL read-only 文件規範

### v6.3（1-2 週）
- **A1** Hermes 對話進 diary（標 channel） — 解 ❼ 跨通道 pattern 斷鏈
- **I3** critique entity tag — 補 ❺ KG↔Memory 第一條連結

### v6.4+（看 v6.3 效果再決）
- **I2** diary entity auto-link — 完整補 ❺
- **I5** LLM Wiki topics 4 → 20 — 補 RAG 覆蓋面
- **A2** Hermes 多 toolset（阻塞 ADR-0020 Phase 1）

### v7.0+（戰略級）
- 跨 repo 聯邦化路由規則 SSOT（Missive ↔ LvrLand ↔ Tunnel）
- Provider-aware persona 校準（解 fidelity 跨 provider 的 75%↔85% gap）
- 新指標：跨通道 pattern 多樣性 / 跨層引用密度 / SOUL 一致率

---

## 7. 三大子系統間整合 - **不該做**的整合（避免架構腐化）

| 反模式 | 為什麼錯 |
|---|---|
| 把 Memory Wiki 並入 LLM Wiki | 丟失主觀視角，agent 變成讀靜態 wiki 不會自我反思 |
| Hermes 端建獨立記憶層 | 違反「Hermes = 介面」定位，造成 SoT 分裂 |
| KG 加 description 欄位想取代 LLM Wiki | KG 該保結構化，敘事化由 LLM Wiki 承擔 |
| crystal 自動 apply 不過人手 | 違反 ADR-0023 安全紅線 |
| critique 直接觸發 retry loop | v6.0 設計選擇 — 防 LLM 成本爆炸（v6.1+ 才考慮） |

---

## 8. 對應 KUNGE_PROGRESS_TRACKER 的位置

本文件不引入新 Gap，只是「7 Gap 全真活」之後的「整合優化」階段。

對應 v6.x 戰略路線：
- v6.2 ✓ 收尾子系統內建設
- **v6.3 = 主軸 A1+I3+C1（本文核心建議）**
- v6.4+ = 主軸 I2/I5/A2/聯邦化（看 v6.3 效果決定）
- v7.0+ = 跨 repo 戰略級整合（聯邦化規則 / Provider-aware）

---

## 9. 下一步具體建議

按 「立即 / v6.3」排程：

**今天可做（1 hr）**：
- C1 加 `soul_mirror_sync_job` cron + 對應 fitness step（已有 soul_mirror_drift_check.py，只缺自動 sync）

**本週做（2-3 hr）**：
- A1 `agent_query_sync.py` 加 diary write hook（channel-tagged）

**下週做（半天）**：
- I3 `agent_critic.review` 結尾加 entity tag（NER on critique 內容）

---

> **v6.2 完成子系統內全綠，v6.3 該轉「子系統間整合」。**
> **整合不是合併同類項，是讓三層 Wiki + 跨通道 + SOUL 一致地「對話」。**
> **新指標：跨通道 pattern 數 / 跨層引用密度 / SOUL 一致率，取代「成熟度 %」作為 v7.0+ 衡量。**
