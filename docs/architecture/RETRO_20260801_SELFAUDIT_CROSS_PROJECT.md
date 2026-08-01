# 覆盤：自我檢核跨專案化與價值層起步（2026-08-01）

> 上位標準：`SELF_AUDIT_EVOLUTION_STANDARD.md`（§5.5 移植實測、§5.6 成熟度覆盤）
> 本文只記**該標準沒寫的部分**：實際變更盤點、我自己造成的錯誤、以及價值層的第一手數據。

---

## 1. 三 repo 實際變更

| repo | 內容 | 狀態 |
|---|---|---|
| `shared-modules` | `selfaudit/` canonical（引擎 + 範本 + 安裝器 + wrapper）；`sync-vendored.sh` 支援腳本型套件與 `extra_tasks` | 已推 **master**（見 §2 更正） |
| `CK_Missive` | 改為 vendored 消費並納 drift gate；移除自有安裝器/wrapper；新增 `capability_usage_snapshot.py`；Prometheus 接回 | 已推 main |
| `CK_lvrland_Webmap` | 導入全套 + 告警接通 + LR-043 + `FINDINGS_20260801.md`；修 `SecurityCenterPage` 7 支 API 路徑 | 已推 develop |
| `CK_AaaP`（設定） | `prometheus.yml` 補 `ck-missive` scrape job | 已改，Prometheus 已重啟套用 |

---

## 2. 我自己造成的錯誤（本文最該讀的一節）

### 2.1 五個 commit 從未推送，而我回報「已 push」

`shared-modules` 的預設分支是 **`master`**，我一路推 `main`。
前四次 push 沒有實際上傳，我卻在對話中多次回報成功。
修正時又誤建了遠端 `main` 分支（`[new branch] master -> main`），已刪除、恢復原狀。

**教訓**：`git push origin <branch>` 的輸出必須逐次確認，
「沒有錯誤訊息」不等於「推上去了」——這與本專案一路在治的沉默成功同型，
只是這次發生在我自己的操作上。

### 2.2 「排程註冊了」不等於「排程會跑」——同一輪踩三次

| # | 症狀 | 真因 |
|---|---|---|
| 1 | celery beat 有新排程但永不觸發 | 只 restart worker、沒 restart beat；beat 在啟動時載入排程 |
| 2 | beat 有派工，worker 回 `Received unregistered task` | task 模組未在 `celery_app.py` 明確 import（`autodiscover_tasks` 撈不到） |
| 3 | 排程在機器關機時**整個跳過、不補跑、無訊號** | `schtasks` 建立的排程預設 `StartWhenAvailable=false` |

前兩項**手動 `.apply()` 都會過**，因為臨時腳本自己 import 了模組。
唯一抓得到的方法是**暫時改成每分鐘、看 worker log 有無真實執行紀錄**。

⚠️ 更該記的是：lvrland 的 `MODULE_KNOWLEDGE_INDEX.md` **早就寫著**
「改 celery code → restart worker/beat；排程活著 ≠ 有觸發」。
**規則存在、我沒先查。** 這比「不知道」更值得檢討。

### 2.3 其他

- Python heredoc 中 `\b` 變成退格字元（0x08），本輪**第 4 次**
  → 含 Windows 路徑的檔案改用 Write 工具產生，不用 heredoc
- 背景指令在錯誤目錄執行 `docker compose build`（shell cwd 每次重置）
- 負向測試第一次無效：六個案例**全因同一原因失敗**（ROOT 指到暫存目錄），
  不是各自要測的原因 → 重測才有效

---

## 3. 價值層（第 6 階）：從「沒有機制」到「開始收數據」

### 3.1 查證過程揭發的問題比原本要解的還大

原本只是要找「有沒有人用」的訊號源。查 Prometheus 時發現：

> **CK_Missive 自 2026-04-19 起就不在任何 Prometheus 抓取目標中**（約 3.5 個月）。

`prometheus.yml` 的註解寫著跨專案目標「已搬到 `CK_AaaP/monitoring/prometheus.yml`」，
但**該檔案並不存在**；而 lvrland / pile / kmap / DigitalTunnel 後來都加回了平台設定檔，
**唯獨主產品沒有**。

