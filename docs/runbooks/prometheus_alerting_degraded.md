# Prometheus / Alertmanager 降級指南 Runbook

> **觸發條件**：Prometheus / Alertmanager / Grafana 任一組件失效，alerting 鏈路斷開
> **預估恢復時間**：5–60 分鐘
> **執行權限**：擁有 server SSH + Grafana admin + LINE notify token
> **風險等級**：MEDIUM（**並非業務中斷**，但**所有 silent failure 偵測會失明**）
> **關聯**：ADR-0028 / `configs/prometheus/alerts.yml` / `configs/grafana/`

---

## 0. 為何此 runbook 重要

ADR-0028 + v6.8 觀測棧建立後，所有 silent failure 都靠 Prometheus alert 偵測：
- `MetricsPopulateErrors`（R3 加）— shadow_baseline silent skip
- `DiaryAppendFailures`（R7 加）— diary fire-and-forget silent
- `AdminPushConsecutiveFailures` — LINE/Telegram 通道死
- `MemoryDiaryStale` — ADR-0022 自進化系統 dormant
- `DbPoolTimeoutSpike` — ADR-0021 race condition 回歸

**alerting 失效 = 系統還在跑但 silent failure 完全看不到**，是「v3.0 洞察 11 失明模式」的最壞延伸。

---

## 1. 何時觸發

| 場景 | 是否觸發本 runbook |
|---|---|
| Prometheus scrape `/metrics` 失敗 < 5min | ❌ 等候 |
| Prometheus scrape 持續失敗 ≥ 15min | ✅ 啟動 §2 |
| Alertmanager UI 不可達 | ✅ 啟動 §3 |
| 某個 alert 應該 fire 但沒推到 LINE | ✅ 啟動 §4 |
| Grafana dashboard 一直 loading | ❌ 不是 alerting 問題（看 §5）|
| 整個 CK_DigitalTunnel 容器全死 | ✅ 啟動 §6 緊急降級 |

---

## 2. Plan A — Prometheus scrape 失敗

### 2.1 確認源頭

```bash
# 從 CK_DigitalTunnel 端
docker exec -it prometheus_container curl -s http://host.docker.internal:8001/metrics | head -20
# 期望：看到 # HELP / # TYPE 開頭的 metric

# 從 ck-backend 端
curl -s http://localhost:8001/metrics | head -20
```

### 2.2 backend 端 OK 但 prometheus 抓不到 → 容器網路

```bash
# CK_DigitalTunnel 端
docker logs prometheus 2>&1 | grep -E "scrape|target down"

# 看 targets
curl -s http://<digitaltunnel_host>:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health=="down")'
```

修法：
- Windows host：`host.docker.internal:8001` 預設可通
- Linux host：用 `--add-host=host.docker.internal:host-gateway` 或固定 host IP

### 2.3 backend 端 `/metrics` 自己 5xx

```bash
curl -i http://localhost:8001/metrics
# 500 → R3 修的 metrics_populate_errors_total 應該已記錄
# 看 logger.error
pm2 logs ck-backend --lines 100 | grep "metric populate failed"
```

---

## 3. Plan B — Alertmanager UI 不可達 / alert 不送

### 3.1 確認 Alertmanager 健康

```bash
docker exec alertmanager wget -qO- http://localhost:9093/-/healthy
# 期望 200

# 看當前 alerts
curl -s http://<host>:9093/api/v1/alerts | jq '.data | length'
```

### 3.2 Alertmanager config 重載

```bash
# 改完 alerts.yml 後要 reload
curl -X POST http://<host>:9093/-/reload

# Prometheus 也要 reload rule
curl -X POST http://<host>:9090/-/reload
```

### 3.3 LINE notify webhook 失敗

```bash
# Alertmanager → LINE notify routing
# configs/alertmanager.yml 中 receivers 看 url
# 直接打測試
curl -X POST "${LINE_NOTIFY_URL}" \
  -H "Authorization: Bearer ${LINE_NOTIFY_TOKEN}" \
  -d "message=test from alertmanager runbook"
# 期望 200 + {"status":200,"message":"ok"}
```

---

## 4. Plan C — 「應該 fire 但沒收到」

最棘手場景：用戶報「明明 X 壞了，怎麼沒 alert」。

