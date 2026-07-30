# 重啟 Pre-Flight Checklist — 2026-07-30

> 本輪主軸：**「沉默成功」大掃除** — 一天之內揭發並根治四個「元件回報成功、實際沒做／做錯，
> 錯誤被吞掉或誤標」的缺陷，並把教訓制度化（契約規則 4 + 3 個新 fitness 護欄）。
> 前一份：`reboot-pre-flight-20260728.md`

---

## ⭐ 重啟後最高優先 — owner 瀏覽器實測（3 項，headless 無法代行）

### A. 核銷全鏈路（本輪修最多的地方）
> **先 `Ctrl+Shift+R` 強制重新整理**（本輪多次 build，舊 bundle 會看不到新功能）

1. `/erp/expenses/6` → 應看得到**收據影像**（已驗 API 回 200 image/jpeg 178KB）
2. `/erp/quotations/167` →「費用核銷」分頁應列出 `DN03384512 $520`，且**該列可點入**開 `/erp/expenses/6`
3. `/erp/ledger` → `expense_invoice` 分錄應有「**檢視來源**」按鈕
4. `/erp/expenses` → 工具列應有「**批次掃描**」（拍一張→自動建檔→接著下一張）
5. 手機掃案件 QR → 登入後應**直接回到帶 case_code 的核銷頁**（returnUrl 修法）
6. 桌機核銷建立頁 → 掃描卡片右上角「**用手機拍照上傳**」QR

### B. Missive auth 修法實測（**自 07-28 起仍未驗，最高優先**）
直登 Missive → 停在 `/taoyuan/dispatch` → **閒置逾 1 小時** → 回來操作
→ 應背景無縫恢復、不再彈「安全憑證已過期」。
- **通過** → 一次做齊 lvrland → pile → DT propagation（範圍已縮小，見下）+ TTL 統一 60min
- **不通過** → `git revert 5bff56d5`

### C. 承攬案件 187 財務紀錄
`/contract-cases/187` →「財務紀錄」→「**建立報價並綁定此案**」→ 存檔後財務紀錄應接通。
（同狀況另有 188 / 190 / 191，fitness step 74 每日監測）

---

## 本輪已完成（全 push origin，工作樹 clean）

| 項 | commit | 部署狀態 |
|---|---|---|
| 覆盤 + auth propagation 前置複核 + 治理儀表板 L73 第三案 | `98bb9dcb` | 文件/腳本 |
| package-lock 同步 | `5e884f92` | — |
| **pattern frontmatter 引號逃逸失控根治（134MB 單檔）** | `cbef195f` | ✅ 檔案修復即時生效 + 碼修已 rebuild |
| I3 propagation 預寫修法（刻意不入主產品） | `d6df15d9` | 文件 |
| 承攬案件補 case_code 欄位 + cross_module_lookup fallback | `d5260298` | ✅ build + rebuild |
| **異地備份「看起來沒在跑」根治（UTF-8 BOM）** | `9c27555e` | ✅ build + rebuild |
| 登入後回跳 returnUrl（手機掃 QR 深連結） | `a2202962` | ✅ build |
| 核銷 QR 入口擴增 + 列印版 + fitness step 75 | `41c72c9b` | ✅ build |
| 建立頁「用手機拍照上傳」交接 QR | `99964ba2` | ✅ build |
| **發票辨識全滅根治（zbar/tesseract/libGL + 視覺模型）** | `b1fc517b` | ✅ rebuild |
| **核銷存檔 409 假重複根治（items lazy-load）** | `70184600` | ✅ rebuild |
| cf_tunnel_verify 空跑根治（三層）+ fitness step 76 | `62bfa9a0` | ✅ rebuild |
| items 改 lazy=selectin（approve 400 同因） | `da51399c` | ✅ rebuild |
| 契約規則 4 + 07-30 四例案例庫 | `3c115b18` | 文件 |
| 孤兒元件整合優化 + 財務紀錄鑽取 + 審核狀態同步 | `30fe63dd` | ✅ build + rebuild |

---

## 重啟前狀態（2026-07-30 驗證）

