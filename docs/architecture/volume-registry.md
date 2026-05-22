# CK_Missive Docker Volume Registry

> **規範**: [[ADR CK_Missive#0044]] Single SSOT for Docker Volumes
> **Audit 工具**: `scripts/checks/docker_compose_volume_consistency.py` (fitness step 38)
> **最後更新**: 2026-05-22（L43 cleanup 後）

---

## Active Volumes（compose 宣告中）

### 業務資料層（必須備份）

| Physical Name | 用途 | Mount Target | 宣告於 (compose) | Alias | Size (5/22) | External |
|---|---|---|---|---|---|---|
| `ck_missive_postgres_dev_data` | **主資料庫**（75 tables / 1788 docs / 24061 KG）| `/var/lib/postgresql/data` | production / dev / infra | `postgres_data` (prod) / `postgres_dev_data` (dev/infra) | 394 MB | ✅ prod only |
| `ck_missive_redis_data` | Cache + session + queue | `/data` | production / dev / infra | `redis_data` (prod) / `redis_dev_data` (dev/infra) | 14 MB | ✅ dev/infra |

**SSOT 注意**：dev/infra 的 alias 名雖叫 `*_dev_data`（命名歷史包袱），但 `name:` 已對齊 production
的 `ck_missive_postgres_dev_data` / `ck_missive_redis_data`。fitness step 38 看 `name:` 判定 ✅。

### 推理 / AI 模型快取（可重建但重 download 慢）

| Physical Name | 用途 | Mount Target | 宣告於 (compose) | Alias | Size | External |
|---|---|---|---|---|---|---|
| `ck_missive_ollama_dev_data` | Ollama 模型（gemma4 8B / nomic-embed）| `/root/.ollama` | dev / infra | `ollama_dev_data` | 9.8 GB | ❌ |
| `ck_missive_vllm_dev_cache` | vLLM huggingface cache | `/root/.cache/huggingface` | infra | `vllm_dev_cache` | 19.4 GB | ❌ |

**注意**：兩者使用 `${COMPOSE_PROJECT_NAME}_*` env var 展開（依賴 .env / repo 目錄名小寫）。
依 ADR-0044 §2 應遷移為顯式 `name:` 避免大小寫變體 ghost（v6.11 W2 一併修）。

---

## Orphan / Historical / Pending Volumes

### 已 cleanup（2026-05-22）

| Physical Name | Size | 性質 | 處置 | 留底位置 | MD5 |
|---|---|---|---|---|---|
| `CK_Missive_postgres_data` | 63.1 MB | 早期專案大寫前綴遺留（2025-09-10）| **刪除 5/22** | `backup/ghost_volume_cleanup_20260522/CK_Missive_postgres_data_20260522.tar.gz` (7.4 MB) | `63516ebe22031bbada912b3e08d1cb67` |
| `ck_missive_redis_dev_data` | 512 KB | 5/21 切 production 前 dev cache 殘留 | **刪除 5/22** | `backup/ghost_volume_cleanup_20260522/ck_missive_redis_dev_data_20260522.tar.gz` (244 KB) | `94bb94265edd69acc79d53db8fbda19e` |

### Incident 證物（保留中）

| Physical Name | Size | 性質 | 處置建議 | 留底位置 |
|---|---|---|---|---|
| `ck_missive_postgres_data` (小寫) | 63.6 MB | **L43 5/21 incident 證物**（被掛錯時建的 17 tables 空殼 postgres）| 保留至 2026-06-21（30 天）後可刪 — 5/21 已 dump | `backup/incident_20260521_volume_mount_drift/wrong_volume_ck_missive_postgres_data.dump` + NAS |

### Pending orphan（v6.11 W1 評估）

fitness step 38 揭發但未確認是否真 orphan：

| Physical Name | Size | Last mtime | Pending 評估 |
|---|---|---|---|
| `ck_missive_backend_logs_dev` | 62.9 MB | 2025-10-08 | 早期 compose 移除的 service 殘留？需查 git log compose |
| `ck_missive_backend_uploads_dev` | 4 KB | 2025-12-26 | 同上 — 但 4KB 表示無 uploads，可清 |
| `ck_missive_frontend_logs_dev` | 4 KB | 2025-12-26 | 同上 |
| `ck_missive_nim_dev_cache` | 5.8 GB | 2026-03-19 | NIM inference profile 殘留（v5.x 早期測過 NVIDIA NIM）| 

**評估方法**：
1. `git log -p docker-compose.dev.yml | grep -A2 backend_logs_dev` 找首次/末次 reference
2. 確認當前無 service mount → cleanup（tar + delete）
3. 若 nim_dev_cache 已無 service 引用 → 6 GB 可回收

---

## 命名 SSOT 規則（ADR-0044）

### 命名 pattern

```
ck_<repo-key>_<purpose>_<env>?

範例：
  ck_missive_postgres_dev_data  ← 主庫（dev 後綴歷史包袱保留）
  ck_missive_redis_data         ← cache
  ck_missive_ollama_dev_data    ← 推理模型
```

### 禁止
- ❌ 大小寫變體（`CK_Missive_*` vs `ck_missive_*` 同邏輯 → ghost）
- ❌ 同邏輯 volume 跨 compose 不對齊 `name:`（L43 反模式）
- ❌ 依賴 `${COMPOSE_PROJECT_NAME}` 自動生成（會跟著 env / repo 目錄名變）

### 強制
- ✅ 顯式 `name:` 宣告
- ✅ 跨 compose 同邏輯一律相同 `name:`
- ✅ Production compose `external: true`（防 down 時誤殺）
- ✅ 業務資料 volume 必須 fitness step 38 GREEN（drift 即 RED）

---

## 變更 SOP（新增 / 改名 / 刪除 volume）

### 新增

1. 選定 SSOT name（遵循上述 pattern）
2. 所有 compose 統一加 `name: <physical>`
3. 跑 `python scripts/checks/docker_compose_volume_consistency.py` 應 GREEN
4. 更新本 registry

### 改名（高風險）

1. **不要直接改 `name:`** — 會建新 volume 然後舊資料變 orphan
2. 走 migration: 新 volume create → `pg_dump | pg_restore`（postgres）或 redis MIGRATE
3. 切換 compose 後跑 step 38
4. 30 天觀察期後刪舊 volume（仿本 registry §Incident 證物 SOP）

### 刪除（backup-before-delete 強制，ADR-0044 §4）

```bash
# 1. 留底
mkdir -p backup/ghost_volume_cleanup_$(date +%Y%m%d)
docker run --rm -v <name>:/d:ro \
  -v "$(pwd)/backup/ghost_volume_cleanup_$(date +%Y%m%d):/out" \
  alpine sh -c "tar czf /out/<name>_$(date +%Y%m%d).tar.gz -C / d && md5sum /out/<name>_$(date +%Y%m%d).tar.gz"

# 2. 寫 README.md（理由 / 還原指令 / MD5）

# 3. 刪除
docker volume rm <name>

# 4. 更新本 registry
```

---

## 跨 repo 推廣（install-template-to.sh）

本 registry 為 CK_Missive 本地，但 ADR-0044 模式可推廣：

| Repo | 預期 volumes | 建議命名 |
|---|---|---|
| CK_lvrland_Webmap | postgres / redis | `ck_lvrland_postgres_data` / `ck_lvrland_redis_data` |
| CK_PileMgmt | postgres / redis | `ck_pile_postgres_data` / `ck_pile_redis_data` |
| CK_AaaP | observability stack | `ck_aaap_loki_data` / `ck_aaap_prometheus_data` |

v6.11 W1 由 `install-template-to.sh` 加 ADR-0044 範本部署。

---

## 7 天追蹤（ADR-0044 §D）

- [ ] 2026-05-29: 跑 step 38 應 GREEN（0 drift + ≤1 incident 證物 orphan）
- [ ] 2026-06-21: ck_missive_postgres_data 小寫 incident 證物可刪
- [ ] v6.11 W1: 4 dev orphans cleanup（backend_logs_dev / uploads / frontend_logs / nim_dev_cache）
- [ ] v6.11 W2: ollama / vllm 改顯式 `name:`（去 `${COMPOSE_PROJECT_NAME}` 依賴）
