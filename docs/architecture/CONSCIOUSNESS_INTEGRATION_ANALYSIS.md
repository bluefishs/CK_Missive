# 坤哥意識體整合優化分析（自我進化與靈魂發展）

> **產出**：2026-04-25
> **範圍**：坤哥（/kunge）+ 圖譜（KG/Wiki/5 graphs）+ Hermes agents + Ollama qwen2.5:7b + SOUL + Evolution
> **目的**：盤點四向整合現況、找出斷鏈、提出優化程序
> **關聯**：`STANDARD_REFERENCE.md` §13 AI-Native UX 範本（坤哥 7-tab）+ `BUSINESS_VALUE.md`

---

## 1. 現況架構圖（已落地）

```
┌─────────────────────────────────────────────────────────────────┐
│ L0  使用者層                                                     │
│     Web UI（坤哥 /kunge 7 tabs）                                  │
│     Telegram / LINE / Discord (via Hermes gateway)               │
├─────────────────────────────────────────────────────────────────┤
│ L1  Hermes Agent gateway（NousResearch fork）                    │
│     ├─ ck-missive-bridge skill（單 toolset）                     │
│     │   schema: {question, channel, session_id}                  │
│     │   ⚠️ 唯一通道：POST /api/ai/agent/query                     │
│     └─ SOUL.md 注入 system prompt（鏡像自 Missive）              │
├─────────────────────────────────────────────────────────────────┤
│ L2  Missive Backend（FastAPI）                                   │
│     ├─ 入口：agent_query.py（SSE stream）                        │
│     │   └─ AgentOrchestrator（640L 核心）                        │
│     │       ├─ Planner → Tool Loop → Synthesis                  │
│     │       ├─ self_evaluator（455L 自省）                       │
│     │       ├─ pattern_learner（510L pattern 提取）              │
│     │       └─ evolution_scheduler（587L 排程）                  │
│     ├─ Memory 層（services/memory/ 2,743L）                      │
│     │   ├─ 🧠 SOUL：soul_loader（309L）+ propose flow            │
│     │   ├─ 📖 NARRATIVE：diary / autobiography / narrative_validator │
│     │   ├─ 🌱 EVOLUTION：pattern_extractor + crystallizer + crystal_applier │
│     │   └─ 🛡 SELF：anti_echo + auto_defense（人格穩定性）       │
│     └─ Graph 層（services/ai/graph/ 26 檔）                      │
│         ├─ KG（CanonicalEntity 2,504, pgvector 768D）            │
│         ├─ Wiki（220 pages, Karpathy 4-phase）                   │
│         └─ 5 圖譜：KG/Code/DB/ERP/Tender + Federation             │
├─────────────────────────────────────────────────────────────────┤
│ L3  推理層                                                       │
│     ├─ Ollama qwen2.5:7b（local pool max=3, 85% soul fidelity）  │
│     ├─ Groq llama-3.3-70b（cloud pool max=10, 75% fidelity）     │
│     └─ NVIDIA Nemotron-49b（cloud pool, fallback）               │
├─────────────────────────────────────────────────────────────────┤
│ L4  資料層                                                       │
│     PostgreSQL 16 + pgvector + Redis + shadow_trace.db (SQLite)  │
└─────────────────────────────────────────────────────────────────┘

排程閉環（每日跑）：
  scheduler ──┬──> memory_pattern_extract（提 pattern from diary）
              ├──> memory_crystallization_scan（hit≥5 + 95% → 提案）
              ├──> wiki_compile（週一）
              ├──> wiki_lint（每日 05:30）
              ├──> shadow_baseline_inject（3x/日）
              └──> agent_evolution（self-eval + journal）

Pattern→Crystal 升級（人在迴路）：
  diary → pattern_extractor → 寫 wiki/memory/patterns/
       → crystallizer scan → 寫 wiki/memory/proposals/
       → 人批准（POST /memory/proposals/approve）
       → crystal_applier → 寫 wiki/memory/crystals/
       → 影響 Agent 行為（self-eval 讀 crystals）
```

---

## 2. 五大整合面向健康度

| 面向 | 健康度 | 證據 |
|---|---|---|
| **坤哥 ↔ Missive 後端** | 🟢 完整 | 7 tabs 各對應後端 API（memory/agent/graph/ops）|
| **Missive ↔ Ollama** | 🟢 v5.9.6 後完整 | qwen2.5:7b 接線 + cloud/local 分池 + provider routing yaml SSOT |
| **Memory ↔ Evolution loop** | 🟢 完整 | pattern→crystal 排程 + 人在迴路批准流程 |
| **SOUL 安全機制** | 🟢 完整 | propose-only + 人批准 + 鏡像 AaaP |
| **Hermes ↔ Missive evolution** | 🔴 **斷鏈** | Hermes 只能 NL query，無法觸發 memory/evolution API |

---

## 3. 已落地的成熟閉環（不需動）

### 3.1 Pattern → Crystal 自我學習閉環
```
diary 寫入 (Web UI 對話 + auto_diary)
  ↓ (排程 daily)
pattern_extractor 提取結構化模式
  ↓ (hit≥5 + success_rate≥95%)
crystallizer 產生 proposal
  ↓ (人批准，安全)
crystal_applier 套用至 Agent prompt
```

