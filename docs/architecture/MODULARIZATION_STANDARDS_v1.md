# 模組化標準 v1 — 新功能落地必過檢查清單

> **版本**：v1.0 草案（2026-05-16）
> **狀態**：待 owner 審核 → accepted
> **基準**：CK_Missive v6.9 + 2026-05-15/16 架構覆盤實證
> **適用**：所有新 service / API endpoint / agent tool / frontend page / fitness step / ADR
> **強制等級**：草案期 advisory，accepted 後納入 PR template + pre-commit
> **權威參考**：
> - `docs/architecture/STANDARD_REFERENCE.md`（範本級）
> - `docs/architecture/RETRO_20260515_BACKLOG.md`（事故證據）
> - `docs/architecture/OPTIMIZATION_PIPELINE.md`（連通圖）
> - `.claude/rules/adr-anti-half-wired-sop.md`（半接通 SOP）
> - `wiki/memory/lessons/LESSONS_REGISTRY.md`（L01-L29）

---

## 為何需要這份標準

v6.9 後架構覆盤揭發三大系統性破口，全部不是「實作能力」問題，而是「標準缺位」問題：

1. **ADR-0028 三守護假基線**（13 天）：腳本寫好放著、pre-commit 沒 wire，違規 PR 進 main 0 阻擋
2. **alias_rls audit 0 risks 假乾淨**：detection regex 太窄，142 endpoint 全進 No-user-filter bucket，第三次 RLS dormant 已埋
3. **L29 dict-key drift 第二次中斷**：`tool.get("name")` vs `tool.get("tool")` 多處未統一 → `tool_name=None` 後 silent except 三重疊加 → domain_scores 全空

三者共同 root cause：**「寫腳本/規範 ≠ 接通到守護點」**。STANDARD_REFERENCE.md 教「該長什麼樣」，本文補位教「新功能上線前要對齊什麼」。

---

## §1 Service 拆分邊界規則（職責 vs 行數）

### §1.1 黃金原則（承接 `feedback_ddd_over_line_count`）

| 訊號 | 拆 / 不拆 |
|---|---|
| 1074 行單一 domain 完整實作 | **不拆** — 領域內聚 |
| 200 行混三 domain 邏輯 | **必拆** — context 邊界混淆 |
| 該檔有自己的 domain events | 獨立子包 |
| 該檔被 ≥ 2 個 context 引用內部方法 | 抽 anti-corruption layer |
| 跨 3+ context 的小功能 | 抽共享 util（不獨立子包）|

### §1.2 新 service 必填 5 題

落地前必須在 PR description 回答：

1. **這個 service 屬於哪個 bounded context？**（document / contract / agency / vendor / erp / pm / taoyuan / tender / ai / memory / calendar / notification / integration / audit / backup / einvoice / security / observability）
2. **如果它跨 2+ context，主 owner 是哪一個？**（決定放在哪個子包）
3. **它依賴哪些其他 context 的服務？**（畫依賴箭頭，禁止循環依賴）
4. **它會發出 domain events 嗎？**（若是，定義 event schema 入 `services/<ctx>/events.py`）
5. **它的下游消費端是誰？**（必須先列出再開工，呼應 ADR 半接通 SOP）

### §1.3 反模式（從本案淬鍊的真實證據）

| 反模式 | 證據 | 解法 |
|---|---|---|
| 頂層散戶累積 | v6.9 retro：`services/` 仍 83 散戶 vs 25 子包 | 必入 `services/<ctx>/` 或合併到 base/common |
| God Service（混 CRUD/匯入/匯出/統計） | `document_processor.py` 早期形態 | 按使用案例拆 `*_io.py` / `*_query.py` / `*_stats.py` |
| Service 跨層直 import 另一 context top-level | `document/core.py:52,55` top-level `import calendar` | 改 lazy import 或 event-driven |
| 0-importer stub 累積 | v6.9 retro：3 個 `*_service.py` 0 importer（本 session 已刪） | 立即刪（不留尾巴）|

### §1.4 服務層 fitness 量化

| 指標 | 警戒 | 目標 |
|---|---|---|
| 頂層散戶比例 | > 25% | < 12%（v6.9 目標）|
| 0-importer stub 數 | > 0 | 0 |
| 單檔行數 > 1500 且非單一 domain | > 0 | 0 |
| `services/*.py` 直接 `session.execute()`（繞過 Repository）| > 5 | 0 |

