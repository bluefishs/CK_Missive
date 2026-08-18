# 重啟前置檢查 —— 2026-08-18

> 依 owner「準備重啟電腦」執行。本檔記錄**重啟前的實測狀態**與**重啟後要對照什麼**。
> 前次：`reboot-pre-flight-20260810b.md`

---

## Pre-Flight 結果（全部實測，非憑印象）

| 檢查 | 結果 |
|---|---|
| 六 repo 未推送 commit | **0**（過程中修掉 3 個閘門，見下） |
| 非自動產物未提交 | **0** |
| **DB volume（L43）** | `ck_missive_postgres_dev_data` ✅ 與 compose `name:` 一致 |
| 容器重啟策略 | 55 個全數 `unless-stopped`／`always` |
| **Windows 排程** | **27 支全部 Ready 且已設 `StartWhenAvailable`** |
| 異地備份 NAS | DB dump **33 份**，最後同步 08-18 03:00 `success` |
| 五系統公網 | 全部 **200**（pile 修復後，見下） |

### 業務量基線 —— 重啟後要對照這組數字

```
documents            = 2011
canonical_entities   = 49796
business_data.ok     = True
```

`/health` 的 `business_data` 若回 **503**，代表掛到空殼 volume（L43 的防禦生效），
**不要重試、不要重建容器** —— 先查 volume 名稱。

---

## 重啟前處理掉的三件事

### ① 三個 repo 的 pre-push 閘門擋住推送（都修了，沒有 bypass）

| repo | 閘門說什麼 | 處理 |
|---|---|---|
| `CK_AaaP` | ADR REGISTRY 內容雜湊偏離 | `python scripts/generate-adr-registry.py` 重生後提交 |
| `CK_lvrland_Webmap` | `dossier_freshness`：guardrails 模組 13:49 異動而履歷停在 10:50 | 依閘門寫的順序重生履歷 |
| `CK_lvrland_Webmap` | vendored `ui_page_sweep.cjs` 未提交 | 比對確認**與 canonical 完全一致**＝同步結果不是手改，提交 |

三支閘門都把修法寫在輸出裡。**沒有用 `--no-verify` 或 `BASELINE_SKIP` 繞過** ——
2026-08-04 記錄過「整個 portfolio 被 ADR 閘門擋住數週」，當時的教訓是修它。

⚠️ 那個 vendored 檔若不提交，下一個人會看到「共用模組被改過」而以為有人違反禁令
—— 那正是這個機制要防的事。

### ② pile 公網 502 —— 我第一次診斷對了方向卻修錯容器

症狀：`pilemgmt.cksurvey.tw` 502，而 `ck_pilemgmt-backend-1` 顯示 `Up (healthy)`、
容器內 `/health` 200。判為 L76 殭屍埠。

**但我先修了 backend** —— 而 `docker restart` 之後 host:8004 立刻 200，
表示 backend 那一側本來就沒事（restart 只是順手治好了一個不存在的問題）。

真因要看 cloudflared 的 log 才看得到：

```
originService=http://host.docker.internal:3005   ← 前端，不是 backend 8004
Unable to reach the origin service ... EOF
```

`ck_pilemgmt-frontend-1` 同樣 `Up (healthy)`、同樣映射了 3005，
而 host:3005 = **000**。restart 前端後即恢復。

> **教訓：判定殭屍埠時，要先問「cloudflared 指向哪個埠」，
> 而不是從最像的那個容器開始修。**
> 容器 healthy 是容器內視角，它對 host 埠轉發一無所知 —— 兩個容器都 healthy，
> 只有一個的 host 埠是死的。

### ③ L76 根除路徑（**待 owner 決定，重啟不影響**）

今天 Missive 與 pile 各撞一次殭屍埠。根除要兩步：

