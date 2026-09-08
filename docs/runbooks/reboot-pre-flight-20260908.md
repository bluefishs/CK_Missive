# 重啟前狀態固定與復原指引（2026-09-08）

> `lifecycle: status=current reviewed=2026-09-08 owner=CK_Missive`
>
> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 前一份：`reboot-pre-flight-20260902.md`（其 §4 的 A66 背景仍有效）。

---

## 0. ⛔ 關機前要做的事

| # | 事情 | 誰做 | 狀態 |
|---|---|---|---|
| 1 | `git push origin main` | — | ✅ **已完成**（未推送 0；工作樹只剩 `backend/config/remote_backup.json`，那是備份排程每天自己寫的狀態檔） |
| 2 | 部署與版本綁定 | — | ✅ **已完成**（v6.75 @ `ac50faa1` 已在跑，見 §1） |
| 3 | **啟動 `mdsched`（A66-P3）** | **owner** | ⚠️ **仍未做**。我沒有管理員權限。**本機從未執行過記憶體診斷**（2026-09-08 實查：`MemoryDiagnostics-Results` 事件 **0 筆**）——「查不到結果」＝還沒跑，不是跑過沒問題 |

`mdsched` 用法（GUI，會問「立即重新啟動並檢查」）：

```
mdsched
```

開機時先跑 30–60 分鐘記憶體測試，期間電腦不能用、公網也還沒回來。
結果：事件檢視器 → Windows 記錄 → 系統 → 來源 `MemoryDiagnostics-Results`。

**這次重啟沒有「改動只在 host 檔案、尚未進映像」的風險** —— 今天所有後端改動都已建進映像並換過容器。

---

## 1. 重啟前基線（2026-09-08 08:45 實測）

| 項目 | 值 |
|---|---|
| 版本 | **v6.75** @ `ac50faa1`，映像建於 `2026-09-08T00:43:49Z` |
| `/api/health/detailed` | `healthy`，fatal 0／degraded 0 |
| 公網 `https://missive.cksurvey.tw/health` | 三次抽樣皆 200 |
| 部署後四層驗證 | `deploy_verify.py` → GREEN（含 ORM／認證鏈） |
| 業務量 | 公文 2,059／實體 50,333／報價單 330／承攬案 285 |
| Alembic | DB `20260907a002` ＝ head（單一 head） |
| 容器 | backend／frontend／postgres／redis `always`；cloudflared `unless-stopped` |
| Volume | `ck_missive_postgres_dev_data`／`ck_missive_redis_data`／`ck_missive_ollama_dev_data` |
| 最新 DB 備份 | `ck_missive_backup_20260908_015959.sql`（549 MB，NAS 30 份） |
| 異地備份 | DB 30 份／附件 1,646 檔／金鑰 14 份／**報價單總表 109 檔＋快照 7 份（今天新納入）** |
| 前端 | `dist/index.html` 建於 09-08 03:55（原始碼最後變更 03:39），公網 chunk `main-BBBneM5i.js` ＝本機 dist |
| 排程 | CK_Missive 6 支全部 `Ready`，今日 03:00–05:10 都有執行紀錄 |

**前端有兩個服務者、同一份檔案**：backend 掛 `./frontend/dist:/frontend/dist:ro` 供公網（Tunnel → :8001），
nginx 容器掛同一個目錄供內網 :3000。`assets/` 累積 26 個 `main-*` 是刻意的（09-04 修 chunk 404：部署保留上一版）。

---

## 2. 重啟後檢查清單（依序）

```bash
# 1. Docker 引擎與容器（5 個都要 Up；backend/postgres/redis/frontend 應自動回來）
docker ps --format "{{.Names}}\t{{.Status}}"

# 2. 本機健康（含業務量門檻，空殼 DB 會 503）
curl -s http://localhost:8001/api/health/detailed | python -c "import sys,json;d=json.load(sys.stdin);print(d['status'],d['build'])"

# 3. 公網三次抽樣（L76：Windows 重啟後常留殭屍埠轉發 ⇒ 容器健康但公網 502，單次 200 不足）
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code} " https://missive.cksurvey.tw/health; sleep 2; done

# 4. 四層驗證（ORM／認證鏈）
python scripts/checks/deploy_verify.py

# 5. 排程沒有被停用（看 LastRunTime，不是只看 State）
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'CK*Missive*' | %{ $i=$_|Get-ScheduledTaskInfo; '{0} {1} {2}' -f $_.TaskName,$_.State,$i.LastRunTime }"
```

**預期**：版本仍是 `v6.75 @ ac50faa1`、業務量與 §1 相同（±當日新增）、公網三次都 200。

### 出問題時的對照

| 症狀 | 多半是 | 處置 |
|---|---|---|
| 容器全 Up 但公網 502 | L76 殭屍埠轉發 | `docker compose -f docker-compose.production.yml restart backend`，再抽樣三次 |
| GPU 容器（`ck-ollama`）起不來、推論全斷而 healthcheck 仍綠 | NVIDIA Container Toolkit prestart hook 崩潰 | `wsl --shutdown` 再啟動 Docker，**不要用 `docker restart`** |
| 公網 1033 | Docker engine 卡死 | 見 `memory/docker_engine_wedge_1033_recovery.md` |
| `/api/health` 503 `business_data_not_present` | Volume 掛錯（L43） | 對照 §1 的 volume 名稱 |
| 版本回報 `unknown` | build 身分沒進映像 | 09-08 已修（`build-args.sh` 綁定不到就不建、部署閘門改前綴比對）；重跑 `bash scripts/deploy/deploy-public.sh` |

---

## 3. 這次重啟前剛改過、要特別看的

| 改動 | 重啟後怎麼確認 |
|---|---|
| `/uploads` 改帶認證＋附件層級規則（L148／A116） | 未登入 `curl -s -o /dev/null -w "%{http_code}" https://missive.cksurvey.tw/uploads/certifications/user_1/x.pdf` → **401** |
| 選單父階權限（staff 補 `reports:view`、圖譜項移位） | 以業務同仁登入，側欄要有「報表分析 → 專案財務／政府標案」 |
| 民國年解析收斂（A119） | `python -m pytest backend/tests/test_roc_date.py` |
| LINE 去重改 redis（A117） | redis 起來後 webhook 重送不會重複回覆 |
| 報價單總表異地備份（A123） | `python scripts/checks/offsite_backup_completeness_audit.py` → 報價單總表 GREEN |
| weekly 118–123 登記進排程 | `bash scripts/checks/run_fitness_weekly.sh` 的步數應為 125 |

---

## 4. 已知會紅、不是重啟造成的

| 項目 | 狀態 |
|---|---|
| weekly 120 報價單總表 vs DB | RED 3 筆：第 59 列無編號、2 筆「總表未標成立而系統已成案」——**要 owner 在總表補 v**，不是系統問題 |
| 公文附件稽核 | YELLOW「NAS 多 2 檔」：同步用 `/XO` 不用 `/MIR`，本機刪過的檔在 NAS 留著是預期 |
| 其他 repo 的排程 | `CK_PileMgmt_PM2_Autostart` result=255、`CK_DigitalTunnel-PostRestart-Check` result=2、`CK-Hermes-Health-Smoke` 從未執行 —— **不是本 repo 的事，只記錄**（跨 session 權責 §1） |