對應腳本：`scripts/checks/service_dir_entropy.py` + `scripts/checks/service-line-count-check.py`

---

## §2 Capability Instrumentation 強制規範

### §2.1 「每個能力都要可被觀測」

新增以下任一資產時，**必須同時加 1 個 Prometheus metric counter**：

| 資產類型 | 必加 counter | 範例 |
|---|---|---|
| Agent tool（`services/ai/tools/`） | `agent_tool_calls_total{tool, outcome}` | search_documents / search_dispatch_orders |
| API endpoint（業務邏輯，非 CRUD list） | `endpoint_business_calls_total{endpoint, outcome}` | morning_report.preview |
| Frontend route（非詳情頁）| 後端 `route_page_view_total{route}`（前端透過 endpoint 回報）| /ai/wiki / /kunge |
| Dashboard panel | 後端對應 metric 存在（panel 是消費者）| - |
| Alert rule | 對應 metric 至少有 1 個 active label | - |
| Fitness step | exit code 必有 0/1/2 三檔（healthy/warning/error）| - |
| ADR | metric 或 fitness step 對應（若邏輯產生狀態變化）| - |
| Lesson | 至少 1 個 regression test + （可選）detection script | - |

### §2.2 為何強制：本 session 揭發的 12 項 dead capability

v6.9 retro 揭發後端有，但 7d 0 觸發或 0 mention 的能力：

- 4 個 graph tools 7d 0 呼叫
- 17,000+ code domain entities mention_count = 0
- autobiography 0 檔（功能存在 6 個月）
- crystals 0 筆（pattern → crystal 路徑寫了 4 個月）
- 4 alert rule 從未 fire
- ... 等 12 項

**共同症狀**：實作有、metric 沒、所以 0 觀測 = 0 使用 = 0 ROI 不可見。

### §2.3 Counter 註冊規範

```python
# backend/app/core/<context>_metrics.py
from prometheus_client import Counter, CollectorRegistry, REGISTRY

class <Context>Metrics:
    def __init__(self):
        # 命名規約：<domain>_<resource>_<action>_total{<dimension labels>}
        self.tool_calls = Counter(
            "agent_tool_calls_total",
            "Agent tool invocation count",
            ["tool", "outcome"],  # outcome ∈ {success, error, timeout, skipped}
        )
```

### §2.4 Counter 真活驗證

PR 必附「proof of execution」：

1. local startup 後 curl `/metrics` 看到 counter 註冊（即使值為 0）
2. unit test 模擬一次正常呼叫 + assert counter incremented
3. integration test 模擬一次失敗呼叫 + assert outcome=error 累計

---

## §3 半接通防範 5 層 Acceptance（承接 adr-anti-half-wired-sop）

任何新 capability（service / endpoint / tool / cron / nav item）上線前必過 5 層：

### 層 1：主路徑 wiring

- [ ] 程式碼可被任何 import path 觸發（grep 至少 1 個 caller）
- [ ] 若是 cron / startup hook，必須驗證 `main.py` / `scheduler.py` 有 register 那行
- [ ] 若是 fitness / pre-commit guard，必須驗證 `.git/hooks/pre-commit` 或 `scripts/checks/run_fitness.sh` 真的呼叫

**反例**：v5.9.0 整批 ADR-0028 三守護存在 13 天但 pre-commit 沒呼叫（本 session C1 已修）

### 層 2：邊角組合 identify

- [ ] 列出「最不容易繞過」用戶身份組合（owner 自己永遠是 admin → 邊角是 staff / 訪客 / 多 alias）
- [ ] 該組合**有對應 integration test**
- [ ] 該組合**owner 親自實測 1 次**

**反例**：ADR-0025 RLS 13 天 dormant，因 staff role + 多 alias 訪問路徑 owner 沒走過

### 層 3：Detection coverage 雙指標

audit / fitness 報告必須附「sample size / coverage rate」雙指標，禁止裸「0 risks」：

