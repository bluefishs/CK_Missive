# 元層覆盤：為何多次治理仍發生 L51 同型事故 (Meta-Governance Retrospective)

> **狀態**: meta-retrospective — 第 N 層覆盤
> **觸發**: Owner 提問「多次覆盤與優化程序為何發生前述議題」
> **作用域**: 不是「修 L51」而是「修治理本身的盲點」
> **日期**: 2026-05-30

---

## 1. 直接證據：既有治理 vs L51 失效鏈

### 1.1 L4x family — 5 件同型事故反覆

| Lesson | 日期 | 事故 | 治理回應 |
|---|---|---|---|
| L41 | 2026-05-21 | JWT secret 跨 repo drift silent fail | ck-sso-js v2.0 |
| L43 | 2026-05-21 | docker volume name 跨 compose 不一致 | fitness step 38 |
| L44 | 2026-05-22 | SSO session lock cross-domain | hot-fix |
| L45 | 2026-05-22 | compose healthcheck override Dockerfile | fitness step 40 |
| **L48** | **2026-05-27** | **SSO env 未注入 container** | compose 補 5 vars |
| **L51** | **2026-05-29** | **LINE env 未注入 container（同 L48！）** | compose 補 8 vars + fitness step 57 |

**結論**：L48 修了 SSO env 注入，**10 天後**仍發生 LINE env 沒注入的同型事故。
→ 修法「只修對應 case」，沒推廣到「所有同類 env」。

### 1.2 F15 LINE notify watchdog 為何沒抓到 L51

```python
# scripts/checks/line_notify_heartbeat_check.py (v6.8 F15)
# 設計：7 天內 LINE push < 1 才告警
```

**事實**：L51 silent disabled 期間是 5/27 19:00 ~ 5/29 09:30 = **40 小時 < 7 天**

→ watchdog **設計上**無法及時抓到（時間窗口太長）

### 1.3 Pipeline 5/16 → 5/26 **連續 11 天 RED** 無人處理

```bash
$ grep "Overall.*RED" wiki/memory/pipeline-reports/*.md | wc -l
# 11 (5/16-5/26 全 RED)
```

優化 pipeline 每日跑、寫 wiki、產 markdown 報告 — **但沒人看**。

→「寫進 wiki」≠「有人看」≠「有人處理」

### 1.4 docker cp 不持久問題未被預想

- v6.7-v6.10 共 4 次大覆盤，**從未** 設計過 image content 驗證
- 既有 fitness step 沒一個檢查 container 檔 vs host 對齊
- L51 commit 5d03562f docker cp 修法「驗證 OK」假象，36h silent disabled
- 直到 L51.7.1 才補 step 60

→「修法跑通」假象，缺**部署完整性**驗證層

---

## 2. 治理本身的 4 個反模式

### 2.1 反模式 1：「修對應 case」而非「掃全範圍」

L48 修 SSO env 注入，**沒順手寫 audit 掃所有 env**。
→ L51 同型事故 10 天反覆。

**修法**：每次修「跨檔 SSOT 失效」事故，必須**同時建立 audit 掃同類所有資源**。

L51.7.1 落實：fitness step 57 container env audit 掃 5 個 group / 18 vars。

### 2.2 反模式 2：watchdog 時間窗口太長

F15 7-day watchdog 對 silent disabled <7d 無效。

實際業務感受層級：
- **1h** 內 silent → owner 體感（即時）
- **24h** 內 silent → 隔日覺察
- **7d** 內 silent → 已嚴重影響業務

**修法**：watchdog 應**分層**（不只 7d）：
- Tier 1（業務 critical）：1h window
- Tier 2（功能 critical）：24h window
- Tier 3（觀測健康度）：7d window

### 2.3 反模式 3：Pipeline 寫 wiki 但無人看 (passive forcing function)

11 天連續 RED 沒處理 — 治理機制存在但**無強迫機制**。

**修法**：Pipeline overall RED 連續 N 天 → **主動推 LINE**（不只寫 wiki）。

實際上 v6.10 optimization_pipeline 設計上有 push admin，但：
- 推 telegram（5/04 永封）+ LINE 但 LINE channel 在 PM2→docker 切換後 silent disabled
- L51 修了 LINE 鏈但 pipeline push 是否被 silent 也要驗

### 2.4 反模式 4：fitness step 增量爆炸無分層

```
v6.10:   27 step
v6.10.3: 38 step (+11)
v6.11:   60 step (+22)
v6.11.1: 61 step (+1)
```

61 step 月跑 ~10 分鐘 — owner 不會每天跑。

但很多 step 應該 **daily**（如 container_env / container_image_freshness / shadow_baseline 24h），不該等月度。

**修法**：分層執行：
- **daily auto** (5-10 step): critical observability
- **weekly auto** (15-20 step): trend tracking
- **monthly manual** (全 61 step): full audit

---

## 3. 覆盤本身的觀測缺口

### 3.1 沒人問「上次覆盤後反覆事故率」

每次覆盤都「**加新 step**」，**沒回頭看**：
- 上個 sprint 寫的 SOP 是否真被遵守？
- 上個季的 audit 跑了幾次？
- 上個月的 RED 處理了幾項？

### 3.2 沒「治理本身」的 metric

