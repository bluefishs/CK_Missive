# 重啟前 Pre-Flight + 重啟後驗收 — 2026-06-02

> Owner 訴求：「更新系統文件與相關設定 確認容器版本準備重啟電腦」
> 對齊：reboot-pre-flight-20260601.md / L43 volume drift 防範 / 今日 23 commits

---

## 0. 重啟前快照（2026-06-02 21:40 真實實測）

### Git
- 本日 commits：**23**（全 push origin）
- `git log origin/main..HEAD` 空（全同步）
- 未追蹤僅 cron 自動產出（GOVERNANCE_INTEGRATED_DASHBOARD / SOUL / log / proposal）

### 容器版本 + 健康
| Container | Image | Status |
|---|---|---|
| ck_missive_backend | ck-missive-backend:production | healthy（今日多次 rebuild，全代碼烘入）|
| ck_missive_frontend | ck-missive-frontend:production | healthy（**21:38 rebuild 對齊今日前端修法**）|
| ck_missive_postgres | pgvector/pgvector:0.8.0-pg15 | healthy |
| ck_missive_redis | redis:7-alpine | healthy |
| ck_missive_cloudflared 等 4 | cloudflare/cloudflared:**2026.5.0**（pinned ✓）| healthy |

### 今日關鍵 config 持久性（重啟後 compose 讀 host .env 生效）
| config | 容器值 | 持久機制 |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | host .env + compose `${OLLAMA_BASE_URL:-}` |
| `PGVECTOR_ENABLED` | `true` | host .env + compose `${PGVECTOR_ENABLED:-false}`（今日補傳）|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | compose 硬寫 60（auth_service 改讀 settings）|

> ⚠️ `.env` 是 gitignore（含密鑰）：OLLAMA/PGVECTOR 改在 **host .env**，重啟後 docker compose 讀它 → 自動生效。**不需手動重設**。

### 後端代碼烘入驗證（content-level md5 host=container）
- ✅ auth_service.py / ai_connector.py / crystallizer.py / scheduler.py 全烘入

### DB volume（避 L43 ghost）
- ck_missive_postgres data volume = **`ck_missive_postgres_dev_data`** ✅（非 ghost）
- docs **1,817** / canonical_entities **26,232** / status healthy

### 前端部署
- host `frontend/dist` = **06-02 19:47**（今日 build，backend SPA :ro mount 服務公網 → 最新）
- frontend container = 21:38 rebuild（:3000 路徑也對齊，不 stale）

---

## 1. 本日 23 commits 摘要（5 大主題）

### A. 平臺自證/cron 真活（silent → LOUD 四層防禦）
- `5c59e7dc` 8 cron `.parent` 路徑 bug（每日覆盤+LINE 等全 silent 死）
- `1468da1a` 開機自檢 cron script 路徑
- `94c12538` silent return → raise（watchdog 能抓 silent no-op）
- `b6ae4810` outcome-freshness watchdog（每日 07:00 自證）
- `1fd30e3f` docs 改可寫（governance dashboard cron）

### B. 學習閉環/架構戰略（三柱）
- `7d3d2b3b` 整體架構發展戰略（學習閉環×Hermes×平臺）
- `00c87167` 柱一 Step A crystallizer tool_sequence 解析修
- `dbbaa9fc` 柱二 H1 撤回（盤點防做白工）/ `c5055144` 柱一 Step B 撤回（PatternLearner 已自動閉環）

### C. vision/embedding/auth config（修真因鏈）
- `deb3f81e` vision task_type → gemma4:e2b（修發票 OCR silent 退 QR）
- **OLLAMA_BASE_URL** localhost→host.docker.internal（host .env，修「無法生成查詢向量」0.0s）
- `9f63a5cc` PGVECTOR_ENABLED compose 補傳（修「pgvector 未啟用」）
- `3192c94a` token SSOT 30→60min（修閒置不到 30 分被登出）

### D. kunge UI（整併 + 崩潰修 + 403 修）
- `9d8f3a8f` tab 整併 7→5 核心主軸 + 去對話重複 / `81aff5ce` 紀錄同步
- `b3782a61` GatewayHealthBadge 改 apiClient（修離線誤判）
- `7e97edf4` 閒置登出倒數徽章
- `93580983` 自省 tab domains dict 崩潰修 / `12d1c782` 追蹤空白 + 服務狀態 error 修
- `c99ae1bc`+`9f63a5cc` chat agent stream 403（raw fetch 補 X-CSRF-Token）

### E. backup
- `42814186` 備份增強（dump 完整性驗證 + 異地 NAS robocopy）

---

## 2. 重啟後驗收（5 步 SOP）

```bash
# Test 1: 基礎服務 boot
docker compose -f docker-compose.production.yml ps   # 期待 5 service healthy
curl -s http://localhost:8001/health | grep status   # healthy / docs>=1817

# Test 2: 今日 config 持久生效
docker exec ck_missive_backend sh -c 'echo "$OLLAMA_BASE_URL | $PGVECTOR_ENABLED | $ACCESS_TOKEN_EXPIRE_MINUTES"'
# 期待 host.docker.internal:11434 | true | 60

# Test 3: embedding 真活（OLLAMA fix）
docker exec ck_missive_backend sh -c 'curl -s --max-time 8 http://host.docker.internal:11434/api/embeddings -d "{\"model\":\"nomic-embed-text\",\"prompt\":\"x\"}"' | python -c "import json,sys;print('embedding dim:',len(json.loads(sys.stdin.read()).get('embedding',[])))"
# 期待 768

# Test 4: 6 v6.13 cron + 開機自檢
docker logs --since 2m ck_missive_backend 2>&1 | grep "開機自檢"   # 期待 ✅ cron script 全在

# Test 5: business endpoint smoke + kunge 頁
docker exec ck_missive_backend python /app/scripts/checks/admin_backup_smoke_test.py   # 10/10 PASS
# 瀏覽器硬重新整理 missive.cksurvey.tw/kunge/ops → 5 tab 正常、自省/追蹤/服務狀態不崩
```

---

## 3. 重啟後若異常 SOP
- **embedding 報錯** → 查 `OLLAMA_BASE_URL`（須 host.docker.internal）+ ck-ollama healthy
- **pgvector 未啟用** → 查 `PGVECTOR_ENABLED=true`（compose 傳 + .env）
- **chat 403** → CSRF（已修；若仍 403 查 csrf_token cookie 是否設）
- **DB 空殼** → 確認 postgres mount `ck_missive_postgres_dev_data`（非 ghost）

---

## 4. 仍待 owner/v6.14（不影響重啟）
- ck_missive_ollama_dev 死容器（dev compose 的 ollama，Created 從未啟動，可選移除）
- ops 11→4 整併 + /ai/memory 技能星雲去重疊（UI 重構，待計畫確認）
- 散落 raw fetch 漏 CSRF（MilestonesTab/PMCaseListPage/ErrorBoundary）+ fitness audit
- 坤哥 vs 乾坤智能體 命名統一（同一意識體、兩名困惑）

---

> **重啟授權狀態**：✅ Pre-Flight 全通過（git 同步 / 容器 healthy / config 持久 / 代碼烘入 / DB 正確 / 前端新鮮），可安全重啟
> **重啟後第一步**：跑 Test 1-5，確認 docker compose 自動 boot 全綠 + 今日 config 生效
