# 坤哥 Memory Signal Producer-Consumer Flow Map v1.0

> **建立**：2026-04-30（v5.12 Phase D，戰略治理 SSOT）
> **目的**：盤點所有 signal/event 的 producer → storage → consumer → action 鏈路，**避免「孤兒 signal」**（只有 producer 沒有 consumer，等同 dead integration）
> **觸發**：v5.10.2 #4 silent failure + v5.11/v5.12 多輪修「半活鏈路」累積教訓
> **跨 repo FQID**：`CK_Missive#MEMORY_SIGNAL_FLOW_v1.0`

---

## 0. 為什麼需要這份 Map

**v5.11 教訓**：加了 entity_alignment signal、auto_apply mode、SOUL evolution 等多個 producer，但沒系統紀錄誰消費誰 → v5.12 又花 3 phase 接通 consumer。

**Map 治理規則**：
1. 任何新 signal 必先寫進此 map（producer + consumer 都要列）
2. fitness step 12 `signal_consumer_lint.sh` 自動偵測孤兒 signal
3. 月度 fitness 跑時報「signal coverage = consumed/total」

---

## 1. Signal Type 全表

### 1.1 Redis-based Signals

| Signal Key | Type | Producer | Storage | Consumer | Action | 狀態 |
|---|---|---|---|---|---|---|
| `agent:evolution:signals` | List | `self_evaluator.evaluate_and_store` | Redis LPUSH | `evolve()._consume_signals_batch` | promote/demote pattern | ✓ 真活 |
| `agent:evolution:query_count` | INT | `should_evolve()` INCR | Redis | scheduler trigger 條件 | trigger evolve() | ✓ 真活（v5.10.2 #4 修復） |
| `agent:evolution:last_run` | TIMESTAMP | `evolve()` SET | Redis | scheduler 24h 觸發條件 | trigger evolve() | ✓ 真活 |
| `agent:critical_feedback:*` | Key (TTL 30min) | `self_evaluator.evaluate_and_store`（CRITICAL signals）| Redis SETEX | `agent_planner._read_critical_signals` | inject system prompt | ✓ 真活 |
| `agent:domain_scores:*` | List | `self_evaluator.evaluate_and_store` | Redis LPUSH | `scheduler.should_evolve()` domain-aware trigger | 5 連敗 → 觸發 evolve | ✓ 真活 |
| `agent:patterns:detail:*` | Hash | `pattern_learner.learn`（success only）| Redis HSET | `agent_router.match` + `evolve.demote_failing` | router fast path / 降級 | ✓ 真活 |
| `agent:patterns:index` | ZSET | `pattern_learner.learn` | Redis ZADD | `evolve.promote_top_patterns / demote_failing` | promote/demote | ✓ 真活 |
| `agent:tool_stats:*:recent` | List | `agent_tool_monitor` | Redis LPUSH | tool health endpoint | UI 監控 | ✓ 真活 |
| `agent:tool_stats:degraded` | Set | `tool_monitor` | Redis SADD | `_filter_degraded_tools` | 排除壞工具 | ✓ 真活 |

### 1.2 Filesystem-based Signals

| File Pattern | Producer | Consumer | Action | 狀態 |
|---|---|---|---|---|
| `wiki/memory/diary/YYYY-MM-DD.md` | `diary_service.append_entry` | `pattern_extractor` (04:00) + `anti_echo` (週一 06:30) + `get_recent_reflections_block` | 抓 pattern / 反方觀點 | ✓ 真活 |
| `wiki/memory/patterns/pattern-*.md` | `pattern_extractor` (04:00) | `crystallizer.scan_and_propose` (04:30) | propose crystal | ✓ 真活 |
| `wiki/memory/failures/failure-*.md` | `pattern_extractor`（active=true）| `auto_defense.load_active_defenses` → `get_defensive_rules_block` | inject planner prompt | ✓ 真活（v5.10.2 確認）|
| `wiki/memory/proposals/crystal-*.md` | `crystallizer.scan_and_propose` | (a) `CrystalApplier.apply_proposal`（人工 batch）/ (b) `_auto_apply_eligible`（v5.11）| 改 yaml config | ⚠ 半活（dry-run 預設） |
| `wiki/memory/crystals/crystal-*.md` | `CrystalApplier.apply_proposal` | （結束狀態 — 改 yaml + audit log）| record-only | ✗ 0 entries（owner 沒批） |
| `wiki/memory/evolutions/YYYY-WNN.md` | `autobiography.persist_autobiography`（週日 18:00）| `autobiography.update_soul_growth` + `anti_echo._collect_entries`（含週自傳數據） | 更新 SOUL.md | ✓ 真活（v5.11 W17 entry 寫入） |
| Diary 內「反迴聲室」段落 | `anti_echo._append_to_today_diary` | `get_recent_reflections_block`（v5.12 C 接通）→ `agent_planner.system_prompt` | inject 反方觀點 | ✓ 真活（v5.12 C） |
| SOUL.md「我的成長」段落 | `autobiography.update_soul_growth`（agent_writable）| `soul_loader.load_soul`（每次 query 起手）| 載入坤哥人格 | ✓ 真活 |
| SOUL.md「我學到的偏好」段落 | `crystal_applier.apply_proposal`（agent_writable）| `soul_loader.load_soul` | 載入偏好 | ✗ 待 crystal apply 後 |