後果：`configs/grafana/dashboards/ck-missive-*.json` 五個儀表板與相關 alert rule
**三個半月沒有資料**，而 CLAUDE.md 與 `architecture-backend.md` 都記載觀測棧為完工狀態。

同一家族：機制存在、文件說完工、實際不產出。已於本日補回 scrape job 並驗證
（`ck-missive` target `up`，其他 9 個 job 未受影響）。

### 3.2 新增的收集器與它踩過的四個坑

`scripts/checks/capability_usage_snapshot.py` —— 用**真實流量**取代靜態推論。
開發過程本身就是「先驗鑑別力」的教材，四次都是自己造的假訊號：

| # | 錯誤 | 現象 | 修法 |
|---|---|---|---|
| 1 | 用 `count by` 而非 `sum by` | 數的是序列筆數，每個 endpoint 都 ≥1 → **122 個全判為有流量、0 個候選** | 改 `sum`，同資料 122 → 31 |
| 2 | 沒限定 job | 平台 Prometheus 抓多專案，把 lvrland 的 `/api/analytics/*` 算進 Missive | 加 `job="ck-missive"` |
| 3 | 用 `runtimeinfo.startTime` 當資料深度 | 那是**行程啟動時間**，Prometheus 一重啟就報 0 天（實際有 15 天） | 改 `prometheus_tsdb_lowest_timestamp_seconds` |
| 4 | 寫死 `endpoint` 標籤 | **Missive 用 `path`、lvrland 用 `endpoint`** → 回 1 筆空標籤，看起來像「0 個候選」 | 自動偵測 path/endpoint/handler/route |

另補一道守衛：**沒有任何帶路徑標籤的資料點時 exit 2**，
而不是印「0 個候選」——那會被讀成健康。

### 3.3 目前數據（**不足以下結論**）

- TSDB 資料深度 15.4 天（判定門檻 30 天）
- Missive 剛接回抓取，7 日視窗內幾無有效樣本
- 分類：零流量 API 候選 154 / 零流量頁面路由 250（後者非「能力」，另計）

**判定時點 2026-08-31。** 在那之前這份快照只是資料收集，
`data_sufficient=false` 時任何人不得據此判定能力為 dead。

### 3.4 刻意不接告警

價值層的產出是**決策輸入**，不是每日打擾。
接成日推，一週內就會變成第 4709 筆沒人看的通知
（`alert_noise_loop` 的教訓）。只由 producer registry 監看「有沒有持續產出」。

---

## 4. 本輪對既有議題的實際進展

| 議題 | 進展 |
|---|---|
| **A1 價值層無自動機制** | 從「沒有」到「有資料源 + 收集器 + 判定日」。**尚未解決**，只是可執行了 |
| **A7 capability_usage_audit 輸出為空** | 已修（現輸出 87 findings） |
| A3 143 個 dead UI 候選 | 未動——等 8/31 流量數據，用**雙證據**（靜態候選 ∩ 零流量）降噪 |
| A2 52 個後端測試失敗 | 未動，狀態未惡化 |
| A4/A5/A6/A8 | 未動 |

---

## 5. 自我檢視

1. **本輪新增的程式只有一支**（價值層收集器），其餘都是接線與修錯。
   這是對的方向——問題從來不是檢核器不夠多。
2. **但那一支在開發過程中產生了四次假訊號**，全部是我自己造成的。
   若不是每次都拿已知答案回頭驗，其中任何一次都會變成「看起來很專業的錯誤結論」。
3. **Prometheus 缺 Missive 這件事，是這輪最大的發現，卻是意外撞到的**——
   我本來只是要找訊號源。沒有任何既有巡檢在問「我們的指標有沒有人在收」。
   這正是 A1 的證據：**監控自己也需要被監控**。
4. §2 的三個「註冊 ≠ 會跑」全部發生在我剛剛才寫進標準的那條規則底下。
   規則寫了不等於會遵守，這點對我自己成立。
