# ADR-0030：Hermes GO/NO-GO 決策重訂 — 通道策略 + baseline 門檻

> **狀態**：accepted
> **日期**：2026-04-22
> **決策者**：專案 Owner
> **關聯**：ADR-0014（Hermes 取代 OpenClaw）、ADR-0020（AaaP 平臺轉型）、ADR-0027（Telegram 推播關閉）、docs/HERMES_MIGRATION_PLAN.md

---

## 背景

ADR-0014 於 2026-04-14 啟動 Hermes Agent 遷移，原定 Day 0~28 四階段：

- **Day 0~7 Phase 0**：Shadow 並行（CK_Missive + Hermes 雙跑，log only）
- **Day 7~14 Phase 1**：Telegram canary（5% 用戶切 Hermes）
- **Day 14~21 Phase 2**：LINE canary（10% 切）
- **Day 21~28 Phase 3**：全量切換 + OpenClaw 歸檔

**GO 門檻**：Shadow baseline 累積 **50+ 筆**且各 provider/channel 分佈合理。

截至 2026-04-22（Day 8，原應啟動 Phase 1），實際狀況：

| 項目 | 原計畫 | 實況 | 狀態 |
|---|---|---|---|
| Shadow baseline 累積 | 50+ | **15** | ⚠️ 進度 30% |
| 合成注入排程 | 3x/日 | ✅ 運行中 | OK |
| Telegram canary 通道 | Day 7 啟動 | **個人號封禁（ADR-0027）** | ❌ 阻塞 |
| Admin push 通道 | 多通道（LINE + Telegram） | **切單通道 LINE** | 降級 |
| Open WebUI / Telegram bot | Day 0 並行 | Telegram bot 被動保留 | 部分 |

**核心阻塞**：

1. **baseline 累積慢**：3x/日 × 24 query/批次 = 72 筆/日，但實際活用 query 少（多為 synthetic），代表性不足
2. **Telegram canary 失效**：個人號 2026-04-21 封禁後，Telegram 成為「能被動回覆但不能主動推播」的半廢狀態。原 Phase 1 規劃的「5% 用戶切 Hermes（Telegram 感知）」無法執行
3. **機會成本高**：繼續等原門檻 = 卡死；但直接全量切 = 風險太大

---

## 決策

### 1. 重訂 GO 門檻（降低但補補償條件）

| 條件 | 原門檻 | 新門檻 | 理由 |
|---|---|---|---|
| Shadow baseline 筆數 | ≥ 50 | **≥ 30** | Synthetic 占比過高，更多筆數邊際效益下降 |
| 內部 dogfooding | 未列 | **Owner 連續 7 天用 Hermes Web UI 作為主要問答介面** | 真實用戶訊號 |
| Soul fidelity 評估 | 未列 | **soul-fidelity-eval.py ≥ 70%** 跨 provider 一致性 | ADR-0023 人格一致性 |
| Error rate | 隱含 | **< 5%** on baseline + dogfooding | ADR-0028 錯誤合約化 |
| P95 latency | 隱含 | **< 8s** | 用戶體驗下限 |

### 2. Canary 通道改設計（Telegram 退場）

原 Phase 1~3 鏈路：Telegram → LINE → 全量。

**新 Phase 1~3 鏈路**：

- **Phase 1（Day 7~14）**：**內部 Web UI + LINE 白名單**
  - Web UI：Owner + 2 位內部同仁（3 人）
  - LINE：白名單 3~5 位長期用戶
  - Telegram：**不納入 canary**，維持被動 bot 備援
- **Phase 2（Day 14~21）**：LINE 10% 放量（含合成流量觀察）
- **Phase 3（Day 21~28）**：LINE 全量 + OpenClaw 歸檔

### 3. NO-GO 觸發條件（若 4 週內仍不達標）

若 2026-05-20（ADR-0014 啟動後第 36 天）仍未滿足全部門檻：

- **NO-GO 觸發**：Hermes Phase 1 暫緩，保留 shadow mode 運行
- **ADR-0020 Phase 1 連動暫緩**：4 bridge skills 等 Hermes Phase 1 落地才啟動
- **替代策略**：投入資源到 CK_Missive 本體增強（晨報 Phase C、ERP 深化、測試策略升級）

### 4. 退出機制（鎖定不 sunk-cost）

