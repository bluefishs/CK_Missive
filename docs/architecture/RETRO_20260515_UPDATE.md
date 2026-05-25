# 架構覆盤更新（下午追蹤）— 2026-05-15

> **承接**：`RETRO_20260515_BACKLOG.md`（早盤產出，含三大破口 + P0-P3 待辦）
> **本文目的**：對早盤 P0 6 項做 grep 實證 + 補早盤未覆蓋的兩塊盲區（效能/韌性、跨 repo/業務橋接）
> **元觀察**：早盤代理 grep `backend/app/main.py`（路徑不存在）誤判 D1，與「ADR-0028 假基線」是同一個 [[arch_pattern_script_existence_not_enforcement]] 反模式 — 證據蒐集本身也會犯同類錯誤

---

## §1 早盤 P0 6 項實證校準

| # | 早盤假設 | 實證指令與結果 | 結論 |
|---|---|---|---|
| **C1** | 3 守護未進 pre-commit | `grep -E "async_session\|sse_headers\|schema_lazy" .git/hooks/pre-commit` → 0 hit | **TRUE — 持效** |
| **C2** | L29 dict-key drift 跨 4 模組 (`agent_orchestrator/conductor/tool_loop/plan_enricher`) | 前 3 個 0 hit；只 `agent_plan_enricher.py:60,80,97` 三連命中 | **降級 4→1 模組**（仍須修） |
| **D1** | DB metrics wiring 失接（grep 只命中 docstring） | 早盤代理用錯路徑 `backend/app/main.py`（不存在）；真路徑 `backend/main.py:97-98,104-105` 真有 `setup_pool_metrics(engine)` + `setup_query_listener(engine)` | **誤判 — CLOSE** |
| **F1** | 3 死 nav 條目 | `init_navigation_data.py:723/728/738` 仍存在 | **TRUE** |
| **S1** | 3 個 0-importer stub 未刪 | 三檔仍在 | **TRUE** |
| **C8** | 文件寫 17 active / 10 archived 與實際漂移 | `adr_lifecycle_check.py` 顯示 active **16** / archived **14** / removed 1；CLAUDE.md + skills-inventory 仍寫 17/10 | **TRUE** |

**P0 真實重排**：6 項 → 5 項（D1 解除誤判，C2 effort 大幅降低）。

---

## §2 下午新發現 A：效能 / AI 推理韌性（早盤未覆蓋）

### E1 — HNSW ef_search 4 檔位只 1 用，其它 3 檔位 dead config

- `backend/app/core/hnsw_config.py` 定義 `precise=200 / default=100 / fast=60 / batch=40`
- 全程式碼 **2 個呼叫點**（`rag_retrieval.py:222` + `canonical_entity_resolver.py:67`）都硬寫 `"precise"`
- `default / fast / batch` 三檔位 **0 caller** — 是 dead config
- **影響**：autocomplete 等本應 fast 的路徑全跑 ef=200；KG 10,792 entity × pgvector HNSW p95 沒 dashboard 觀測；`SLOW_QUERY_THRESHOLD_MS=5000` 但 histogram bucket 上限 10s，spike 可能就埋在 5–10s bucket 內

### E2 — Token budget 超額無 hard cutoff

- `token_usage_tracker.record()` 回 `budget_exceeded=True` 但 **0 caller** 用此值做拒絕
- `_send_budget_alert` 已是 no-op；告警轉嫁給 `llm_quota_check_job`（每 **6 小時**）
- `ai_connector.py:919-927` `_smart_route_decision` daily_pct≥90% → `prefer_local=True`（只是切 Ollama，沒拒絕）
- **影響**：Groq daily quota 真爆時 6h 內不會主動告警；勉強切 local → Ollama GPU pool (semaphore=3) 與正常請求競爭 → 雙倒

### E3 — Scheduler 04:00-06:30 擠 11 job 無 jitter / 無 max_runtime

