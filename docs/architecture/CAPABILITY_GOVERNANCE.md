# Capability Governance — 能力治理工具規範

> **版本**：v1.0 草案（2026-05-16）
> **狀態**：proposed → 待 owner 審核
> **基準**：CK_Missive v6.9 後架構覆盤揭發 12 項 dead capability
> **適用**：所有 active capability（tool / endpoint / route / dashboard / alert / fitness / ADR / lesson / wiki）
> **執行頻率**：每月 retro + 季末大盤點
> **權威參考**：
> - `docs/architecture/MODULARIZATION_STANDARDS_v1.md`（§2 instrumentation 是 CG 前置）
> - `docs/architecture/OPTIMIZATION_PIPELINE.md`（10 條優化環節連通圖）
> - ADR-0028 錯誤合約化 / ADR-0029 ADR Lifecycle
> - `.claude/rules/adr-anti-half-wired-sop.md`

---

## 為何需要 Capability Governance

v6.9 後架構覆盤揭發**12 項 dead capability**：實作完整、文件齊全、但 7d / 30d / 6m 零觸發或零產出。例：

| Capability | 實作狀態 | 觀察狀態 | dormant 時間 |
|---|---|---|---|
| 4 個 graph tools | 完整 | 7d 0 呼叫 | 月級 |
| code domain 17,000+ entities | 已 ingest | mention_count = 0 | 月級 |
| autobiography 生成 | 已實作 6 月 | 0 檔產出 | 半年 |
| crystals (pattern → crystal) | 已實作 4 月 | 0 筆 | 月級 |
| 4 alert rules | 已 wire | 從未 fire | 月級 |
| ADR-0028 三守護 | 腳本完整 | pre-commit 沒呼叫（本 session C1 已修） | 13 天 |
| alias_rls_audit | 跑得通 | 0 risks 假乾淨 | 月級 |
| `default/fast/batch` HNSW 3 檔位 | 已定義 | 0 caller | 季級 |
| `MorningReportDeliveryService.subscribe()` | 已實作 | 0 user | 月級 |
| `digital_twin` 30+ 端點 | 已 wire | 7d <5 呼叫 | 月級 |
| `agent_nemoclaw` deprecated 端點 | 標 deprecated | 仍佔位 | 月級 |
| 3 個頂層 0-importer service stub | 仍在（本 session 已刪） | 0 引用 | 跨版本 |

**結論**：傳統 ADR-0029 lifecycle policy 只管「ADR 數量」，無法管「能力健康度」。需要 CG 這層治理。

---

## §1 三層健康度模型（Existence × Usage × Outcome）

### §1.1 三維度定義

| 維度 | 問題 | 量測方式 |
|---|---|---|
| **Existence** | 程式碼是否存在 + import path 可達？ | grep + ast import-graph |
| **Usage** | 7d/30d 內有人/系統觸發嗎？ | Prometheus counter + log scan |
| **Outcome** | 觸發後產出有效嗎？ | DB row 增量 / business metric 達標 |

### §1.2 健康度組合（8 種狀態）

| 狀態 | E | U | O | 意義 | 處置 |
|---|---|---|---|---|---|
| ✅ Healthy | 1 | 1 | 1 | 真活 | 持續觀察 |
| ⚠️ Sterile | 1 | 1 | 0 | 有人用但沒效果 | Investigate（quality bug）|
| ⚠️ Dormant | 1 | 0 | - | 寫了沒人用 | Activate or Block-deprecate |
| 🔴 Half-wired | 1 | 0 | 1 | 看似有產出但無人觸發（cron 自跑）| 評估是否真有用戶 |
| 🔴 Mythical | 0 | 1 | - | 沒程式碼但有人試呼叫 | 補實作 or 加 404 |
| 🔴 Phantom | 0 | 0 | 1 | 沒程式碼但有產出（外部寫入）| Audit data source |
| ⚪ Vacant | 0 | 0 | 0 | 不存在 | 確認預期 |
| 🟡 Latent | 1 | 0 | - 但有未來計畫 | 暫存 | 列 backlog 限期 |

### §1.3 偵測自動化

每月 retro 跑 `scripts/checks/capability_usage_audit.py`（本 session 已建，fitness step 23）：

