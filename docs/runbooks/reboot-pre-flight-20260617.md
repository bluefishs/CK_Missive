# 重啟 Pre-Flight 與驗收 — 2026-06-17

> 觸發：標案(tender)整輪整合優化 + SSO bootstrap 競態真根因修(06-16 ⑦) 後準備重啟電腦。
> 體例沿用 `reboot-pre-flight-20260616.md`。

---

## A. Pre-Flight（重啟前，已全數通過 ✅）

| # | 檢查 | 結果 |
|---|---|---|
| 1 | git 已 commit/push（無遺失風險） | ✅ `main` ahead origin **0**、非 cron dirty **0**；尾段 `abe87f6a`(PCC直連)→`5ec45d7c`(enrich欄位/服務)→`dc602a07`(enrich定論+L77) |
| 2 | 容器全 healthy | ✅ backend/frontend/postgres/redis/cloudflared 全 Up healthy（backend 為今日含修法版 image） |
| 3 | backend image 為含修法版 | ✅ rebuilt 2026-06-17（tender Option B/同義詞/排除/承攬史建議/PCC直連/enrichment 服務） |
| 4 | frontend dist 為含修法版（bind-mount） | ✅ `frontend/dist` = `main-D9ieryq3.js`（公網 serve 一致；含「推薦規則設定」自維 UI） |
| 5 | **DB volume 正確（L43）** | ✅ postgres mount = `ck_missive_postgres_dev_data`（非空殼） |
| 6 | 業務量在位（healthcheck 依此） | ✅ **1,855 docs / 27,407 KG**、ok=true；`tender_records=55,858` |
| 7 | alembic head 一致 | ✅ `20260617a001`（tender enrichment 欄位，ADD COLUMN IF NOT EXISTS 零刪除已上 head） |
| 8 | L76 公網關卡 | ✅ host→8001=200、公網 `/api/health`=200 |

### 重啟會「自動生效」的待生效項
- backend 新 image + 新 dist 已在運行/serve，重啟後 Docker `unless-stopped` 自動恢復同版。
- alembic 已在 head（無待跑遷移）。

### 工作樹殘留（無害、可再生、不阻斷重啟）
- `wiki/memory`(diary/patterns/soul_drift/integration-health/pipeline-reports/self-retrospective)、`wiki/SOUL.md`、`GOVERNANCE_INTEGRATED_DASHBOARD.md`：cron 每日/每週自動再生的副產物，重啟後 cron 重建，無資料遺失風險。

---

## B. 重啟後驗收（開機後執行）

```bash
# 1) 容器自動恢復
docker ps --format '{{.Names}} {{.Status}}' | grep missive   # 5 容器 healthy

# 2) DB volume 仍為 dev_data + 業務量在位（L43 防空殼）
docker inspect ck_missive_postgres --format '{{range .Mounts}}{{.Name}}{{end}}' | grep dev_data
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -t -c "SELECT count(*) FROM documents;"  # ≈1855

# 3) ★L76 關卡：host→8001 + 公網（容器內 health≠公網可達；殭屍埠轉發風險）
curl -s -o /dev/null -w "host8001=%{http_code}\n" http://localhost:8001/health      # 必 200
curl -s -o /dev/null -w "public=%{http_code}\n" https://missive.cksurvey.tw/api/health  # 必 200
#   若 public 502 而容器 healthy → docker restart ck_missive_backend（L76 殭屍埠轉發修）

# 4) alembic head
docker exec ck_missive_backend sh -c 'cd /app && alembic current'   # 20260617a001

# 5) 標案數字一致（今日最新=今日標案、業務推薦無儀器噪音）
docker exec ck_missive_backend sh -c "curl -s -X POST localhost:8001/api/tender/analytics/dashboard -H 'Content-Type: application/json' -d '{}'" \
  | python3 -c "import sys,json;d=json.load(sys.stdin)['data']['stats'];print('今日標案',d['latest_bid'],'本週標案',d['week_new_bid'],'本週決標',d['week_new_award'])"
```

### ⚠️ 重啟後需 owner 親驗（不可代行）
- **SSO+reload 端到端**：`www.cksurvey.tw` → `missive.cksurvey.tw` 應**第一次就穩定落 dashboard、不停 entry**（06-16 ⑦ bootstrap 競態治本的最終驗收）。
- **標案 UI**：`/tender/search → 關鍵訂閱` 應見「推薦規則設定」面板（排除/同義詞/承攬史建議，即時生效）；`/tender/dashboard` 卡片皆週單元；標案官方直連可開完整 PCC 頁。

---

## C. 若重啟後異常的回滾錨點
- 前端：`frontend/dist` 由 src build；如需回滾 tender UI，`git revert <commit>` + `npm run build`。
- 後端：image 對應 git HEAD；如需回滾 tender 邏輯/enrichment，`git revert` 對應 commit + rebuild（走 L76 驗證）。
- DB：volume `ck_missive_postgres_dev_data` 為唯一真實資料源；**切勿**指回 `ck_missive_postgres_data`（L43 空殼）。enrichment 欄位為純新增（無回滾必要）。

---

## D. 本輪重點（2026-06-17，供覆盤）
- **標案 tender 整輪**：統計口徑 SSOT（dashboard 全卡週單元、今日最新=今日標案 DB 同源去重）；業務推薦 Option B（關鍵字優先 title-only/不受預算門檻/財物+負面關鍵字排除）；**自維 UI**（關鍵訂閱→推薦規則設定：排除/同義詞/承攬史建議一鍵加入、即時生效免 rebuild，L75.x）；PCC 官方直連修（pkPmsMain 原始=）。
- **Enrichment 定論（勿重試）**：server 端 PCC 詳情 enrichment 不可行（openfun 需 org_id、org_id 只在被端點限流的 PCC 詳情頁；非全面 IP 封、爬蟲資料源正常）。詳見 `TENDER_RECOMMENDATION_FLOW.md` 附錄 B + `LESSONS_REGISTRY.md#L77`。
- **lessons**：L74(SSO bootstrap 競態)、L75.x(標案相關性)、L76(Windows 殭屍埠轉發)、L77(PCC enrichment 死結)。
