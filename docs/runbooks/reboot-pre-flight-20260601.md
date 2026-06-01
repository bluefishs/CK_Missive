# 重啟前 SOP + 重啟後驗收清單 — 2026-06-01

> Owner 訴求：「先更新系統相關紀錄與設定並確認容器版本完整與正確性，準備重啟電腦」
> 對齊：reboot-acceptance-checklist.md / L43 volume drift 防範 / OA-3 PM2 廢除 SOP

---

## 0. 重啟前快照（2026-06-01 09:50 真實實測）

### Git 狀態
- 本日 commits: **36**
- 跨日 commits (5/30-6/1): **82**
- 本地與 origin: **全同步**（git log origin/main..HEAD 空）
- 無未追蹤關鍵檔（只有 cron 自動產出 integration-health json）

### Docker 容器狀態
| Container | Image | Status | RestartCount |
|---|---|---|---|
| ck_missive_backend | ck-missive-backend:production (bd9887465a3a) | healthy / Up 27min | 0 |
| ck_missive_frontend | ck-missive-frontend:production | healthy / Up 3d | 0 |
| ck_missive_postgres | pgvector/pgvector:0.8.0-pg15 | healthy / Up 3d | 0 |
| ck_missive_redis | redis:7-alpine | healthy / Up 3d | 0 |
| 4 cloudflared | cloudflare/cloudflared:2026.5.0 (pinned ✓) | all healthy | - |

### Critical Files md5 比對（host = container）
| 檔案 | md5 | 狀態 |
|---|---|---|
| `kunge.py` | `3c8bcb1e...` | ✅ host = container |
| `crystal_applier.py` | `56eef1c1...` | ✅ host = container |
| `agent_orchestrator.py` | `1d98ca1b...` | ✅ host = container |
| `paths.py` | `69cf58be...` | ✅ host = container |

### DB Volume 對齊（避 L43 重演）
- ck_missive_postgres mounts: **`ck_missive_postgres_dev_data`** ✅（**非** `ck_missive_postgres_data` ghost）
- documents: **1,809**
- canonical_entities: **26,152**
- agent_query_traces: **1,025**

### Integration E2E（第 7 次連跑）
```
✅ chain_1_missive_health (documents 1809 / entities 26152)
✅ chain_2_kunge_snapshot (lessons 16 / patterns 10 / proposals 5 / pending 2)
✅ chain_3_tools_manifest (kunge_snapshot 公開)
✅ chain_4_hermes_container (host.docker.internal:8642 status 200)
✅ chain_5_bridge_skill
OVERALL: ✅ ALL PASS
```

### v6.13 真活訊號
- crystals: 0 → **2** (3 soul proposal applied)
- pending_proposals: 5 → **2**
- lessons (含 L62/L63): **16**
- DB agent_learnings: **837**
- v6.13 6 cron 全註冊（02:00/02:05/02:15/02:20/02:30/02:45）

---

## 1. 重啟前 Pre-Flight 4 步（已執行）

- [x] **Step 1** — git status + log 確認全 push origin ✅
- [x] **Step 2** — docker ps + health + image 版本確認 ✅
- [x] **Step 3** — host vs container md5 比對 4 critical 檔 ✅
- [x] **Step 4** — DB volume + business data row count 確認 ✅

---

## 2. 重啟前已紀錄項

- [x] `wiki/log.md` 加入 v6.13 重啟前快照（5 大成果 + 4 RED + 容器狀態）
- [x] `docs/runbooks/reboot-pre-flight-20260601.md`（本檔）
- [x] L62 + L63 universal lesson 入 wiki/memory/lessons/universal/
- [x] V6_13_REAL_VERIFICATION_REPORT_20260531.md 完整實證

---

## 3. 重啟後驗收清單（5 步 SOP）

### Test 1：基礎服務 boot
```bash
# 1.1 docker compose 自動啟動
docker compose -f docker-compose.production.yml ps
# 期待 4 service all Up (healthy)

# 1.2 backend 健康
curl -s http://localhost:8001/health | grep status
# 期待 healthy / documents>=1809 / entities>=26152
```

### Test 2：cron 6 個 v6.13 全註冊
```bash
docker logs --since 5m ck_missive_backend 2>&1 | grep "已添加.*v6.13" | wc -l
# 期待 6 (3 個 daily + 3 個 weekly)
```

### Test 3：Integration E2E 全綠
```bash
docker exec ck_missive_backend python /app/scripts/checks/integration_e2e_validation.py
# 期待 OVERALL: ✅ ALL PASS
```

### Test 4：kunge_snapshot real
```bash
TOKEN=$(grep MCP_SERVICE_TOKEN .env | cut -d= -f2 | tr -d '"')
curl -s -X POST http://localhost:8001/api/ai/kunge/snapshot \
  -H "X-Service-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"window_days": 7}' | python -c "import json,sys; d=json.loads(sys.stdin.read()); print('crystals:',d['counts']['crystals'])"
# 期待 crystals: 2
```

