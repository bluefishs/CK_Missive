# Shadow Baseline 三重真因揭發 — 2026-05-30

> **觸發**：Sprint 3.P3.15 W1 「修 synthetic_baseline cron 真因」開始執行
> **揭發深度**：3 層真因，第 1 層本批已修，2-3 層待深入
> **影響**：Hermes GO/NO-GO 1/5 → 預估修完後 3-4/5

---

## 真因 #1：populate Gauge 重複註冊（✅ 本批已修）

### 症狀

```
ValueError: Duplicated timeseries in CollectorRegistry:
  {'shadow_baseline_rows_total'}
```

每次 `/metrics` scrape 都 fail，累積 9+ errors。

### 真因

`backend/app/core/shadow_baseline_metrics.py:98` 每次 populate 都 `Gauge(...)` 新建，第二次起拋 ValueError。

### 修法

新增 `_get_or_create_gauge()` helper，try except ValueError 後從 registry 撈既有 collector 重用。

對齊 scheduler.py 同 pattern (v6.12 #2 落地時用過)。

### 驗證

- ✅ `metrics_populate_errors_total{source="shadow_baseline"}` 不再增加
- ✅ rebuild + restart 後 `/metrics` shadow_baseline 不再 ValueError

---

## 真因 #2：cron `node` missing in container（⏳ 待修）

### 症狀

```
shadow_baseline subprocess error: [Errno 2] No such file or directory: 'node'
```

scheduler `shadow_baseline_export_job` (cron 20:00) 嘗試 `node shadow-baseline-report.cjs` 但 backend container 內無 node。

### 真因

- `scripts/checks/shadow-baseline-report.cjs` 是 Node.js script
- backend Dockerfile 只裝 python，沒裝 node
- 5/26 OA-3 PM2 廢除後從 host (有 node) → container (無 node)

### 修法選項

| 選項 | 工時 | 風險 |
|---|---|---|
| A. backend Dockerfile 加 `RUN apt install nodejs` | 5min | image 增 ~50MB |
| B. 將 .cjs 改寫成 python | 30min | 額外維護成本 |
| C. 移除 shadow_baseline_export cron（讓 prometheus 自身 scrape 即可）| 1min | 失去定時匯出 JSON 能力 |

推薦 **C**（cron 移除）— prometheus + grafana 已能自動 scrape，jsonl 匯出可能重複。

---

## 真因 #3：shadow_logger 寫入鏈 5/21 後失效（⏳ 待深入）

### 症狀

```sql
SELECT MAX(ts) FROM query_trace;
→ 2026-05-21T01:03:24+00:00 (9 天前)
SELECT COUNT(*) FROM query_trace WHERE ts > datetime('now', '-24 hours');
→ 0
```

shadow_trace.db 1095 rows 歷史但 24h 全空。

### 已驗證

- ✅ `SHADOW_ENABLED=1` 注入 container
- ✅ `is_enabled() = True`
- ✅ synthetic-baseline-inject.py 跑成功（3-5 query success）
- ❌ 但 shadow_trace.db 沒新增 row

### 待深入

可能真因：

1. **synthetic-baseline-inject.py 走 `/api/ai/agent/query` endpoint 沒呼叫 shadow_logger.log_trace**
2. **SHADOW_SAMPLE_RATIO=0.3 太低**（30% sample），13 query × 0.3 ≈ 4 寫入，但實際 0
3. **shadow_logger.log_trace 內 silent except 吞錯**（line 167 `logger.warning + pass`）
4. **路徑漂移**：`BACKEND_DIR / "logs" / "shadow_trace.db"` 在 container 內計算錯誤

### 下一輪驗證命令

```bash
# 1. 確認 endpoint 鏈呼叫
grep -rn "log_trace\|shadow_helpers" backend/app/api/endpoints/ai/

# 2. 直接呼叫 shadow_logger 強制寫入測試
docker exec ck_missive_backend python -c "
from app.services.ai.agent.shadow_logger import log_trace
log_trace(channel='test', question='test', answer='ok',
          success=1, latency_ms=100, provider='test')
import sqlite3
conn = sqlite3.connect('/app/logs/shadow_trace.db')
print(conn.execute('SELECT COUNT(*) FROM query_trace').fetchone())
"

# 3. 把 SAMPLE_RATIO 改 1.0 強制全寫
echo "SHADOW_SAMPLE_RATIO=1.0" >> .env
docker compose restart backend
```

---

## 整體影響

### Hermes GO/NO-GO 改善預估

| 條件 | 修前 | 修真因 #1+#3 後 |
|---|---|---|
| 1. baseline ≥ 30 | 2 ❌ | 30+ ✅ |
| 2. dogfooding ≥ 7d | 0 ❌ | 0 ❌（owner 手動）|
| 3. soul fidelity ≥ 70% | 未跑 ❌ | 未跑 ❌（待 owner 跑 eval）|
| 4. error rate < 5% | 0% ✅ | 0% ✅ |
| 5. p95 < 8s | 38s ❌ | 38s ❌（待修 Ollama cold start）|

**1/5 → 2/5 預估**（修 #1+#3 解 baseline 累積）

### 對齊 v6.12 治理元洞察

3 重真因揭發本身就是 v6.12「audit + 觀測」價值：
- 若無 `metrics_populate_errors_total` counter → 真因 #1 silent
- 若無 `scheduler_job_last_run_age_seconds` → 真因 #2 silent
- 若無 SQLite 直查命令 → 真因 #3 silent 9 天

**audit 觀測閉環 = 早期揭發 silent dormant 的唯一手段**。

---

## 後續排程

| Week | 任務 |
|---|---|
| 本批 ✅ | 修真因 #1 populate Gauge 重複 |
| W1 (6/1) | 移除 shadow_baseline_export cron (真因 #2) |
| W1 (6/2) | 深入修 shadow_logger 寫入鏈 (真因 #3) |
| W2-W4 | Owner dogfooding + 修 p95 + soul fidelity |
| 6/28 | 自動 audit + GO/NO-GO 決策 |

---

> **元洞察**：「修 synthetic cron 真因」表面是 1 個 bug，實際 3 層 silent 疊加。
> 對齊 L43 教訓「5 重 silent fallback 疊加」+ L52「修法本身製造下一個 silent dormant」。
> 本批揭發是進步，修完 1/3 是進度，2/3 留下批。
