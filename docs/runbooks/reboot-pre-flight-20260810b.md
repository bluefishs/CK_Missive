# 重啟 Pre-Flight —— 2026-08-10（第二次，資安變更後）

> 上一份：`reboot-pre-flight-20260810.md`（同日稍早）
> 本份的差別：那之後做了**五個專案的容器重建**（資料層埠改綁 127.0.0.1），
> 以及一連串 owner 回報的缺陷修復。容器被重建過，重啟前必須重驗。

---

## 一、結論

**可以安全重啟電腦。** 八項 pre-flight 全數通過。

重啟後只需做一件事：跑 `bash scripts/checks/run_fitness_daily.sh`（12 步，約 1 分鐘）。

---

## 二、Pre-Flight 檢查結果

| # | 項目 | 結果 |
|---|---|---|
| 1 | 未推送 commit | ✅ 0（七個有 remote 的 repo）|
| 2 | 未提交的本輪產物 | ✅ 0 —— pre-flight 期間抓到 **DT 的埠變更漏提交**（先前的 ✓ 是誤判），已補 |
| 3 | **⭐ 重啟政策** | ✅ 56 容器全數 `unless-stopped`／`always`。**今天重建過的 11 個容器逐一確認**——重建有可能重置這個設定，不驗就是賭 |
| 4 | **⭐ DB volume（L43）** | ✅ 四個 postgres 今天都被重建過，volume 名稱逐一確認與變更前一致；Missive **1994 docs / 49649 KG** 不變 |
| 5 | 資料層埠暴露 | ✅ **GREEN** —— 14 個敏感埠皆僅本機可連 |
| 6 | Windows 排程 | ✅ 23 支 CK 排程全數存活 |
| 7 | 異地備份 | ✅ NAS 30 份 / 14.6 GB / 今日 03:00 |
| 8 | 每日檢核 | ✅ 12 步 all passed |

**業務量基線：1994 docs / 49649 KG**（重啟後應 ≥ 此數）。

---

## 三、本輪異動摘要

### 3.1 ⭐ 資料層不再對區域網路開放（**最重要**）

原本 5 個專案共 12 個埠綁在 `0.0.0.0`，實測**可被利用**：

- postgres：以佈署當時的預設密碼**從 LAN 位址登入成功、讀出業務資料**
- redis：**完全無密碼**，可讀**也可寫**（session 27／token 68／csrf 134／auth 4 個鍵）

能寫入的 redis 比能讀取的 DB 更危險——可竄改 session 與 csrf 資料，
有機會偽造已登入狀態，而稽核紀錄會顯示成合法使用者所為。

| 專案 | 埠 |
|---|---|
| CK_KMapAdvisor | 5436 |
| FT_StorageTank | 5440 / 6390 / 9010 / 9011 |
| CK_PileMgmt | 6381 |
| CK_DigitalTunnel | 15432 / 16379 / 19000 / 19001 |
| CK_Missive | 5434 / 6380 |

**這不是取捨而是漂移**：`CK_lvrland_Webmap` 早就綁 `127.0.0.1`，
同一個 portfolio、同一套架構——有人做對了但沒有擴散。
現由 `service_port_exposure_audit`（weekly 42）持續看著。

複測先前實際成功的兩條路徑：postgres `OperationalError`、redis `ConnectionRefusedError`。

⚠️ **操作順序很重要**：直接 `docker compose up -d` 換綁定會撞 Windows 埠未釋放
（L76 家族），pile 的 redis 因此沒起來。正確作法是 **`stop` + `rm` 後再 `up -d`**。

### 3.2 owner 回報的缺陷（皆已修並實測）

| 回報 | 真因 | 備註 |
|---|---|---|
| 同仁變成代碼／重複編碼 | 三個人各有兩個帳號（4 月已依 ADR-0025 合併），但**分身沒有從人員下拉拿掉**；且 08-04 我把標籤從「姓名 (email)」簡化成只剩姓名，**拿掉了唯一能分辨的資訊** | 修在單一實作處，四個下拉共用 |
| 不該出現 superuser | 種子帳號 2025-12-28 即停用，但過濾沒排除停用帳號 | 用 `is_active`，不特判帳號名稱 |
| 承攬狀態改了沒反應 | **成案其實成功了** —— `promote_to_project` 成案後把 PM 狀態設為 `in_progress`，而前端詞彙沒有這個值，fallback 顯示成「評估中」 | ⚠️ 我第一次診斷成「表單被背景查詢重設」是錯的，已更正（那個缺陷是真的、修法也留著，但不是本症狀的原因）|
| 承攬案件重複 | 兩條建立路徑各自防重、**擋不住彼此** | 已加同一條規則到兩條路徑；重複案件經 owner 決定留 011、010 已刪 |
| 超管帳號無法維護 | 守衛寫成絕對禁止，不管系統裡還有沒有其他可用超管 | 改為只擋「最後一個」與「自己」 |

### 3.3 ⚠️ 連帶抓到走查本身的潛伏缺陷

`ui_smoke_auth.py` 挑帳號只看 `is_admin`、**沒看 `is_active`**，挑中了停用的種子帳號，
導致整套走查認證全滅（PASS 1 / SKIP 16）。

