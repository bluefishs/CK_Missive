# CK_Missive 觀測棧配置

> **目的**：集中 CK_Missive 的 Prometheus / Grafana / Loki 觀測資源，
> 供 `CK_DigitalTunnel` 的 PLG stack 使用。

## 檔案清單

| 檔案 | 用途 |
|---|---|
| `provisioning-datasources.yml` | Grafana 自動註冊 Prometheus + Loki 資料源 |
| `promtail-pm2.yml` | Promtail scrape config — 抓 PM2 產生的 logs |
| `dashboards/ck-missive-overview.json` | 系統總覽 |
| `dashboards/ck-missive-http.json` | HTTP 流量與錯誤率 |
| `dashboards/ck-missive-db-pool.json` | DB pool 與查詢效能 |
| `dashboards/ck-missive-inference.json` | LLM inference 與 shadow baseline |
| `../prometheus/alerts.yml` | Alert rules（error budget、silent failure、capacity、business）|

---

## 部署步驟（CK_DigitalTunnel 端）

### 1. Datasources

```bash
# CK_DigitalTunnel grafana 容器中：
cp CK_Missive/configs/grafana/provisioning-datasources.yml \
   /etc/grafana/provisioning/datasources/ck-missive.yml
```

### 2. Dashboards

```bash
# Grafana 透過 dashboards provisioning 自動載入
cp CK_Missive/configs/grafana/dashboards/*.json \
   /var/lib/grafana/dashboards/ck-missive/
```

或在 Grafana UI 手動 Import → Upload JSON。

### 3. Promtail

```bash
# 合併 scrape_configs 到主 Promtail 設定
# 或用 file_sd_configs 指向此檔
docker compose -f CK_DigitalTunnel/docker-compose.yml restart promtail
```

### 4. Prometheus alerts

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/alerts/ck-missive.yml

# 將 CK_Missive/configs/prometheus/alerts.yml 複製或 mount 到該路徑
```

### 5. 驗收

```bash
# Loki 收到 CK_Missive log
curl -G -s "http://localhost:3100/loki/api/v1/label/job/values" | jq
# 預期含："ck-missive-backend", "ck-missive-watchdog"

# Prometheus scrape CK_Missive /metrics
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="ck-missive")'

# Alert rules 載入成功
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | .name'
# 預期：error_budget / silent_failure / capacity / business
```

---

## CK_Missive 本機需啟用

### /metrics 端點

已於 `backend/app/main.py` 載入 `PrometheusMiddleware`，暴露 `/metrics` port 8001。

Prometheus scrape config（在 CK_DigitalTunnel 端）：

```yaml
scrape_configs:
  - job_name: 'ck-missive'
    scrape_interval: 15s
    static_configs:
      - targets: ['host.docker.internal:8001']
        labels:
          service: ck-missive
```

### structlog JSON log

`backend/app/core/structured_logging.py` 已將 stdlib logging 橋接至 structlog JSON 格式，
寫入 `backend/logs/backend-error.log`（PM2 管理）。

---

## Dashboard 快速參考

- **HTTP**：`{uid: ck-missive-http}` — request rate / error rate / latency p95 / active
- **DB Pool**：`{uid: ck-missive-db-pool}` — pool active/idle/size / overflow / query p95 / slow queries
- **Inference**：`{uid: ck-missive-inference}` — completion rate / fallback / rate limit / shadow baseline

---

## 相關 ADR

- ADR-0019 structlog 統一日誌
- ADR-0028 錯誤合約化 + silent failure policy
- ADR-0030 Hermes GO/NO-GO（shadow baseline 門檻）