### 4.1 確認 metric 真的有值

```bash
# 直接 query Prometheus
curl -s "http://<host>:9090/api/v1/query?query=memory_diary_append_failures_total" | jq
# 期望：看到 result 有資料

# 若 0 筆 → counter 在 backend 沒被 inc，alert 永遠不會 fire
#   可能：metric_inc 自己壞了（chicken-and-egg） — 看 R7 修法
```

### 4.2 確認 alert rule 還在

```bash
curl -s http://<host>:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name=="DiaryAppendFailures")'
# 期望：rule 存在 + state="inactive" or "firing"
```

### 4.3 確認 routing 把該 alert 送到 LINE

```yaml
# configs/alertmanager.yml routing
route:
  receiver: 'line-notify'  # 預設
  routes:
    - match:
        severity: 'critical'
      receiver: 'line-notify'
      continue: true  # ⚠ 沒設這個 → 子 route match 後不會繼續觸發 default
```

---

## 5. Grafana dashboard 不 work（**非 alerting 問題**）

純儀表板問題，不影響 alerting 鏈路。

```bash
# 重啟 Grafana
docker restart grafana_container

# Dashboard 載入失敗 → 重新 provision
# CK_DigitalTunnel 端：configs/grafana/dashboards/ 改完
docker exec grafana_container grafana-cli admin reset-admin-password <new>
```

---

## 6. Plan D — 緊急降級（CK_DigitalTunnel 整個失效）

最壞情境：觀測棧整個死，無法在短期內恢復。

### 6.1 直接由 backend 推 LINE notify

ck-backend 端有 `admin_push_dispatcher.py` 會直送 LINE。即使 Prometheus 全死：

```bash
# .env 確保有 LINE 推送 fallback config
LINE_NOTIFY_TOKEN=<token>
LINE_ADMIN_USER_ID=<user_id>
ADMIN_PUSH_FALLBACK_DIRECT=true  # 跳過 alertmanager 直送
```

### 6.2 暫時手動跑 fitness

`run_fitness.sh` 在 `--strict` 模式可當「人工 alerting」：

```bash
# 每 30min cron 跑
*/30 * * * * cd /path/to/CK_Missive && bash scripts/checks/run_fitness.sh --strict 2>&1 | mail -s "Fitness Failed" admin@cksurvey.tw
```

### 6.3 Quick LINE notify 取代 alert

對最關鍵的 silent failure（diary stale / shadow baseline stalled），直接在 ck-backend cron 加：

```python
# scripts/checks/manual_silent_failure_watchdog.py
# 每 1h 跑：直接讀 metrics + 比門檻 + LINE notify
# 在 alertmanager 恢復前 stand-in
```

---

## 7. 治理層級的 invariant

| Invariant | 違反後果 | 偵測方法 |
|---|---|---|
| `/metrics` endpoint 永遠 200 | alert 全失明 | `MetricsPopulateErrors` rule |
| Counter 啟動時即註冊（F19 模式）| 首次失敗前 metric 不存在 | 各 metric 的 import-time 註冊 unit test |
| Alert rule 改完必 reload Prometheus | 改了沒生效 | `curl -X POST /-/reload` 入 deploy 流程 |
| 至少兩通道送 alert（LINE + email） | 單通道死全失明 | §6.1 fallback |

---

## 8. 事後檢討

24 小時內：
- 寫 `wiki/memory/failures/failure-prometheus-alerting-<date>.md`
- 量化「失明時長」（alerting 從失效到恢復）
- 補 LESSON 至 `docs/architecture/LESSONS_REGISTRY.md`
- 評估是否要建 §6.3 stand-in watchdog 為常設

---

## 附：相關資產

- `docs/adr/0028-error-contract-silent-failure-policy.md`
- `configs/prometheus/alerts.yml` — 7 groups × 18 alert rules
- `configs/grafana/dashboards/` — 5 dashboards
- `configs/grafana/promtail-pm2.yml` — log shipping
- `backend/app/core/admin_push_dispatcher.py` — backend 端直推
- `backend/app/core/prometheus_middleware.py` — `/metrics` endpoint（R3 後 silent fail 有 counter）

> **首要原則**：alerting 失效**不是業務中斷**但**比業務中斷更可怕** — 因為你看不到中斷正在發生。
