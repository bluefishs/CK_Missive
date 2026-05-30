---
title: L57 — BACKEND_DIR/logs vs docker-compose mount target drift (L52 family 第七案 sub-path SSOT)
type: lesson
date: 2026-05-30
fqid: CK_Missive#L57
family: cross-file-ssot
related: [L52, L43, L41, L51]
---

# L57 — sub-path SSOT 治理 (L52 family 第七案)

> **日期**：2026-05-30
> **觸發**：W1 修 Hermes baseline 真因 #3 深入 → 揭發 path drift
> **dormant**：5/21 → 5/30 = **9 天 silent**
> **修法**：commit `5ca1d720`

---

## 真因鏈

### 表面 ✗ 1 個 bug

shadow_baseline_rows_total 卡在 0-2，cron 跑不累積。

### 深挖揭發 4 層 silent 疊加

| 層 | 真因 | 揭發方法 |
|---|---|---|
| #1 | populate Gauge 重複註冊 | `metrics_populate_errors_total` counter |
| #2 | cron `node` missing | `scheduler_job_last_run_age_seconds` |
| #3 | shadow_logger 寫入 silent | SQLite 直查 |
| **#4** | **BACKEND_DIR/logs vs mount /app/logs path drift** | **force await + write done + rows=0** |

### #4 真因 細節

```python
# shadow_logger.py / shadow_baseline_metrics.py 計算:
from app.core.paths import BACKEND_DIR
_DB_PATH = BACKEND_DIR / "logs" / "shadow_trace.db"
# BACKEND_DIR = PROJECT_ROOT/backend (container 內 = /app/backend/)
# → _DB_PATH = /app/backend/logs/shadow_trace.db
```

```yaml
# docker-compose.production.yml mount:
- ./backend/logs:/app/logs   # ← 不是 /app/backend/logs
```

→ shadow_logger 寫到 `/app/backend/logs/shadow_trace.db`（container 內 ephemeral 新 file）
→ host backend/logs/shadow_trace.db 5/21 後 0 新寫入
→ shadow_baseline metric 從 ephemeral file 讀，每次 backend restart 重置

---

## L52 family 擴至 7 案

| Case | 主題 | 修法 commit |
|---|---|---|
| L41 | JWT secret 跨 repo drift | `bb1ca4ec` |
| L43 | volume mount drift | `097cdf68` |
| L44 | SSO session lock 跨 subdomain | ck-sso-js v2.0 |
| L45 | compose vs Dockerfile healthcheck | `505ee9d2` |
| L51 | docker-compose env 注入缺漏 | `efa895d9` |
| L52 | paths.py vs compose mount | `4bd27997` |
| **L57** ★ | **BACKEND_DIR/logs vs mount sub-path** | `5ca1d720` |

L52 的「Container PROJECT_ROOT path」SSOT 概念延伸至 **sub-path（BACKEND_DIR / WIKI_DIR / SCRIPTS_DIR 等）**。

---

## 治理立法升級

### cross-file-ssot-governance.md §1 補

| 資源類型 | 推薦 SSOT 位置 | 範例 |
|---|---|---|
| **Container sub-path (BACKEND_DIR/logs 等)** | **paths.py + docker-compose mount 對齊** | **`/app/logs` 必須 = paths.py 計算的 `BACKEND_DIR/logs`** |

### 新 fitness step (待補)

`paths_sub_path_compose_mount_audit.py`:
- 抓 paths.py 所有 sub-path 變數 (LOGS_DIR / WIKI_DIR / SCRIPTS_DIR 等)
- 對比 docker-compose mount target
- 不對齊 → YELLOW/RED

### 修法 SOP

**任何 paths.py 變數改動 grep 3 處**：
1. paths.py 自身（SSOT）
2. docker-compose.*.yml mount target
3. 所有 import `from app.core.paths import ...` 的 module

---

## 元洞察 — 修法揭發下一層

「修 #1 Gauge 重複」表面已修，但 baseline 還 2.0 不漲：
- 揭發 #3 shadow_logger 沒寫
- 揭發 #4 path drift

**3 重 silent → 4 重 silent**（修一層才見下一層）。

對齊 L43 教訓「5 重 silent fallback 疊加」+ L52「修法本身揭發下一個 silent」。

每修一層的價值：
1. **解一層 silent** → 業務真活恢復
2. **揭發下一層** → 治理價值大於修法

---

## 驗證真活

修法後：
- ✅ `_DB_PATH = /app/logs/shadow_trace.db` 對齊 mount
- ✅ 1095 historical rows 可讀
- ✅ 5 synthetic query 跑後 → 1097 rows (+2)
- ✅ `shadow_baseline_rows_total{24h}=2` metric 對齊 sqlite

下次 cron 14:00/20:00 自然累積，明天 09:00 後應 30+ rows。

---

## 修法資產

| 檔案 | 行為 | commit |
|---|---|---|
| `backend/app/core/shadow_baseline_metrics.py` | 用 `CK_LOGS_DIR` env 對齊 | `5ca1d720` |
| `backend/app/services/ai/agent/shadow_logger.py` | 同上 | `5ca1d720` |
| `wiki/memory/lessons/L57_*.md` | NEW lesson (本批) | （本批）|

---

> **核心精神**：path SSOT 不只在 PROJECT_ROOT，也在每個 sub-path。
> 修一處 silent 揭發下一層，是治理進化的真實循環。
> 對齊 v6.12 第 1 句立法「抽象不是錯，建後不 audit 才是」+ L52 「修法本身揭發 silent」。