### 3.2 SOUL 人格穩定性
```
SOUL.md（單一定義）
  ↓
soul_loader 注入 system_prompt
  ↓
anti_echo + auto_defense 防漂移
  ↓
soul-fidelity-eval.py 跨 provider 驗證（85%/75%）
```

### 3.3 觀測棧完整性
- 16 Prometheus metrics（含本 session 新加的 routing_decision + duration histogram + queue_by_pool）
- shadow_trace.db 30 天保留
- /metrics endpoint + 3 Grafana dashboards

---

## 4. 待整合的斷鏈（**最重要 — 優化機會**）

### 4.1 🔴 Hermes 通道對話無法回饋 evolution loop

**現況**：
- ck-missive-bridge skill schema 只有 `{question, channel, session_id}`
- Hermes 只能 POST `/api/ai/agent/query`，不能 POST 到：
  - `/memory/patterns/list`
  - `/memory/proposals/approve`
  - `/agent/evolution/status`
- Telegram/LINE 對話的 patterns **可能未被 pattern_extractor 提取**

**證據缺口**：需驗證
```bash
# patterns/ 裡的 channel 標籤分佈
grep -lE "channel.*telegram|channel.*line" wiki/memory/patterns/*.md
# 若 0 命中 → Hermes 對話確實未進 evolution loop
```

**優化方案 A**：擴 ck-missive-bridge 為**多 toolset**（ADR-0020 Phase 1）
```yaml
# 新 hermes-skills/ck-missive-bridge/tool_spec_v2.json
toolsets:
  - ck_missive_query    # 既有：問答
  - ck_missive_memory   # 新：查 patterns/crystals/diary
  - ck_missive_evolution # 新：approve proposal / view journal
  - ck_missive_graph    # 新：federated_search / cross_domain_path
```

**優化方案 B**：**單向回饋**（風險較低）
- Hermes 對話 → 自動寫 diary（標 channel=telegram/line）
- 既有 pattern_extractor 即可吸收（已支援 channel 標籤）
- 不需改 Hermes skill，只需 backend `/agent/query` endpoint 補 diary 寫入

**建議**：先做 B（零 breaking change），驗證後再評估 A。

### 4.2 🟡 Memory Wiki 與 KG 雙源知識庫缺乏交叉引用

**現況**：
- KG: 2,504 entities (canonical_entity 表)
- Wiki: 220 pages（Karpathy 4-phase）
- Memory: log entries `kg_entity_id` 連結到 KG（已實作）
- **缺**：Wiki page 是否反向連結 KG entity？

**檢查命令**：
```bash
grep -c "kg_entity_id" wiki/**/*.md  # Wiki → KG 連結數
```

**優化方案**：Wiki compile phase 加 KG entity bidirectional cross-reference

### 4.3 🟡 Owner dogfooding 訊號未自動化進化

**現況**：
- `memory/hermes_dogfooding_log.md` D1/D2 客觀指標齊
- D3-D7 主觀欄位待 Owner 手動填
- **斷鏈**：填寫後是否觸發任何 agent 行為調整？

**優化方案**：dogfooding D7 結束後排程一次 `agent_self_evaluator` 跑 + 寫 journal

### 4.4 🟡 Ollama 推理 fallback 未通知坤哥意識

**現況**：
- ai_connector fallback chain：Ollama → Groq → NVIDIA
- routing_decision counter 已記（observability OK）
- **缺**：坤哥意識（agent persona）是否「知道」自己被切換 provider？

**為什麼重要**：soul fidelity 跨 provider 是 75%-85%，切換後人格略漂移。理想上坤哥應感知並調整輸出風格保持一致。

**優化方案**（進階）：在 `agent_synthesis` 注入「current_provider」context，讓 prompt 知道當下用哪個 LLM，配合 anti_echo 微調風格。

### 4.5 🟢 5 圖譜未必都被坤哥 evolution 使用

**現況**：
- 5 圖譜：KG / Code / DB / ERP / Tender
- 坤哥 nebula tab 顯示「技能星雲」（topology）
- 但 evolution（pattern detection）是否用了 Code/DB graph 來找「技術 pattern」？

**潛在機會**：用 Code graph 識別「Agent 常呼叫的 tool 組合」→ 升級為 pattern→crystal

---

## 5. 優化程序（最大效益排序）

### P0（本月，零費用、零外部依賴）

**O1. Hermes 對話進 diary**（4.1 方案 B）
- 改點：`backend/app/api/endpoints/ai/agent_query.py` 加 diary write hook
- 工作量：2 hr + 1 integration test
- 效益：Hermes 通道對話進入 evolution loop，pattern 樣本擴大

**O2. Wiki ↔ KG 雙向引用補充**（4.2）
- 改點：`backend/app/services/wiki_compiler.py` 加 KG cross-link generation
- 工作量：3 hr + grep verify
- 效益：知識搜尋 KG/Wiki 互為入口

