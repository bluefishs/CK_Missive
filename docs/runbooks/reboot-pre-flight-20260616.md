# 重啟 Pre-Flight 與驗收 — 2026-06-16

> 觸發：v6.19（wiki↔KG 根治 + graph_domain 自癒部署 + SSO 治本）後準備重啟電腦。
> 體例沿用 `reboot-pre-flight-20260602.md` / `reboot-acceptance-checklist.md`。

---

## A. Pre-Flight（重啟前，已全數通過 ✅）

| # | 檢查 | 結果 |
|---|---|---|
| 1 | git 已 commit/push（無遺失風險） | ✅ `main` ahead origin **0**；今日 6 commits 已 push：`22f8a424`(wiki/graph_domain)→`a66d410b`(SSO retry)→`17373757`(SSO 治本)→`edc0f2b5`(docs)→`27d7ba8e`(wiki 歸檔)→`74340416`(桃園派工 tab+分母) |
| 2 | 容器全 healthy | ✅ backend/frontend/postgres/redis/cloudflared + hermes×2/ollama 全 Up healthy |
| 3 | backend image 為含修法版 | ✅ `ck-missive-backend:production` built 2026-06-16（含 graph_domain 自癒 + ingest_entity preserve + morning-status 無期限派工納入） |
| 4 | 前端 dist 為含 SSO 治本版（bind-mount） | ✅ `frontend/dist` 服務 bundle = 含 SessionGate/sessionStore（`./frontend/dist:ro`） |
| 5 | **DB volume 正確（L43）** | ✅ postgres mount = `ck_missive_postgres_dev_data`（非空殼）；compose `postgres_data` → `name: ck_missive_postgres_dev_data` |
| 6 | 業務量在位（重啟後 healthcheck 依此） | ✅ **1,852 docs / 26,935 KG entity** |
| 7 | compose 配置有效 | ✅ `docker compose -f docker-compose.production.yml config` OK |
| 8 | 圖譜治理 audit | ✅ `graph_domain_tagging_audit` 誤標 **0** GREEN；wiki↔KG **213/226 = 94%** |

### 重啟會「自動生效」的待生效項
- **L72 `code_graph_incremental` misfire_grace_time=7200**（06-12 補、註記「下次重啟生效」）→ 重啟後排程器重載即生效。
- backend 新 image 與新 dist 已在運行/serve，重啟後 docker 自動恢復同版。

### 工作樹殘留（無害、可再生、不阻斷重啟）
- `wiki/memory`(diary/patterns/soul_drift_snapshot)、`wiki/topics`、`wiki/SOUL.md`(W24 autobiography)、`GOVERNANCE_INTEGRATED_DASHBOARD.md`：**cron 每日/每週自動再生**的副產物。
- `wiki/entities` 4 個 untracked：今早 compile 新增的真實業務實體（115年派工×3 + 地政所）。
- → 已於本次以 chore 歸檔（見下方 commit）；即使未歸檔，重啟後 cron 也會重建，**無資料遺失風險**。

---

## B. 重啟後驗收（5 步，開機後執行）

```bash
# 1) 容器自動恢復（Docker Desktop 自啟）
docker ps --format '{{.Names}} {{.Status}}' | grep missive   # 5 容器 healthy

# 2) DB volume 仍為 dev_data + 業務量在位（L43 防空殼）
docker inspect ck_missive_postgres --format '{{range .Mounts}}{{.Name}}{{end}}' | grep dev_data
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -t -c \
  "SELECT count(*) FROM documents;"   # 應 ≈1852（>100 healthcheck gate）

# 3) 後端業務 healthcheck（公網流量依此）
docker exec ck_missive_backend sh -c 'curl -s localhost:8001/api/health'   # status:healthy

# 4) SSO 治本 live 煙霧（匿名載入不卡 SessionGate）
node scripts/checks/sso_entry_smoke.cjs   # exit 0 = PASS

# 5) 圖譜治理 audit 不回退
PYTHONIOENCODING=utf-8 python scripts/checks/graph_domain_tagging_audit.py   # 誤標 0 GREEN

# 6) 桃園派工總覽分母一致（morning-status 納無期限派工）
docker exec ck_missive_backend sh -c "curl -s 'localhost:8001/api/taoyuan-dispatch/dispatch/morning-status' \
  -X POST -H 'Content-Type: application/json' -d '{\"contract_project_id\":21}' \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print(\"total=\",d[\"total\"],\"sum=\",sum(d[\"summary\"].values()))'"
  # 應 total == sum(summary)（project 21 = 30），分母與看板一致
```

### ⚠️ 重啟後唯一需 owner 親驗（不可代行）
- **SSO+reload 端到端**：真實瀏覽器從 `www.cksurvey.tw` 進 `missive.cksurvey.tw` → 應**穩定落 dashboard、不再停在 entry/閃訪客跳回**（SSO 治本的最終驗收，需 owner 真實 ck_employee cookie）。

---

## C. 若重啟後異常的回滾錨點
- 前端 SSO 治本若意外擋登入：`frontend/dist` 由 src build；可 `git revert 17373757` + `npm run build` 還原（今天的 `a66d410b` retry 止血仍在 `17373757` 之前的行為亦安全）。
- 後端：image `ck-missive-backend:production` 對應 git HEAD；如需回滾 graph_domain/ingest_entity，`git revert 22f8a424` + rebuild。
- DB：volume `ck_missive_postgres_dev_data` 為唯一真實資料源；**切勿**讓 compose 指回 `ck_missive_postgres_data`（L43 空殼事故）。