- **git**：CK_Missive **未提交 0 / ahead 0**。
  其他 repo：lvrland clean；pile 4（`package-lock` + `.agents/.codex/AGENTS.md` 工具產物）；
  DT 3（同工具產物）；shared-modules 98（**他人 WIP，勿動**）。
- **docker**：**55 容器全 Up、0 非健康**；Missive 全容器 `restart=always`
  （cloudflared `unless-stopped`）→ 重啟自動拉回。
- **DB volume**：`ck_missive_postgres_dev_data`（**L43 正確**，勿誤掛空殼 `ck_missive_postgres_data`）。
- **五系統公網**：missive / lvrland / pilemgmt / digitaltwin / www **全 200**。
- **業務量**：documents **1968** / KG **49487**（持續成長）。
- **shared drift**：`sync-vendored.sh --check` = **GREEN**。
- **新增 3 個 fitness 護欄**：step 74 🟡（4 筆待補，預期）/ step 75 ✅ GREEN / step 76 ✅ GREEN。
- **producer watchdog**：契約覆蓋 51 jobs = 監控 15 + 非producer 38 + **未納管 0**。
- **前端 dist**：`main-BONihQDI.js`（公網取得的即此支，四項新功能已確證在內）。

---

## ⚠️ Watch items（非重啟阻斷）

> **2026-07-30 晚間覆盤更新**：以下 3 項**已全部診斷到可執行**（含精確修法與風險），
> 另新增第 4 項（owner 貼 LINE 告警追出的告警噪音迴圈）。
> 一律以 `docs/architecture/RETRO_20260730_POST_SWEEP_REVIEW.md` §3 為準，本節僅保留原始描述。
> - #1 標案推薦 RED → **經查為誤報**（政策關閉，非失敗）：RETRO §3.1
> - #2 測試 27 紅 → RETRO §3.3（列為 P1）
> - #3 收據路徑前綴 → **1 行修法已定位、現況無髒資料**：RETRO §3.2
> - #4 **新增**：吹哨者每日 66 筆告警、未讀累積 4708、690 筆陳年 pending 事件 → RETRO §3.4

1. **`標案業務推薦` producer RED**：`tender_recommendation_history` 今日 0 筆，
   且該 job `detail=null` **無法區分「合理空」與「真失敗」** → 契約規則 2 未落實之例。
   建議：讓該 job 回傳 `{count, reason}`（重啟後處理）。
2. **`ERPExpensePages.test.tsx` 27 個測試全紅**（經 `git stash` 對照確認為 **pre-existing**，
   hooks mock 缺 `usePMCases`/`useCaseCodeMap`/`useAutoLinkEinvoice`）→
   **此測試檔目前沒有保護力**，建議另開一次修。
3. **smart-scan auto_create 的 receipt_image_path 前綴不一致**：
   auto_create 存 `uploads/receipts/x.jpg`，而 `receipt-image` 端點會再補 `uploads/` →
   `uploads/uploads/...` 不存在 → 該路徑建立的紀錄看不到影像。
   （upload-receipt 端點存 `receipts/x.jpg` 才正確。）**未修，重啟後處理。**

---

## 重啟後驗收 SOP（5 步）

1. **Docker 自動拉回**：`docker ps` 全 Up、0 unhealthy
   （若 ck-ollama Exited → `wsl --shutdown` + 重啟 Docker 引擎，**勿用 `docker restart`**）。
2. **五系統公網**：curl missive/lvrland/pilemgmt/digitaltwin/www + `/api/health`。
3. **L76**：後端若有 recreate，必驗 host `:8001` + 公網皆 200。
4. **drift GREEN**：`bash ../shared-modules/sync-vendored.sh --check`。
5. **⭐ owner 瀏覽器實測**：本文最上 A / B / C 三組。

---

## 相關文件
- 沉默成功契約（**本輪新增規則 4 + 四例案例庫**）：`docs/architecture/PRODUCER_SELF_CHECK_CONTRACT.md`
- auth 修法設計（§3 矩陣 07-29 讀碼修正）：`docs/architecture/AUTH_LIFECYCLE_ROBUSTNESS_DESIGN.md`
- auth propagation 預寫修法：`docs/architecture/AUTH_I3_PROPAGATION_PATCHES.md`
- Tier 3 刻意分歧 registry：`docs/architecture/TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md`
