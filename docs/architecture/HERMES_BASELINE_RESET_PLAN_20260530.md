# Hermes GO/NO-GO Baseline 重訂規劃 — Sprint 3.P3.15

> **觸發**：Sprint 3.P3.15 pending（自 5/12 ADR-0030 提案以來 18 天未動）
> **建立**：2026-05-30
> **設計理念**：v6.12 metric 化後，GO 門檻可改為「自動評估 + 自動推 LINE」forcing function
> **時程**：30 天累積 + 評估 + GO/NO-GO 決策

---

## 1. 現況 vs ADR-0030 門檻

### ADR-0030 (2026-04-22) 設定門檻

| 條件 | 門檻 | 現況 (5/30) | 達標 |
|---|---|---|---|
| Shadow baseline 筆數 | ≥ 30 | 2 | ❌ 7% |
| Owner 連續 7 天用 Hermes Web UI | 7 天 | 未追蹤 | ❌ 未知 |
| Soul fidelity 跨 provider | ≥ 70% | 未跑 | ❌ 未知 |
| Error rate | < 5% | 0% (2/2) | ✅ 100% |
| P95 latency | < 8s | 38s (gemma-local) | ❌ 475% 超 |

**綜合**：1/5 達標，**仍 NO-GO**。

---

## 2. 真因分析

### 為何 baseline 累積慢

`synthetic_baseline_inject` cron 設定 09:00/14:00/20:00 每次 10 筆 = 30/日。
24h 應 30 筆，但實際 2。

可能真因：
1. **cron 未執行**：scheduler tracker 顯示 0 success count → cron silent dormant
2. **shadow_logger 寫入 fail**：寫入路徑或 jsonl 結構錯
3. **Metric populate 計算 24h window 滑動 bug**

驗證方法：
```bash
# 跑 scheduler_job_age metric 看 cron 是否真活
curl -s http://localhost:8001/metrics | grep "synthetic_baseline_inject"

# 直接查 shadow_baseline jsonl
ls -lh wiki/memory/shadow_baseline_history.jsonl
tail -3 wiki/memory/shadow_baseline_history.jsonl
```

### 為何 P95 38s

gemma-local Ollama 推理（CPU/GPU 切換 cold start）。
解法選擇：
- A. 改 provider 為 groq（網路 LLM）p95 < 3s
- B. Ollama warmup keep-alive
- C. 降低 max_tokens 加速

---

## 3. 新 Baseline 重訂方案

### 方案 A. 維持 ADR-0030 門檻 + 修真因（推薦）

**理由**：原門檻已是降低過的（≥30 from ≥50）。重點是修「為何累積 2 筆」根因。

**執行 30 天**：

| Week | 任務 |
|---|---|
| W1 (5/31-6/6) | 修 synthetic_baseline cron 真因（驗 scheduler tracker / jsonl 寫入）|
| W2 (6/7-6/13) | 修 P95 38s 真因（Ollama keep-alive 或切 groq）|
| W3 (6/14-6/20) | Owner 試用 Hermes Web UI 7 天連續 |
| W4 (6/21-6/27) | 跑 soul-fidelity-eval.py 4 provider 評估 |
| 6/28 | GO/NO-GO 決策（5/5 門檻達標 → GO；< 4/5 → 修+延 1 month）|

### 方案 B. 降低門檻

| 條件 | ADR-0030 | 方案 B |
|---|---|---|
| baseline | ≥30 | **≥15** |
| dogfooding | 7 天 | **3 天** |
| soul fidelity | ≥70% | **≥60%** |
| p95 | <8s | **<15s** |

**反對**：降門檻 = 標準稀釋。對齊 L31 ROI 原則「entities 少但 quality 高」 → 不應降。

### 方案 C. 廢棄 Hermes 路線

若 30 天後仍卡 → 認賠 + 寫 lesson。
對齊 L53 facade B 方案前例。

---

