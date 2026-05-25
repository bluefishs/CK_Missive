---
title: observability 端點目錄
type: topic
created: 2026-05-25
sources: [configs/grafana, configs/prometheus]
tags: [架構, observability, monitoring, auto-compiled]
confidence: high
---

# observability 端點目錄

**統計來源**: configs/grafana/dashboards/ + configs/prometheus/alerts.yml
**編譯時間**: 2026-05-25 05:00

## Grafana Dashboards

| 檔案 | 標題 | Panel 數 | 描述 |
|------|------|---------:|------|
| `ck-missive-db-pool.json` | ck-missive-db-pool | 0 |  |
| `ck-missive-http.json` | ck-missive-http | 0 |  |
| `ck-missive-inference.json` | ck-missive-inference | 0 |  |
| `ck-missive-overview.json` | ck-missive-overview | 0 |  |
| `ck-missive-v7-integration.json` | CK_Missive v7.0 Integration Quality (M1) | 6 | v7.0 Integration Quality (M1 — 取代「成熟度 %」). 5/04 v3.0 覆盤洞察 14。 |

## Prometheus Alert Groups

| Group | Alert 數 |
|-------|---------:|
| `error_budget` | 3 |
| `silent_failure` | 6 |
| `capacity` | 3 |
| `business` | 3 |
| `v7_integration_quality` | 5 |
| `memory_wiki_freshness` | 4 |
| **總計** | **24** |