### Test 5：business endpoint smoke（L49 SOP）
```bash
# admin login + backup status + files download + agent query
# (依 scripts/checks/admin_backup_smoke_test.py)
docker exec ck_missive_backend python /app/scripts/checks/admin_backup_smoke_test.py
# 期待 10/10 PASS
```

---

## 4. 重啟後若發現異常 SOP

### 4.1 L43 防範（DB 空殼 ghost volume）
```bash
# 確認 postgres 指向 dev_data 不是 ghost
docker inspect ck_missive_postgres --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}'
# 期待含 "ck_missive_postgres_dev_data"

# 業務量檢查
docker exec ck_missive_postgres psql -U ck_user -d ck_documents \
  -c "SELECT COUNT(*) FROM documents;"
# 期待 >= 1809
```

### 4.2 L51 防範（container image vs host code drift）
```bash
# 比對 4 critical 檔 md5
for f in kunge.py services/memory/crystal_applier.py services/ai/agent/agent_orchestrator.py core/paths.py; do
  H=$(md5sum backend/app/$f | cut -d' ' -f1)
  C=$(docker exec ck_missive_backend md5sum /app/app/$f | cut -d' ' -f1)
  [ "$H" = "$C" ] && echo "✅ $f" || echo "❌ $f drift!"
done
```

### 4.3 cron silent dormant 防範
```bash
# 1h 內 cron 真實 fire 紀錄
docker exec ck_missive_backend tail -20 /app/logs/cron_events.jsonl
```

---

## 5. 仍 RED 待 owner 決策（重啟後不影響）

| 項目 | 狀態 | 待 |
|---|---|---|
| LINE routing 偏向 search_documents | 揭發 4 真因 | v6.14 intent_rules 補 |
| Groq 429 rate limit | 30min 6 次 | v6.14 quota 升級 |
| shadow_baseline p95=71.2s | 量化暴露 | Hermes 6/28 重評 |
| 2 LOW crystal-intent 設計性 no-op | pattern 空 | v6.14 pattern_extractor 升級 |

---

## 6. 本批 v6.13 完整交付清單

### 新建 (本批 36 commits)
- `backend/app/api/endpoints/ai/kunge.py` (kunge_snapshot endpoint)
- `scripts/checks/integration_e2e_validation.py` (5 鏈 E2E)
- `scripts/checks/proposal_aging_alert.py` (學習閉環 aging)
- `scripts/checks/weekly_evolution_generator.py` (W22 generator)
- `scripts/checks/critique_health_audit.py` (critique silent 揭發)
- `scripts/sync/fix_dangling_admin_permissions.py` (admin perms 修)
- `wiki/memory/lessons/universal/L62_*.md` (整合連通持續驗證)
- `wiki/memory/lessons/universal/L63_*.md` (學習閉環 aging alert)
- `wiki/memory/crystals/crystal-20260601-000204.md` (5/10 soul applied)
- `wiki/memory/crystals/crystal-20260601-000216.md` (5/24+5/31 applied)

### 修法 (本批)
- `backend/app/services/memory/crystal_applier.py` (soul_section handler + 4 修法)
- `backend/app/services/ai/agent/agent_orchestrator.py` (chitchat trace 補)
- `backend/app/core/paths.py` (L52 family 第 8 案 fallback)
- `scripts/checks/alias_rls_coverage_audit.py` (path fallback)
- `scripts/checks/queryKey_drift_audit.py` (container INFO skip)
- `scripts/checks/service-line-count-check.py` (path fallback)
- `scripts/checks/service_dir_entropy.py` (path fallback)
- `scripts/checks/signal_consumer_lint.sh` (SCAN_DIR 動態)
- `scripts/checks/run_fitness.sh` (step 6 container skip + step 62 E2E)
- `scripts/checks/daily_self_retrospective.py` (metric() label fallback)
- `scripts/checks/agent_evolution_health.py` (DSN +asyncpg strip)

### 文件
- `docs/architecture/KG_HERMES_KUNGE_THREE_LAYER_RETRO_20260531.md`
- `docs/architecture/KUNGE_AGENT_INTEGRATION_DEEP_RETRO_20260531.md`
- `docs/architecture/V6_13_OVERALL_RETRO_AND_V6_14_PLAN_20260531.md`
- `docs/architecture/V6_13_REAL_VERIFICATION_REPORT_20260531.md`
- `docs/runbooks/reboot-pre-flight-20260601.md` (本檔)

---

> **重啟授權狀態**：✅ 所有 Pre-Flight 4 步通過，可安全重啟
> **下次 session 接手點**：對齊本檔 §5 仍 RED 項目 + v6.14 路線
> **重啟後第一步**：跑 Test 1-5 5 步驗收，確認 docker compose 自動 boot 全綠
