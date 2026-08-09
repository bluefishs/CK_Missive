# 重啟 Pre-flight（2026-08-09）

> 本輪主軸：**DT 大幅變動**（21 個 commit 部署、nginx 與 NAS 解耦、MinIO 異地備份）
> ＋ 檢核機制強化（走查入口收斂、weekly RED 差異、跨 repo 退出碼約定）。
> 重啟後最需要確認的是 **DT**，其餘四系統本輪未動 runtime。

---

## 1. Pre-flight 檢查結果（2026-08-09 執行）

| 項目 | 結果 |
|---|---|
| 五系統公網（首頁＋API 兩層） | **全 200**（DT API 401＝需認證，端點活著）|
| 容器 | **56 Up / 0 非健康** |
| 重啟策略 | 全部 `unless-stopped`／`always` → Docker 會自動拉回 |
| Missive DB volume（L43）| `ck_missive_postgres_dev_data` ✅（**不是**那個空殼 `ck_missive_postgres_data`）|
| 業務量基線 | **documents 1991 / KG 49634** |
| Windows 排程 | **21 支全 Ready + StartWhenAvailable** |
| 異地備份 | Missive DB dump 30 份／**DT MinIO 6 bucket（本輪新增）** |
| Hermes | gateway :8642 = 200、ollama :11434 = 200 |
| 檢核閘門 | 走查入口委派／文件數字納管／producer watchdog／共享 drift 皆 exit=0 |
| daily fitness | all passed |

### 各 repo git 狀態

| repo | 未推送 | 未提交 | 說明 |
|---|---|---|---|
| CK_Missive | 0 | 6 | 全為 cron 自動產物（SOUL/diary/evolutions/health JSON）|
| CK_Website | 0 | 2 | 走查結果 JSON（自動產物）|
| CK_DigitalTunnel | 0 | 10 | **他人進行中**：panorama viewer／survey_service／public_contract_check |
| CK_PileMgmt | 1 | 2 | **他人的** commit（`fix(csp): connect-src 補 SSO IdP`）+ 走查 JSON |
| CK_lvrland_Webmap | 4 | 41 | 我的 2 筆被 baseline 閘門擋（見 §4）+ **他人**的 08-07 架構覆盤 |
| shared-modules | 0 | 98 | 其他模組的既有未追蹤檔（非本輪）|

> **我這一輪的改動全部已提交並推送**，未提交項皆為自動產物或他人工作。

---

## 2. 重啟前不需要做的事

- **不需要**手動停容器：全部 `unless-stopped`，Docker Desktop 會自動拉回
- **不需要**重新 build 任何前端：DT 的 `frontend/dist` 是 bind-mount 且 gitignored，
  檔案留在磁碟（現為新 build `index-DTOHaka-.js`），重啟後直接生效
- **不需要**重跑異地備份：排程每日 03:30，且 `StartWhenAvailable` 會補跑

---

## 3. 重啟後驗收

### 3.1 基礎（照舊）

```bash
docker ps --format '{{.Status}}' | grep -c Up          # 期望 56
docker ps --format '{{.Status}}' | grep -icE 'unhealthy|restarting'   # 期望 0
for u in missive lvrland pilemgmt digitaltwin; do curl -s -o /dev/null -w "$u %{http_code}\n" https://$u.cksurvey.tw/; done
curl -s https://missive.cksurvey.tw/health | grep -o '"documents":[0-9]*'   # 期望 >= 1991
```

⚠️ **L76**：Missive 後端若曾 rebuild，必驗 `http://localhost:8001/health` **與**公網兩層。
本次未 rebuild Missive backend，但重啟後仍建議兩層都看一次
（Windows 殭屍埠轉發：不通則 `docker restart ck_missive_backend`）。

⚠️ 四系統若**同時**回 530，先看 cloudflared 日誌是否在重新註冊 —— 本輪出現過一次，
本機直連始終 200、tunnel 重連完即恢復，**不是應用故障**。

### 3.2 本輪新增，重啟後要特別確認

| 項目 | 怎麼驗 | 期望 |
|---|---|---|
| **DT nginx 能起來**（本輪最重要）| `docker ps \| grep ck-tunnel-nginx-1` | `healthy` |
| DT acute3d 掛載點存在 | `ls D:\CKProject\CK_DigitalTunnel\nginx\acute3d-mount` | 有 `.gitkeep` |
| DT 前端為新 build | 首頁原始碼含 `index-DTOHaka-.js` | 是 |
| DT MinIO 異地備份排程 | `Get-ScheduledTask CK_DigitalTunnel-MinIO-Offsite` | Ready |
| DT 走查排程 | `CK_DigitalTunnel-SelfAudit-{Flow,Sweep}` | Ready |

