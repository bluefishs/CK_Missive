# Fitness 分層執行 SOP (v6.12 治理進化 P0)

> **狀態**: enforced — v6.12 治理改進 #1 落地
> **觸發**: 元覆盤揭發「61 step 月跑 = 沒人看 = passive forcing function」反模式
> **作用域**: 把 fitness 61 step 分 3 層執行，daily/weekly/monthly
> **日期**: 2026-05-30

---

## 1. 問題背景

v6.11 累積 61 fitness step，月跑 1 次需 ~10 min，且：
- Owner 不會每天跑（manual reactive）
- 60 step 全跑後看「All passed」summary，細節 RED 容易被蓋過
- 部分 step 應 daily（如 container_env / image_freshness / shadow_baseline 24h），不該等月度

---

## 2. 分層原則

按時效性 + 執行成本：

```
Tier 1 — Daily (5-10 step, ~1 min) ★ auto cron
  優先級: 觀測層 silent failure 偵測
  失敗即推 LINE / Telegram

Tier 2 — Weekly (15-20 step, ~3 min) ★ auto cron
  優先級: 趨勢追蹤 + governance metric
  失敗寫 wiki + 連續 2 週推 LINE

Tier 3 — Monthly (全 61 step, ~10 min) ★ manual / owner 月度
  優先級: 完整架構覆盤
  失敗寫 wiki + 不 alarm（informational）
```

---

## 3. Tier 1 — Daily (5-10 step)

每日 02:00 自動執行（在 03:00 optimization_pipeline 之前）。

### 3.1 包含 steps

| Step | 內容 | 失敗動作 |
|---|---|---|
| 57 | container env alignment | RED 即 LINE |
| 58 | agent_query starvation | shadow 24h n=0 推 LINE |
| 60 | container image freshness | drift 即 LINE |
| 38 | docker_compose volume consistency | drift 即 LINE |
| 40 | compose/dockerfile healthcheck SSOT | drift 即 LINE |
| 47 | startup race condition audit | 異常即 LINE |

### 3.2 執行方式

```bash
# scripts/checks/run_fitness_daily.sh (新)
bash scripts/checks/run_fitness_daily.sh --strict
```

### 3.3 Cron 註冊（v6.12 加）

```python
# backend/app/core/scheduler.py
@tracked_job("fitness_daily")
async def fitness_daily_job():
    """每日 02:00 跑 Tier 1 daily fitness (~1 min)
    任一 RED → 推 LINE
    """
    ...
```

---

## 4. Tier 2 — Weekly (15-20 step)

每週日 02:30 自動執行。

### 4.1 包含 steps（額外）

| Step | 內容 |
|---|---|
| 3 | SOUL.md mirror drift |
| 4 | Wiki ↔ KG link audit |
| 5 | KG pgvector embedding 覆蓋率 |
| 7 | Agent evolution health |
| 10 | Memory Wiki metrics alive |
| 11 | SOUL evolution alive |
| 21 | alias_rls_audit |
| 22 | domain_score_freshness |
| 53 | tender_subscription_watchdog |
| 55 | tender_enrichment_freshness |
| 59 | diary density audit |
| 61 | facade adoption audit |

### 4.2 失敗動作

連續 2 週同 step RED → 推 LINE 提示 owner 介入

---

## 5. Tier 3 — Monthly (全 61 step)

由 owner 主動跑（不自動），月度架構覆盤時：

```bash
bash scripts/checks/run_fitness.sh         # warning mode
bash scripts/checks/run_fitness.sh --strict # 嚴格模式
```

---

## 6. 為何 Tier 1 必須 daily auto

L51 揭發的 silent failure 模式：

| 反模式 | 時間窗口 | 後果 |
|---|---|---|
| docker cp 不持久 → image 內檔舊 | < 24h | 36h silent disabled |
| env 未注入 container | < 24h | 40h silent disabled |
| Pipeline silent dormant | 3 天 | 報告完全沒寫 |

→ **Tier 1 必須 daily auto** 才能在 < 24h 內捕捉。

monthly 跑 = 「30 天 silent 才能發現」太晚。

---

## 7. 落地時間表

| 階段 | 任務 | 工作量 |
|---|---|---|
| v6.12 W1 | 寫 `run_fitness_daily.sh` + `run_fitness_weekly.sh` | ~2h |
| v6.12 W1 | 註冊 fitness_daily / fitness_weekly cron | ~1h |
| v6.12 W1 | 寫 alarm 邏輯（RED → LINE）| ~1h |
| v6.12 W2 | 跑 7 天觀察 | — |
| v6.12 W3 | 根據觀察調整 Tier 分配 | ~1h |

**總投入**：~5h（一個 sprint）

---

## 8. 連帶：Pipeline silent dormant 配套修法

v6.12 治理進化 #1 必含：

```
✅ Tier 1 daily auto fitness
✅ Pipeline silent dormant 偵測 (5/28-5/30 揭發)
✅ Pipeline 連續 3 天 RED → 推 LINE (v6.12 #2)
✅ Tier 2 連續 2 週 RED → 推 LINE
```

→ silent → alerted < 24h

---

## 9. 對 Owner 的 SOP

### 9.1 每天（被動）

LINE 收到 fitness Tier 1 RED → 立即修

### 9.2 每週日（半被動）

LINE 收到 Tier 2 連續 2 週 RED → 排 sprint 修

### 9.3 每月（主動）

跑 `bash scripts/checks/run_fitness.sh` 整體覆盤

### 9.4 每季（meta-retrospective）

跑「governance fitness run count metric」看自己治理有沒有真活

---

## 10. Refs

- 元覆盤: `META_GOVERNANCE_RETROSPECTIVE_20260530.md` §2.4 反模式 4
- L51 incident: `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md`
- 完整 60 step: `scripts/checks/run_fitness.sh`
- Pipeline silent dormant 修法: `backend/app/core/paths.py` + `docker-compose.production.yml`
