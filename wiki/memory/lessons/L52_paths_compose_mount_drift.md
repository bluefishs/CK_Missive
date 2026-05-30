---
title: L52 — paths.py PROJECT_ROOT vs docker-compose mount target drift silent dormant
type: lesson
date: 2026-05-30
fqid: CK_Missive#L52
family: cross-file-ssot
related: [L41, L43, L44, L45, L48, L49, L51]
---

# L52 — paths.py vs compose mount drift

> **日期**：2026-05-30（v6.12 #2 補完 + shadow_baseline 真活恢復）
> **觸發**：fitness step 58 agent_query_starvation RED 持續，發現 cron synthetic_baseline silent return
> **規模**：1 commit / 2 file fix（compose mount target + token fallback）
> **dormant 時長**：~5 小時（同日 paths.py 改完 → shadow_baseline 仍 n=0）

---

## 真因雙層

### #1 docker-compose mount target 跟 paths.py 漂移

**Step 1（v6.12 上午）**：
為解 optimization_pipeline silent dormant，加 `CK_PROJECT_ROOT=/app` env override，paths.py 計算改為：
```python
_env_root = os.getenv("CK_PROJECT_ROOT")
PROJECT_ROOT = Path(_env_root).resolve() if _env_root else Path(__file__).resolve().parents[3]
```

**Step 2（同日下午）**：
撞到 cron `synthetic_baseline_inject_job` 找 `PROJECT_ROOT / "scripts" / "checks" / ...`：
```python
# scheduler.py line 1227
script = project_root / "scripts" / "checks" / "synthetic-baseline-inject.py"
# = /app/scripts/checks/synthetic-baseline-inject.py
```

**Step 3（漏接）**：
但 `docker-compose.production.yml:250` mount target 還是舊：
```yaml
- ./scripts:/scripts:ro   # ← 對齊舊 PROJECT_ROOT=/
```

→ `/app/scripts/checks/...` 不存在
→ silent `if not script.exists(): return` 中斷
→ shadow_baseline 24h n=0
→ fitness step 58 agent_query_starvation RED

### #2 synthetic-baseline-inject token 讀法

container 內 cwd=/app 沒 `.env` 檔（host-only），但 env vars 全注入 container。

原 token 讀法只走 .env file → 永遠 token=空 → 401 Unauthorized → 整年 silent fail。

修法：三層 fallback 順序
1. `--token` CLI arg
2. `os.environ["MCP_SERVICE_TOKEN"]` ← v6.12 補
3. `.env` file（host dev mode）

---

## 為何 L41/L43/L44/L45 cross-file SSOT 規範沒擋住

L41-L45 family 規範焦點：
- L41 跨 repo secret
- L43 跨 compose volume
- L44 跨 domain auth state
- L45 compose vs Dockerfile healthcheck

但**沒涵蓋「container 內運行時 path SSOT」**：
- paths.py 計算的 absolute path 是「contract」
- compose mount target 是「contract impl」
- 兩處同 contract 但宣告位置不同 → 漂移

L52 = L4x family 第六案，補規範缺口。

---

## 治理立法（cross-file-ssot-governance §1 表格新增 entry）

| 資源類型 | 推薦 SSOT 位置 | 範例 |
|---|---|---|
| **Container path (paths.py)** | **`backend/app/core/paths.py` PROJECT_ROOT** | **同步檢查所有 docker-compose.* 的 mount target prefix** |

§2 audit script 表格新增：

| 資源 | Audit Script | Fitness Step |
|---|---|---|
| **paths.py vs compose mount** | **`paths_compose_mount_audit.py`** | **step 62（本批新增）** |

---

## Fitness step 62 — paths.py vs compose mount consistency audit

`scripts/checks/paths_compose_mount_audit.py`：
- 抓 `backend/app/core/paths.py` 內 PROJECT_ROOT 算法
- 抓 docker-compose.*.yml 所有 host:container mount line
- 對比 container target prefix 是否對齊 PROJECT_ROOT
- 不對齊 → YELLOW (warn)
- container target 在 PROJECT_ROOT 外但被 cron/service 用 → RED

設計：靜態分析，不需要 backend running。

---

## 修法資產

| 檔案 | 修法 | commit |
|---|---|---|
| `docker-compose.production.yml:250` | `./scripts:/scripts:ro` → `./scripts:/app/scripts:ro` | `8842e8a2` |
| `scripts/checks/synthetic-baseline-inject.py` | token 三層 fallback | 同上 |
| `scripts/checks/paths_compose_mount_audit.py` | fitness step 62 | （本批新增）|
| `.claude/rules/cross-file-ssot-governance.md` | §1 加 entry / §2 加 audit | （本批新增）|

---

## 元洞察

L52 是「修法本身製造下一個 SSOT 漂移」的 meta-case：
- 為解 silent dormant A（pipeline 寫 /wiki 失敗）改 paths.py
- 但 paths.py 改完沒 grep 找所有 readers（含 compose mount）
- → 製造 silent dormant B（synthetic_baseline 找 /app/scripts 失敗）

防禦：
1. **任何 SSOT 改動 grep 全 codebase** — 不只程式碼，也含 yaml / dockerfile
2. **fitness step 自動偵測** — 規範存在但不靠人記
3. **paths.py 內加 docstring 警示** — 「若改 PROJECT_ROOT 同步檢查所有 compose mount」

---

> **核心精神**：修一處 SSOT 之前先想「誰讀這個 contract」。
> 否則修法本身就是下一個 silent dormant 的源頭。