```python
# 偽 code
for cap in CAPABILITY_REGISTRY:
    existence = check_import_path_reachable(cap)
    usage = scrape_prometheus_counter(cap.metric_name, "7d")
    outcome = query_outcome_metric(cap.outcome_metric)
    state = classify(existence, usage, outcome)
    report.append({"cap": cap.name, "state": state})
```

---

## §2 應被監控的 Capability 類別

### §2.1 Capability 分類表

| # | 類別 | 識別方式 | 健康度量測 |
|---|---|---|---|
| 1 | **Agent tool** | `services/ai/tools/tool_definitions*.py` registered | `agent_tool_calls_total{tool}` 7d > 0 |
| 2 | **API endpoint** | `api/endpoints/**/*.py` route 註冊 | `http_requests_total{path}` 7d > N（按 tier 定）|
| 3 | **Frontend route** | `router/AppRouter.tsx` Route element | 後端 page_view counter 7d > 0 |
| 4 | **Grafana dashboard panel** | `configs/grafana/dashboards/*.json` panel | 對應 metric 有 7d 資料 |
| 5 | **Prometheus alert rule** | `configs/prometheus/alerts.yml` rule | rule 30d 至少 evaluate 過（即使 0 fire）|
| 6 | **Fitness step** | `run_fitness.sh` 編號 step | 每月 retro 跑得通（exit 0/1/2 任一）|
| 7 | **ADR** | `docs/adr/*.md` accepted | L2+ 必有對應 fitness/metric；30d 至少觀察一次 |
| 8 | **Lesson** | `wiki/memory/lessons/*.md` | 至少 1 regression test；referenced by 1+ memory |
| 9 | **Wiki page** | `wiki/**/*.md` | 30d 有人讀（page_view counter）or 引用度 > 0 |
| 10 | **Cron job** | `core/scheduler.py` job 註冊 | 連續成功 ≥ 預期頻率的 80% |
| 11 | **Config flag** | `config/*.yaml` key / env var | 至少 1 caller（dead config 偵測）|
| 12 | **DB entity domain** | `canonical_entities.entity_type` | mention_count > 0 比例 > 50% |

### §2.2 每類別 detection method（必須可自動化）

| 類別 | 1 行 detection |
|---|---|
| Agent tool | `prometheus.query('rate(agent_tool_calls_total[7d]) by (tool)')` |
| API endpoint | `prometheus.query('rate(http_requests_total[7d]) by (path)')` |
| Frontend route | `grep -r "to=\"<route>\"" frontend/src/` + page_view metric |
| Dashboard panel | `jq` parse panel queries, check metric 7d count > 0 |
| Alert rule | `promtool query instant 'ALERTS{alertname=<name>}'` 30d |
| Fitness step | `bash run_fitness.sh --strict` exit code check |
| ADR | `grep -l "ADR-NNNN" backend/ tests/ scripts/` |
| Lesson | `grep -l "L<NN>" wiki/memory/` count |
| Wiki page | `wiki_kg_link_audit.py` referenced count |
| Cron job | scheduler log + `cron_health_check.py` (exists) |
| Config flag | `config_dead_reader_scan.py` (exists, v3 multi-target) |
| Entity domain | `SELECT entity_type, AVG(mention_count) FROM canonical_entities GROUP BY entity_type` |

### §2.3 Capability Registry SSOT

建議建 `scripts/checks/capability_registry.yml`（Phase 1 工作）：

```yaml
# 範本（部分）
agent_tools:
  - name: search_documents
    metric: "agent_tool_calls_total{tool='search_documents'}"
    outcome_metric: "agent_tool_success_rate{tool='search_documents'}"
    healthy_threshold: 7d > 5
    owner: "ai/agent"

api_endpoints:
  - path: "/api/ai/agent/query/stream"
    tier: 0  # 核心
    healthy_threshold: 7d > 100
  - path: "/api/ai/digital_twin/profile"
    tier: 2  # 次要
    healthy_threshold: 7d > 1

# ... 等
```

---

## §3 A/B/C 決策矩陣

每月 retro 對 dormant / sterile capability 做決策：

### §3.1 三個動作