`scheduler.py:1797-2078` 集中時段：
- 03:30 erp_graph_ingest + db_graph_refresh（同分）
- 04:00 kb_coverage + memory_pattern_extract（同分）
- 04:30 kg_embedding_backfill + memory_crystallization_scan（同分）
- 04:45 embedding_warmup + soul_mirror_sync（同分）
- 05:00 ledger_reconciliation + wiki_compile (週一)
- 06:00 tender_refresh + agent_self_diagnosis + memory_anti_echo (週一)（**三 job 同分**）

每個 job `max_instances=1 + coalesce=True` 但無 `misfire_grace_time` / 無 `max_runtime`；`apscheduler` 預設 misfire_grace_time=1s — 過了直接跳過下一輪 silent skip。

### 5 個未覆蓋故障情境（無對應 alert / runbook）

1. **Triple-provider OPEN**：Groq 429 + NVIDIA 配額 + Ollama OOM 三 CB 全 OPEN → 走 `_generate_fallback_response`（`ai_connector.py:936` 硬碼 6 關鍵字罐頭回應），`InferenceNoCompletions` alert **看不到**（fallback 也算 completion）
2. **DB pool 滿 × asyncio.gather 誤用**：ADR-0021 有 `run_with_fresh_session` 但**無 lint guard** 防誤用；scheduler 04:30 雙 job × SSE stream (持 connection 60s) → pool exhaustion；`DbPoolTimeoutSpike` alert `for: 3m` 太寬鬆
3. **CF Tunnel 故障 vs LINE webhook 30s timeout**：runbook 在但**沒對應 alert**；LINE 認定 webhook 死 → 自動降級重送機制未驗證
4. **pgvector index 損壞或膨脹**：KG 10,792 + dispatch 127 + wiki 220 embedding；**無 VACUUM/REINDEX 排程**，無 `pgvector_index_size_bytes` gauge
5. **Ollama 切 qwen2.5:7b (4.7GB) × semaphore=3 → 理論 VRAM peak 14.1GB**（RTX 4060 8GB 必爆）；backend 端 `InferenceSemaphore.acquire(timeout=90.0)` 可能仍會放 3 task 進去等 GPU swap；**無 VRAM gauge 進 Prometheus**

---

## §3 下午新發現 B：跨 repo 治理 + 業務域橋接（早盤未覆蓋）

### G1 — v6.9 範本 9 條 0 採用，consumers.yml 14 天未動

- 5/12 新增 9 條範本（`provider_circuit_breaker` / `alias_rls_coverage_audit` / `domain_score_freshness_check` / `metrics_populate_errors` / `memory_diary_append_failures` / `L29_lesson` / 3 runbook）僅在 `skills-inventory.md` 自我聲明
- `docs/architecture/consumers.yml` mtime = **2026-04-28**（v5.10 後沒更新；lvrland/PileMgmt/KMapAdvisor `adopted_assets: []`，9 條新範本連 `pending_review` 都沒登）
- 跨整個 D:/CKProject **0 個檔案**引用這 9 條 FQID

### G2 — ck-missive-bridge skill 是 facade-of-one

- `docs/hermes-skills/ck-missive-bridge/tool_spec.json` 只暴露 **1 tool（query_missive）**指向 `/api/ai/agent/query_sync`
- 但 CK_Missive 本身 AI 子系統有 **46 真工具**
- skill mtime = **2026-04-14**（距 v6.9 已 28 天，R3/R6/R7/L29 等錯誤合約強化全未反映）
- **後果**：Hermes 控制平面實際只能問 NL question，ADR-0030 5/20 GO/NO-GO baseline 無法穿透到工具層級

### G3 — ADR TEMPLATE 缺 §How to apply 強制欄位（ADR-0028 假基線根源）

- `docs/adr/TEMPLATE.md` 只有「背景 / 決策 / 後果 / 替代方案」4 段
- **未引用** `adr-anti-half-wired-sop.md` 的 A-E 檢查清單（5/06 ADR-0025 dormant 13 天後才訂立的 SOP）
- ADR-0034 (5/06) 是 SOP 訂立後第一個新 ADR，**未在 template 強制 §A 程式碼接通 / §B 自動驗證 / §C 邊角組合 / §D 7 天追蹤 / §E 文件對齊**
- ADR 行**沒有任何 L1-L4 接通完整度級別欄位**