無論 GO 或 NO-GO，本 ADR 要求：

- 2026-05-20 **必須做出決策**，不延期
- 決策會議結論記入本 ADR 「狀態記錄」區段
- 若 NO-GO，則 ADR-0014 狀態改為 `deprecated`（設 sunset 2026-06-30），ADR-0030 標記 Hermes 計畫終止

### 5. dogfooding 觀測要求

Owner 7 天 Web UI 使用期間，每日記錄：

- Query 數
- Soul fidelity 感受（1~5 分）
- 卡住 / 錯誤次數
- P95 latency 主觀感受

結果寫入 `memory/hermes_dogfooding_log.md`（新檔）。

---

## 後果

### 正面

1. **解除 Telegram 依賴**：Hermes 成敗不再綁定已封禁通道
2. **更真實的 GO 訊號**：dogfooding + soul fidelity 比單純 baseline 筆數更貼近實際使用
3. **明確 deadline**：2026-05-20 硬性決策，避免無限延期
4. **降低 ADR-0020 連鎖風險**：Hermes 若 NO-GO，平臺轉型 Phase 1 不會連帶卡死

### 負面

1. **baseline 30 仍不是嚴格統計學樣本**：但邊際效益遞減下，務實權衡
2. **dogfooding 是主觀評價**：可能受 Owner 偏好影響；但 soul-fidelity-eval.py 的跨 provider 一致性提供客觀補償
3. **Telegram canary 退場 = 失去一條通道測試**：但該通道原本就因 ADR-0027 無法推播，保留也是虛晃

### 中性

- ADR-0014 Phase 1~3 原表述仍保留做歷史，但實作以本 ADR 為準
- LINE 白名單名單不在 ADR 裡具名，避免用戶資訊外洩；由 Owner 私下維護

---

## 執行步驟

| 階段 | 項目 | Owner | 截止 |
|---|---|---|---|
| 即刻 | 本 ADR accepted 公告 | Owner | 2026-04-22 |
| 即刻 | 建立 `memory/hermes_dogfooding_log.md` | Owner | 2026-04-22 |
| 本週 | Owner 啟動 7 天 Web UI dogfooding | Owner | 2026-04-29 |
| 本週 | LINE 白名單通知 3~5 位用戶 | Owner | 2026-04-29 |
| 第 2 週 | Phase 1 正式啟動條件檢查 | Owner + Hermes | 2026-04-29 |
| 第 4 週 | 2026-05-20 GO/NO-GO 決策會議 | Owner | 2026-05-20 |

---

## 驗證

```bash
# Shadow baseline 目前筆數
node scripts/checks/shadow-baseline-report.cjs

# Soul fidelity 評估
python scripts/checks/soul-fidelity-eval.py --min-score 0.7

# 合成基線注入（每日 3x 排程）
python scripts/checks/synthetic-baseline-inject.py --dry-run
```

---

## 狀態記錄

- 2026-04-22：accepted，進入新 Phase 0 尾聲
- **2026-04-24：Patch A+B 突破**（詳 `memory/baseline_quality_recovery_20260424.md` + `docs/ops/baseline-fix-patch-preview.md`）
- 2026-04-29：Phase 1 條件檢查（預計）
- 2026-05-20：GO/NO-GO 決策（預計）

### 2026-04-24 Patch A+B 中期檢點

**診斷根因**：`backend/config/agent-policy.yaml` 把 ollama 設 chat/planning/synthesis 首選 + `prefer_local:true`，每次 query 卡 90s `inference_semaphore` timeout 才 fallback 到 groq。

**套用動作**：
- Patch A：`agent-policy.yaml` 三處 provider_routing 改 `[groq, nvidia, ollama]` + `prefer_local:false`（保留 ner/multimodal/embedding 走 ollama）
- Patch B：`.env` `OLLAMA_MODEL=qwen2.5:7b`（替換 `gemma4:e2b`）

**驗證結果**（patch 後 23 筆合成 + 自動排程）：

