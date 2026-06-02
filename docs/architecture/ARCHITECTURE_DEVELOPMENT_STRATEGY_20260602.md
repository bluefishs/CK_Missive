# 整體架構發展戰略 — 坤哥學習閉環 × Hermes agents × 平臺服務管理

> 撰寫：2026-06-02 | 性質：戰略綜述（分析先行、grounded 真實接通狀態，非空泛規劃）
> 對齊 owner：「就整體坤哥學習閉環與 Hermes agents 與平臺服務管理等整體架構發展為核心」
> 紀律：本檔為唯讀分析產物，任何據此的變更須先走 [[feedback_rigor_no_self_inflicted_instability]] 影響盤點協議

---

## 0. 架構脊柱（貫穿三柱的單一主題）：**接通與真活**

本 session 跨三柱反覆驗證出同一條架構債：

> **能力早已建構，但在「終點接通」斷裂、或「silent 失效」未被自證。**
> 架構成熟度不該用「建了什麼」衡量，而是「**接通了什麼 + 證明它活著**」。

三柱具體病灶（皆本 session 實證）：
| 柱 | 已建能力 | 斷點 / 假活 |
|---|---|---|
| 學習閉環 | 7 環節 cron + crystal | intent 終點**開路**（tool_preference 無消費端）|
| Hermes agents | agent 23 工具 + federation | bridge 只暴露 9；intent 路由曾幻覺（LN2 已修）|
| 平臺服務 | cron/排程/觀測 | 8 cron `.parent` silent 死、docs :ro 擋寫、LINE metric 失明 |

→ **架構發展的核心動作 = 把每一條「建了但沒接通/沒自證」的線補成「接通 + 真活 + 自證」。**

---

## 1. 柱一：坤哥學習閉環（半閉合 → 全閉合）

### 現況真實鏈（實證）
```
diary(daily) → pattern_extract(04:00) → crystallize(04:35) → proposal
   → crystal_applier(admin gate) → crystal
        ├── 終點A SOUL：crystal_applier 寫 SOUL.md → agent_roles/chitchat 讀 → 人格  ✅ 閉合
        └── 終點B intent：crystal_auto(tool_preference) → intent_rules.yaml
                但 rule_engine 只讀 pattern/extract/confidence，不讀 tool_preference  ❌ 開路
```

### 架構問題
- **「閉環」實為半閉合**：SOUL 軌回饋人格（真閉環）；intent 軌寫了 crystal 卻不影響行為（schema 不符 + 無消費端）。
- crystals 現況 2（皆 SOUL 軌）；2 intent proposal 已 superseded（不造假）。
- 基礎設施脆弱：閉環各環節 cron 曾因 `.parent` silent 死（本 session 修）。

### 發展方向
1. **閉合 intent 終點**（L1）：升 pattern_extractor 保存「觸發 query 文字」→ crystallizer 生成真 regex pattern + extract → rule_engine 既有路徑即生效（不需新消費端）。或在 planner 建 tool_preference bias 消費端。
2. **閉環自證**：memory_loop fitness（已誠實化）+ proposal_aging（已建）持續監控閉環不斷。
3. **目標態**：pattern→crystal→behavior 雙軌全閉合，ratio ≥0.5，行為改變可被 trace 觀測。

---

## 2. 柱二：Hermes agents（能力 ⇄ 暴露 ⇄ 路由 三層對齊）

### 現況三層（實證）
```
L0 channel：LINE / Telegram / Web / OpenAI-API
   ↓
L1 bridge：tools_manifest（missive_ prefix）暴露 9 高階動作
   ↓ (HTTP /api/ai/agent/query_sync 等)
L2 agent：23 內部工具 + federation（cross_domain_link/path / federation_client/delegation/discovery）
   ↓
L3 routing：pattern → gemma4 intent(_INTENT_TOOL_MAP 確定性) → llm fallthrough
```

### 架構問題
- **bridge 9 vs agent 23 不對齊**：ERP/finance/contract/asset 能力未暴露給 Hermes gateway 直呼（discoverability gap）。
- **上游 Hermes gateway skill 註冊**（hermes-stack repo）：ck-* skill 未進 meta profile snapshot → 對話入口無法 dispatch（跨 repo，CKProject CLAUDE.md 記載）。
- routing 曾幻覺中文工具名（LN2 已用確定性映射修）。

### 發展方向
1. **bridge↔agent SSOT 對齊**：tools_manifest 自 tool_registry 動態生成（非手維 9 條），消除漂移。
2. **federation 為平臺級整合骨幹**：Missive 的 cross_domain 能力是「KG 聯邦 hub」雛形 → 跨專案（lvrland/pile）知識互通的架構基石。
3. **上游協調**：Hermes meta profile skill 註冊（hermes-agent session）。