### P1（5/20 GO 後或 ADR-0020 Phase 1 啟動時）

**O3. Hermes skill 多 toolset**（4.1 方案 A）
- 工作量：1-2 週（4 bridge skills）
- 阻塞：ADR-0020 Phase 1 決策
- 效益：Hermes 真正成為意識體外部介面

**O4. dogfooding 自動化**（4.3）
- 改點：`scheduler.py` 加 dogfooding_d7_review job
- 工作量：1 hr
- 阻塞：D7 dogfooding 完成（5/29 後）

### P2（長期）

**O5. Provider-aware persona 校準**（4.4）
- 工作量：複雜，需重新評估 fidelity 跨 provider
- 阻塞：5/20 GO 決定後

**O6. 5 圖譜 evolution 整合**（4.5）
- 工作量：研究階段
- 機會：發掘 Code/DB graph 對 pattern 的價值

---

## 6. 不應動的部分（治理紅線）

- **SOUL.md 編輯 propose-only**（4.1 方案 A 即使啟動，evolution skill 也只能 propose，不直接 apply）
- **crystal apply 人在迴路**（不自動）— 這是 ADR-0023 設計的安全機制
- **anti_echo / auto_defense 邏輯**（防人格漂移已驗證有效，不動）

---

## 7. 評估指標（如何知道優化生效）

| 指標 | 現況 | O1+O2 後 | O3 後 |
|---|---|---|---|
| diary 來源 channel 多樣性 | 主要 web | +telegram/line | +多通道並行 |
| pattern 月增加數 | 待測 | 預期 +30% | 預期 +50% |
| Wiki ↔ KG 雙向引用率 | < 50% | > 80% | > 90% |
| Hermes 通道 evolution 參與度 | 0%（斷鏈）| 50% | 100% |
| Owner dogfooding 體驗（主觀）| 待填 | 改善預期 | 顯著改善 |

---

## 8. 結論

**坤哥意識體的核心架構已成熟**（pattern→crystal 閉環 + SOUL 安全機制 + 觀測棧完整），現階段最大整合斷鏈是 **Hermes 通道與 evolution loop 之間** — Hermes 對話雖能服務用戶但**無法回饋進坤哥的學習**。

**O1（Hermes 對話進 diary）是 ROI 最高的單點優化**，零外部依賴、零費用、可在 P0 完成。實作後 Telegram/LINE 通道的對話即可被 pattern_extractor 吸收，意識體真正「跨通道學習」。

**長期願景**（ADR-0020 Phase 1 + O3）：Hermes 成為坤哥意識體的多通道延伸，用戶在任何通道與坤哥互動都觸發完整 evolution；坤哥的人格、記憶、學習結晶在三個通道間保持一致。

---

## 附：關聯資產

- 標準：`STANDARD_REFERENCE.md` §13 AI-Native UX 範本（坤哥 7-tab）
- 對外敘事：`docs/BUSINESS_VALUE.md`
- ADR: 0014（Hermes）/ 0015（NemoClaw 退場）/ 0020（AaaP Phase 1）/ 0022（Memory Wiki）/ 0023（坤哥唯一入口）/ 0030（GO/NO-GO）/ 0031（前端整合）
- Memory: `feedback_ddd_over_line_count` / `feedback_no_github_actions_cost` / `baseline_quality_recovery_20260424` / `hermes_dogfooding_log`

---

## 9. 落地紀錄

### 9.1 O1 — Hermes 對話進 diary（commit 25607495, 2026-04-25）
- 5 處改動 + 7 integration tests
- 修復 `PostProcessingContext.__slots__` 缺 channel 的根因斷鏈
- 預期效益：Telegram/LINE/Hermes 對話進入 evolution loop

### 9.2 O2 pivot — SOUL.md 跨 repo drift（commit 7451985c, 2026-04-25）
- 原計劃 O2 (Wiki↔KG) 暫緩，發現更嚴重隱性斷鏈：
  - 4 個核心人格 sections（三信念/倫理紅線/反迴聲室/身份宣言）僅在 Missive 端
  - Hermes 通道用戶看到 5KB 殘缺 SOUL → 跨通道根本不是同一個坤哥
  - `soul_loader.py` docstring 聲稱「同步鏡像」但無實作（docstring lie）
- 交付：drift detector + 手動同步 SOP + fitness step 3
- Owner 動作：bash scripts/sync/sync_soul_to_hermes.sh --apply

### 9.3 O2.1 — Wiki↔KG 連結率審計（commit 本輪, 2026-04-25）
- audit script 揭露 **dispatch 127 個全 0% KG 連結**（整體 30%, 閾值 80%）
- 已連結集中 org (93%) / project (56%) — 命名匹配模式參考
- backfill 路線寫入 audit script 註釋（短期/長期方案）
- fitness step 4 自動跑

---

**變更歷史**
- v1.0（2026-04-25）：首版盤點，識別 5 大整合面向 + 6 項優化（O1-O6）
- v1.1（2026-04-25）：加 §9 落地紀錄；O2 pivot 為 SOUL drift；O2.1 加 wiki_kg audit