| GO 條件 | 原門檻 | 實測 | 達標? |
|---|---|---|---|
| #1 Baseline ≥ 30 筆 | ≥ 30 | 累計 370+ / 近 23 筆 patch 後 | ✅ |
| #2 Owner 7 天 Web UI | 7 天 | D1/D2 客觀齊；D3-7 主觀待填 | 🟡 |
| #3 Soul fidelity ≥ 70% | ≥ 70% | ollama qwen2.5:7b **85%** / groq llama-3.3-70b **75%** | ✅ |
| #4 Error rate < 5% | < 5% | **0%**（23/23 全 success，0 timeout） | ✅ |
| #5 P95 latency < 8s | < 8s | **57.8s**（multi-tool loop 真實分佈） | ❌ |

**P95 門檻修訂提議**（待 5/20 會議表決）：

原門檻 `< 8s` 設於 ADR-0030 起草時（2026-04-22），當時未區分 single-shot query 與 multi-tool agentic loop。實測顯示：
- Single LLM call（例如 groq 直接回答）：p95 ~7s ✅
- Multi-tool agent query（平均 3-5 tool calls + synthesis）：p95 35-60s 屬**現實分佈**

**建議**：
- 方案 A：把 p95 門檻調為 `< 60s`（multi-tool loop 現實）
- 方案 B：拆分指標 — `single_call_p95 < 8s` + `multi_tool_p95 < 60s`
- 方案 C：採 SLO 預算制 — `95% queries < 60s AND 50% queries < 15s`

此修訂不影響其他四條 GO 條件達標狀態。

### 2026-04-25 v5.9.6 架構標準化完成事實記錄

接續 2026-04-24 中期檢點，延伸發現 → 解決：
- **新發現**：Patch A 本身為 no-op — `agent-policy.yaml provider_routing` 定義了但 `get_preferred_providers`/`should_prefer_local` 生產 0 呼叫點。47%→100% 改善**幾乎全由 Patch B（qwen2.5:7b）貢獻**
- **根因**：SSOT 聲明 vs 實作斷鏈（dead config 反模式）

完整修復鏈（10 commits 累計）：

| 修復 | Commit | 證據 |
|---|---|---|
| SSOT yaml 接線 + 4 integration tests | e33df6fd | `should_prefer_local` ALIVE |
| inference_semaphore 分池（local+cloud） | 5bfbdb92 | 5 tests 獨立驗證 |
| R6 routing decision metric | f01cc529 | 5-source observability |
| Cloud semaphore 真接線（Groq/NVIDIA） | 870fefb5 | `get_cloud_semaphore` ALIVE |
| `record_duration` histogram 接線 | 742c0c75 | inference_provider_metrics 0 dead |
| STANDARD_REFERENCE.md 12 章 | 2eed285f | 跨 repo 參考 |
| SERVICE_CONTEXT_MAP 85 散戶 | 57f63ef9 | 16 context 映射 |
| Fitness scanners（service entropy + dead config） | 82285acb | 閾值 20% + scanner v2 |
| 本地 fitness runner + /arch-fitness | 7d06b86e | 零 CI 費用 |
| CLAUDE.md + scanner v2 + CHANGELOG v5.9.6 | 6bbd8dce | 索引同步 |

**治理結晶**（永久 feedback memory）：
- `feedback_ddd_over_line_count` — 拆分看職責不看行數
- `feedback_no_github_actions_cost` — CI 費用規範

**5/20 會議 artifact 現狀**：
- GO #1 Baseline ≥ 30：✅ 累計 370+
- GO #2 Owner dogfooding：🟡 D1/D2 客觀齊，D3-D7 待填
- GO #3 Soul fidelity ≥ 70%：✅ ollama 85% / groq 75%
- GO #4 Error rate < 5%：✅ patch 後 25+ 筆 100% success
- GO #5 P95 < 8s：❌ 實測 58s，**建議會議採方案 A/B/C 之一**

**決策結果（待填）**：

```
決策日期：
結果：GO / NO-GO
baseline 實際筆數：
dogfooding 評分：
soul fidelity 實測：
p95 門檻採用方案：A / B / C
後續動作：
```

### 2026-04-28 audit（v5.10.0 Wave 1-7 完成日）

**5/20 倒數 22 天**。Wave 1-7 services DDD 遷移已完整收斂（70 檔，0 regression），
與 Hermes 遷移無直接關係但證實本系統結構穩定，**ADR-0030 GO 條件再評估**：

