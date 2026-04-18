# ADR-0014: 以 NousResearch Hermes Agent 取代 OpenClaw

> **狀態**: accepted (amended 2026-04-18)
> **日期**: 2026-04-14
> **決策者**: 專案 Owner
> **關聯**: ADR-0010 (Qwen3-4B 本地 LLM), `memory/hermes_openclaw_deferred.md` (superseded), docs/HERMES_MIGRATION_PLAN.md

## 2026-04-18 修訂（Amendment）

原決策內容保留作為歷史脈絡。以下兩點為後續執行中發現的實質變更，在本節補註（未更動正文），後續若範圍再擴大將另立 ADR：

1. **LINE 通道保留**（覆蓋原「LINE 小花貓 Aroan 下線」）
   - **原因**：臺灣用戶主力集中於 LINE，Telegram/Discord 無法替代。
   - **執行路線**：Phase 0/1 不動 LINE bot（續走 OpenClaw / Missive LINE adapter），Phase 2 硬切時再評估 LINE adapter 改寫（對接 Hermes gateway OpenAI-API `:8642/v1`）。
   - **影響**：OpenClaw 下線時程需與 LINE adapter 遷移同步；NemoClaw 歸檔日（2026-05-26，ADR-0015）仍維持，但 LINE bot 所需的底層服務需確保不在歸檔範圍。

2. **Phase 0 主力 LLM 為 Groq，Anthropic 暫緩**（覆蓋原「Groq 作為 P1 fallback」定位）
   - **原因**：Anthropic credit 未充值；Groq 免費層（llama-3.3-70b-versatile）在 Phase 0 shadow 流量下額度充裕。
   - **執行**：`CK_AaaP/runbooks/hermes-stack/config.yaml.example` 已將 Groq 設為 `model`（主），Ollama gemma4:e2b 設為 `fallback_model`；Anthropic 區塊註解化，待後續架構穩定後再議。
   - **GO/NO-GO 影響**：Phase 0 baseline p95 / tool-call 等價率改以「Groq + Ollama」為實測對象；若 Groq tool-calling 品質達標，可直接進 Phase 1，無需等 Anthropic。



## 背景

1. **成本痛點**：OpenClaw 依賴 Claude Haiku API 處理訊息格式化／意圖辨識，每日穩定流量下成本持續累積。
2. **架構痛點**：OpenClaw 僅作 Skill 轉發層，本身不具學習、技能累積、跨 session 記憶能力。Missive backend 已有 `agent_orchestrator`，但通道側（OpenClaw）無狀態重傳增加整體複雜度。
3. **外部選項**：`NousResearch/hermes-agent` (MIT, 2026-04 釋出) 為自帶學習閉環的 Agent runtime，具備 gateway 多通道、SQLite session、skill self-improvement、40+ 內建 tool、serverless 部署（Daytona/Modal）等特性，與我們的目標直接對應。

## 決策

**取代 OpenClaw 為 Hermes Agent 作為通道側 Agent runtime**：

- Hermes gateway 接管 **Telegram + Discord** 通道。
- **LINE 小花貓 Aroan 下線**（Hermes 原生不支援 LINE；不值得為單通道自建 adapter）。
- Missive backend 不動核心，僅提供 **HTTP Tool 介面**（`/ai/agent/query_sync`）供 Hermes 呼叫。
- LLM 使用本機 Ollama Gemma 4 8B Q4（P0 已部署），雲端 Groq / NVIDIA 作為 P1 fallback。
- 遷移分 4 Phase 執行（見 HERMES_MIGRATION_PLAN.md），**Shadow Logger 作為切換前的基線證據**。

### 範圍界定

| 範圍 | 保留 | 變更 | 下線 |
|---|---|---|---|
| Missive backend Agent | ✅ 保留完整 | 僅暴露 HTTP tool | — |
| CK_NemoClaw Docker | ✅ 保留 | 新增 hermes 服務 | openclaw 服務 |
| LINE webhook | — | — | ❌ 下線 |
| LINE Bot Service (`backend/`) | ✅ 程式碼保留 | 停止 webhook 註冊 | — |
| Telegram webhook | — | 轉指向 Hermes gateway | — |
| Discord Interactions | — | 轉指向 Hermes gateway | — |

## 後果

### 正面

- **LLM 成本歸零**：Haiku → 本機 Gemma 4 8B（Ollama GPU，RTX 4060 8GB 已部署）。
- **Agent 能力升級**：Hermes 自帶 skill 累積、FTS5 跨 session 搜尋、學習閉環。
- **部署彈性**：支援 Daytona/Modal serverless，idle 近零成本。
- **生態對齊**：與 agentskills.io 開放標準相容，未來可引入社群 skill。
- **降架構複雜度**：單 gateway 取代 OpenClaw + 三通道 adapter 堆疊。

### 負面

- **失去 LINE 通道**：小花貓 Aroan 停止服務；LINE 業務流需改走 Telegram/Discord 或直接 Web。
- **學習曲線**：Hermes skill 撰寫規範（`~/.hermes/skills/`）與現有 `channel_adapter.py` 不同。
- **雙 Agent 治理**：Hermes（通道側）+ Missive orchestrator（資料側）需明確職責切分，避免重複學習/記憶。
- **LINE 歷史資料沉澱風險**：OpenClaw 現有對話歷史/config 需歸檔備查。

## 替代方案

| 方案 | 排除原因 |
|---|---|
| **A. 僅換 LLM（Haiku→Gemma）保留 OpenClaw** | 解決成本但不解決架構問題；與本次選定方向相反 |
| **C. Hermes 取代 + 自建 LINE adapter** | 工作量 1–2 週且與 Hermes 升級路徑耦合；維運兩條 gateway |
| **D. Hybrid（Hermes 接 TG/Discord, OpenClaw 僅留 LINE）** | 雙橋增運維負擔；LINE 成本仍在 |
| **E. 原地不動** | 痛點未解 |

## 驗證與回滾

- **驗證指標**（Shadow Logger 3–7 天基線）：p50/p95 延遲不劣於 Haiku、成功率 ≥ 95%、tool-use 分佈合理。
- **回滾路徑**：OpenClaw 容器 compose 保留（註解）2 週；webhook 可回切；LINE 通道回復需 24h 內。
- **關閉條件**：Phase 3 結束後觀察 14 天無重大事故 → Phase 4 下線 OpenClaw。
