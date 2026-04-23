# ADR-0028：錯誤合約化與 Silent Failure 政策

> **狀態**：accepted
> **日期**：2026-04-22
> **決策者**：專案 Owner（v5.7.1/v5.8.1 連續覆盤觸發）
> **關聯**：ADR-0019（structlog）、ADR-0021（asyncpg concurrent session）、ADR-0022（Memory Wiki）、CHANGELOG v5.9.0

---

## 背景

v5.7.1（2026-04-20）與 v5.8.1（2026-04-22）兩個連續覆盤版本合計修復 **7 層 silent failure**：

| 版本 | 層級 | 位置 | 根因類型 |
|---|---|---|---|
| v5.7.1 | 1 | `_flush_trace_lightweight` | request 結束 session dispose 後 `create_task` 靜默失敗 |
| v5.7.1 | 2 | `agent_trace.to_db_dict` | varchar(20) 被長字串截斷 → `StringDataRightTruncationError` |
| v5.7.1 | 3 | `run_with_fresh_session` 雙 commit | `This transaction is closed` |
| v5.7.1 | 4 | `agent_learning_repository.update_graduation` | naive datetime 寫入 UTC-aware 欄位 |
| v5.7.1 | 5 | `capability_profile_cached` db=None | cache-only path crash |
| v5.7.1 | 6 | `post_processing` 3 處 `ctx.db` race | fresh session 遺漏 |
| v5.7.1 | 7 | orchestrator duplicate trace flush | 兩條主路徑重複 flush |
| v5.8.1 | A | `UserResponse.model_validate` | lazy-load relationship `aliases` → MissingGreenlet |
| v5.8.1 | B | SSE `Content-Encoding` | GZip middleware 覆蓋 SSE stream |
| v5.8.1 | C | synthesis/quality-review timeout 過長 | 60s silent gap |
| v5.8.1 | D | admin push 連續失敗 | 無 counter、無告警 |

**共同模式**：

1. **失敗路徑只 log.warning 不 raise / 不 metric** → error 完全隱形
2. **邊界不明**：schema ↔ ORM、session ↔ request lifecycle、stream ↔ middleware
3. **timeout 過長**：silent gap 比明顯失敗更難發現
4. **缺失 regression guard**：改完就改完，沒寫 lock test，下次改相同區域又壞

單元測試數量（3385+）並不能防止這類問題。**問題不在「測試量」，在「error path 沒有明確合約」**。

---

## 決策

### 原則 1 — Silent Failure 零容忍

所有 `except Exception` / `except <Specific>` 區塊必須同時滿足三件事：

```python
# ✅ 正確合約
try:
    await risky_operation()
except SpecificError as e:
    logger.error(                              # 1) 用 error（非 warning）
        "operation_failed",
        operation="risky_operation",
        error=str(e),
        exc_info=True,
    )
    ERROR_COUNTER.labels(                      # 2) 打 Prometheus metric
        operation="risky_operation",
        error_type=type(e).__name__,
    ).inc()
    raise                                      # 3) 默認 re-raise；吞掉必須註明理由
```

**例外清單（允許吞錯但仍需 log.error + metric）**：
- Fire-and-forget 的 `asyncio.create_task` 尾端（須加 wrapper 把 error counter 打出來）
- 背景 scheduler job（失敗不能阻塞下次排程，但必須入 `scheduler_job_failures_total`）
- 通知 / 推播發送（失敗不能阻塞主業務，但必須入 `admin_push_failures_total`）

**`logger.warning` 只在業務正常路徑使用**（e.g. validation soft fail、rate limit hit），不得用於技術異常。

### 原則 2 — 明確 timeout 合約

| 操作類型 | timeout 上限 | 理由 |
|---|---|---|
| LLM synthesis | 35s | 超過 → 換 provider fallback |
| Quality review | 10s | 是 nice-to-have，不阻塞主輸出 |
| RAG retrieval | 8s | 超過 → 降級為 keyword search |
| Tool execution | 15s | 超過 → 回 partial result + error |
| DB query（單筆） | 5s | 超過 → kill query，alert slow_query_total |
| HTTP → LLM | 30s | 對應 LLM synthesis 上限 |

**實作要求**：
- 每個 timeout 必須是具名常數（禁止裸 `asyncio.wait_for(..., timeout=60)`）
- 常數集中在 `backend/app/core/timeouts.py`
- 超時後必須 log.error + counter `operation_timeout_total{operation=...}`

### 原則 3 — 邊界類型守護（Static Guards）

擴展 `scripts/checks/schema_lazy_load_guard.py` 的靜態檢查思路至三類守護：

