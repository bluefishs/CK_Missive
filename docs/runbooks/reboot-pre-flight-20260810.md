# 重啟 Pre-Flight —— 2026-08-10

> 上一份：`reboot-pre-flight-20260809.md`
> 本輪主軸：**存量表態全數清空（106→0）＋兩個真實缺陷**（資料層對 LAN 開放、
> 員工「看得到卻用不了」）。

---

## 一、結論

**可以安全重啟。** 八項 pre-flight 全數通過，見下表。

重啟後只需做一件事：看 `docs/health/` 下當日的檢核結果，或直接跑
`bash scripts/checks/run_fitness_daily.sh`（12 步，約 1 分鐘）。

---

## 二、Pre-Flight 檢查結果

| # | 項目 | 結果 |
|---|---|---|
| 1 | 六個 repo 未推送 commit | ✅ 0 |
| 2 | 未提交的非自動產物 | ✅ 0（`shared-modules` 98 項為他人 WIP，日期 1–3 月，**不屬本輪**，不得代為提交）|
| 2b | pre-flight 期間發現並收尾的殘留 | ✅ DT 有一筆**未提交的 react-router v6.30→v7.18.2 大版本升級**（node_modules 已裝、但容器跑舊 build）—— 這正是跨 session 最容易遺失的狀態。已驗證後提交：tsc 0／build 通過／dist 是 bind mount 故即時生效／**走查 27 PASS 0 FAIL**／公網 200 |
| 3 | **DB volume（L43）** | ✅ `ck_missive_postgres_dev_data`，與 compose 宣告一致，**1993 docs**（空殼會是 502 以下）|
| 4 | 容器重啟政策 | ✅ 56 容器全數 `unless-stopped` / `always` |
| 5 | Windows 排程 | ✅ **23 支 CK 排程全數存活**（`windows_task_liveness_audit` GREEN）|
| 6 | 異地備份 | ✅ NAS **30 份 / 14.6 GB**，最新 `ck_missive_backup_20260810_015957.sql`（今日 03:00 排程寫入）|
| 7 | 五系統公網 | ✅ 首頁 200 ×5 ／ **API 層 401 ×3**（首頁 200 不代表後端活著 —— 08-08 lvrland 就是這樣騙過複查）|
| 8 | Hermes / ollama ／共享引擎 drift | ✅ gateway 200、ollama 200、4 容器 healthy、drift exit=0 |

**業務量基線：1993 docs / 49648 KG**（重啟後應 ≥ 此數，明顯低於即為 L43 家族事故）。

---

## 三、本輪異動摘要

### 3.1 存量表態全數清空（106 → 0）

164 支檢核腳本逐一檢視，按「**誰在跑它**」重建 `scripts/checks/README.md`
（原版停在 39 支、「run_fitness 6 step」）。無排程的 25 支逐一寫明理由。

閘門（`declaration_gate.py`，daily step 0）主索引改讀 README。
過程中它**當場抓到我自己**新增的兩支腳本沒進索引 —— 那正是它該做的事。

### 3.2 ⚠️ 資料層對區域網路開放（**待 owner 決定，本輪只報不改**）

既有 `public_exposure_audit` 問的是「五個公開網域的 **HTTP** 開了什麼」，
問得很好，但資料庫埠不在那個座標系裡。新增 `service_port_exposure_audit`（weekly 42）：

| 專案 | 狀況 |
|---|---|
| CK_Missive postgres :5434 | 綁 `0.0.0.0`；**以佈署當時的預設密碼從 LAN 位址登入成功、讀出業務資料** |
| Missive / pile / FT redis | 綁 `0.0.0.0`，**未設密碼**，PING 直接回應 |
| DT / FT / KMap postgres·minio | 同樣綁 `0.0.0.0` |
| 合計 | **5 個專案 12 個埠** |
| **CK_lvrland_Webmap** | **早就綁 `127.0.0.1`** ← 有正確範例卻沒擴散＝drift，不是刻意分歧 |

不在公網（Cloudflare Tunnel 只代理 HTTP），但「不在公網」與「安全」是兩件事。

**為什麼只報不改**：改埠綁定要重建 postgres，而本專案最嚴重的事故（L43）
正是重建時掛到空殼 volume。修法本身只有一行：

```yaml
ports:
  - "127.0.0.1:5434:5432"   # 原為 "5434:5432"
```

host 端工具連 `localhost:5434` 完全不受影響，LAN 即不可見。
**執行前務必先確認 volume 名稱**（見上方第 3 項）。
密碼輪換另案 —— 需同步更新所有消費端。

### 3.3 員工「看得到卻用不了」（已修並部署）

一位員工的 `role='admin'` 但 `is_admin=false`（13 個在職帳號中唯一不一致），
而管理員判定散在四處、規則不同：