```
[BAD]
Audit complete. 0 risks found.

[GOOD]
Audit complete. Scanned 142 endpoints (regex pattern: `\.user_id == current_user\.\w+`).
Coverage: 142/142 endpoints scanned, but 0/142 matched detection pattern.
WARNING: pattern may be too narrow — endpoints commonly extract user_id to variable
first then pass to service layer. Manual review recommended for `services/*/core.py`
where RLS actually applies.
```

**反例**：alias_rls_coverage_audit 跑 0 risks 13 天，因 regex 只匹配 endpoint 內直寫，實際 endpoint 全先抽變數再傳 service

### 層 4：寫入 vs 讀取對稱性

- [ ] 若改了寫入面（merge 寫 canonical_user_id），讀取面（RLS query）必須同時對齊
- [ ] 若改了正向邏輯（OK → mark good），逆向邏輯（NOT OK → mark bad）必須對稱實作

**反例**：ADR-0025 寫了 canonical_user_id 但 RLS query 沒展開 alias group

### 層 5：上線後 7 天追蹤

- [ ] 第 7 天 owner check-in：邊角身份用戶有沒有 friction
- [ ] 第 7 天看 metric：counter 是否有正常累計（即使 outcome=skipped 也比 0 好）
- [ ] 第 7 天看 alert：對應 alert rule 連續 7 天綠燈
- [ ] **7 天無 friction + counter 累計 + alert 綠燈 → 真活宣告 + 寫 `wiki/memory/evolutions/`**

---

## §4 ADR L1-L4 自評強制（承接 ADR-0028 + ADR-0029）

### §4.1 L1-L4 級別定義

| 級別 | 描述 | 驗證強度 |
|---|---|---|
| **L1** | 文件型（governance / convention，無程式碼變動） | 無需自動驗證 |
| **L2** | 完整接通：程式碼 + 自動驗證（fitness / E2E / pre-commit） | 範本 |
| **L3** | 半接通風險：程式碼接通但無自動驗證（僅 unit test） | 接受但需 owner 14 天內補完 |
| **L4** | 高風險：複雜邊角 + 無/不足驗證 | 不得 accepted，須降級 proposed |

### §4.2 自評強制流程

新 ADR 從 `proposed` → `accepted` 前，ADR 文末必填：

```markdown
## 接通完整度自評

- **級別**：L2 / L3 / L4（圈選）
- **驗證資產**：
  - [ ] Unit test：tests/unit/test_<scope>.py
  - [ ] Integration test：tests/integration/test_<scope>_integration.py
  - [ ] Fitness step：scripts/checks/<name>.py + 寫入 run_fitness.sh step N
  - [ ] Prometheus metric：<metric_name>{labels}
  - [ ] Alert rule：configs/prometheus/alerts.yml § <group>
  - [ ] Pre-commit guard（若靜態可掃）：scripts/checks/<name>_guard.py + 寫入 .git/hooks/pre-commit
- **邊角組合實測紀錄**：wiki/memory/diary/YYYY-MM-DD.md § ADR-NNNN 上線實測
- **7 天追蹤檢點日期**：YYYY-MM-DD
```

### §4.3 自動分級偵測

加 fitness step：`scripts/checks/adr_level_audit.py`（待建）

- 掃 `docs/adr/*.md` frontmatter，計算每 ADR 是否含上述自評區塊
- 若 status=accepted 但無自評 → exit 1
- 若自評 L4 但 status=accepted → 強制降級警告

### §4.4 ADR Active 數量治理（呼應 ADR-0029）

- Active ADR ≤ 20 健康；> 20 觸發強制盤點
- 文件數字 vs 實際 grep 差距 ≤ 1 容忍（v6.9 retro 揭發 17 vs 16 漂移，本 session C8 已對齊）
- 每月 retro 必跑 `adr_lifecycle_check.py` 對齊 CLAUDE.md / skills-inventory.md

---

## §5 文件對齊 SOP — 每改一處同步 N 處

### §5.1 已知同步矩陣

| 改動類型 | 必須同步的位置 |
|---|---|
| 新增 ADR | `docs/adr/NNNN-*.md` + `CLAUDE.md`（active 計數）+ `.claude/rules/skills-inventory.md`（archived 計數）+ `docs/adr/README.md` |
| 新增/廢止 nav 條目 | `frontend/src/router/types.ts`（ROUTES）+ `frontend/src/router/AppRouter.tsx`（Route）+ `backend/app/scripts/init_navigation_data.py`（DEFAULT_NAVIGATION_ITEMS）|
| 新增 lesson | `wiki/memory/lessons/<name>.md` + `LESSONS_REGISTRY.md` table + `MEMORY.md` quick link |
| 新增 fitness step | `scripts/checks/<name>.py` + `scripts/checks/run_fitness.sh` step N + `STANDARD_REFERENCE.md` §12 表 |
| 新增 Prometheus metric | `backend/app/core/<scope>_metrics.py` 定義 + `prometheus_middleware.get_metrics_endpoint()` lazy populate（若需）+ `configs/prometheus/alerts.yml` 對應 alert + `configs/grafana/dashboards/*.json` panel |
| 新增 agent tool | `backend/app/services/ai/tools/tool_definitions*.py` + `tool_executor_*.py` + `agent-policy.yaml` routing + counter（§2.1）|
| 新增 schema | `backend/app/schemas/<entity>.py`（唯一來源）+ `frontend/src/types/<entity>.ts` |
| 新增 service to bounded context | `services/<ctx>/__init__.py` re-export + 移除頂層 stub（若有）+ `SERVICE_CONTEXT_MAP.md` 更新 |

### §5.2 自動偵測

- `scripts/checks/doc-sync-check.cjs`（已有，pre-commit 觸發）— 守 CLAUDE.md / CHANGELOG / skills-inventory
- `scripts/checks/route-sync-check.js`（已有）— 守 nav 三方同步
- 建議新增：`adr_doc_drift_check.py`（自動檢測 ADR 數字漂移）

### §5.3 PR Template 強制 checklist

在 `.github/PULL_REQUEST_TEMPLATE.md` 加：

```markdown
## 文件對齊 checklist
- [ ] 若新增 ADR：CLAUDE.md + skills-inventory.md + adr/README.md 已同步
- [ ] 若改 nav：types.ts + AppRouter.tsx + init_navigation_data.py 三方對齊
- [ ] 若新增 lesson：LESSONS_REGISTRY 已加 row
- [ ] 若新增 metric：alert rule + dashboard panel 已配
- [ ] 若新增 fitness step：run_fitness.sh 已 wire + STANDARD_REFERENCE §12 已加
```

---

## §6 Repository 層強制規範

### §6.1 BaseRepository 繼承強制

當前狀態（v6.9）：top-level 22/30 繼承 `BaseRepository[T]`，**8 個未繼承**：

- `agent_learning_repository.py`
- `agent_trace_repository.py`
- `case_nature_repository.py`
- `entity_extraction_repository.py`
- `project_staff_repository.py`
- `project_vendor_repository.py`
- `relation_graph_repository.py`
- `role_permissions_repository.py`

**規範**：

- 所有新 repository **必須**繼承 `BaseRepository[T]`
- 既有 8 個排入 P2 sprint 補繼承（先補高頻 5 個）
- Service 層**禁止** `session.execute()` — 必須走 Repository

### §6.2 RLS 強制接通（呼應 ADR-0025）

當前狀態：只有 `services/contract/core.py` + `services/document/core.py` 使用 `apply_*_rls` helper。`calendar_repository.py` 12 處 + ERP / taoyuan 系列全用裸 `user_id ==` 比對 → ADR-0025 第三次 dormant 已埋。

**規範**：

- 所有 query user-scoped 資料的 repository method **必須**使用 `RLSFilter` 或 `apply_*_rls` helper
- 禁止裸 `User.id == current_user_id` 比對（會繞過 alias 展開）
- fitness step `alias_rls_coverage_audit.py` 必須升級為「import-graph 偵測 RLSFilter 經過率」（regex 偵測 v6.9 已證明 false-negative）

### §6.3 Query Builder 三層

複雜查詢（5+ filter 條件 / 3+ JOIN）必須走 query_builders：

```
repositories/
├── base_repository.py           ← 第一層：CRUD + 分頁
├── document_repository.py       ← 第二層：domain-specific method
└── query_builders/
    └── document_query_builder.py ← 第三層：Fluent API
```

---

## §7 API Endpoint 重複 Pattern 抽 base class

### §7.1 偵測訊號

新 endpoint 在 5+ 處重複以下 pattern 時，必須抽 base class 或 helper：

| Pattern | 重複位置 | 建議 helper |
|---|---|---|
| `try: ... except Exception: pass` 包 `session.commit()` | 各 endpoint | `@safe_commit` decorator + counter |
| `@require_auth` + `db: Session = Depends(get_db)` 重複 | 全部 endpoint | `@authed_endpoint` composer |
| `if not user.is_admin: raise HTTPException(403)` | 各 admin endpoint | `Depends(require_admin)` 已存在 — 強制使用 |
| pagination boilerplate（skip/limit/total）| list endpoints | `Depends(get_pagination)` 已存在 — 強制使用 |
| SSE streaming setup（headers / disconnect handle）| AI endpoints | `create_sse_response()` helper（已部分存在）|

### §7.2 ai/ 子目錄拆分需要

`api/endpoints/ai/` 已有 27+ 檔，且 `graph_query.py` 等已拆出 admin/entity/unified 子變體 → 證明已開始膨脹。建議導入二級分類：

```
api/endpoints/ai/
├── agent/         ← agent_query / agent_capability / agent_evolution / agent_traces / agent_nemoclaw（已 deprecated）
├── document/      ← document_ai / document_analysis / entity_extraction / embedding_pipeline
├── graph/         ← graph_admin / graph_entity / graph_query / graph_skills_map / graph_unified / relation_graph
├── search/        ← rag_query / search_benchmark / search_history
├── memory/        ← memory / morning_report / morning_report_subscriptions
└── ops/           ← ai_stats / ai_monitoring / ai_feedback / ollama_management / token_usage / tools_manifest / synonyms / prompts / diagram_analysis / voice_transcription / digital_twin
```

### §7.3 endpoints/ai.ts 前端對齊

前端 `frontend/src/api/endpoints/ai.ts` (124 端點) + `erp.ts` (130 端點) 雙 100+ 已過閾值 → 需切割對齊後端二級分類（P2 任務）。

---

## §8 Silent Failure 巡檢守則（呼應 ADR-0028）

### §8.1 當前狀態

72 個檔案有 `except Exception: pass` pattern（v6.9 retro 數據）。高熱區：

- `agent_synthesis.py` / `agent_orchestrator.py` / `agent_evolution_scheduler.py` / `agent_planner.py`
- `morning_report_service.py`
- `crystallizer.py` / `pattern_extractor.py`
- ERP `expense_approval.py` / OCR / QR

### §8.2 規範

新增程式碼**禁止**裸 `except Exception: pass`。任何 `except` 必三件事齊備：

```python
# ❌ 禁用
try:
    do_thing()
except Exception:
    pass

# ✅ 必用
try:
    do_thing()
except SpecificError as e:
    logger.error(
        "do_thing failed",
        exc_info=True,
        extra={"context_key": context_value},
    )
    <metric>.labels(error_type=type(e).__name__).inc()
    raise  # 預設 re-raise；若必須吞錯需註明理由

# ✅ Fire-and-forget 可接受變體（背景任務 / metric write 不阻擋主流程）
try:
    fire_and_forget()
except Exception:
    logger.warning("fire_and_forget skipped", exc_info=True)
    # 不 re-raise，但仍 log
```

### §8.3 漸進式清理

72 檔不能一次清，分批排：

- P1（2 週內）：6 大熱區（agent_synthesis / agent_orchestrator / agent_evolution_scheduler / agent_planner / morning_report / crystallizer）
- P2（1 月內）：scrapers / OCR / QR（fire-and-forget 性質，至少加 logger.warning）
- P3（1 季內）：其餘

每批清完加 1 條 regression test 鎖定該事故。

---

## §9 Frontend 對應規範

### §9.1 SSOT 嚴格 enforcement

- `frontend/src/types/` barrel 是唯一型別來源；endpoint 自訂 interface 禁止
- 詳情頁必用 `DetailPageLayout`；Modal/Drawer CRUD 禁止
- React Query 唯一資料取得方式；`useEffect + apiClient` 禁止

### §9.2 路由四方同步（強化 §5.1）

- `frontend/src/router/types.ts` ROUTES
- `frontend/src/router/AppRouter.tsx` Route 元素
- `frontend/src/components/layout/Sidebar.tsx` 顯示
- `backend/app/scripts/init_navigation_data.py` DEFAULT_NAVIGATION_ITEMS

任一處改動必過 `/route-sync-check`。

### §9.3 endpoints 二級拆分（>100 端點觸發）

- `endpoints/ai.ts` 124 → 拆 `endpoints/ai/{agent,graph,search,memory,ops}.ts`
- `endpoints/erp.ts` 130 → 拆 `endpoints/erp/{quotation,invoice,billing,expense,asset,ledger,einvoice}.ts`

---

## §10 Fitness Step 新增 SOP

### §10.1 何時加 fitness step

新增 ADR 或 lesson 若邏輯具備「silent stale」可能性（無人觸發就無人察覺）→ 必加 fitness step。

### §10.2 step 必填要素

```python
# scripts/checks/<scope>_<concern>_check.py

import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true", help="CI 模式：發現問題 exit 1")
    args = parser.parse_args()

    # 1. 蒐證
    sample_size, hits = collect_evidence()

    # 2. 雙指標報告（§3 層 3）
    print(f"Scanned: {sample_size} items")
    print(f"Detection coverage: {hits}/{sample_size}")
    print(f"Pattern: {DETECTION_PATTERN}")

    # 3. 三檔位 exit code
    if hits == 0 and sample_size > 0:
        # 可能 false-negative，需 owner 檢視 detection coverage
        print("WARNING: 0 hits in non-empty sample — verify detection pattern")
        return 1 if args.ci else 0
    elif hits > THRESHOLD:
        print(f"ERROR: {hits} > threshold {THRESHOLD}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### §10.3 wire 到 run_fitness.sh

新 step 必須加到 `scripts/checks/run_fitness.sh` 並更新 step 編號註解。當前 22 step（v6.9），本 session 新增 step 23（capability_usage_audit）。

---

## §11 跨層整合自查清單（新 capability 落地前必填）

```markdown
## 落地自查清單（複製到 PR description）

### 拆分邊界
- [ ] §1.2 五題已回答
- [ ] 不創造頂層散戶
- [ ] 不違反「跨 3+ context = 共享 util」原則

### Instrumentation
- [ ] 加 Prometheus counter（§2.1 對照表）
- [ ] 加 unit test 驗證 counter 累計
- [ ] 加 integration test 驗證 error path counter 累計

### 半接通防範
- [ ] §3 五層 acceptance 全綠
- [ ] 邊角身份組合已 identify + 實測
- [ ] 寫入 vs 讀取對稱性已驗證

### ADR / 文件對齊
- [ ] 若涉及 ADR：L1-L4 自評已填
- [ ] §5.1 對應同步矩陣已過
- [ ] PR template checklist 全勾

### 7 天追蹤
- [ ] 追蹤日期已寫入 wiki/memory/diary/
- [ ] alert rule 對應 metric 已配
```

---

## §12 與既有規範的關係

| 規範 | 角色 | 與本標準關係 |
|---|---|---|
| `STANDARD_REFERENCE.md` | 範本級「該長什麼樣」 | 本標準補位「新功能落地前該對齊什麼」 |
| `MANDATORY_CHECKLIST.md` | 任務類型 → 檢查清單 | 本標準是 meta-checklist（任何類型必過 §11）|
| `adr-anti-half-wired-sop.md` | ADR 級半接通 SOP | 本標準 §3 廣義化到所有 capability |
| `LESSONS_REGISTRY.md` | 失敗模式集（L01-L29）| 本標準從 lessons 反推「應該怎樣才不會死」|
| `CAPABILITY_GOVERNANCE.md`（配套）| capability 健康治理工具 | 本標準是落地門檻、CG 是運行期治理 |
| `OPTIMIZATION_PIPELINE.md`（配套）| 10 條優化環節連通圖 | 本標準是「上線」門檻、Pipeline 是「日常運行」 |
| ADR-0028 錯誤合約化 | silent failure 政策 | 本標準 §8 是落地端 enforcement |
| ADR-0029 ADR Lifecycle | active ADR 數量治理 | 本標準 §4.4 強化文件對齊 |

---

## §13 滾動更新

- v1.0（2026-05-16）：首版，從 v6.9 retro 三大破口反推
- 每月架構 retro 修訂一次
- 新 lesson（L30+）入 LESSONS_REGISTRY 後對應修訂本標準對應章節
- 跨 repo（lvrland / PileMgmt）採用後反饋落地痛點修訂
