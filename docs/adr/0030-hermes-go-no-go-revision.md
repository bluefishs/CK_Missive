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
