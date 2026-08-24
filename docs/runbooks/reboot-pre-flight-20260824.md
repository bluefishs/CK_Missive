# 重啟前置檢查與重啟後驗收（2026-08-24）

> 建立：2026-08-24 02:4x｜前次：`reboot-pre-flight-20260810b.md`
> 用途：**重啟前確認不會掉東西、重啟後知道要看什麼**。
> 這一份的差別在於：本輪剛修好三個備份缺陷，重啟後那三項是首要複驗對象。

---

## 0. 一句話結論

**可以重啟。** 291 個未提交檔案**全數是 wiki 自動產物**（逐一分類過，需人工判斷的是 **0**），
56 個容器全部有重啟策略，DB volume 正確，異地備份四類齊全且都在 1 小時內。

---

## 1. 重啟前（已完成，含實測值）

| 項目 | 結果 | 判準／備註 |
|---|---|---|
| 六 repo 未推送 | Missive 0／lvrland 0／pile 0／DT 0／CK_Website 0／**AaaP 1** | AaaP 那 1 個屬該 repo，已知 |
| 未提交（需人工） | **0** | 291 個全在 `wiki/`，由 cron 產生。用路徑前綴逐一分類，不是目測 |
| **DB volume（L43）** | `ck_missive_postgres_dev_data` | ⚠️ **最重要的一項**。2026-05-21 那次事故是 compose 指向空殼 `ck_missive_postgres_data`，17 tables／502 docs，dormant 10 小時 |
| 容器 | 執行中 **56**｜非健康 **0**｜已停止 2 | 停止的兩個是 dev/builder，非常駐（`frontend-dev` Exited 137 四天前、`tunnel-frontend-builder` Exited 0 五天前） |
| 重啟策略 | 52 `unless-stopped` ＋ 4 `always` = **56/56** | 全部會自動拉回 |
| Windows 排程 | 35 支：Ready **34**／Disabled **1**／SWA 為否 **0** | Disabled 的是 `CK_Missive-SOUL-Mirror-Sync`（見 §4） |
| 異地備份四類 | 全 **GREEN** | DB 30 份 522MB（0.2h）／里程碑 6 份／附件 1529＋1 打包／**金鑰 14 份（0.0h）** |
| 業務量基線 | **2018 docs／49899 KG／256 報價單／253 PM 案件／88 承攬** | 重啟後拿這組對照 |
| runtime 版本綁定 | `v6.60 @ 964d3357` | 重啟後應維持同值（映像不變） |

---

## 2. 重啟後驗收（依序，約 10 分鐘）

### ① 容器自動拉回（等 3-5 分鐘再看）

```bash
docker ps -a --format '{{.Names}}\t{{.Status}}' > /tmp/ps.txt
grep -c 'Up ' /tmp/ps.txt          # 期望 56
grep -ciE 'unhealthy|restarting' /tmp/ps.txt   # 期望 0
```

⚠️ **DB volume 必須複驗**，這是 L43 的教訓：

```bash
docker inspect ck_missive_postgres --format \
  '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}'
# 必須是 ck_missive_postgres_dev_data
```

### ② 業務量對照（volume 掛錯時這裡會塌）

```sql
SELECT (SELECT count(*) FROM documents) docs,
       (SELECT count(*) FROM canonical_entities) kg,
       (SELECT count(*) FROM erp_quotations) quotations;
-- 期望 ≈ 2018 / 49899 / 256（只會增不會減）
```

### ③ 公網兩層（**只看首頁會漏掉後端掛掉**）

```bash
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0" https://missive.cksurvey.tw/
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  https://missive.cksurvey.tw/api/documents-enhanced/statistics
# 期望：首頁 200、API **401**（401 才對 —— 200 代表資安收斂回退了）
```

判準來自 2026-08-08 lvrland 那起故障：後端 hang 住、API 對真實使用者完全不可用，
而**公網首頁仍回 200**。五個系統都要用兩層查。

### ④ runtime 說得出自己是哪一版

```bash
docker exec ck_missive_backend python -c \
  "import sys; sys.path.insert(0,'/app'); from app.core.build_info import build_info; print(build_info())"
# 期望 {'version': 'v6.60', 'commit': '964d3357', ...}
```
與 `git rev-parse --short HEAD` 不符 ⇒ 映像沒跟上程式碼。