### B1 — 7 圖譜 `graph_domain == 'knowledge'` 獨佔 → KG-2~7 邊緣化

- backend 共 **13 處 hardcode** where clause（graph_query 4 / graph_traversal 3 / graph_statistics 5 / wiki_coverage 1 / scheduler 1 / embedding_manager 1）
- `tender` 已建獨立 `graph_domain='tender'`（`tender_graph_ingest.py`）但**只有 1 處 ingest，0 處 query** — 寫入 KG 但 wiki/agent 都不會讀
- 符合 dead config 反模式（L02）

### B2 — wiki kg_entity_id 全域覆蓋率 75.8%（235/310），其中 75 個有商業性 entity 漏連

- MEMORY.md 聲稱「dispatch 100% / project 86%」是 by category，但**整體 wiki 仍有 75 個漏連**
- 漏連樣本含 `社團法人中華民國全國中小企業總會` / `臺中市112年度都市計畫樁測釘案` — 是**有業務價值的 entity**
- 反向（KG 有但 wiki 無）未量化 — `wiki_kg_link_audit.py` 只跑單向

### B3 — 跨業務域工具僅 1/46 = 2.2%

- 唯一是 `auto_tender_to_case`（tender → contract case）
- 缺：「公文→自動建 dispatch」「ERP 報價→自動產 milestone」「critique→自動發 report」這類組合
- `case_code` 雖 35 處引用但**沒有一個 service 純粹做「橋接 PM↔ERP↔doc」**，證明 case_code 只是 column 等於 bridge ID 而非 bridge service

---

## §4 健康度更新（疊加 5-15 早盤表）

| 層 | 5-15 早盤 | 下午校準 | 主因 |
|---|---|---|---|
| Service 層（DDD） | GREEN+ | GREEN+ | 不變 |
| Repository / DB | YELLOW | **YELLOW+** | D1 wiring 實證 OK |
| 觀測棧 / 錯誤合約 | YELLOW- | YELLOW- 但 + E1/E2/E3 容量盲區 | 3 點新破口 |
| 認證 / RLS | RED | RED | 不變 |
| Frontend | GREEN- | GREEN- | F1 仍未做 |
| ADR 治理 | GREEN- | **YELLOW** | G3 揭發 template 缺 SOP 強制引用 |
| **AI 推理韌性**（新欄）| — | **YELLOW** | E1/E2/E3 量化盲區 |
| **跨 repo / FQID**（新欄）| — | **YELLOW-** | G1/G2 證據明確 |

---

## §5 補 backlog 排序（疊加 5-15 早盤 P0-P3）

### P0 半天清單（校準後 5 項）

| # | 任務 | Effort |
|---|---|---|
| C1 | 3 守護加進 `.git/hooks/pre-commit` | 30 min |
| C2 | `agent_plan_enricher.py:60,80,97` 三處改 `tc.get("tool") or tc.get("name")`（降級工作量；ToolCall schema 可延後） | 15 min |
| F1 | 移除 `init_navigation_data.py:723/728/738` 3 條死 nav | 30 min |
| S1 | 立刪 3 個 0-importer stub | 10 min |
| C8 | 校正 CLAUDE.md / skills-inventory.md「17→16, 10→14」 | 10 min |
| ~~D1~~ | ~~DB metrics wiring~~ | **CLOSED（誤判）** |

**合計約 95 min**（含 task switching），半天前段即可清完。

### P1 兩週新增（今日新發現）

| # | 任務 | Effort | 對應破口 |
|---|---|---|---|
| **N1** | Triple-provider degradation alert：`rate(inference_fallback_total{to_provider="fallback"}[5m]) > 0` → critical | 2h | E2 silent fallback |
| **N2** | Token budget hard cutoff：`record()` 回 `budget_exceeded=True` raise exception；`llm_quota_check_job` 6h→1h | 0.5d | E2 |
| **N3** | Scheduler stagger：04:00-06:30 加 `jitter=300` + `misfire_grace_time=600` + `scheduler_job_duration_seconds` histogram | 0.5d | E3 |
| **N4** | ADR TEMPLATE 加 §How to apply（A-E from adr-anti-half-wired-sop）+ L1-L4 級別 metadata；補 ADR-0034 self-assess | 2h | G3 / 預防下個 ADR-0028 假基線 |
| **N5** | `consumers.yml` 加 9 條 v6.9 範本到 `pending_review`，跑 `notify-consumers.py` dry-run 推 CK_AaaP/hermes-agent | 1h | G1 |