## 4. 推薦選擇 — 方案 A + 自動化 audit

### 新增 fitness step 68: hermes_baseline_gate_audit.py

每日 06:30 daily_self_retrospective 跑時，audit 5 GO 條件即時狀態：

```python
def main():
    # 1. baseline rows
    rows = metric("shadow_baseline_rows_total")
    # 2. owner dogfooding (從 user_sessions 表查 Hermes Web UI login 7 天連續)
    dogfood_days = query_owner_hermes_web_consecutive_days()
    # 3. soul fidelity (從 fidelity_log.jsonl)
    fidelity = read_fidelity_24h_avg()
    # 4. error rate
    success = metric("shadow_baseline_success_ratio")
    # 5. p95
    p95_ms = metric("shadow_baseline_latency_p95_ms")
    
    # GO/NO-GO 自動評估
    conditions = {
        "baseline ≥30": rows >= 30,
        "dogfooding ≥7d": dogfood_days >= 7,
        "fidelity ≥70%": fidelity >= 0.70,
        "error < 5%": (1 - success) < 0.05,
        "p95 < 8s": p95_ms < 8000,
    }
    met = sum(conditions.values())
    
    if met == 5:
        print("✅ GO — 5/5 達標，可進入 Phase 1 dogfooding 擴展")
    elif met >= 3:
        print(f"🟡 NEAR-GO — {met}/5，缺 {5-met} 條件")
    else:
        print(f"🔴 NO-GO — {met}/5")
        return 1 if "--strict" in sys.argv else 0
```

### 接 daily 06:30 cron

每日 06:30 自動 audit + LINE 推 owner 看 5 條件即時達標度。
連 7 天 GO → 自動執行 Phase 1 切換。

---

## 5. 30 天 重評時程

### Week 0（本批 - 5/30）

- ✅ 寫此規劃文件
- ✅ 寫 fitness step 68 hermes_baseline_gate_audit（不擅自跑修法）

### Week 1（6/1-6/7）

- 修 synthetic_baseline cron 真因
- 期望 baseline 從 2 → 30+

### Week 2-3（6/8-6/20）

- Owner 連續 7 天用 Hermes Web UI
- 修 p95 38s（切 groq 或 Ollama keep-alive）

### Week 4（6/21-6/27）

- soul fidelity 評估
- 累積 4 週 baseline 看穩定性

### Week 5 (6/28)

- 自動 audit + GO/NO-GO 決策
- 若 GO → Phase 1 dogfooding（內部 Web UI 3 人 + LINE 白名單 3-5）
- 若 NO-GO → 寫 L56 lesson + 決定方案 B 或 C

---

## 6. 元洞察 — 自動化 GO/NO-GO

對齊 v6.12 第 2 句立法「觀測不是奢侈，自治理就是」：
- ADR 設定門檻 = 假設
- audit 自動跑 = 裁判
- 5/5 達標自動 GO = 不靠 owner 主動評估

**Hermes GO/NO-GO 從 manual review → 自動化裁判 + LINE forcing**。

對齊 ADR=假設 / audit=裁判 / lesson=傳承 SOP。

---

## 7. 驗收標準

### Phase 0（本批，2026-05-30）

- ✅ 規劃文件交付
- ✅ fitness step 68 落地

### Phase 1（2026-06-28 重評）

- 5/5 達標 → GO
- 3-4/5 → NEAR-GO 延 1 month
- < 3/5 → NO-GO 考慮方案 C

### Phase 2（GO 後 60 天）

- Phase 1 dogfooding 用戶滿意度
- 業務 metric（agent_query_success / latency）

---

> **元洞察**：Hermes GO/NO-GO 之前卡 18 天因為「owner 沒空主動評估」。
> 改 audit 自動跑 + LINE forcing → owner 每日 06:30 看到 5 條件達標度，不需主動決策。
> 對應 v6.12 第 2 句立法「自治理就是」。
