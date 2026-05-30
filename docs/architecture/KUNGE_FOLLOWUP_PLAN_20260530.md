# L51.7 坤哥優化 Follow-up Plan (3 大件留待 v6.12)

> **狀態**: planning — 待 owner 安排
> **背景**: L51.7 Sprint 1+2+3 已 commit 12/15 件（80%），剩 3 件工作量大留 v6.12
> **關聯**: KUNGE_AGENT_CHAIN_REVIEW_20260530.md / INCIDENT_REPORT_20260529

---

## 已完成（12/15, commit `a8c27319` `8aab4d18` + 本批）

| Sprint | 任務 | 狀態 |
|---|---|---|
| 1.P0.1 | v7_channel_diversity metric 修法 | ✅ |
| 1.P0.2 | v7_soul_drift metric snapshot fallback | ✅ |
| 1.P0.3 | SOUL sync 跨 repo | ✅ |
| 1.P0.4 | 4 proposals LINE 提示 | ✅ |
| 1.P1.5 | crystal_review_overdue_alarm cron | ✅ |
| 1.P1.6 | agent_query_starvation fitness 58 | ✅ |
| 2.P1.8 | shadow_baseline scripts mount + 修法 | ✅ |
| 2.P2.9 | LINE 訊息加 /kunge quick action | ✅ |
| 2.P2.10 | autobiography 自動 SOUL drift snapshot + sync 提示 | ✅ |
| 2.P2.11 | diary density audit fitness 59 | ✅ |
| 2.P2.12 | anti_echo critique starvation prompt | ✅ |
| 3.P3.13 | 坤哥週學習摘要 cron 週日 11:00 | ✅ |

---

## 推遲 v6.12（3/15）

### P1.7 — 12 facade importer 收口（≥3 per facade）

**現況** (5/30 實測)：
```
MemoryFacade        5  ████████
IntegrationFacade   4  ███████
CalendarFacade      3  █████
WikiFacade          2  ████
ContractFacade      1  ██
DocumentFacade      1  ██
NotificationFacade  1  ██
AgencyFacade        1  ██
VendorFacade        1  ██
AIFacade            1  ██
ERPFacade           1  ██
AuditFacade         1  ██
TenderFacade        1  ██
─────────────────────────
平均 1.7 importer/facade（目標 ≥3）
```

**工作量**：~3 天（拆 13 件 stub 重新導入 facade）
**做法**：對 9 個 1-importer facade，找原 module 還有 2+ 處從非-facade 路徑 import，
改走 facade。需 `stub_import_lint.sh` 找 hotspot。

**ROI**：抽象層真活、減少跨 context 直 import 反模式 — 但對業務功能無立即可見效益

**建議排程**：v6.12 Sprint 規劃內，與 v5.10.2 Wave 9 stub 移除合併

---

### P3.14 — `/kunge` UX 重設計

**現況**：
- 7 tabs (chat / identity / memory / evolution / nebula / dialogues / ops)
- agent_query 流量 2h=0 (24h shadow_baseline 0)
- LINE 訊息已加 quick action 連結但 owner 仍偏好 LINE

**設計問題**：
- web 入口比 LINE 多 1 步 (打開瀏覽器/找書籤)
- web 沒提供「LINE 收訊息」之外的獨特價值
- 缺「視覺化檢索」功能（如 evolution 時間軸/pattern 熱圖）

**設計方向**（草案）：
1. **chat tab**：歷史對話檢索 + 跨日期關聯
2. **memory tab**：proposal/crystal review 一鍵 approve/reject UI
3. **evolution tab**：W17-W21 時間軸 + 信念演化視覺化
4. **dialogues tab**：critique 寫入頁面（templates + entity tag picker）

**工作量**：~1-2 週（含前端設計 + backend API）
**ROI**：potentially 啟動 agent_query 流量、達 v7_channel_diversity ≥2

**建議排程**：v6.12 Sprint 2-3，與 P3.14 同期，作為 critique 啟動配套

---

### P3.15 — Hermes GO/NO-GO baseline 重訂

**現況**：
- ADR-0030 (Hermes 替代 OpenClaw GO/NO-GO) baseline 過期
- v6.8 揭示 p95=58s 警訊
- shadow_baseline 24h n=0（修法後跑 synthetic cron 應恢復）

**待重訂**：
1. p95 latency 新門檻（原 60s 已不適用）
2. tool_use_count 期望分布
3. provider mix（Groq/NVIDIA/Ollama 比例）
4. success_rate 目標
5. error_budget 容忍度

**工作量**：~1 週（含 4 週累積 + 數據分析）
**前置依賴**：synthetic_baseline_inject cron 連續 4 週累積真實數據

**建議排程**：v6.12 P3.15 — 6 月底（4 週累積後）跑數據分析 + ADR-0030 更新

---

## 量化目標（v6.12 完工後）

| 指標 | 現值（5/30）| v6.12 目標 |
|---|---|---|
| v7_channel_diversity | 0（等下次 cron） | ≥2 (LINE + Web) |
| v7_reference_density_diary_pct | 17.9% (RED) | ≥30% (P2.11+P2.12 配套) |
| v7_reference_density_critique_pct | 0% | ≥10% (P2.12 啟動) |
| v7_soul_drift_lines | 0 | 0 持續 (P2.10 auto-sync) |
| crystals applied | 0 (4 pending) | ≥2 (P1.5 alarm 推動) |
| agent_query 7d | 0 | ≥10 (P3.14 UX) |
| shadow_baseline 24h n | 0 | ≥20 (P1.8 scripts mount) |
| facade avg importer | 1.7 | ≥2.5 (P1.7) |

---

## Refs

- `KUNGE_AGENT_CHAIN_REVIEW_20260530.md` — 原覆盤 + 3 路線提案
- `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md` §10.6 — docker cp regression lesson
- Sprint 1 commit: `a8c27319`
- Sprint 2.P2.10 + incident #8: `8aab4d18`
- Sprint 2+3 batch: (本批 commit)
