---
title: integration health 月報
type: topic
created: 2026-05-25
sources: [prometheus v7 gauges]
tags: [架構, integration, v7, fitness, monthly, auto-compiled]
confidence: high
---

# integration health 月報

**統計來源**: prometheus v7 gauges (M1, 5/04 v3.0 覆盤)
**編譯時間**: 2026-05-25 05:00

## v3.0 8 接觸面當下健康度

| 接觸面 | 當前 | 目標 | 狀態 |
|--------|-----:|-----:|------|
| ❼ 跨通道 pattern 多樣性 | 0 | ≥ 4 | ✗ WARN |
| ❺ Diary↔KG entity tag % | 13.8% | ≥ 50% | ✗ WARN |
| ❹ Critique↔KG 引用 % | 0.0% | ≥ 80% | ✗ WARN |
| ❽ SOUL drift lines | 60 | ≤ 5 | ✗ WARN |

## 對應 v3.0 review 洞察

- 洞察 11：整合 commit ≠ 活體運轉，需 fitness step 14
- 洞察 14：「成熟度 %」已死，v7.0 用以上 4 指標取代
- 洞察 15：silent skip + 體感層 = 死亡，需 LINE notify watchdog

## 月度 SOP

1. owner 月度跑 `bash scripts/checks/run_fitness.sh`（16 step）
2. 看 `python scripts/checks/v7_metrics_report.py` 完整報表
3. Grafana `CK_Missive v7.0 Integration Quality (M1)` dashboard 即時
4. 連 7/14 天 warn 觸發 alert → owner 處理