| 動作 | 意義 | 條件 |
|---|---|---|
| **A — Activate** | 救活：補 UI / 補文件 / 補晨報曝光 | 該 capability 仍有戰略價值，只是發現路徑斷 |
| **B — Block-deprecate** | 標 deprecated，6 個月後砍 | 該 capability 戰略過期 + 替代方案存在 |
| **C — Catch-rescue** | 補半接通缺口（wiring 接通即可） | 該 capability 有戰略價值但實作斷層 |

### §3.2 決策準則

```
┌─────────────────────────────────────────────────────┐
│  capability is dormant/sterile                       │
└─────────────────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
   Still strategic?        Already superseded?
            │                     │
        ┌───┴───┐             ┌───┴───┐
       Yes      No           Yes      No
        │       │             │       │
        ▼       ▼             ▼       ▼
   Is there a   B          B         C
   broken      (already   (Block-    (Catch-
   wiring?     better     deprecate) rescue
        │      replaced)             missing
   ┌────┴────┐                       wire)
   Yes      No
   ▼        ▼
   C        A
  (fix     (find users,
  wire)    add UI/path)
```

### §3.3 範例（從 v6.9 retro 12 dead capability 套用）

| Capability | 狀態 | 決策 | 理由 |
|---|---|---|---|
| 4 graph tools 7d 0 呼叫 | Dormant | **A** | 戰略上 graph 是 KG 核心；UI 入口斷（建 `/ai/graphs` 已是 ADR-0031 落地步驟）|
| code domain 17000+ entity 0 mention | Sterile | **A**（routing rule）| 已有，路徑沒導；本 session 已加 cross-graph router rule |
| autobiography 0 檔 | Dormant | **C** | crystallizer → autobiography 鏈路斷；補 wire |
| crystals 0 筆 | Half-wired | **C** | CRYSTAL_AUTO_APPLY 預設 false，本 session 已改 live |
| 4 alert rule 0 fire | Sterile | **A** | 真正沒事故就不該 fire；改觀察 evaluate 次數而非 fire |
| ADR-0028 三守護 | Dormant | **C** | wiring 缺口，本 session C1 已修 |
| alias_rls_audit 0 risks | Sterile | **A** | detection pattern 太窄，需擴 import-graph 偵測（P1 D2）|
| HNSW 3 檔位 0 caller | Dormant | **B** | 戰略可有可無，砍掉降複雜度（P2 D7）|
| MorningReportDelivery 0 user | Dormant | **A** | UI 入口斷 |
| digital_twin 30+ 端點 7d <5 | Half-wired | **A**（整併進 /kunge）| ADR-0031 已規劃整合到 /kunge/ops |
| agent_nemoclaw deprecated | Dormant | **B** | 5/26 已歸檔，照原計畫砍 |
| 3 個 0-importer stub | Dormant | **B** | v6.9 retro S1 已列 P0（本 session 已執行刪除） |

---

## §4 每月 ROI 復盤流程

### §4.1 月度 retro 議程（建議 30 min）

```
T+0    開場：上月 capability health snapshot（自動產生）
T+5    Dormant 清單 review（按優先級）
T+15   ABC 決策：每 capability 1-2 分鐘討論
T+25   行動項分配 + 14 / 30 / 90 天追蹤
T+30   結案，更新 capability_registry.yml
```

### §4.2 自動產出報告

`scripts/checks/capability_usage_audit.py --json`（已建）+ `optimization_pipeline_orchestrator.py`（已建）合成日/月報：

```markdown
# Capability Health Audit — 2026-MM-DD

## Summary
- Total capabilities tracked: 348
- Healthy: 273 (78%)
- Sterile: 18 (5%)
- Dormant: 41 (12%)
- Half-wired: 12 (3%)
- Mythical: 0
- Phantom: 0
- Vacant: 4

## Dormant 41 items (priority sorted)
1. autobiography_generator — 6mo dormant, owner: memory, decision: ?
2. ...

## Half-wired 12 items
1. crystal_applier (cron exists, threshold too high) — decision: ?
2. ...

## Recommend actions
- 3 items recommend A (Activate)
- 5 items recommend B (Block-deprecate)
- 4 items recommend C (Catch-rescue)
```

### §4.3 ROI 量化指標

