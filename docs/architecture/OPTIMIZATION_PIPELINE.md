# 優化流水線連通圖 (Optimization Pipeline)

> **建立日期**: 2026-05-16
> **動機**: 每日散修零件累積成「dis-integrated」系統。本文檔把所有優化環節畫成一張連通圖，標明每節「上游→處理→下游」+ 真實活/斷狀態。
> **核心命題**: **建好的環節不等於連通的環節**；任何環節 dead segment 都會讓上游投資打水漂。
> **執行者**: `backend/app/services/optimization_pipeline_orchestrator.py`（每日 cron）+ `OptimizationDashboard.tsx`（一張圖看健康度）

---

## 一、10 條優化環節盤點（每節 上游 → 處理 → 下游）

### 環節 1: Pattern → Crystal 自學閉環
```
agent_trace        →  pattern_extractor  →  patterns/*.md
patterns           →  crystallizer       →  proposals/*.md
proposals          →  crystal_applier    →  crystals/*.md + intent_rules.yaml
intent_rules.yaml  →  agent_router       →  Agent fast-path 路由
```
**狀態**: 🟡 YELLOW
- 上游：patterns 9 個 ✅ / proposals 3 個 ✅
- **斷點**: proposals → crystals 卡 25 天（owner gate）
- **本 session 修法**: `CRYSTAL_AUTO_APPLY_MODE=live` (.env 已改)
- **驗證**: 重啟後 7 天看 crystals/*.md 是否從 0 → N
- **斷則影響**: 9 個月學習無效，agent 不會根據成功經驗加速

### 環節 2: Domain Score → Evolution Trigger
```
self_evaluator     →  Redis agent:domain_scores:{domain}
domain_scores      →  evolution_scheduler  →  promote action
promote action     →  agent_router pattern catalog 擴充
```
**狀態**: 🟡 YELLOW
- 上游：5/8 domain 真活（doc/dispatch/pm/analysis/graph PASS）
- **斷點**: 19 trigger / 0 crystal — evolution scheduler 跑但不會自動結晶
- **本 session 修法**: 環節 1 修好後，evolution → crystal_applier 應該自動連通
- **斷則影響**: 自我進化只「promote pattern」不「結晶 rule」，能力增長慢

### 環節 3: Shadow Baseline → Observability
```
agent.query       →  shadow_logger  →  query_trace SQLite
query_trace       →  shadow_baseline_metrics  →  /metrics Prometheus gauge
/metrics          →  Grafana dashboard  →  owner 視覺化
metrics threshold →  Alertmanager rule  →  ??? push channel
```
**狀態**: 🔴 RED（出口斷）
- 上游：log + DB + metrics 全活 ✅
- p95=65s 警訊已暴露
- **斷點**: alert rule 觸發但**沒人/沒 channel 接收** — owner 從沒看過 Grafana
- **修法**: alert → LINE/Telegram push + 每日 morning report 含 p95
- **斷則影響**: 觀測再多也是「dashboard 孤兒」，owner 不知系統真實狀態

### 環節 4: Memory Diary → Autobiography → SOUL 演化
```
session 結束       →  diary writer  →  wiki/memory/diary/YYYY-MM-DD.md
diary 連續 N 天    →  autobiography_writer  →  wiki/memory/autobiography/*.md
autobiography 觀察 →  belief_check  →  proposals (SOUL section)
SOUL proposal     →  owner approve →  wiki/SOUL.md 更新
```
**狀態**: 🔴 RED（中段斷）
- diary 28 連續天 ✅ / SOUL proposal 1 個（pending 6 天）
- **斷點**: **autobiography 0 檔** — 應每週生成卻沒任何輸出（silent fail 不知多久）
- **修法**: 找出 autobiography scheduler 為何不跑 / 是否 import error / cron 漏設
- **斷則影響**: 「自我演化」少一層證據累積，SOUL 修正提案信心不足

### 環節 5: 業務流 → KG mention → Agent context
```
公文/派工 寫入     →  entity_extractor  →  mentions 累積
canonical_entity  →  search_entities tool  →  agent context
canonical_entity  →  search_across_graphs  →  跨域 RAG（本 session 修）
```
**狀態**: 🟡 YELLOW
- search_entities 7d 43.3% ✅ / find_correspondence 9.1% ✅
- **斷點**: search_across_graphs 7d **0%**（本 session router rule 已修）
- **斷點**: code domain 17,000+ entity 0 mention（by-design — 業務文件不會提 py_function）
- **修法**: 本 session 改善 1 router rule
- **驗證**: 重啟後 7 天看 search_across_graphs uses 是否從 0 → N

### 環節 6: Fitness Steps → CI/Local → Owner Decision
```
scripts/checks/*.py (22 steps)  →  run_fitness.sh  →  stdout report
report  →  ??? owner 知道  →  decision
```
**狀態**: 🔴 RED（出口完全斷）
- 22 step 存在 ✅
- **斷點**: 沒人在每日/每月固定跑 + 跑了 stdout 也沒人看
- **修法**: cron 每日 03:00 跑 → LINE/Telegram push 紅燈 step → owner /digest 命令查詳情
- **斷則影響**: 防護腳本變裝飾品（本 session ADR-0028 3 守護的元問題）

### 環節 7: Capability Usage Audit → Dead Decision
```
shadow_trace + DB + filesystem  →  capability_usage_audit.py  →  dead list
dead list  →  ??? owner A/B/C decision  →  rescue / deprecate / activate
```
**狀態**: 🔴 RED（剛建未接通）
- 本 session 剛寫 ✅
- **斷點**: 未接 cron，未推 owner，未有 decision tracker
- **修法**: 接 cron + push + dashboard tab
- **斷則影響**: 12 項 dead capability 每月再增

### 環節 8: GitNexus → Bridge → Agent Tool
```
GitNexus serve  →  bridge MCP client  →  5 method
bridge method   →  agent tool gitnexus_query  →  agent toolkit
agent_router rule  →  trigger gitnexus_query  →  影響面分析
```
**狀態**: 🟡 YELLOW（skeleton ready）
- 本 session 已部署 GitNexus + bridge skeleton ✅
- **斷點**: agent tool 未註冊到 registry，router 無 trigger rule
- **修法**: 下輪 Phase 2a — register tool + router rule
- **斷則影響**: ADR-0035 投資未兌現

### 環節 9: Commit → Pre-commit Guard → 阻擋違規
```
git commit  →  .git/hooks/pre-commit  →  3 守護腳本
守護腳本  →  exit 1 if 違規  →  阻擋 commit
```
**狀態**: 🟢 GREEN（本 session C1 已修）
- 本 session 加 3 守護到 pre-commit ✅
- **驗證**: 下次 commit 違規時應該阻擋（待實證）

### 環節 10: Commit → 7d Follow-up
```
commit 真活宣告  →  ??? 7d 排程 verify  →  /capability_usage_audit
audit 結果       →  push owner if 該 capability 7d 仍 0 使用
```
**狀態**: 🔴 RED（完全未實作）
- 「真活宣告」流程缺最後一哩驗證
- **修法**: 建 `commit_post_check_scheduler` 7 天後跑 capability audit
- **斷則影響**: 本 session 改善 1+2+3 沒人驗證真的有救活

---

## 二、整體健康度評分（10 環節）

| # | 環節 | 狀態 | 斷在哪 |
|---|---|---|---|
| 1 | Pattern → Crystal | 🟡 | owner gate（本 session live 已開）|
| 2 | Domain Score → Evolution | 🟡 | 環節 1 斷則 2 斷 |
| 3 | Shadow → Observability | 🔴 | **alert push channel 缺** |
| 4 | Diary → Autobiography | 🔴 | **autobiography 0 檔 silent fail** |
| 5 | 業務 → KG → Agent | 🟡 | cross-graph 0%（本 session 改善 1 已修）|
| 6 | Fitness → Owner | 🔴 | **cron + push 缺** |
| 7 | Capability Audit | 🔴 | **cron + push + decision tracker 缺** |
| 8 | GitNexus Bridge | 🟡 | tool 未註冊 |
| 9 | Pre-commit Guard | 🟢 | 本 session C1 修 |
| 10 | 7d Follow-up | 🔴 | **完全未實作** |

**統計**: 🟢 1 / 🟡 4 / 🔴 5（**50% 環節斷**）

---

## 三、根因 — 為什麼這麼多斷點？

### 根因 1: **散修文化** — 沒人負責「pipeline 完整性」
每次 /loop 都修個別零件，沒人問「修了這個的下游接好沒？」
→ 結果：環節都能跑，但跨節零連結。

### 根因 2: **缺中央協調器**
沒有一個 daemon / cron 「每日把所有環節跑一遍 + 報告」。
→ 各自跑各自的，沒人合成 daily digest。

### 根因 3: **缺視覺化儀表板**
Grafana 5 dashboards 沒人開；Capability Audit 跑了沒人看。
→ 沒有「一張圖 = 今天系統健康度」的 single source of truth。

### 根因 4: **owner push 路徑斷**
所有「結果」都停在 stdout / file / DB，沒有主動 push 給 owner。
→ owner 等於沒被通知，等於沒做。

---

## 四、解法：建中央 Pipeline Orchestrator

### Step 1: `optimization_pipeline_orchestrator.py`（每日 cron 03:00）
順序執行：
1. Fitness 22 steps（保留紅燈摘要）
2. Capability Usage Audit（dead list）
3. Memory Loop Health（diary / pattern / crystal / autobiography 計數）
4. Shadow Baseline 24h p95 / success_ratio
5. ADR Orphan 偵測
6. Pre-commit hook 真活 probe（過去 24h 阻擋率）
7. 各 cron 任務真活 probe（last_run_ts）

**產出**: JSON daily report + Markdown summary。

### Step 2: 推送通道
- LINE push 紅燈摘要（每日 08:00 一條訊息）
- Telegram backup（LINE 失敗時）
- Email weekly digest（週一 09:00）

### Step 3: 視覺化 Dashboard
`/kunge/ops` 加 tab「Pipeline Health」：
- 10 環節即時狀態（綠/黃/紅）
- 點任一節 → drill-down log
- 「下一步建議」自動列出待 owner 決策的事項

### Step 4: 7d Follow-up Auto-Verify
每筆 commit hash + 「真活宣告」標記寫入 `wiki/memory/commitments.json`：
- 排程 7 天後自動跑 capability_usage_audit 對該 capability
- 0 usage → 自動降級為「半接通」標 + push owner

---

## 五、ROI 對比

| 路徑 | 本 session 估算 effort | 解決幾條斷點 |
|---|---|---|
| 繼續散修個別環節 | 每環節 ~30 min - 2h | 1 條/輪 |
| **建中央 Orchestrator + Push** | **4-6h** | **6 條同時**（環節 3/4/6/7/10 + 部分 8） |

**結論**: 寫一次 orchestrator 把 6 條斷點同時連通，ROI 遠勝個別散修。

---

## 六、實施計畫

### Phase A（本 session 立刻可做，2-3h）
- [x] 本文件草案（OPTIMIZATION_PIPELINE.md）
- [ ] `optimization_pipeline_orchestrator.py` skeleton（含 fitness + capability + memory 三模組）
- [ ] orchestrator unit test
- [ ] cron schedule 加 03:00 跑 orchestrator

### Phase B（下輪 1-2 sessions）
- [ ] LINE push 通道接通（用既有 line_bot_service）
- [ ] `/kunge/ops/pipeline-health` 前端 tab
- [ ] 7d follow-up scheduler + commitments.json

### Phase C（後續演進）
- [ ] 環節 8 GitNexus bridge 真正接 agent tool（ADR-0035 Phase 2a）
- [ ] 環節 4 autobiography silent fail 根因排查
- [ ] 環節 1 crystal auto-apply 真活驗證（7d 後跑 capability audit）

---

## 七、本 session 既有工作如何接入

| 本 session 產出 | 對應環節 | 接入方式 |
|---|---|---|
| `capability_usage_audit.py` | 環節 7 | Phase A: orchestrator 第 2 步呼叫 |
| C1 pre-commit 3 守護 | 環節 9 | Phase A: orchestrator 第 6 步 probe |
| 改善 1 cross-graph router | 環節 5 | Phase A: 7d 後 capability audit 驗證 |
| 改善 2 CRYSTAL_AUTO_APPLY=live | 環節 1 | Phase A: 7d 後 memory loop check 驗證 |
| 改善 3 條件式 KG 注入 | 環節 3 | Phase A: 7d 後 shadow p95 重測 |
| ADR-0035 GitNexus bridge | 環節 8 | Phase C: agent tool 註冊 |

每個本 session 修法都有「驗證的環節」— 不再是 commit 後就忘記。

---

> **核心訊息**: **整合勝過散修**。建好的環節必須有「上游餵入 + 下游推出」才不是浪費。
> 從今天起，每個新功能上線都該畫進這張連通圖，標明上下游，否則自動視為「孤島投資」候選。