| 守護腳本 | 目標 | 觸發場景 |
|---|---|---|
| `schema_lazy_load_guard.py`（已有） | schema 不得 `getattr(orm, <relationship>)` | v5.8.1 事故 A |
| `async_session_race_guard.py`（**本 ADR 新增**） | `asyncio.gather` 內 2+ task 不得共用 `ctx.db`/`self.db` | v5.7.1 事故 6 + ADR-0021 未竟工作 |
| `sse_headers_guard.py`（**本 ADR 新增**） | SSE endpoint 必須顯式設 `Content-Encoding: identity` | v5.8.1 事故 B |

這三個守護在 pre-commit 與 CI 均執行，靜態攔截，不依賴執行時覆蓋。

### 原則 4 — Regression Lock Test 強制

每一個 silent failure 修復必須附帶一個 **regression lock test**（命名 `test_<feature>_regression.py` 或 `test_<feature>_silent_failure.py`），鎖定「不能再犯」的行為。

範例（v5.7.1 遺留）：
- `test_trace_flush_regression.py` — 3 層 silent failure 防退回
- `test_schema_no_lazy_load.py` — UserResponse 不再 getattr aliases
- `test_sse_content_encoding.py` — SSE header 必須 identity

### 原則 5 — Observability 三指標合約

所有「會失敗」的 code path 必須同時 emit：

1. **Counter**：失敗次數（label: operation, error_type）
2. **Structured log**：`logger.error` with exc_info + 關鍵 context
3. **Trace tag**（若在 trace 範圍內）：`span.set_attribute("error", True)`

Alert 規則由觀測棧負責，不在本 ADR。

---

## 後果

### 正面

1. **Silent failure 升級為一等公民議題**，不再 case-by-case 修
2. **新增 3 個靜態守護**，攔截 v5.7.1/v5.8.1 三類事故的回歸風險
3. **timeout 統一合約**，消除「60s silent gap」這類延遲型故障
4. **Observability 三指標強制綁定**，配合 ADR-0019 的 structlog JSON 日誌、Prometheus /metrics 形成完整鏈路
5. **Regression lock test 文化**，累積「不能再犯」的知識資產

### 負面

1. **短期 PR 變大**：新增 catch 同時要寫 metric + log + raise + regression test，單次修復成本↑30%
2. **靜態守護誤殺**：已知 false positive（例如 getattr() 非 schema 的合法用法），需維護白名單
3. **timeout 常數需要 code review**：`timeouts.py` 變成 hot-spot，每次調整需 ADR 或 CHANGELOG 記錄
4. **既有 warning 清理是長工程**：估計 50+ 處 `except Exception: logger.warning` 需漸進升級，列入 v5.9 ~ v6.0 技術債

### 中性

- ADR-0021 的「未來工作：gather + db= Lint 規則」本次併入實作
- ADR-0019 的 structlog 已提供 `logger.error` + exc_info 基礎設施，本 ADR 無需新增日誌層

---

## 執行步驟（落地順序）

| 階段 | 項目 | 驗收 |
|---|---|---|
| **v5.9.0** | `scripts/checks/async_session_race_guard.py` | pre-commit 與 CI 均執行，可掃出現有 18 處 gather |
| **v5.9.0** | `scripts/checks/sse_headers_guard.py` | 檢出所有 SSE endpoint 確實設 identity |
| **v5.9.0** | `backend/app/core/timeouts.py` | synthesis=35s / quality=10s / rag=8s / tool=15s 等常數 |
| **v5.9.0** | `backend/app/core/error_metrics.py` | 統一 `ERROR_COUNTER` / `TIMEOUT_COUNTER` 匯出 |
| **v5.9.0** | `docs/guides/error-contract.md` | 開發者手冊，含「如何寫合規 except」範例 |
| **v5.9.1** | 既有 `except Exception: logger.warning` 漸進升級 | 每週至少 5 處，至 v6.0 清零 |
| **v5.10.0** | 把三個守護接入 `scripts/checks/verify_architecture.py` | 架構驗證 +3 項 |

---

## 驗證

```bash
# 靜態守護
python scripts/checks/async_session_race_guard.py        # 應回報 18+ gather 位置
python scripts/checks/sse_headers_guard.py               # 應回報所有 SSE endpoint
python scripts/checks/schema_lazy_load_guard.py          # 既有

# Regression lock tests
cd backend && python -m pytest tests/regression/ -v

# Metric 合約（啟動後）
curl -s http://localhost:8001/metrics | grep -E "(error_total|timeout_total|admin_push_failures)"
```

---

## 參照

- ADR-0019：structlog JSON 日誌（提供 `logger.error(exc_info=True)` 基礎設施）
- ADR-0021：asyncpg 並行 session（本 ADR 的「未來工作」承接人）
- ADR-0022 覆盤補記：Memory Wiki 四層 silent failure 首次完整揭露
- `scripts/checks/schema_lazy_load_guard.py`：靜態守護 pattern 範本

## 狀態記錄

- 2026-04-22：accepted，v5.9.0 落地
- 本 ADR 取代 ADR-0021 「未來工作」區段（歸併本文）