### ⑤ ⭐本輪新修的三項備份缺陷（首要複驗對象）

```bash
python scripts/checks/offsite_backup_completeness_audit.py
```
期望四類全 GREEN。**這一項要特別看**，因為本輪剛改了執行順序：

| 缺陷 | 修法 | 複驗點 |
|---|---|---|
| 附件失敗把金鑰一起殺掉（`exit 1` 連坐） | 金鑰段移到附件判定之前 | 金鑰檔日期要是當天 |
| NAS 遞迴掃描會**間歇性把整支腳本帶走**（try/catch 攔不到） | 金鑰再往前移到掃描之前 | 掃描死掉時金鑰仍應完成 |
| 呼叫 `tar` 沒指定哪一個（Git 的 tar 把 `C:\` 當遠端主機） | 明確用 `System32\tar.exe` | log 不應出現 `Cannot connect to C:` |

⚠️ **這三項在排程情境才會現形**，手動跑可能都過。要看 `logs/backup/*.log` 當天的紀錄。

### ⑥ 其餘既有檢核

```bash
docker exec ck_missive_backend bash /app/scripts/checks/run_fitness_daily.sh
python scripts/checks/public_endpoint_auth_audit.py     # 缺口必須是 0
python scripts/checks/windows_task_liveness_audit.py
```

---

## 3. 本輪（08-21～24）已完成、重啟後應維持的狀態

| 項目 | 值 |
|---|---|
| 無認證端點缺口 | **0**（735 端點，28 條刻意公開且各有理由） |
| 版次三方一致 | runtime `v6.60 @ 964d3357` = git HEAD = CLAUDE.md |
| 異地備份四類 | GREEN，且**狀態檔已寫到目的地**供跨 repo 讀取 |
| portfolio 備份盤點 | 每週會報 CK_Website／dataform **兩個缺口**（刻意保留可見） |
| 排程逾時上限 | 自家兩支 PT72H → PT1H；pile 的 PT72H 已通報（跨 repo 不代改） |
| `.git`／`.env` 外洩 | 五系統 15 個組合零外洩（**先驗過鑑別力**才敢說零） |

---

## 4. 重啟後可能仍是紅的（**已知，不是新故障**）

| 項目 | 為什麼 | 出處 |
|---|---|---|
| `CK_Missive-SOUL-Mirror-Sync` **Disabled** | 本機有程式在持續停用排程（含異地備份），與斷電無關。事件 ID 142 顯示分散在整個下午，執行身分 User1；IObit Advanced SystemCare 的「啟動優化」是高度嫌疑但**不是確證** | OPEN_ITEMS C1 |
| 兩支 Logon 觸發排程需**提權**才能啟用 | `Enable-ScheduledTask` 一般權限回 `Access is denied` | OPEN_ITEMS A6 |
| DT MinIO 備份判「待確認」 | 排程有跑 rc=0 但目的地最新 90h。**我分不出「來源沒變」與「同步空跑」**，那要產出端說 | 已通報 DT |
| CK_Website／dataform 無異地備份 | NAS 上完全沒有目錄。前者是四系統的 SSO IdP | 已分別通報 |
| pile `CK_PileMgmt_DB_Backup` = PT72H | 3 天形同沒有上限；他們前一天才剛經歷單一請求卡 23 小時 | 已通報，跨 repo 不代改 |

⚠️ **重啟後 20 分鐘內量到的紅燈，有很高比例是恢復過程本身造成的**（08-18 斷電那次的教訓）。
恢復窗口內產生的結果檔要重跑覆蓋，否則會留在檔裡持續污染下游。

---

## 5. 若重啟後出事——先查這三個

1. **DB volume 掛錯**（L43）→ 業務量會塌，先看 §2①②
2. **Windows 埠未釋放**（L76）→ backend 起來了但公網 502。正解是 `stop` + `rm` 再 `up -d`，不是直接 `up -d`
3. **NVIDIA prestart hook 崩潰** → GPU 容器起不到、推論全斷而 healthcheck 仍綠。
   解＝`wsl --shutdown` 重啟 Docker 引擎，**不要用 `docker restart`**

災難還原程序見 `docs/runbooks/disaster-recovery.md`。