### P2 一月新增

| # | 任務 | Effort | 對應破口 |
|---|---|---|---|
| **N6** | HNSW 動態 ef_search（query_complexity 推斷）+ `pgvector_query_duration_seconds` histogram by `search_type` + Grafana panel | 1d | E1 |
| **N7** | Ollama VRAM 觀測：寫 `ollama_vram_usage_bytes` gauge（每 30s 拉 `/api/ps`）+ saturation alert；換模型 SOP 強制 `N×size ≤ 7GB` 驗證 | 1d | Ollama OOM |
| **N8** | ck-missive-bridge 加第 2/3 tool（`list_documents` / `get_case_status`），SKILL.md 同步 v6.9，補 references 同步 R3/R6/R7 metrics | 4h | G2 |
| **N9** | 抽 helper `default_graph_domains()` 取代 13 處 hardcode；至少 graph_statistics 支援 tender domain query | 3h | B1 |
| **N10** | `wiki_kg_link_audit.py` 加反向審計（KG entity 無 wiki page）+ 補 75 個漏連 wiki kg_entity_id | 2h | B2 |
| **N11** | 建 `case_code_bridge_service`（單一 service 純粹做 PM↔ERP↔doc 三方 JOIN），收斂 35 處散戶 query；補跨域 Agent tool「create_quote_from_doc」 | 半天 | B3 |
| **N12** | `pgvector_index_size_bytes` gauge + 每週日 03:00 `VACUUM ANALYZE` + 月度 `REINDEX CONCURRENTLY` | 0.5d | pgvector 維護 |
| **N13** | CF Tunnel + LINE webhook synthetic probe：每 10 min hit `missive.cksurvey.tw/health` 經外網 → `cf_tunnel_external_probe_failures` alert | 0.5d | webhook silent fail |

---

## §6 元教訓

### Pattern Z — 「覆盤代理也會犯反模式」

下午驗證才發現 5-15 早盤代理 grep `backend/app/main.py`（路徑不存在）但**沒有 raise 任何警告**，導致 D1 結論為「DB metrics wiring 失接」誤判。這個錯誤的形態與「ADR-0028 3 守護假基線」「alias_rls 0 risks false-negative」屬於**同一個元反模式**：

> 工具回傳「沒命中」時，**到底是真的沒問題、還是工具自己掃錯地方？**

[[arch_pattern_script_existence_not_enforcement]] 強調「腳本存在 ≠ 守護生效」，[[arch_pattern_audit_zero_risk_false_negative]] 強調「audit 0 risks 要看 detection coverage」。今天再補一條：

**Pattern Z**：覆盤工具（含 LLM agent）回傳「找不到」時，**先驗證搜尋目標存在**再判定結論。建議所有 audit 報告強制顯示「sample size / coverage rate / file existence proof」三指標。

### 下一輪 retro 建議

- 每個防護腳本要附 **proof of execution**（pre-commit log / metric counter / startup hook 名稱）
- 每個 audit 報告強制顯示 **N/M 涵蓋率**（N=驗證樣本，M=實際 codepath 數）
- 代理 grep 報 0 hit 時，**先 ls 驗證目標路徑存在**再下結論

---

## 後續執行順序建議

1. **半天 P0 5 項**（95 min）— 清掉假基線最大破口
2. **N1 + N4 兩件 P1**（4h）— 補 silent fallback alert + ADR template，防範下個 ADR-0028
3. **N5 consumers.yml 推送**（1h）— G1 影響面最廣
4. 其餘 N2/N3/N6-N13 按 sprint 排