| 指標 | 目標 | 警戒 |
|---|---|---|
| Healthy capability 比例 | > 80% | < 70% |
| Dormant > 30d 數量 | < 20 | > 40 |
| Half-wired 數量 | < 5 | > 10 |
| 上月決策落實率（A/B/C 完成）| > 70% | < 50% |
| 每月「真活」新增 ratio（dormant → healthy）| > 5 | < 2 |

---

## §5 與既有政策的關係

### §5.1 ADR-0028（錯誤合約化 / Silent Failure Policy）

ADR-0028 解「程式碼層面 silent error」；CG 解「觀測層面 silent dormant」。**互補**：

- ADR-0028 確保 error 不被吞 → CG 才看得到 error counter 變化
- CG 找出 dormant → 反過來檢視該 capability 是否藏 silent error

### §5.2 ADR-0029（ADR Lifecycle Policy）

ADR-0029 只管 ADR 數量（active ≤ 20）；CG 把 ADR 視為一種 capability，加上「實際被引用 / 對應 fitness 真活」檢查。**擴展**。

### §5.3 adr-anti-half-wired-sop

該 SOP 是新 ADR 上線前的 5 步檢查；CG 是上線後的持續監控。**接力**：

- SOP 確保上線時是 Healthy
- CG 監控是否退化為 Dormant / Sterile

### §5.4 LESSONS_REGISTRY

每個 lesson 是一種 capability（防範模式）。CG 對 lesson 量測「referenced by 多少 commit / regression test」，避免 lesson 寫了沒人看。

### §5.5 OPTIMIZATION_PIPELINE

CG 偵測「靜態」dead capability；Pipeline 把 CG + 其他 9 條環節串成「每日自動流水線」，產出 daily digest 推 owner。**接力**：CG 找問題 → Pipeline 推 owner → owner ABC 決策。

---

## §6 落地路線圖

### §6.1 Phase 1（2 週）— 基礎建設

- [x] 本 session 已建 `scripts/checks/capability_usage_audit.py`（fitness step 23）
- [x] 本 session 已建 `backend/app/services/optimization_pipeline_orchestrator.py`
- [ ] 建 `scripts/checks/capability_registry.yml`，蒐錄當前 348 capability
- [ ] 跑首次審計，產出 baseline 報告
- [ ] 整合進 `run_fitness.sh` 作為 step 23

### §6.2 Phase 2（1 個月）— 首次決策輪

- [ ] 月度 retro 議程加入 30min CG section
- [ ] 對 v6.9 揭發 12 dead capability 做 ABC 決策（部分已在 retro backlog）
- [ ] 訂定下月目標：healthy ratio + 5%

### §6.3 Phase 3（1 季）— 跨 repo 推廣

- [ ] 把 capability_registry.yml schema 抽成跨 repo 範本
- [ ] CK_AaaP / lvrland / PileMgmt 各自建 registry
- [ ] CK_AaaP 統一 dashboard（meta-CG）

---

## §7 反模式（CG 自身可能犯的錯）

| 反模式 | 描述 | 防範 |
|---|---|---|
| **CG 自己變 dormant** | capability_usage_audit.py 寫了沒人跑 | 強制 wire 到 run_fitness.sh + 月度 retro 議程 |
| **registry 漂移** | 新 capability 加了沒入 registry | PR template 加 checklist：新 metric/endpoint 同步 registry |
| **healthy 標準 too lax** | 7d > 0 就算 healthy，掩蓋實際冷卻 | 按 capability tier 分級門檻（核心 > 100/7d，邊角 > 1/7d）|
| **量化崇拜** | 為追 healthy ratio 砍掉戰略 latent 能力 | A/B/C 決策加「戰略價值」維度，不只看數字 |
| **decision 不落實** | ABC 決定後沒人執行 | 追蹤上月決策落實率（§4.3）|

---

## §8 滾動更新

- v1.0（2026-05-16）：首版，從 v6.9 retro 12 dead capability 反推三層模型
- 每季回顧一次（capability 類別可能新增）
- 跨 repo 推廣後吸收 lessons 修訂

---

**關鍵理念**：寫程式碼是建設 capability；CG 是保證 capability 持續活著、被用、有產出。三者缺一就是技術債。
