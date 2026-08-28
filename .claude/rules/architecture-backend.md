---
paths:
  - backend/**
---

<!-- 2026-08-27 /doctor：加上 paths 讓這份改為**延遲載入**（後端目錄結構與契約 —— 只在動到 backend/ 時才需要）。
     內容零刪除；只是不再每個 session 都進 context。 -->
# 專案結構與架構

> **v5.9.0 錯誤合約化（ADR-0028）**：3 靜態守護 + Silent failure 零容忍 + Timeout 合約
> **v5.9.0 觀測棧完工**：Prometheus 16 指標 + 3 Grafana dashboards + 12 alert rules + Promtail v2

## 根目錄結構

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

## 請求流與中間件執行順序（v6.18 覆盤補充 2026-06-12）

公網請求流：`cloudflared tunnel` → FastAPI（`backend/main.py`）。

> ⚠️ 2026-08-27 校正：origin 是 **`http://host.docker.internal:8001`**，不是 `localhost:8001`，
> 而且**設定不在 repo 裡** —— `ck_missive_cloudflared` 的 cmd 是 `tunnel run`（無 `--config`、無掛載），
> 屬**遠端管理型 tunnel**，ingress 規則存在 Cloudflare Dashboard。
> `configs/cloudflare-tunnel.yml` 目前**沒有任何程序在讀**（內容也與實際不符：
> 它寫 hostname `cksurvey.cloudflareaccess.com` + catch-all 404，而實際服務的是 `missive.cksurvey.tw`）。
> 這是 L02「Dead Config」型態 —— 照著它排障會得到錯的結論。

中間件**註冊在 `main.py:632-684`**；FastAPI 後加=最外層，故**實際執行由外到內**：

| 執行序 | 中間件 | 職責 |
|---|---|---|
| 1（最外） | `RequestIdMiddleware` | request id 追蹤 |
| 2 | `PrometheusMiddleware` | 指標採集（排除 /health, /health/liveness, /health/readiness, /metrics）|
| 3 | `ApiDocsGuardMiddleware` | `/openapi.json`・`/api/docs` 僅限內網（2026-08-03；**獨立於 `TUNNEL_GUARD_ENABLED`**）|
| 4 | `TunnelGuardMiddleware` | 外網路由守衛（僅放行 `/api/{line,discord,public}/*` + `/api/health`）⚠️ **現況 `TUNNEL_GUARD_ENABLED=false`**，見下方註 |
| 5 | `CSRFMiddleware` | X-CSRF-Token 驗證（webhook 走 X-Service-Token 豁免）|
| 6 | `SecurityHeadersMiddleware` | 安全標頭 + **CSP（目前為 `Content-Security-Policy-Report-Only`，尚未強制）** |
| 7 | `LoggingMiddleware` | structlog 結構化日誌 |
| 8 | `GZipMiddleware` | 回應壓縮（minimum_size=1000）|
| 9（最內） | `CORSMiddleware` | CORS（最後註冊＝最內，符合 OWASP）|

> 2026-08-27 校正：原表只有 8 層、缺 `ApiDocsGuardMiddleware`，且沒有標出
> TunnelGuard 實際是關閉的、CSP 只是 Report-Only。**這三個都不是細節** ——
> 讀這張表的人會據此判斷「公網打得到什麼」，而少一層守衛、或把 Report-Only
> 當成已強制，得到的結論會相反（2026-08-21 那次外洩正是這個誤判的變形）。

### CSP 現況（2026-08-27 實測）

`Content-Security-Policy-Report-Only` 已上線，違規回報端點
`POST /api/security/csp-report`（`include_in_schema=False`，故不在 openapi 裡）實測回 204。

**它正在回報真實違規**，不是零：

```
directive=style-src-elem  blocked=https://accounts.google.com/gsi/style
document=https://missive.cksurvey.tw/entry
```

⇒ 照原樣轉強制會擋掉 Google 登入按鈕的樣式（`style-src` 原本缺
`https://accounts.google.com`，2026-08-27 已補）。**Report-Only 這個機制是有效的
—— 它抓到了靜態閱讀 CSP 抓不到的東西。**

違規現在同時累加 `csp_violations_total{directive,disposition}`（2026-08-27 加）。
在此之前它只寫一行 container log，沒有任何檢核、排程或儀表板在讀，
而 log 是 json-file 10m×3 ⇒ 重啟就沒了 —— 「觀察一段時間確認零違規再轉強制」
在結構上永遠收束不了。**轉強制的門檻現在可以用 metric 回答：
`increase(csp_violations_total[7d]) == 0`。**

> 認證流細節見 `docs/AUTH_FLOW_DIAGRAM.md`；CSRF 死結教訓見 `LESSONS_REGISTRY.md#L68`/`#L69`。

## LLM Provider 三層 Fallback（`backend/app/core/ai_connector.py`）

| 序 | Provider | 觸發條件 | 用途 |
|---|---|---|---|
| P1-1 | **Groq** `llama-3.3-70b` | `GROQ_API_KEY` 存在 + prompt < `GROQ_SKIP_PROMPT_CHARS`(10k) | 免費快速主力（429 不重試，直接 fallback）|
| P1-2 | **NVIDIA** nemotron-49b | Groq 429/逾時 + `NVIDIA_API_KEY` | 高品質雲端 |
| P2 | **Ollama** 本地 | 雲端全失敗 | 離線備援 |
| P3 | canned | 全部失敗 | 智慧預設回應 |

**Task 特化模型映射**（`TASK_MODEL_MAP`，SSOT；L64 修法）：`planning`/`vision`/`synthesis` → `gemma4:e2b`。
⚠️ 新增 task_type 若漏映射會落 `qwen2.5:7b`(p50 52.8s) → 35s synthesis budget 必超時（見 `cross-file-ssot-governance.md` TASK_MODEL_MAP 條目）。

## 錯誤合約化（ADR-0028）

所有 `except` 區塊必須同時滿足三件事：
1. `logger.error`（非 warning）+ `exc_info=True` + 結構化 context
2. 打 Prometheus metric counter（error_type label）
3. 默認 re-raise；吞錯必須註明理由

**Timeouts 統一合約**（`backend/app/core/timeouts.py`）：
- LLM synthesis 35s / Quality review 10s / RAG retrieval 8s / Tool execution 15s / DB query 5s

**3 靜態守護 pre-commit 執行**：
- `async_session_race_guard.py` — `asyncio.gather` + `ctx.db` 共用偵測
- `sse_headers_guard.py` — SSE endpoint 必須含 `Content-Encoding: identity`
- `schema_lazy_load_guard.py` — Pydantic schema 不得訪問 ORM lazy relationship

**Regression lock tests**：每一個 silent failure 修復必須附 `test_*_regression.py` 鎖定。

## 觀測棧（configs/grafana/ + configs/prometheus/）

> v6.8 重大重構：6 類 metric 集中於 `prometheus_middleware.get_metrics_endpoint()`
> per-scrape lazy populate（解 F26+F27 dual /metrics endpoint silent fail 事故）

| 類別 | 檔案 | 內容 |
|---|---|---|
| Dashboards | `configs/grafana/dashboards/ck-missive-http.json` | HTTP 流量 / 錯誤率 / P50/95/99 latency（6 panels） |
| Dashboards | `configs/grafana/dashboards/ck-missive-db-pool.json` | Pool 狀態 / 查詢 p95 / 慢查詢（6 panels） |
| Dashboards | `configs/grafana/dashboards/ck-missive-inference.json` | LLM completion / fallback / rate limit / shadow baseline（7 panels） |
| Dashboards | `configs/grafana/dashboards/ck-missive-overview.json` | 系統總覽 |
| Dashboards | 🆕 `configs/grafana/dashboards/ck-missive-v7-integration.json` | **v6.8 M1 v7.0 4 指標**（channel diversity / reference density / SOUL drift / provider gap）+ 7 天趨勢（6 panels） |
| Alert rules | `configs/prometheus/alerts.yml` | **5 groups × 17 rules**（v6.8 加 v7_integration_quality 5 rules） |
| Promtail | `configs/grafana/promtail-pm2.yml` v2 | 5 scrape targets（error / out / app / admin_push / watchdog） |
| 部署指南 | `configs/grafana/README.md` | CK_DigitalTunnel 端 provisioning 步驟 |

### Prometheus metric 集中清單（v6.8 後）

| 類別 | 來源檔 | 範例 metric |
|---|---|---|
| HTTP / middleware | `prometheus_middleware.py` | `http_requests_total` / `http_request_duration_seconds` |
| 系統 5 metric (F27) | `prometheus_middleware.py` | `ck_missive_app_info` / `ck_missive_up` / `ck_missive_db_healthy` / `ck_missive_memory_rss_bytes` / `ck_missive_cpu_percent` |
| Memory Wiki 7 gauge + 4 counter | `memory_wiki_metrics.py` | `memory_diary_days_total` / `memory_proposals_pending` / ... |
| **v7.0 5 gauge (M1+M4)** | `memory_wiki_metrics.py` | `v7_channel_diversity` / `v7_reference_density_diary_pct` / `v7_reference_density_critique_pct` / `v7_soul_drift_lines` / `v7_provider_fidelity_gap_pct` |
| **F19 fact_check counter** | `memory_wiki_metrics.py` | `agent_synthesis_unsourced_numbers_total` |
| KG stats | `kg_stats_metrics.py` | `kg_entities_total` / ... |
| DB pool / query | `db_pool_metrics.py` / `db_query_metrics.py` | pool active / query duration histogram |
| Inference provider | `inference_provider_metrics.py` | completion / fallback counter |
| **Shadow baseline 5 gauge (F26)** | `shadow_baseline_metrics.py` | `shadow_baseline_rows_total` / `shadow_baseline_latency_p95_ms` / `shadow_baseline_success_ratio` / `shadow_baseline_call_total` / `shadow_baseline_tool_use_count` |

## 後端模型結構

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

## 後端 Service 層結構

### Wave 1-8 後 12 Bounded Contexts 結構（v5.10.2）

**重要**：73 個原頂層散戶已遷入 12 bounded context 子包（73 stub 維持向後相容，預計 2026-Q3 移除）。
詳見 `docs/architecture/SERVICE_CONTEXT_MAP.md` + `docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md` v2.2。

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

**Service Entropy 軌跡**：29.4% (Wave 0) → 23.5% (Wave 8) → ~12% (v6.0 stub 移除後預估 GREEN)

## 後端 API 結構

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

## 後端 Repository 層結構 (34 類別)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