---

## 3. 柱三：平臺服務管理（service = 自證真活的單元）

### 現況（Missive 在 AaaP 平臺的角色）
- Missive 是平臺**業務核心服務**，以 **tools_manifest 公開契約**（`missive_` prefix）+ **federation hub** 對外。
- 兄弟服務：CK_AaaP（平臺基礎+治理）、CK_Showcase（治理 API）、hermes-agent（控制核心）、lvrland/pile（領域服務）。
- 服務管理基礎設施：APScheduler（~100 job）、cron_events.jsonl 檢核紀錄、SchedulerEventsPage 複查頁、daily_self_retrospective 自動覆盤、cron_self_health_alert watchdog。

### 架構問題（本 session 集中爆發）
- **silent 失敗對監控失明**：watchdog 只抓 `failed>=1`，但 silent no-op（早退假成功）記為 success → 逃過偵測（8 cron `.parent` 即此）。
- **跨檔 SSOT 漂移**：mount target / path / config 在多檔分別宣告，一處改另一處沒跟（L43/L52/L57 family 反覆）。
- **觀測假活**：metric 宣稱追蹤卻沒接（messaging_push_total /metrics 顯 0 但真推過）。

### 發展方向（本 session 已落地部分）
1. **silent → LOUD**（已落地）：script-not-found `return`→`raise`（12 處）+ 開機自檢 → watchdog 自動 LINE 報。
2. **outcome-freshness watchdog**（建議下批）：檢查「每日 cron 是否產出今日檔」，比 failed 監控更徹底（連 rc!=0 早退也抓）。
3. **跨檔 SSOT 收口**：mount/path 集中宣告 + audit（cross-file-ssot-governance 已立規，需補 cron_script_path / metric_exposure audit）。
4. **觀測真活**：metric registry 曝露對齊（修 messaging_push_total 等 F26/F27 同型）。

---

## 4. 統一發展原則（架構北極星）

> **每一個「被依賴的能力」都必須：① 接通到終點 ② 失敗要 LOUD ③ 真活可自證。**

| 原則 | 反模式 | 落地機制 |
|---|---|---|
| 接通到終點 | 建了 crystal 沒人讀 / bridge 暴露不全 | 終點消費端 + SSOT 動態生成 |
| 失敗 LOUD | silent return 假成功 | raise + 開機自檢 + watchdog（已落地） |
| 真活自證 | metric 失明 / 靠人工發現 | outcome-freshness + 觀測 registry 對齊 + SchedulerEventsPage |

---

## 5. 發展優先序（建議，待 owner 定）

| # | 動作 | 柱 | 風險 | 狀態 |
|---|---|---|---|---|
| P0 | outcome-freshness watchdog（cron 產出今日檔自證）| 三 | 低（純加） | ✅ **完成**（2026-06-02 commit `b6ae4810`，每日 07:00，全綠 silent / stale→LINE，驗證雙向 + E2E PASS）|
| P0 | ~~metric registry 曝露對齊~~ | 三 | — | ⚪ **校正撤回**：原「LINE metric 失明」證據有瑕疵（subprocess push 有獨立 counter，非 backend 程序）→ metric 很可能正常。**不憑瑕疵證據改 code**，待 in-backend push 確認 |
| P1 | 閉合 intent 終點（pattern_extractor 補 query + crystallizer 生 regex）| 一 | 中（routing）| 待 — 走影響盤點協議 |
| P1 | tools_manifest 自 tool_registry 動態生成 | 二 | 中 | 待 — 走影響盤點協議 |
| P2 | federation 跨專案 KG hub 強化 | 二/三 | 中 | 待 — 跨 repo |
| P2 | Hermes meta profile skill 註冊 | 二 | — | 待 — 上游 hermes-agent |

> **本 session 防禦升級（柱三「失敗 LOUD」已落地三層）**：① 8 cron `.parent` 修（`5c59e7dc`）② 開機自檢（`1468da1a`）③ silent return→raise 12 處（`94c12538`）④ outcome-freshness watchdog（`b6ae4810`）。silent 中斷現在「開機現形 + 失敗 watchdog 報 + 產出 freshness 報」三重自證。

> **紀律**：P1/P2 涉行為/路由/跨檔，動手前一律走 [[feedback_rigor_no_self_inflicted_instability]] 影響盤點。P0 純加可先做。

---

> **架構發展一句話**：坤哥（學習閉環）是「大腦自我進化」、Hermes agents 是「神經與感官接通」、平臺服務管理是「器官自證存活」——三者的共同發展軸是**從「建構」走向「接通 + 真活 + 自證」**。能力都在，差的是把線接到底、讓斷裂自己叫出來。