業務 metric 完整（v7 4 指標、tender、kunge）。
但**治理 metric 缺**：
- fitness step 月度跑率（owner 真實跑次數）
- Pipeline RED 連續天數
- 同型事故反覆率（L48/L51 同型）
- SOP 違反次數（docker cp 不跟 rebuild）

### 3.3 沒有「治理元覆盤」cron

業務有 weekly autobiography / monthly fitness。
但**治理元覆盤**沒有 cron — 全靠 owner 主動問。

---

## 4. 真正可持續治理原則（4 條）

### 原則 1：每個治理動作必含「掃全範圍」配套

```
反模式：
  L48 SSO env 修法 → 只補 SSO

正模式：
  L48 SSO env 修法 + 同時寫 container_env_alignment_audit
                  → 揭發 LINE/TELEGRAM/GOOGLE/AI 全範圍
                  → 同步補（不等下次事故）
```

實際 L51.7.1 已落實此原則：fitness 60 = 「image freshness」audit 掃 11 個 critical 檔。

### 原則 2：observability 必須**分層 forcing function**

```
Tier 1 (1h 內，業務感受層):
  - Prometheus alert (failure rate >50% / 1h)
  - 立即推 LINE + Telegram fallback
  - alertmanager 設置

Tier 2 (24h 內，功能健康):
  - tracked_job 完成寫 last_run timestamp
  - cron 24h 無觸發即 fitness RED
  - 已有 fitness step 58/59 cover

Tier 3 (7d 內，觀測健康):
  - 月跑 fitness 60+ step
  - 已有 run_fitness.sh
```

### 原則 3：治理本身 metric 化

新加 metric (v6.12 規劃)：
- `governance_fitness_run_count_30d`
- `governance_pipeline_red_consecutive_days`
- `governance_sop_violation_count_30d`
- `governance_lesson_repeat_rate` (L4x family 反覆率)

### 原則 4：元覆盤 cron（每季強制）

新 cron (v6.12)：
- 季初跑 `governance_meta_retrospective_job`
- 統計：
  - 上季 fitness 跑了幾次
  - 上季 Pipeline RED 連續天數
  - 上季同型事故反覆數
- 推 LINE：「上季治理健康度報告」

---

## 5. 為何 L51 不是「治理失敗」而是「治理進化」

L51 從 LINE silent disabled 40h 開始，最終揭發了：
1. docker-compose 缺 8 個 env vars
2. L48 同型事故反覆（治理「掃全範圍」缺漏）
3. PM2→docker 切換 runtime context 副作用
4. docker cp 不持久 silent regression
5. Pipeline 11 天 RED 無人處理
6. Facade 0 importer 孤兒設計
7. v7 4 metric 計算邏輯錯誤
8. SOUL 跨 repo drift SEVERE

**single design choice（tender_recommendation_history table）連帶解 8 個潛伏問題**。

但更重要：揭發**治理本身 4 個反模式** + 引導「治理進化」4 原則。

→ L51 不是治理失敗，是治理**達到下一階段**的契機。

---

## 6. v6.12 治理元議題改進路線

| 項目 | 預期 |
|---|---|
| **分層 fitness 執行**：daily/weekly/monthly | daily 10 step / weekly 25 step / monthly 全 61 step |
| **Tier 1 alertmanager rule** | messaging_push_failure_rate >50%/1h |
| **Pipeline RED forcing** | 連續 3 天 RED 強推 LINE |
| **治理 metric 化** | 4 個 governance_* metric |
| **元覆盤 cron** | 季初推治理健康度報告 |
| **同型事故鏈 audit** | 自動偵測 L4x family 重演 |

---

## 7. 對 Owner 的元層啟示

### 啟示 #1：治理是迭代的，不是「修完一勞永逸」

每次覆盤揭發新層次。L51 揭發治理本身的盲點 — 這是進步，不是失敗。

### 啟示 #2：「加新 step」≠「治理改善」

61 step fitness 沒人看 = 0 step 沒人看。

關鍵是**讓人或機器主動看**（cron / alertmanager / LINE push）。

### 啟示 #3：silent 比 error 更危險

L51 silent 40h 比 Hard error 40s 危險 1000 倍。
未來新功能優先設計：**silent 偵測 > error 處理**。

### 啟示 #4：同型事故鏈追蹤

L41-L51 共 5 案「跨檔 SSOT 治理失效」family。
治理應加「同型 family 追蹤」：每出現新案，自動掃同 family 所有歷史 case 是否已關閉。

---

## 8. Refs

- L51 主事故報告: `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md`
- v6.11 整合: `V6_11_INTEGRATED_GOVERNANCE_PROCEDURE_20260530.md`
- 坤哥覆盤: `KUNGE_AGENT_CHAIN_REVIEW_20260530.md`
- 跨檔 SSOT 規範: `.claude/rules/cross-file-ssot-governance.md`
- ADR 半接通 SOP: `.claude/rules/adr-anti-half-wired-sop.md`
- Pipeline reports: `wiki/memory/pipeline-reports/2026-05-*.md`
- Lessons family: `wiki/memory/lessons/L4{1,3,4,5,8}_*.md` + L51
- 元覆盤這份 (本文)