| 判定處 | 規則 | 對他 |
|---|---|---|
| `require_admin`（**156 個端點**） | flag 或 role | 可用 |
| `backup.py` / `reminders` / `document_calendar`（**13 個端點**） | **只看 flag** | 403 |

前端選單併看 role → **看得到，點進去就失敗**。這種最難自行診斷：
使用者會以為是自己操作錯。

已收斂為單一實作 `dependencies.is_admin_user` / `is_superuser_user`
（superuser 分開一支：語意較窄，且用在保護性檢查 —— 漏看 role 就是**保護不到**）。
實測以該員工身分：`/api/backup/list` **403 → 200**。
新增 weekly 43 擋第五份判定出現。

⚠️ **待 owner**：修法讓行為與 `role='admin'` 一致。若該員工本來就不該是管理員，
要改的是**資料**（role→staff）不是程式 —— 那是業務判斷，未擅自更動。

### 3.4 走查修復（lvrland / pile）

| repo | 前 | 後 |
|---|---|---|
| lvrland | 59 PASS / 3 FAIL | **61 / 0** |
| pile | 33 PASS / 3 FAIL | **36 / 0** |

- lvrland 走查 token **沒有任何角色宣告** → 所有 admin 頁面對走查永遠是紅的。
  那不是頁面壞了，是走查根本沒進去過。claims 已對齊真實登入、值從 DB 讀真值
  （假造權限會讓走查在真實使用者被擋的地方通過，**比假陽性更糟**）。
- 區域樹 `localeCompare` 崩潰：`city_options` 實際有兩種形狀（字串／`{label,value}`），
  型別檢查看不出來。轉換收在 `utils/filterOptionShapes`，兩個元件共用。
- pile 的 `known_limitations` 寫成純字串**完全不生效**（比對要 route 相等），
  躺了兩個月、頁面照紅。引擎現在直接拒絕執行並指出是第幾項。

### 3.5 價值層退出碼（weekly 41）

`capability_usage_snapshot` 本來就有排程（04:50），缺的是**判定時點到了會不會有人被叫醒**。
底層原本把「資料還在累積」與「Prometheus 掛了」都回 exit 2，
於是包裝只好一律吞成 0 —— 代價是**觀測棧真的掛了也沒人知道**。
改為三態（未到期 0／到期 1／依賴壞 2），三條路徑各自實測。

**判定時點 2026-08-31**：到期那週 weekly 會轉 YELLOW 提請決策。

---

## 四、重啟後驗收

```bash
# 1. 容器自動拉回（Docker 會自己來，只需確認）
docker ps --format '{{.Status}}' | grep -c Up          # 期望 56
docker ps --format '{{.Status}}' | grep -icE 'unhealthy|restarting'   # 期望 0

# 2. ⭐ 業務量（L43 家族的唯一可靠訊號）
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -t -A \
  -c "SELECT count(*) FROM documents"                  # 期望 ≥ 1993

# 3. 五系統：首頁 + API 兩層（只看首頁會漏掉後端掛掉）
for u in missive lvrland pilemgmt digitaltwin www; do
  echo -n "$u 首頁 "; curl -s -o /dev/null -w '%{http_code}\n' https://$u.cksurvey.tw/
done
for u in missive lvrland pilemgmt; do
  echo -n "$u API "; curl -s -o /dev/null -w '%{http_code}\n' -X POST https://$u.cksurvey.tw/api/auth/me
done   # 期望 首頁 200 / API 401

# 4. 每日檢核（12 步，約 1 分鐘）
bash scripts/checks/run_fitness_daily.sh
```

### 若 host:8001 不通而公網通（L76 殭屍埠）

```bash
docker restart ck_missive_backend
```

Windows 的埠轉發在容器重建後偶爾指向已死的舊容器。先等 30 秒（可能只是還在啟動），
仍不通再重啟 —— 本輪就踩過一次「其實只是啟動未完」。

---

## 五、已知且刻意保留的紅燈

| 項目 | 為什麼留著 |
|---|---|
| weekly 35 SSO 覆蓋率 RED | `id=1 admin@example.com` 未綁 SSO 且密碼登入已停用（ADR-0033）＝**現在就已鎖死**。這是測試種子帳號，處置需 owner 決定（綁定或 `is_active=FALSE`）。留著紅燈正是這條檢核存在的意義。 |
| weekly 42 服務埠暴露 RED | 見 §3.2 —— 修法要重建 postgres，屬破壞性操作，待 owner 授權。 |
| daily YELLOW `CK_SSO_JWKS_URL` | compose 有注入、`.env` 無值（prod 暫關 JWKS 路徑），非故障。 |

**紅燈不消，是因為它們指向的問題還在。** 為了讓畫面好看而消掉紅燈，
就是把訊號變回噪音 —— 那正是本專案反覆記的教訓。