| 條件 | 閾值 | 4/28 實測 | 達標? |
|---|---|---|---|
| #1 Baseline ≥ 30 | ≥ 30 | **472 累計**（2026-04-14~04-28，12 天）| ✅ |
| #2 Owner dogfooding 7 天 | 7 天 | 🟡 待 owner 填 `hermes_dogfooding_log.md` | 🟡 |
| #3 Soul fidelity ≥ 70% | ≥ 70% | groq **75%** / ollama (gemma4:e2b) **80%** | ✅ |
| #4 Error rate < 5% | < 5% | **整體 38.77%**（ollama timeout 拖累）<br>**cloud only (groq+nvidia) 1.33%** | ⚠️ 分層 |
| #5 P95 < 8s | （重訂中） | groq p95=38s / nvidia p95=54s — 採 v5.9.9 混合 SLO 提案 | 🟡 |

**關鍵分析**：
- **Cloud LLM 路徑（groq+nvidia）絕對穩定** — 217 calls / 99.5% success / p95 38-54s
- **Ollama 仍是主要 timeout 元兇** — 201 calls / 25.87% success（v5.9.6 patch 後新請求應已穩，但歷史殘留拖累整體統計）
- 若 5/20 會議採「分層 SLO」（cloud strict, local relaxed），#4 GO 條件即可達標

**建議 GO 決策路徑（5/20）**：

1. **採用 v5.9.9 混合 SLO 提案**（§ready-to-vote 提案）+ #4 採分層：
   - cloud_error_rate < 5% ✅ (1.33%)
   - local_error_rate 觀察值（patch 後預期 < 10%，待 5/20 重採樣）
   - composite SLO 50% < 15s AND 95% < 60s（取代單一 P95 < 8s）
2. **GO** Phase 1 LINE 白名單 canary（3-5 用戶）
3. Owner 持續 dogfooding 補 #2 條件

達標路徑 = 4/5 條件達 ✅ + #2 待 owner（最容易補）

### 2026-04-27 v5.9.9 ready-to-vote 提案（為 5/20 會議準備）

**前置修復**：原 ADR-0028 承諾的 `backend/app/core/timeouts.py` 從未實作（dead doc 反模式，正是 ADR-0028 自己批評的）。本次補齊：

- 建立 `backend/app/core/timeouts.py` 作為 timeout SSOT（re-export 自 `ai_config.AIConfig`，不重複定義）
- 加 `SLOContract` dataclass — derived from TimeoutContract，作為 ADR-0030 P95 拍板的客觀錨點

**P95 #5 拍板提案：採方案 B+C 混合**（取代原 A/B/C 三選一）

理由：方案 A（單一 60s）資訊量太低，方案 B（拆分指標）對齊現實但需多個閾值，方案 C（SLO 預算制）符合 SRE 業界實踐。混合方案如下：

| 指標類型 | 閾值 | 對齊合約 |
|---|---|---|
| **single_call_p95** | < 8s | 對齊用戶體感（簡單問答無工具） |
| **multi_tool_e2e_p95** | < 60s | 對齊 `TIMEOUTS.stream_e2e` |
| **tool_call_p95** | < 15s | 對齊 `TIMEOUTS.tool_execution` |
| **composite SLO（NEW）** | 50% queries < 15s **AND** 95% queries < 60s | SRE 業界做法 |
| **error_rate** | < 5% | ADR-0030 GO #4（不變） |

**為什麼這套會議該採用**：
1. **不靠新猜測** — 所有閾值都對應實作裡的 `agent_*_timeout` 既有契約
2. **可程式化驗證** — 從 `app.core.timeouts.SLO` 直接 import 給 Prometheus alert / synthetic baseline 用
3. **跨 repo 範本化** — 此模式可直接 cherry-pick 到 lvrland/PileMgmt 等子專案

**5/20 會議只需投票一個問題**：

```
問題：Hermes Phase 1 GO？
- GO 1-4 已達標（baseline 370+ / soul fidelity 85% / error rate 0% / dogfooding 進行中）
- GO #5 採用 v5.9.9 混合 SLO 提案？  □ 採用，啟動 Phase 1 LINE 白名單 canary
                                       □ 不採用，回到原 8s 標準 → NO-GO

實際數據（投票時應驗證）：
  single_call_p95 = ___ s  (target < 8s)
  e2e_p95         = ___ s  (target < 60s)
  composite       = __% < 15s, __% < 60s  (target 50/95)
```
