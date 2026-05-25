# 架構覆盤待辦清單 — 2026-05-15

> **來源**：v6.9 整體架構覆盤（service / repository+DB / 跨切面 / frontend 四層並行調研）
> **狀態**：規劃中，下一輪 dynamic /loop 執行
> **優先級規則**：P0 = 半天內必做（關 false-positive 安全感）/ P1 = 兩週內 / P2 = 一月內 / P3 = 一季內

---

## 三大系統性破口（必須先理解再執行）

### 破口 1：ADR-0028「3 守護」是文件騙局
`scripts/checks/{async_session_race,sse_headers,schema_lazy_load}_guard.py` 三檔存在可執行，但 `.git/hooks/pre-commit` **完全沒呼叫它們**。pre-commit 實際只跑 skills/TSC/py_compile/ruff/pattern_yaml_type/bandit/敏感檔/smoke/doc-sync。任何違反這三條的 PR 進 main 沒有任何阻擋。**v5.9.0 整批 GREEN 是假基線。**

### 破口 2：alias_rls「0 risks」是偵測層級錯位
`alias_rls_coverage_audit.py` step 21 跑 0 risks，但 regex 只匹配 endpoint 內直寫 `.user_id == current_user.X`，實際 endpoints 都先抽變數再傳 service 層 → 142 個 endpoint 全進 `No user filter` 而 risks 永遠 = 0。

DB 層更嚴重：**只有 `services/contract/core.py` 與 `services/document/core.py` 真用 `apply_*_rls`**；`calendar_repository.py` 12 處 + ERP / taoyuan 系列全用裸 `user_id ==` 比對 → ADR-0025 第三次 dormant 已埋。

### 破口 3：L29 dict-key drift 還剩 4 處未修
`agent_self_evaluator.py:281` 已加 `tool.get("tool") or tool.get("name")`，但同樣 pattern 在 `agent_orchestrator.py / agent_conductor.py / agent_tool_loop.py:149,151 / agent_plan_enricher.py:60,80,97` 共 **4 模組未統一**。`agent_plan_enricher.py` 三連命中是下次中斷的明確倒數。`TOOL_DOMAIN_MAP` 49/98 涵蓋率 < 50%。

---

## P0 — 半天清單（重啟後立刻做）

| # | 項目 | 路徑 | Effort |
|---|---|---|---|
| **C1** | 把 3 守護加進 `.git/hooks/pre-commit`（5 行 bash，照 `pattern_yaml_type_guard.py` 模式） | `.git/hooks/pre-commit` | 30 min |
| **C2** | 建 `ToolCall` Pydantic schema 並全鏈強制 — 取代 raw dict，4 處 `tc.get("name")` 換 `tc.tool_name`；contract drift 變 type error | `backend/app/schemas/tool_call.py` + 4 agent 模組 | 1 h |
| **D1** | 驗證 `setup_pool_metrics(engine)` / `setup_query_listener(engine)` 是否實際在 startup 執行（grep 只命中 docstring）；若失接，DB observability 為假象 | `backend/app/main.py` + `backend/app/db/database.py` | 30 min |
| **F1** | 移除 `init_navigation_data.py` 3 條死 nav 條目（`/agent/dashboard`、`/ai/digital-twin`、`/admin/ai-assistant`）— 新環境 reset 會 seed 殭屍菜單 | `backend/app/scripts/init_navigation_data.py` | 30 min |
| **S1** | 立即刪 3 個 0-importer stub | `backend/app/services/{wiki,tender_search,tender_analytics}_service.py` | 10 min |
| **C8** | 校正 CLAUDE.md / skills-inventory.md「Active 17」→ 16；「Archived 10」→ 14 | `CLAUDE.md` + `.claude/rules/skills-inventory.md` | 10 min |

**完成這 6 項可關掉**：(a) ADR-0028 假基線 (b) L29 第三次同類中斷最近熱區 (c) DB observability 是否空殼的疑問 (d) 新環境 onboard 殭屍菜單 (e) doc-actual drift。

---

## P1 — 兩週清單

### Repository / DB
- **D2**（2d）: RLS alias 展開全面接通 — `calendar_repository.py` 12 處 + ERP / taoyuan repo 系列裸 user_id 比對；同步重設 audit 範圍從「endpoints regex」擴到「import-graph 偵測 RLSFilter 經過率」
- **D3**（0.5d）: `db_query_metrics.SLOW_QUERY_THRESHOLD_MS` 5000 → 1000ms + 加 `table` 標籤 + 對應 alert rule
- **D4**（1d）: embedding 加 `model_version` 欄位（5 個 Vector 表）+ ingest 寫入 — 防 `EMBEDDING_MODEL` env 漂移污染
- **D5**（0.5d）: 修 `core.py:99-100`（`lazy="dynamic"`）+ `document.py:61-65`（4 個 eager 並陳的笛卡爾積風險）