**為什麼 DT nginx 是重點**：本輪把 acute3d 由 CIFS docker volume 改成 host bind mount。
改這個的原因正是 **08-08 那次 CIFS 掛載失敗讓整個 nginx 起不來**，
連帶逼出「用 Vite dev server 對外」而公開了原始碼。
現在 host 目錄必定存在，理論上不會再發生 —— 但這是**重啟後第一次**驗證該假設。

若 nginx 起不來：`docker logs ck-tunnel-nginx-1 --tail 30`，
並確認 `nginx/acute3d-mount/` 目錄還在（被誤刪會讓 bind mount 建出空目錄，仍可啟動）。

### 3.3 檢核基線（重啟後跑一次，與此對照）

```bash
cd D:/CKProject/CK_Missive && bash scripts/checks/run_fitness_daily.sh     # all passed
cd D:/CKProject/CK_Missive && bash scripts/checks/run_ui_smoke.sh --sweep  # PASS 87 / FAIL 0
cd D:/CKProject/CK_DigitalTunnel && bash scripts/checks/run_selfaudit.sh --sweep  # PASS 26 / FAIL 1
cd D:/CKProject/CK_PileMgmt && bash scripts/checks/run_selfaudit.sh --sweep       # PASS 34 / FAIL 2
cd D:/CKProject/CK_lvrland_Webmap && bash scripts/checks/run_selfaudit.sh --sweep # PASS 62 / FAIL 0
cd D:/CKProject/CK_Website && bash scripts/checks/run_ui_smoke.sh --sweep         # PASS 8 / FAIL 0
```

---

## 4. 已知狀態（非故障，重啟後仍會看到）

| 現象 | 說明 |
|---|---|
| DT 走查 `/unfolded` FAIL | `3dtiles-cache` bucket 為空，Celery 轉檔從未跑過。需一次耗時運算，**本輪未擅自觸發** |
| DT `asset_integrity_audit` RED | 25 筆 crack_detection 標 completed、MinIO 只有 18 組輸出 → 7 筆無產物 |
| pile 走查 2 FAIL | `/openapi.json` 與 `/docs/*` 不對公網開放＝**刻意的安全決策** |
| `windows_task_liveness_audit` exit=2 | 上面兩項的下游，非排程故障 |
| `CK_Missive-Fitness-Weekly` last=1 | 三態約定：1＝有 RED step（跑完了、紅的是內容），已在 `ALLOWED_NONZERO` 宣告 |
| lvrland 4 筆未推送 | 被 baseline 閘門擋（**他人**未提交的 `coordinate_pipeline.py` 799→804 行超標）。**未用 `BASELINE_SKIP` 繞過** |
| DT `/scenes` 顯示空清單 | NAS 未掛載＝預期。⚠️ 目前「憑證沒設／連不上／真的沒場景」三種狀態無法分辨 |

---

## 5. 待 owner 決定（重啟不受影響）

1. **DT 資產路徑無認證** —— 實測未帶憑證可取 722MB 點雲（206）與裂縫影像（200）。
   已關閉 `/acute3d/` 公開列舉；內容本身要不要加 `auth_request` 屬產品決策，
   會改變檢視器的 iframe／Range／CORS 行為，**未擅自加**。見
   `CK_DigitalTunnel/docs/runbooks/acute3d-mount-point.md`。
2. **3MX 儲存位置** —— 查證結論是**不宜搬進 MinIO**（本機 docker volume、
   原本零備份、且 MinIO 是 DB 備份的目的地）。建議留在 NAS，見同上文件。
3. `/unfolded` 與 `/cracks` 的缺產物是否重跑（耗時運算）。

---

## 6. 若重啟後出問題

| 症狀 | 先看 |
|---|---|
| DT 首頁 502／nginx 起不來 | `docker logs ck-tunnel-nginx-1 --tail 30`；確認 `nginx/acute3d-mount/` 存在 |
| Missive 公網不通但本機 200 | L76 殭屍埠 → `docker restart ck_missive_backend` |
| 四系統同時 530 | cloudflared 重連中，看 `docker logs ck_missive_cloudflared --tail 10` |
| GPU 容器起不來、推論全逾時 | NVIDIA hook 崩潰 → `wsl --shutdown` 後重啟 Docker（**勿用 `docker restart`**）|
| DB 業務量異常偏低 | **立即停手**，對照 L43：確認 volume 是 `ck_missive_postgres_dev_data` |