### 1.3 In-Memory Signals（Process-level，不跨 process）

| Signal | Producer | Consumer | Action | 狀態 |
|---|---|---|---|---|
| `EvalScore.entity_alignment` | `self_evaluator._eval_query_entity_alignment`（v5.11）| `agent_post_processing.success` + `agent_planner.entity_preservation_hint`（v5.12 B）| 排除汙染 + inject 警示 | ✓ 真活 |

### 1.4 Prometheus Metrics（觀測，不影響行為）

| Metric | Producer | Consumer | 用途 |
|---|---|---|---|
| `kg_entities_total / embedded_total / coverage_ratio` | `kg_metrics_refresh_job`（15min）| Grafana | 知識圖譜健康監控 |
| `memory_diary_days_total / patterns_total / crystals_total / proposals_pending / autobiographies_total` | `memory_metrics_refresh_job`（15min，v5.10.2 P1）| Grafana | 意識體鏈路健康 |
| `memory_diary_appends_total` | `diary_service.append_entry` | Grafana | diary 即時寫入頻率 |
| `memory_pattern_extract_runs_total{status}` | `pattern_extractor` | Grafana | cron 成敗 |
| `memory_crystal_applied_total` | `crystal_applier.apply_proposal` | Grafana | crystal 累積 |

---

## 2. 孤兒 Signal 警報（Lint 規則）

**Lint 偵測規則**：
1. grep `redis.lpush(SIGNAL_KEY` → 找 producer
2. grep `redis.lrange(SIGNAL_KEY` / `redis.brpop(SIGNAL_KEY` → 找 consumer
3. signal 在 producer 但 consumer 0 → fail（warning mode 先警告）

**v5.12 Phase D 已知狀況**：
- ✗ 0 個孤兒 signal（v5.12 三 phase 把所有半活 consumer 接通）
- ✓ 但仍 1 個半活：`crystals/` 0 entries（owner 瓶頸非 dead integration）

---

## 3. 治理 SOP（v5.13+ 新加 signal 必走流程）

新增任何 signal type 時：

1. **Producer 設計**：哪個 service 寫、寫到哪個 storage、key/file 命名規約
2. **Consumer 設計**：誰讀、讀完做什麼動作（必須有具體動作，不能只是「以後會有人用」）
3. **更新本檔**：在 §1 對應 table 加新行
4. **lint 驗證**：跑 `signal_consumer_lint.sh` 確認新 signal 被偵測為「has consumer」
5. **commit message** 末尾加 `Refs: MEMORY_SIGNAL_FLOW`

**反例（v5.10.2/v5.11 教訓）**：
- entity_alignment signal 加但 consumer 在 v5.12 才接通 → **延遲 1 個 minor version**
- crystal auto_apply 邏輯加但 mode 切換 endpoint 在 v5.12 才補 → **半活狀態 1 周**

---

## 4. 跨 repo lessons 連結

- L01 dead integration（SSOT 聲明 vs 實作斷鏈）
- L21 silent failure 雙疊（agent_post_processing typo + health script key 拼錯）
- L25 grep 關鍵字陷阱（驗證鏈路要實際呼叫，不能只 grep 函式名）
- 本 doc 是 L01 + L25 的治理級總和：**不靠 grep 一個關鍵字判斷，列出每個 signal 的完整 flow**

---

## 5. v5.12 後狀態

| 鏈路 | 狀態 | Producer | Consumer |
|---|---|---|---|
| 1A Pattern Router | ✓ 真活 | pattern_learner.learn | agent_router.match |
| 1B Crystal apply | ⚠ 半活 | crystallizer.scan_and_propose | crystal_applier.apply_proposal（人工 / auto_apply dry-run） |
| 2 Defense Block | ✓ 真活 | failure 寫檔 | get_defensive_rules_block → planner |
| 3 entity_alignment | ✓ 真活 | self_evaluator | agent_post_processing + planner（v5.12 B） |
| 4 SOUL 演化 | ✓ 真活 | autobiography | update_soul_growth → soul_loader |
| 5 Anti-Echo | ✓ 真活 | anti_echo._append | get_recent_reflections_block → planner（v5.12 C） |

**v5.12 後 5/6 鏈路真活，1 半活（owner 瓶頸非 dead）**。

---

> 真正智能體 = 每個 signal 都有 consumer，每個 consumer 都改變行為。
> 此 Map 是治理級防呆，避免「signal 通膨」（producer 多 consumer 缺）。