### 跨切面
- **C3**（0.5d）: `alias_rls_coverage_audit.py:39-46` 改寫為 import-graph 偵測（從 endpoint reachability 看是否經過 `RLSFilter`）
- **C4**（1.5d）: 72 檔 `except Exception: pass` 巡檢 — 至少先消滅 agent_synthesis / agent_orchestrator / agent_evolution_scheduler / agent_planner / morning_report / crystallizer 6 大熱區
- **C5**（0.5d）: HTTP middleware path label 加路由歸一化（避免 raw URL 把 cardinality 炸開）

### Service
- **S2**（0.5d）: 斬唯一硬耦合 — `document/core.py:52,55` top-level 直 import calendar → 改 lazy 或抽 event

### Frontend
- **F4**（0.5d）: 修 2 處真違規 `useEffect + apiClient`（`QueryProvider.tsx` / `UnifiedAgentPage.tsx`）

---

## P2 — 一月清單

### Service 層 stub 收尾
- **S3**（1.5d）: 排 sprint 把剩 ~7 個 stub 的 import 全 codemod 改寫，2026-Q3 一次性砍 73 檔
- **S4**（1.5d）: `wiki/compiler.py` 1901L → 拆 fetch/template/incremental/slugify 4 檔
- **S5**（1d）: `memory/autobiography.py` 687L 跨打通道 → 抽 `services/ports/MessagingPort`

### Repository 治理
- **D6**（1.5d）: 18/34 repo 補繼承 `BaseRepository[T]`（先補 agent_learning/agent_trace/relation_graph/entity_extraction/role_permissions 5 高頻者）
- **D7**（0.5d）: `backfill_kg_embeddings_all.py` 走 HNSW `batch` mode（目前只用 precise，10K+ entity 浪費延遲）

### 跨切面
- **C6**（1d）: `domain_whitelist + csrf + cors` 三件互不引用 → 抽 `core/security_config.py` 單一 audit 入口
- **C7**（1d）: adr-anti-half-wired-sop 在 ADR template 強制引用 + 自動分級 L1-L4 偵測腳本

### Frontend
- **F2**（0.5d）: `endpoints/ai.ts` (124) + `endpoints/erp.ts` (130) 二次拆分對齊後端 contexts
- **F3**（1d）: `types/erp.ts` (1108L) + `types/taoyuan.ts` (890L) 內拆

---

## P3 — 一季清單

- **S6**（2d）: `ai/agent/` 40 檔做二級拆分（core/evolution/pattern/supervision/shadow/tools_glue）
- **S7**（1d）: `ai/misc/` 12 檔雜貨櫃 → 拆 skills/voice/code_wiki/user_signals
- **D8**（1d）: `documents` CASCADE 連動 chunks/entities/AI/mentions — 評估改 SET NULL + soft delete
- **F5**: 46 pages 內聯 apiClient → 抽共用 mutation hook（漸進，2-3 sprint）
- **F6**（1h）: `pages/TaoyuanProjectDetailPage.tsx`（外層）改用 DetailPageLayout 或刪除（已有子版本）

---

## 結構性反思（給下一個 retro）

### Pattern A：「腳本存在 ≠ 守護生效」
3 個 ADR-0028 守護、alias_rls audit、整套 fitness 多項都犯同類問題 — 寫了腳本以為防護，但 wiring（pre-commit / startup / 偵測 pattern）未驗證。

**建議下輪做「腳本生效率審計」**：每個防護腳本要附「proof of execution」（pre-commit log / metric counter / startup hook 名稱）。

### Pattern B：「audit 0 risks」要看 detection coverage
alias_rls 0 risks、ADR L1-L4 0 引用，都是「偵測機制掃不到」而非「真乾淨」。**建議所有 audit 報告強制顯示「sample size / coverage rate」雙指標**，避免 false-positive 安心感。

### Pattern C：「真活宣告」的下一層門檻
v6.9 的 L26 穿透式驗證已大幅提升真活含金量，但仍有「驗證範圍 vs 實際使用範圍」差距。下一階段建議所有 audit 要附「N/M 涵蓋率」（N=驗證樣本，M=實際 codepath 數）。

---

## 各層健康度評分（總表）

| 層 | 健康度 | 主要結論 |
|---|---|---|
| Service 層（DDD） | **GREEN+** | 真實散戶 < 3% 遠低於 12% 目標；剩 73 stub 阻塞點僅 7 處 |
| Repository / DB | **YELLOW** | RLS alias 擴展只 2/34；3 守護未進 pre-commit；DB observability wiring 未驗證 |
| 觀測棧 / 錯誤合約 | **YELLOW-** | 3 守護完全脫鉤；72 檔仍 silent except |
| 認證 / RLS | **RED**（看似 GREEN，實為 false-positive 安全感） | audit pattern 過窄；ADR-0025 第三次 dormant 風險 |
| Frontend | **GREEN-** | SSOT 合規高；ai.ts/erp.ts 雙 100+ 端點需切；後端 nav seed 含 3 條死選單 |
| ADR 治理 | **GREEN-** | 實跑 16 active vs 文件 17；adr-anti-half-wired-sop 0 引用孤兒 |