值得記的是引擎報的是 **INCOMPLETE（未驗完）而不是 PASS** ——
認證掛掉時假裝通過，比報錯更糟。修後回到 17/17。

---

## 四、重啟後驗收

```bash
# 1. 容器自動拉回
docker ps --format '{{.Status}}' | grep -c Up                        # 期望 56
docker ps --format '{{.Status}}' | grep -icE 'unhealthy|restarting'  # 期望 0

# 2. ⭐ 業務量（L43 家族唯一可靠訊號）
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -t -A \
  -c "SELECT count(*) FROM documents"                                # 期望 ≥ 1994

# 3. ⭐ 埠綁定有沒有回到 0.0.0.0（compose 已改，理應不會，但要確認）
python scripts/checks/service_port_exposure_audit.py                 # 期望 GREEN

# 4. 五系統：首頁 + API 兩層
for u in missive lvrland pilemgmt digitaltwin www; do
  echo -n "$u 首頁 "; curl -s -o /dev/null -w '%{http_code}\n' https://$u.cksurvey.tw/
done
for u in missive lvrland pilemgmt; do
  echo -n "$u API "; curl -s -o /dev/null -w '%{http_code}\n' -X POST https://$u.cksurvey.tw/api/auth/me
done   # 期望 首頁 200 / API 401

# 5. 每日檢核
bash scripts/checks/run_fitness_daily.sh
```

### 若 host:8001 不通而公網通（L76 殭屍埠）

```bash
docker restart ck_missive_backend
```

先等 30 秒（可能只是啟動未完），仍不通再重啟。本輪重建後端三次、每次都撞到，屬常態。

---

## 五、已知且刻意保留的紅燈

| 項目 | 為什麼留著 |
|---|---|
| weekly 35 SSO 覆蓋率 | 種子帳號 `admin@example.com` 未綁 SSO。**它現在已是停用狀態**，且超管守衛已放寬，owner 可自行刪除或維持現狀 |
| daily YELLOW `CK_SSO_JWKS_URL` | compose 有注入、`.env` 無值（prod 暫關 JWKS 路徑），非故障 |

## 六、待 owner 的後續（非阻斷）

- **Redis 設密碼** —— 改綁定後已不對外，屬縱深防禦
- **DB 密碼輪換** —— 需同步更新所有消費端，工程量最大；暴露面已關閉故可緩
- **洪慶忠的 `role='admin'`** —— owner 已確認是預期值，程式行為已對齊，無待辦

---

## 七、收尾覆盤複驗（2026-08-10 17:40，零 app 變更）

上面那些是「做完當下」量的；這一節是**幾小時後回頭再量一次**的結果，因為
「改完是好的」與「它現在還是好的」不是同一件事。

| 面向 | 複驗結果 |
|---|---|
| 五系統公網 | 首頁 + `/api/health` 兩層皆 200 |
| 容器 | 56 支、0 非健康、0 exited |
| 業務量 | documents **1995**、KG **49649**、承攬案件 88、在職帳號 10（總 16） |
| daily fitness | **12/12 all passed** |
| producer watchdog | **31 GREEN、0 blind spot**（另 1 項「月度架構覆盤」未驗完＝無近期事件） |
| 走查（5 repo） | **全部 0 fail**：Missive 17+87／lvrland 2+61／pile 2+36／DT 2+27／CK_Website 2+8 |
| Windows 排程 | **23 支全 GREEN**（含把「內容 FAIL」與「任務沒跑」分開判） |
| 共用模組 drift | GREEN（5 repo `.shared-*` 全同步） |
| 跨 repo 連續性 | GREEN（五 repo 皆與 origin 同步、無停在半途的工作） |
| 靜態檢查 | tsc EXIT=0、`app/**` py_compile 0 fail |
| 資料層埠 | GREEN（14 個敏感埠僅本機可連） |
| 異地備份 | NAS 30 份、509MB、今日 03:00 由排程寫入 |

### 本次複驗新發現（皆非阻斷）

1. **`backups/manual/` 從來沒有 gitignore 規則** —— 已補（見 `.gitignore`）。
   ⚠️ 08-05／08-07 兩份業務資料 CSV **已在版控中**，本輪未動：`git rm --cached`
   只讓它從未來的 clone 消失、歷史仍在，真要清除得改寫歷史 → 屬 owner 決定。
2. **`paths.py` docstring 非 raw string**，每次 import 噴 SyntaxWarning → 已改 `r"""`。
   無害，但它會混在真正的錯誤訊息裡。
3. **PM2 `tmp-docker-probe` 是殭屍條目** —— script 在 Claude session 的 scratchpad 底下，
   已被 `pm2 save` 寫進開機自啟清單，**重開機後會起不來**。
   清理需 `pm2 delete tmp-docker-probe && pm2 save`，會動到所有 repo 共用的開機清單 → 待 owner。
   ⚠️ 同時釐清：PM2 16 支裡 **9 支是 cron 型，`stopped` 是兩次 fire 之間的正常狀態**，
   不要看到一排 stopped 就判成故障。

### 重啟後仍照原步驟

第三、四節不變。額外看一眼 `pm2 list` 是否出現 `tmp-docker-probe` errored——
若已依上面清掉就不會有。