1. 把 cloudflared 接上對應的 docker network（我可以做，`docker network connect`，不需重啟容器）
2. 在 **CF Dashboard** 把 origin 由 `http://host.docker.internal:<port>`
   改為 `http://<容器名>:<port>` —— **只有 owner 能做**（tunnel 走 `--token`，
   ingress 在 Dashboard 不在本機）

第 2 步之後流量不再經過 Windows 埠轉發，這一族就消失。

---

## 重啟後驗收（依序，約 5 分鐘）

```bash
# 1. 容器自動回復（Docker 會自己拉，不需人工）
docker ps --format "{{.Names}}" | wc -l          # 應 ≈ 55
docker ps -a --format "{{.Status}}" | grep -icE "unhealthy|exited"

# 2. 業務量 —— 對照上方基線
curl -s http://localhost:8001/health | python -c "import sys,json;print(json.load(sys.stdin)['business_data'])"

# 3. 五系統公網（首頁＋API 兩層，只看首頁會漏掉後端掛掉）
for u in missive lvrland pilemgmt digitaltwin www; do
  echo "$u $(curl -s -o /dev/null -w '%{http_code}' https://$u.cksurvey.tw/)"
done

# 4. 若某系統 502 但容器 healthy → 先看 cloudflared log 找 originService 的埠，
#    再對「那個埠所屬的容器」restart（見上方 ②）
docker logs <該系統的 cloudflared> --tail 20 | grep originService

# 5. daily 檢核（容器內，那是排程實際執行的環境）
docker exec ck_missive_backend bash scripts/checks/run_fitness_daily.sh
```

**Windows 排程不需人工處理** —— 27 支全設了 `StartWhenAvailable`，
關機期間錯過的會補跑（2026-08-12 那次異常關機讓 12 支整批漏跑且不補，
就是因為當時沒設；已於 08-02～08-12 補齊並實測）。

---

## 待辦（重啟不影響，供後續接手）

### 待 owner 決定

| 項目 | 說明 |
|---|---|
| **報價單版面** | 08-18 已上線輸出功能（以 owner 提供的範本為底）。請開 `/erp/quotations/167` 按「輸出報價單」看一份，版面要調就說改哪一格 |
| **L76 根除第 2 步** | CF Dashboard 改 origin（見上方 ③） |
| **`ck-kv-snapshot`** | wrangler 走**互動式 OAuth**、PM2 非互動環境拿不到 session → CK_Website 的 KV 備份停在 07-18。兩條路：①改用非互動憑證並注入 PM2；②移出 PM2 由具 OAuth session 的環境跑 |
| **兩個鎖死的 admin** | id 29/30（cks3401／showlin272）未綁 SSO，ADR-0033 停用帳密登入後**現在就登不進去**。本人用 Google 登入一次即自動綁定，或標 `is_active=false` |
| **馮俊翔的假信箱** | `staff_馮俊翔@example.com` |
| **3 筆懸空 case_code** | `CK2025_PM_02_001`／`CK2026_PM_01_008`／`_009` 指不到 pm_cases。真因已根治（手動建承攬案件改用 GN 產號），既有 3 筆改名涉及多表引用 |
| **`CK2026_PM_01_006`** | PM 標 `contracted` 但財務端完全不存在，合約金額 33 元 |

### 其他 repo（非本 repo，重啟不影響）

- `CK_PileMgmt` 工作樹 9 項未提交、`CK_DigitalTunnel` 10 項未提交 —— 屬各自 repo 的 WIP
- pile sweep fail=36、DT sweep fail=27（頁面層真實故障，各自 repo 處理）

### 觀測中

- **價值層判定**：`capability_usage_snapshot` 判定時點 2026-08-31
- **毛利可算 23%**（下限 20%）—— 分母 13 筆執行中案件，成本可來自估列／應付／核銷／帳本
- **公司留成比率**目前 **0**（不扣）。要生效在 `/admin/site-management` 把
  `erp_company_profit_rate` 改為 `10`，改完立即生效
