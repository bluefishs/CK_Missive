# 待辦與待決議題總表（2026-08-19 收斂）

> 建立：2026-08-19
> 用途：這一輪跨越斷電復原、標案三缺陷、ERP 一條龍、既有 XLS 匯入，
> 產生的待辦散在四份文件與十幾個 commit 裡。**這一份是唯一的入口**，
> 不重複內容，只指路並標明狀態。

---

## 📌 2026-08-29 結案總表（owner 授權後執行完畢，逐項已線上驗證）

> 判準：**「已完成」＝ commit + 部署 + 獨立複驗**（L79：寫好＋測試綠 ≠ 在系統裡）。
> 本表只列已走完三步的；仍待 owner 的移到下方「現行待決」。

| 項 | 事實 | 驗證證據 |
|---|---|---|
| **A32** 案號轉換 | 175 筆（pending）＋74 筆（scope all）全數轉 CK 制 | 三表 legacy 殘留 **0**；`legacy_quotation_no` 回溯齊全 |
| **成案批次** | 85 筆乾淨成案；51 筆機械成案後查出同名同年既有案，**已整批撤回** | 撤回交易斷言 51/51/51；91 筆併入 A33 待判讀 |
| **H1** 假 `_PM_` 案號 | 15 筆無上游建案的承攬案號改 GN（八表同步） | 孤兒 **0**；GN 16 筆；竹崎 `CK2026_GN_01_002` |
| **A38** 附件掃描容錯 | `_safe_rglob` 改 `os.walk(onerror=)` | **02:00 無人值守實證**：`attachments_files: 1559`（原 120） |
| **A38 觸發器** | 上傳檔名 UTF-8 位元組封頂 200 | 回歸測試 2 項；新檔不再長出 >255 bytes |
| **A39** 殭屍排程 | `CK_Missive_Daily_Backup` 已刪除（171 天連續失敗） | `schtasks /query` 查無此任務 |
| **A40①** 備份狀態檔 | `BackupScheduler` 成功/失敗都寫 `_backup-status.json` | 實檔：`result: ok, ran_at: 08-29T02:01:59, saved: 1560` |
| **A40②** 備份守門 | `backup_last_success_timestamp_seconds` gauge ＋ 2 條告警 | `/metrics` 有值、`consecutive_failures: 0` |
| **A41** ck_auth 0.3.0 | wheel 換版＋rebuild | 四行驗證全過；`ck_sso_verify_total{path="rs256"}` 計數會動 |
| **P0-1** 帳本重複入帳 | 刪 2 筆毫秒級重複＋補 1 筆零額；加部分唯一索引 | **AR 對帳歸零**：帳本收入 = 已收款 22,435,123 |
| **P0-2** 應付未入帳 | `_sync_ledger_if_paid`（create 路徑原本完全沒有）＋金額校正 | payable 69 經新路徑校正為 960,000 |
| **對帳告警** | 接進晨報第 0 段（不受主題訂閱篩選） | 實測渲染出 AP/AR 兩則 |
| **M2** 成案觸發判準 | 改「狀態**改變**為 contracted」才觸發 | 91 筆待判讀案件不再被無關編輯靜默成案 |
| **M1/M3** | 編輯不再吞掉「成案未完成」訊息；列表「已承攬・未成案」徽章 | — |
| **H2** 案號空白 | id 190 前導空白已修＋4 個寫入 schema 加 strip | QT2026_020 join 復原 |
| **民國年家族** | client-accounts／vendor-accounts／財務總覽／發票彙總 **四例全修** | KG 頁不動（後端自己 +1911，民國是它的合法契約） |
| **統計卡分母** | client-accounts totals ＋ 統一帳本 `/ledger/totals` | 全量 SQL SUM，不再是「本頁收入」 |
| **年度維度** | 應收/應付明細頁 ＋ 統一帳本 補年度選擇器 | vendor 78：全年度 6 案 vs 2026 年 3 案 |
| **報價流程** | 範本式一頁建單、01 委辦案輸出放開、XLS 範本樣式預覽 | 01 案輸出實測 200；範本預覽回真 PDF |
| **A29** frontend 容器 | 改掛 `frontend/dist`（映像只剩 nginx 外殼） | 內網 :3000 bundle 與 dist hash 一致 |
| **排程視窗** | 16 支 Interactive → S4U（NAS 相關刻意排除） | 白天 cmd 視窗來源清零 |
| **AutoStart 假失敗** | `CK_Missive_AutoStart` 永遠 result=1 **而容器其實全部正常啟動** —— PowerShell 對 native 指令用 `2>&1`，每行 stderr 被包成 ErrorRecord 使 `$?` 為 false，即使 docker 退出碼是 0（而 docker compose 的進度訊息**本來就走 stderr**）。改 `exit $LASTEXITCODE` | 端到端觸發實測 **result=0**；排程稽核 RED 7→6。<br>⚠️ **這是 A39 家族的第三型**：①路徑不存在（真失敗、沒人看）②工作被接手（假失敗、該刪）③**動作成功但退出碼騙人**（假失敗、該修）—— 三者在稽核上長得一模一樣，都只顯示「這支紅了」 |
| **B2** 報價單附件 | 複核**早已完成**（帳目過期） | `AttachmentPanel` 已接 |

### 結案總表（續）—— owner 逐項指示與跨 session 互查的產出

| 項 | 事實 | 驗證證據 |
|---|---|---|
| **161 未收款對不上** | 同一個詞兩種算法：詳情頁用「合約額−已收款」＝15,915,000，而 receivable 分頁與 client-accounts 用「已請款−已收款」＝2,680,000 | 已對齊全系統定義，並補「未請款」讓兩條等式在畫面可驗算 |
| **發票統計卡** | 前端 reduce 當頁 20 筆而發票實有 48 筆 | 實測修法前顯示 1,892,988、正確值 **7,258,898**（少 74%）；後端補分頁前 SQL SUM |
| **統一帳本** | 無年度篩選、卡片只能標「本頁收入」 | 新增 `/erp/ledger/totals`（濾鏡與 /list 共用 builder）＋年度選擇器；實測 2026 支出 112,124 vs 全部 3,286,496 |
| **明細頁年度** | 應收/應付明細頁補年度維度（後端本就支援，缺前端接線） | vendor 78 實測：全年度 6 案/60,196,000 vs 2026 年 3 案/40,666,000 |
| **XLS 範本呈現** | 建單前無處可看正式版面 | 新增 `/erp/quotations/template-preview`（空白範本經同一條 LibreOffice 鏈轉 PDF），實測回真 PDF |
| **開票防呆** | 累計開票 > 合約額 110% 即擋 | 存量掃描零誤傷；線上實測擋下超限請求 |
| **應付上限稽核** | weekly 78 `payable_budget_ceiling_audit` | 5 筆 YELLOW（委外經費未填），零 RED |
| **模型下架偵測** | weekly 79 `llm_model_availability_audit` —— 補 A31 那個 27 天盲區 | NVIDIA 確認下架（同家族候選已列）；Groq 403 判 YELLOW 不下結論 |
| **委託單位關聯** | 我 08-28 新增的建單頁用自由文字、不寫 FK，正持續產生「只有文字無連結」的案件 | 改主檔 Select＋inline 新增；順帶補後端 `create` 的 FK→名稱回填（`update` 早有而 create 沒有 ⇒ 報價單客戶抬頭會空白） |
| **digest 回填（L96）** | drain 刪除與 send 之間無事務性，送不出去即永久遺失 | `restore_digest` ＋回歸測試 2 項；**寫完當天就攔下我自己的清理動作**（18 則真實告警，含 3 則跨 repo 送來的） |
| **告警長期記憶** | 跨 repo 治理告警的唯一入口只活在 48h TTL | `logs/digest_history.jsonl` append-only；端到端實證落檔 |
| **AutoStart 假失敗（L95）** | 永遠 result=1 而容器全部正常啟動（PowerShell `2>&1` 陷阱） | 改 `exit $LASTEXITCODE`，觸發實測 1→0，稽核 RED 7→6 |
| **scope 使用量觀測** | B9/A11 決策所需的實際資料（此前只有會被淹沒的 log） | `service_token_scope_usage{scope}` counter，**實證會動**（非只驗程式碼存在） |
| **L76 首次外部證據（L94）** | 兩筆公網 502 期間 `cron_events` 顯示排程照跑無空窗 ⇒ backend 活著、CF 打不進來 | 由 CK_Website 的 edge Worker 持續監測提供；**`deploy-public.sh` 的單次 curl 驗證會漏掉間歇性殭屍埠** |

> **本輪跨 session 互查的結構性收穫**：三條判準寫進 `verification_signal_too_coarse` 記憶檔
> （第六型量測工具在待測對象上失效／第七型「同一指令的兩個世界」＝隱式參數／
> 正向控制與負向對照），三條教訓入冊 **L94–L96**。
> ⭐ 最值得記的一句（CK_Website）：**「分析出一個陷阱不會讓人免疫於它，只會讓人在事後認出它」**
> ⇒ 判準要寫成**事後可執行的檢查**，不是「要記得小心」。

---

### 公文 6 個欄位：schema 收得到、ORM 沒有（2026-08-29 weekly 83 抓到）

`DocumentBase` / `DocumentUpdate` 宣告了 **contract_case（承攬案件）／doc_word（公文字）／
doc_class（公文類別）／priority_level（速別）／creator（建立者）／user_confirm**，
而 `OfficialDocument` ORM **一個對應欄都沒有**（也沒有改名版本，逐一比對過）。

⇒ **API 收得到但存不進去；回應也永遠不含它們。**

實測後果（不是推論）：`DocumentDetailPage` 與行事曆的 `useIntegratedEvent`
都在**讀** `document.priority_level`，而它永遠是 undefined ⇒ 每次都落到
預設值 `|| 3`。**使用者看到的速別從來不是真的，而畫面上看不出來。**

這是 `model_response_field_reach_audit`（weekly 61，管 ORM→API 沒到達）的
**反方向**：API→ORM 沒到達。同一個家族，先前沒有守門。

⚠️ **需要 owner 決定，我不會自己做**：修法是加 ORM 欄位 + Alembic migration
（資料模型變更），或反過來從 schema 移除這些欄位（等於承認這些業務欄位不做）。
兩條路的差別是「速別要不要真的能用」，那是業務決定不是技術決定。

---

### ⚠️ 後端事件迴圈整天反覆停擺（2026-08-29 發現，根因未明）

CK_Website 的跨平台探針回報 `/api/auth/sso-bridge` 每天約 15% 的 502，
四個平台都會中。追 missive 這一側的結果：

**排程漏失率有明確的起始日期**（`health_check_broadcast` 每 5 分鐘一次，
統計「間隔 > 6.7 分＝漏掉至少一次」）：

| 日期 | 執行 | 空窗 | 漏失率 |
|---|---|---|---|
| 08-24 | 285 | 3 | 1.1% |
| 08-25 | 287 | 1 | 0.3% |
| 08-26 | 287 | 2 | 0.7% |
| **08-27** | 272 | 17 | **6.2%** |
| **08-28** | 260 | 24 | **9.2%** |
| **08-29**（半天）| 145 | 20 | **13.8%** |

**而 CK_Website 的 502 資料正好從 08-27 開始**（15.5% / 15.8% / 12.9%）。
兩個獨立來源、同一個起始日、同向的量級 —— 這是同一件事。

單次空窗 7～16 分鐘，全天散佈。cloudflared 側對應
`Unable to reach the origin service ... EOF`，24h 內 780 行，
**單一分鐘最高 76 筆**（叢發，不是穩定低頻）。

#### 已排除的解釋

* **不是部署**。實測一次已知部署：容器 `05:10:00` → app ready `05:10:32`，
  該次只產生 **8 行錯誤、橫跨 18 秒**。⚠️ 我一度估「每次 5–6 分鐘 × 8 次
  ≈ 45 分鐘」——**錯了 10 倍**，因為我拿 5 分鐘週期的排程去推，漏一次
  就看起來像 6 分鐘。**量測工具的解析度比事件粗**（同 CK_Website 的
  15 分鐘探針看不到 5 分鐘叢發）。
* **不是排程量變多**：逐日 job 執行次數 1129 / 1129 / 1135 / 1120 / 1106，
  無變化。
* **不是長時間 job**：今日 >20 秒的 job 只有 6 個，解釋不了 20 次空窗。
* **不是容器重啟**：`RestartCount=0`。
* ⚠️ 我一度想用「排程秒數漂移＝行程重啟」當簽名，**自己推翻了**：
  今日漂移 28 次，遠多於部署次數 ⇒ APScheduler 本身就會漂。

#### 2026-08-29 取證結果（44 分鐘密集取樣）

每 15 秒一筆、連續 **179 筆**：

| 指標 | 值 |
|---|---|
| HTTP 200 | 177 / 179 |
| 延遲中位 / p95 / 最大 | 80ms / 122ms / **499ms** |
| 超過 1 秒 | **0 筆** |
| 非 200 | 2 筆（14:34:54、14:35:09）|
| 窗口內排程空窗 | **1 次**（14:31:06 → 14:40:15）|

⭐ **那 2 筆失敗與那 1 次空窗，都夾著新加的 `scheduler_start` 標記
（14:35:15）—— 亦即它們全部是我自己的部署。** 標記在加入的當天就
證明了它的用途：在此之前，那兩筆會被讀成「間歇性故障」。

⇒ **44 分鐘密集取樣中，零自發性停擺、零慢回應。**

#### 這個結果證明了什麼、沒證明什麼

**證明了**：部署造成的中斷是 ~20–30 秒的立即拒絕（連線被拒，不是變慢），
而且現在可以從事件流裡辨識出來。

**沒證明**：今日空窗率約每小時 1.4 次 ⇒ 44 分鐘的期望值約 1 次，
而我觀察到的正好是 1 次（我的部署）。這個結果**同時相容於**
「所有空窗都是部署」與「真有停擺而我剛好沒撞到」。**分不出來。**

⇒ 先前那張 08-24~08-29 的漏失率表（1.1% → 13.8%）**請當作未確認**：
我今天部署約 10 次，足以主導那個統計。有了 `scheduler_start` 標記，
**明天的資料不需要任何額外工作就能乾淨區分兩者** ——
扣掉標記前後的空窗，剩下的才是真停擺。

#### 未確認的假設（不當結論用）

宿主資源競爭：08-27 起連續三天都有 session 在跑重負載
（tsc/npm build/playwright，一度 35 個 chrome 程序）。當下量測
CPU 22%、RAM 45.7/63.8 GB，**不擁擠**——但那是我沒在跑建置的時候量的，
證明不了尖峰時的狀況。

⚠️ **這一項需要 owner 知道，因為它是使用者可見的**：從 www 跳轉子系統時
約每 7 次撞到 1 次 502。而它**不是我今天才造成的**，08-27 就開始了。

下一步（我還沒做）：在停擺當下抓後端 thread stack / 宿主 CPU，
才分得出「事件迴圈被阻塞」與「整個容器被 descheduled」。

---

### 廠商身分矛盾 3 筆——其中一筆是兩個不同的人（weekly 70，2026-08-29 實跑）

`vendor_identity_ssot_audit` 報 **3 筆「同一張單、兩個名字」**：

| 應付 | 自存文字 | FK 指向 | 判讀 |
|---|---|---|---|
| #47 | 竣吉不動產估價師 | 竣吉不動產估價師事務所（id=4）| 像是同一家的簡稱 |
| **#39** | **林晉廷** | **林宥廷測量技師事務所（id=71）** | ⚠️ **晉 vs 宥 —— 兩個不同的人** |
| #51 | 銢欣有限公司乃耳企業社 | 銢欣有限公司（id=76）| 像是兩家併寫 |

⚠️ **#39 是最嚴重的**：不是名稱變體，是**不同的名字**。若 FK 是對的，
那筆應付的文字寫錯了人；若文字是對的，那筆錢正被算到別人頭上。
**系統無法自己決定誰對**，需要人核對原始單據。

同時 `vendor_contract_payable_consistency`（weekly 69）報 **3 筆
「有應付卻沒有合約經費」**，皆為 `CK2024_01_01_002`、金額各 **$1**、
各 1 期 —— 金額 1 元看起來像佔位資料而非真帳，但**那也是需要人確認的**
（要嘛補合約經費，要嘛刪掉那三筆佔位）。

⚠️ **更正一個我差點寫錯的因果**：這兩個紅燈**不是**被我今天弄壞的 runner
藏起來的 —— 損壞是今天才造成的，先前的 weekly 會跑到它們。
我的損壞是會讓它們**從今以後**看不見。**紅燈存在多久、有沒有人看過，
是另一個問題**（`fitness_daily` 有連紅 2 週進 digest 的機制，但那管的是
daily 不是 weekly）。

---

### 跑測試套件會吃光生產資料庫的連線額度（2026-08-29 實測）

`max_connections = **50**`（不是 PostgreSQL 預設的 100 —— 有人調低過）。

跑完整 pytest（4,353 passed / 12 分 46 秒）期間：

* `alembic upgrade`、`psql` **都連不進去**：`FATAL: sorry, too many clients already`
* 6 小時內被拒 **257 次**，最早 15:05 本地
* 168 小時內總共 267 次 ⇒ **不是長期問題**，是測試期間的急性事件
* 測試結束後連線降到 **21/50**，`psql` 立刻可用 ⇒ **因果確認**

⚠️ **服務本身沒有中斷**（公網 3/3 200、五容器 healthy）——
既有連線池能用，只有**新連線**進不去。所以它不會被 healthcheck 看到。

#### 為什麼這是真問題

測試用的是獨立資料庫（`ck_documents_test`），但**同一台 postgres 伺服器**，
共用同一組 `max_connections`。⇒ **跑測試會讓生產後端拿不到新連線。**
若後端此時需要擴充連線池或重連（例如某個連線斷了），就會失敗。

#### 但它**不是** 502 的根因

時間分佈對不上：502 的排程空窗從 **08-27** 開始，而 `too many clients`
在 168 小時內只有 267 次、其中 257 次集中在今天 15:05 之後。
⇒ 兩者是不同的事，不要因為都跟連線有關就併成一個。

#### 可能的方向（需 owner 決定，我不自行更動基礎設施）

1. **提高 `max_connections`**（50 → 100/150）—— 最直接，但每個連線有記憶體成本
2. **測試用獨立的 postgres 容器** —— 徹底隔離，但多一個容器
3. **限制測試的連線池大小**（`pytest` 的 DB fixture 加 `pool_size`）—— 不動基礎設施
4. **不在營運時間跑完整測試** —— 迴避而非解決

⚠️ 我傾向 3 或 1，但那是取捨不是技術問題：3 會讓測試變慢，1 會吃記憶體。

---

## A. 需要 owner 決定（我不會自己做）

| # | 議題 | 為什麼需要你決定 | 詳見 |
|---|---|---|---|
| A1 | **實際執行匯入**（彙整表 277 列／回簽 5 檔） | 寫入業務資料的時機是你的判斷（可能想先確認備份）。功能已驗證可用 | `QUOTATION_LIFECYCLE_PLAN` §4 |
| A2 | **報價單狀態機**是否採 `draft → issued → signed → confirmed` | 動的是既有 75 筆 `confirmed` 的語意周邊 | 同上 §1.2 |
| A3 | **可見性策略** A（只加篩選鈕，建議）／B（預設只看自己） | B 會讓 77 張 `created_by` 為 NULL 的舊資料在預設檢視中消失 | 同上 §2.2 |
| A4 | **77 張報價單的 `created_by`** 留 NULL 還是回填 | 回填需要你指認每張是誰開的，我無從得知 | 同上 §2 |
| A5 | **回簽是否為成案的必要條件** | 若是，只能對新案件生效（既有 88 件無一有回簽檔） | 同上 §1.2 |
| A6 | **兩支 Logon 排程需提權啟用** | `Enable-ScheduledTask` 一般權限回 `Access is denied` | `unexpected-shutdown-recovery` §0 |
| A7 | **發票號在哪** | 兩份彙整表 25 欄逐一確認**都沒有發票號**，只有發票日期 | `QUOTATION_LIFECYCLE_PLAN` §6 |
| A8 | **角色模型**：先做 A（`position` 表達職稱）還是直接 B（RBAC） | 取決於人資站點的時程 —— **順序不能顛倒** | `ROLE_MODEL_PLAN` §4 |
| A9 | **`D:\tmp` 18 個檔案**（7/14 起累積）是否清理 | 非本輪產生，但確實是資料四散的來源 | — |
| A10 | **✅ 已由 pile session 處理（08-24：62 個端點收斂、真缺口 319→161），可降級。**原文：**CK_PileMgmt 確認有公開外洩，而它沒有 session 在處理** —— **完整診斷已落檔：`PILE_AUTH_GAP_20260821.md`**（含公網實測證據、48 條控制點端點、⚠️ 含爬蟲任務 cancel/pause/resume 等**控制**類、修法判準）。2026-08-21 再次公網實測未帶憑證仍 200（22 縣市控制點統計、含衛星追蹤站）| 2026-08-21 跨 repo 探測：395 條無認證端點，其中含 **11,025 個控制點**的資料。其餘四個 repo 當日都已開 session 自行處理，pile 沒有 ⇒ **需要你指派**。工具已可直接用：`AUTH_AUDIT_CONTAINER=ck_pilemgmt-backend-1 python scripts/checks/public_endpoint_auth_audit.py`（⚠️ 先依判準 11 由 pile 自己列白名單） | 本檔判準 11 |
| A11 | **`require_scope` 的 token→scope 對照要不要做**（原 B9 升級為需決策） | 跨 repo：`MCP_SERVICE_TOKEN` 由 Hermes／LINE／CK_Website 共用，改成多把或帶 scope 宣告要各消費端同步改。2026-08-21 已先讓它**出聲**（每次通過都記 log 說明未做對照），不再只寫在註解裡 | 本檔 B9 |
| A12 | **CK_Website 沒有異地備份** | 四系統的 SSO IdP。08-11 已知 `ck-kv-snapshot` 失敗（PM2 非互動環境缺 `CLOUDFLARE_API_TOKEN`），最新可用備份停在 07-18；NAS 上完全沒有目錄 | `RETRO_AND_PLAN_20260824` |
| A13 | **dataform frontend／ORS 埠是否收斂** | 收斂會移除 CLAUDE.md 明載的「從別台機器開 UI」功能。⚠️ ORS `0.0.0.0:8080` 自區網 `/ors/v2/health` 回 200 ⇒ 別人可用我們的路徑運算資源（§0） | 同上 |
| A14 | **dataform 的 NAS 備份路徑與 push 授權** | 動到共用資源與遠端 | 同上 |
| A15 | **pile 的 82 條公開業務查詢是否去識別化** | 已補 60/min 防爬取；公開與否屬產品決策 | 同上 |
| A16 | **DT 點雲／裂縫影像的內容認證** | 08-09 判為產品決策；**新論據＝頻寬成本**（§0） | 同上 |
| A17 | **`FT_StorageTank` NAS 備份停在 54 天前，且該專案無 session** | 需指派 | 同上 |
| ~~A18~~ | ~~**L43 的 503 防禦只覆蓋了一半**~~ | **2026-08-26 由 CK_AaaP 推翻前提，已撤銷**。我原本要 owner 去 CF Dashboard 查「該 tunnel 的 health path 指向哪一個」—— **那個角色根本不存在**。他們從外部打四條路徑證明：任意路徑都被原樣轉發到同一個 origin service，由應用決定回什麼 ⇒ CF Tunnel 的 ingress 是 **hostname → service** 的映射，**它不會挑一個 health path 去探 origin**（除非另掛 CF Load Balancer 並設 origin health monitor，那是 LB 的設定不是 tunnel 的）。⇒ 容器 healthcheck 指 `/health`（正確、實測 `ok=True docs=2023 KG=49919`）與 CF 是**兩件互不相干的事**，L43 的防禦沒有缺口。`configs/cloudflare-tunnel.yml` 不生效仍然是事實（已在檔頭標明），但它不生效**不代表有另一份設定在別處決定 health path** | 無需 owner 動作。⚠️ 副產品已落地：他們同時指出本站 **SPA catch-all 讓任意路徑回 200 + text/html**，而 `/api/*` 才回 404 JSON ⇒ **「200 就是通過」會把 catch-all 讀成認證繞過**。已加進 `probe_fingerprint_guard`（weekly 67）當第二種指紋 |

| A19 | **「假死自動復原」現在是空的 —— 要不要補回來** | `ecosystem.config.js` 宣告的 `health-watchdog`（每 2 分鐘探 `/health`、連 2 次失敗就重啟）**沒有在 PM2 上跑**（`pm2 jlist` 的 14 支全屬別的 repo）。容器端看似有覆蓋其實沒有：healthcheck 只會把容器標成 **unhealthy**，而 **Docker 不會因為 unhealthy 就重啟容器**（`restart: always` 只在程序結束時作用）⇒ 一個「還活著但卡住」的 backend 會停在 unhealthy 不動。08-24 那次「56 容器 0 非健康」量的是**狀態**，不是**復原能力**。三選一：① `pm2 start ecosystem.config.js --only health-watchdog`（最快，但 PM2 是第三個排程層、只有註冊覆蓋沒有執行結果哨兵）② 加 container autoheal ③ 明確接受「假死靠人看」並把 `health-watchdog.sh` 歸檔 | `ecosystem.config.js` 檔頭（2026-08-27 已標註三支的實際接手者）|
| A20 | **CSP 轉強制的時機** | 判準已經可查證：`increase(csp_violations_total[7d]) == 0`，**且 backend 起來要滿 7 天**（counter 隨重啟歸零）。最早可判日 **2026-09-03**。已知一筆違規已修（`accounts.google.com/gsi/style`，`style-src` 已補）。轉強制只改一個參數名，回退成本很低 —— 但要你決定何時開那個維護窗 | `docs/runbooks/csp-report-only-to-enforce.md` |
| A21 | **Facade B 方案 60 天 trial 已到期 28 天** | 到期日 2026-07-30，儀表板 §10 一直列著「待 owner 結案」。建議（RETRO_20260730 §4 已寫）：**全保留 + 停止設成長目標 + 往後新增 facade 須先有 ≥3 既存 caller**。這不需要新的分析，只需要你說一句「就這樣」，然後把它從 §10 拿掉 —— **一個永遠不結案的待辦，會訓練人忽略整張待辦表** | `RETRO_20260730_POST_SWEEP_REVIEW.md` §4 |

| ~~A22~~ | **✅ 2026-08-29 已修**（migration `20260829b001`：`created_at` 的 server_default 改為 `timezone('UTC', now())`，兩欄同基準）。**既有 1,185 筆不回填** —— 它們是已過期的歷史 session，回填等於改寫稽核軌跡，而「哪些是舊基準」本身是有用的資訊（判準＝`created_at` 是否早於該次部署）。**認證邏輯刻意不動**：它自洽且在運作，改它才會傷到使用者。原文：**`user_sessions` 的 `expires_at` 與 `created_at` 存在不同時區** | 2026-08-27 實測同一列：`created_at=11:26:33`（DB 本地 Asia/Taipei，`server_default=func.now()`）而 `expires_at=04:26:33`（Python `datetime.utcnow()`）⇒ **每一筆 session 一建立就「已過期 7 小時」**，欄位型別是 `timestamp without time zone`，沒有任何一端會做轉換。**應用本身是一致的**（`session_repository` 兩處都用 `UserSession.expires_at > datetime.utcnow()`），所以功能正常 —— 壞的是**任何拿 `expires_at` 跟 DB `NOW()` 比的東西**：`admin_backup_smoke_test.py:55` 就是這樣寫的，它永遠找不到有效 session、每次都新插一筆（靠 fallback 才沒出事）；`ui_smoke_auth.py:130` 的註解已經記過同一件事。⚠️ **我沒有動它** —— 時區慣例屬「帳號／權限架構」，而本專案 SSO 反覆回歸（L74／L78／L80）的教訓都指向同一件事：這一區改動的失敗不在 happy path。要修的話兩條路（統一為 UTC ／統一為 DB `func.now()`），**都需要先盤點所有讀這三個欄位的地方**，是獨立一輪的工作 | 本輪由 owner console 的 `auth/renew 401` 追出（該 401 本身來自 CK_Website 的 IdP 端，Missive 側無對應錯誤；11:26 有新 session 建立＝已重新登入自行復原）|

| A23 | **4 個權限沒有任何角色拿得到 —— 命名怎麼收** | 2026-08-27 七層鏈路盤點。`hasPermission` **只對 superuser 短路，admin 走正常過濾** ⇒ 這四個功能除了超級管理員之外沒有人做得了。**`projects:write`**（erp/expenses 的 approve／batch-approve／reject／delete 四支端點＋前端「新增承攬案件」與費用審核）與 **`admin:access`**（ERPEInvoiceSyncPage 管理區塊）**兩份 SSOT 都沒有這個名字** ⇒ 權限編輯畫面不會列出，**任何人都無法授予**；**`operational:write`／`operational:approve`** 在兩份 SSOT 裡都有、只是還沒分派 ⇒ 會以「未分派紅點」出現，你在畫面上就能給（⚠️ 但對應端點只要 `require_auth`，目前是前端擋、後端不擋）。**待你決**：`projects:write` 改成 `projects:create`／新開 `expenses:approve`／或補進 SSOT；`admin:access` 多半應改成 `admin:settings` | `scripts/checks/permission_unreachable_baseline.json`（每條註明理由）；檢核＝`role_permissions_consistency_check` 第 5 項 |
| A24 | **兩位 admin 的實際權限是唯讀 6 項** | 張坤樹（id 29）與賴秀玲（id 30）role='admin'，而 `users.permissions` 只有 `documents:read／projects:read／agencies:read／vendors:read／calendar:read／reports:view`，**角色定義是 33 項**。兩人 `last_login` 皆為 NULL ⇒ 從沒登入過，所以沒有人發現。成因同 A25：改角色不會改既有使用者的權限。**待你決**：在 `/admin/permissions/admin` 按「同步至所有用戶」即可補齊（會一併影響其他 3 位 admin，但他們已經是 33 項、屬「已對齊」會被略過）| 2026-08-27 盤點；新的 `pending_sync_users` 計數會顯示 admin=2 |
| A25 | **6 位在職業務同仁的權限尚未套用角色定義** | 你 08-27 11:22 把「業務同仁」設成 14 項含 `vendors:create/edit`，但 `update_role_permissions` 只寫角色定義表 —— `role_permissions` 只在**建立新帳號**那一刻被讀一次。曾廷睿／邱元宏／張浩翊／馮俊翔 各 8 項（缺 6）、**王駿穠與賴柏霖各只有 5 項唯讀**（缺 9，連 `documents:create` 都沒有）。何丞穎 `permissions` 是 NULL 但已停用、不受同步影響 | 修法已上線：該頁現在會顯示「尚未套用到 N 位在職使用者」，儲存時也會提醒。按右上角「同步至所有用戶」執行 |

| ~~A26~~ | **✅ 2026-08-29 已收斂**（owner 裁示「erp權限收斂」）。⚠️ **不是掛頂層單一權限** —— 我第一版把整個 ERP router 鎖在 `reports:erp:view`，實測會造成回歸：`site_navigation_items` 裡各 ERP 頁面**要求的權限本來就不同**（client-accounts／vendor-accounts／quotations→`reports:finance:view`；assets→`reports:assets:view`；其餘→`reports:erp:view`），而 staff **有財務檢視、沒有 ERP 檢視** ⇒ 他們看得到「委託單位帳款」選單、點下去卻 403。改為**各子 router 掛該頁面本來就宣告的那一個權限**（導覽表是既有 SSOT，API 對齊它，不另發明一套）。**A24/A25 的前置條件也已滿足**：實測 5 位 admin 皆為 33 項含兩個 ERP 權限、superuser 走短路 ⇒ **沒有把任何人鎖在外面**。原文：**⚠️ ERP／財務資料現在沒有被角色保護** | `erp/` 端點 **60 支只有 `require_auth`**（4 支 `require_permission`、1 支 `require_admin`）。實測 uid=7（`role='staff'`、`users.permissions` 只有 5 項唯讀、**選單完全看不到 ERP**）直接打 API：統一帳本 200／5 筆、營運帳目 200／3 筆、報價單 200／5 筆、ERP 財務總覽 200 ⇒ **唯一的屏障是「選單看不到」，而選單不是安全機制**。修法是把 router 從 `require_auth` 改為 `require_permission("reports:erp:view")`（加在 **router 層**，逐一改會漏）。⚠️ **這會改變現況行為**，需要你先確認「ERP 資料本來就不該人人可見」；⚠️ 且**順序不能顛倒** —— 目前連兩位 `admin` 都只有 6 項唯讀權限（A24），端點一鎖他們立刻被擋在外面，**必須先同步使用者權限再鎖端點** | `ROLE_MODEL_PLAN` §6.1／§7 階段 0 |
| A27 | **角色扁平：三個職能角色要不要開**（owner 08-27 提「財務角色／高階主管／ERP 財務與營運等管理」） | 現況 `reports:erp:view` **只有 `admin` 這一個角色擁有** ⇒ 想讓財務看 ERP 的 9 個選單，唯一做法是給 `admin`，**順帶給 23 個系統管理選單＋使用者權限管理＋部署＋備份＋資安**。賴秀玲現在的 role 正是 `admin`。✅ 好消息：`users.role` **沒有任何 CHECK 約束**、`role_permissions` 是普通表 ⇒ **加角色零 schema 成本**，`/admin/permissions/:role` 現成可編輯。建議 `finance`／`ops`／`exec` 三個；**`exec` 刻意設計成全域唯讀**（預設是「不給」而不是「admin 減幾項」，新增功能時才不會自動放行）。**待你決**：三個角色的名稱與中文顯示、`exec` 是否需要簽核類寫入 | `ROLE_MODEL_PLAN` §6.3／§7 階段 1 |
| A28 | **`CK_Missive-SOUL-Mirror-Sync` 這支排程只剩下製造紅燈的功能 —— 要不要移除** | 它跑的是 `sync_soul_to_hermes.sh --apply`，而那支腳本**自 2026-08-02 起被寫成拒絕執行**（commit `53195de1`「把『不應執行』寫成 exit —— 註解擋不住 scheduler」）：目標檔不生效（Hermes `active_profile=meta`，寫的是 root 檔）、前提已被 ADR-CK-003 推翻（坤哥與 meta 是**不同意識體**，內容不同是設計）、真改成寫 meta 會蓋掉 06-16 的業務查詢強制規則。實測 `LastTaskResult=3`，`soul_mirror_drift_check` 也直接印「**不要**跑這支」。⇒ 排程存在的唯一效果是每次稽核固定三個紅燈（Disabled／9 天沒跑／沒補跑），**而沒有任何人能處理它們**，那與「連 9 週 RED 無人知」是同一個下場。⚠️ **2026-08-27 我先把它啟用了，那是錯的** —— 我只看了稽核的紅燈，沒有先問這支排程在做什麼；發現後已還原為 `Disabled`。刪除動作被權限守衛擋下（正確），因此列為需你決定。**還原用**：任務 XML 已備份於 `%TEMP%\soul_mirror_task_backup.xml`（3,356 bytes）| `schtasks /delete /TN CK_Missive-SOUL-Mirror-Sync /F`；腳本本身留在 repo 不動 |

---

| A29 | **`ck_missive_frontend` 這個容器：健康、陳舊、外面連不到、也不在使用者路徑上 —— 要不要留** | 2026-08-28 實測四件事合起來才看得懂：① `docker ps` 顯示 **Up 8 days (healthy)**，容器內 `wget /nginx-health` 也回 `healthy`；② **但發布出去的埠是死的** —— `curl http://127.0.0.1:3000/` 回 `000`（連不上），因為執行中的容器仍是 `80/tcp → 3000`，而容器內 nginx 聽的是 3000；③ **它沒有任何 mount**，供的是 image 裡烘進去的內容，`index.html` 日期 **Jun 2**（三個月前的 build）；④ **公網不是它在供** —— 公網 index.html 引用 `assets/main-NZ6nPzVL.js`，與我剛 build 的本地 dist **完全一致**，而 `frontend/dist` 是 bind mount 進 **backend**（`docker-compose.production.yml:310`），由 FastAPI 供 SPA。<br>⚠️ **我自己的半接通**：08-27 我把 compose 從 `"3000:80"` 改成 `"3000:3000"`，**但沒有重建容器** ⇒ 修法在檔案裡，不在系統裡。<br>⚠️ **而我不建議現在重建** —— 重建之後它會變成「一個能連的埠，供著三個月前的應用」，那比一個死埠更危險。<br>⇒ 真正該問的是**這個容器還該不該存在**：沒有 mount、沒有流量、內容陳舊，而 healthcheck 永遠是綠的。 | **待你決**：①移除它（compose 拿掉該 service）②保留但重建＋改為掛 `frontend/dist`，讓它真的能供最新版 ③維持現狀並在 compose 註明「刻意不使用」。<br>⚠️ 另註：它綁的是 `0.0.0.0:3000` 而非 `127.0.0.1`，與 08-10「資料層全綁 127.0.0.1」的處置不一致（雖然目前那個埠是死的） |

| A30 | **`actual_llm_provider` 空了 27 天 —— 根因已定案，修法二選一需你決定** | 每日 pipeline 的 `shadow_baseline` 長期 RED（真人平均 19.1s／合成 40.4s），而**指不出是哪個 LLM**：`provider` 欄只是通道標籤（web→`gemma-local`），真答案在 `actual_llm_provider`，**最後一次有值是 2026-08-01**。<br>**根因（已驗證，非推論）**：合成跑在 `agent_orchestrator.py:457` 的 `asyncio.create_task(_run_tool_loop())` **子任務**裡，而 `set_actual_provider` 就在那個子任務的 context 副本中執行。六行腳本實測：async generator **會**把 ContextVar 傳回父層，**`create_task` 與 `gather` 都不會** ⇒ 父層的 `fire_shadow_trace` 永遠讀到 None。<br>⚠️ 過程中我三個假設錯了兩個（`wait_for` 阻斷／走 stream fallback），一個因為**我自己剛部署過、日誌只剩一分鐘**而驗不了。現場證據：容器起來 13 分鐘內 30 次查詢、**5 次 `synthesis_end`**，而同期 trace 仍全空。 | **待你決**（動到核心推論接線，我沒有自行實作）：<br>**①（正解）** ContextVar 改存**可變容器**，請求進入時設一次 —— 子任務共用同一個物件，改它父層看得到；但要動請求生命週期。<br>**②（一行）** `shadow_logger` 在 ContextVar 為空時退回 `connector._last_provider`（該屬性已存在，`agent_orchestrator:80` 正是這樣取 model_used）—— 但**跨併發請求會互相污染**。本站真人一天 2 次、污染機率低，可是那正是「日後沒人會質疑的錯數字」。 |

| A31 | ⭐⭐ **兩個雲端模型都已下架，agent 已在本地慢速備援上跑了約 27 天 —— 換成哪一個要你決** | 追 `actual_llm_provider` 為何全空時追到的，**比原本要查的嚴重得多**。<br>**現場日誌**：`Synthesis timed out after 35s` → `Groq circuit OPEN → skip 直接走 NVIDIA` → `NVIDIA circuit OPEN → skip 直接走 Ollama`。<br>**錯誤**：Groq 回 **HTTP 404**、NVIDIA 回 **HTTP 410 Gone**。<br>**已向兩家的 models API 查證（不是推論）**：API key 都有效（models 端點皆回 200），而設定的模型**都不在清單裡**：<br>　· `GROQ_DEFAULT_MODEL = llama-3.3-70b-versatile` → **已下架**<br>　· `NVIDIA_DEFAULT_MODEL = nvidia/llama-3.3-nemotron-super-49b-v1.5` → **已下架**<br>⇒ 每次推論都退到本地 ollama（記憶：p50 52.8s），合成 35s 逾時 ⇒ 答案走 fallback、`actual_llm_provider` 因為 `chat_completion` 從未成功返回而永遠空。<br>⚠️ 這也解釋了 `shadow_baseline` 連續 27 天 RED，以及 `actual_llm_provider` 最後一次有值正是 **2026-08-01**。 | **待你決**：換哪一個模型。<br>Groq 現有可用（實查）：`openai/gpt-oss-120b`／`openai/gpt-oss-20b`／`qwen/qwen3.6-27b`／`groq/compound`<br>NVIDIA 現有 nemotron 系列：`nvidia/llama-3.1-nemotron-70b-instruct`／`nvidia/llama-3.1-nemotron-51b-instruct`／`nvidia/llama-3.1-nemotron-ultra-253b-v1`<br>⚠️ 換模型會改變回答品質與 TPM 限制（`ai_connector.py:60` 的註解記著 llama-3.3-70b 的 TPM 是 12K，換模型要重看那個假設），且**不得引入新增費用**（`development-rules.md` §0）—— 兩家都要確認新模型仍在免費 tier。<br>⚠️ 我沒有自行改模型名：那是**會改變系統行為與成本**的決策。 |

| ~~A32~~ | ✅ **2026-08-28 owner 授權後已執行完畢**：備份（553MB 尾端已驗）→ dry-run 對照一致 → 單一交易寫入（pm_cases 175／報價單 175／承辦同仁 101，交易內斷言全過）→ 獨立複驗 pending 歸零、`legacy_quotation_no` 回溯齊全。批次成案結果：**85 筆乾淨成案**；51 筆成案後查出同名同年既有案（委託名稱變體騙過守衛）**已整批撤回**、40 筆被守衛擋下 ⇒ **91 筆併入 A33**，判讀清單＝`A33_CASE_LINK_REVIEW_20260828.md`。原文（點開 git 歷史可見）： | owner 2026-08-27~28 確立：`case_code` = **建案案號**（案子的身分），而報價單彙整匯入把**報價單編號**寫了進去 ⇒ **175 個已承攬的案子無法成案**（`promote_to_project` 的新規則是「去掉 `_PM_`」，legacy 案號去不了），而它們的畫面看起來流程已經走完。<br>**dry-run 實測**（`scripts/sync/backfill_case_code_ck.py`）：待轉換 175／新案號互異 175／**與既有 292 個案號逐筆實查零相撞**／轉換後可直接成案 95／仍被防重擋 80／缺合約金額 0。<br>要一併替換的引用：pm_cases 175／報價單 175／承辦同仁 101。 | **待你決**：要不要跑 `--apply`。<br>執行前我會先做完整備份並再產一次 dry-run 給你對照。<br>⚠️ 舊編號保存在 `erp_quotations.legacy_quotation_no`（該欄位本來就為此存在）⇒ 轉換後仍可用舊編號回溯，回簽 PDF 掛回不受影響。 |
| A33 | **91 筆（2026-08-28 更新，原估 80）同名的案子：是「已建過只是沒接上」還是「不同案」** —— 逐筆清單含兩側委託單位對照：[`A33_CASE_LINK_REVIEW_20260828.md`](A33_CASE_LINK_REVIEW_20260828.md)。⚠️ 51 筆曾被機械成案又撤回（守衛的「同委託單位」條件被名稱變體騙過：技師本人 vs 事務所、啓/啟相容字），**撤回只撤成案、案號轉換不受影響**。原文： | A32 轉換後仍會被既有防重擋下的 80 筆，判準是「同名 + 同年度 + 同委託單位」。實測訊息長這樣：`同名承攬案件已存在：CK2026_01_01_008（南投縣政府115年度委外辦理圖根點清理…）`。<br>⇒ 多半是**已經建過案、只是 `case_code` 沒接上**，需要的是「接上」而不是「補建」。 | **待你決**：逐批確認後，是把它們的 `case_code` 指向既有承攬案件，還是確實要新建。<br>我不會自己判 —— 判錯會產生兩個代表同一件工作的承攬案件。 |
| A34 | **26 組分身（`B114-B003` vs `B114-B003-0`）怎麼處理** | 匯入只比對**完整** `case_code`，於是彙整表帶子號的那一側被當成新案建立，兩側案名完全相同。<br>⚠️ **26 組的「有碼那一側」都有金流** ⇒ **分身沒有金流是正常的，不要當成漏記帳去補**。<br>⚠️ 也**不要把子號當版次去掉** —— 實測推翻過：`B114-B026`（平鎮區土地協議市價查估）與 `B114-B026-2`（翠64透地雷達）是**完全不同的案子**，去尾碼會造成 4 組硬掛在一起、36 組重複建立。 | **待你決**：逐組確認要合併哪些、保留哪些。<br>合併是**語意變更**（兩筆併一筆），與 A32 的機械式替換風險不同級，應分開決定。 |
| A35 | **3 筆廠商「同一張單、兩個名字」哪個對** | `vendor_identity_ssot_audit`（weekly 70）RED：<br>　應付#47 自存「竣吉不動產估價師」 vs FK「竣吉不動產估價師事務所」<br>　應付#39 自存「**林晉廷**」 vs FK「**林宥廷**測量技師事務所」<br>　應付#51 自存「銢欣有限公司乃耳企業社」 vs FK「銢欣有限公司」<br>⚠️ **#39 是不同的字，不是簡稱差異** —— 比較像掛錯 `vendor_id`，而那代表**那筆錢會算到別人頭上**。 | **待你決**：三筆各以哪一個為準。<br>系統無法自己決定 —— 尤其當兩個名字是不同的人時。 |
| A36 | **金粟科技 320 萬應付（4 期）沒有合約經費** | `vendor_contract_payable_consistency`（weekly 69）：`CK2025_01_03_001` 有 4 期共 $3,200,000 的應付，而協力廠商那邊**沒有填合約經費**。<br>依你 2026-08-27 的規範「**合約經費是上位，應付在它之下執行**」⇒ 那 320 萬**沒有任何上限在管**。 | **待你決**：補填合約經費金額，或確認這個案子不走合約經費管控。 |
| A37 | **`careful-guard` 修好後的誤判要不要收斂** | 該守衛原本沒有 UTF-8 BOM ⇒ PS 5.1 cp950 解析失敗 ⇒ **12,491 次呼叫一次都沒攔到東西**（已修，實測危險刪除指令現在 exit 2 擋下）。<br>**代價**：修好後一小時內就擋下一個正常的 `git commit` —— 因為 commit message 裡引用了危險指令的字面值當說明。守衛掃的是**整個指令字串**，分不出「要執行的指令」與「heredoc／訊息裡的文字」。 | **待你決**：要不要讓它忽略 heredoc 與 `-m`／`-F` 之後的內容。<br>⚠️ **不要因為誤判就關掉它** —— 它壞了 30 天沒人發現，正是因為它從不出聲。目前繞法：`git commit -F <file>`。 |
| **A38** | ✅ **根因已查明並修復：附件掃描的「容錯」從來沒有生效過** （原標題「異地備份 92% 從未備份」**已推翻**，見下）| 2026-08-28 **13:00 續查，兩件事要分開**：<br>**① 真因＝generator 語意，不是路徑、不是過濾條件**：`_safe_rglob` 寫的是 `while True: try: next(it) except OSError: continue`，但包住的是一個 **generator** —— generator 一旦拋出非 StopIteration 的例外就進入 **closed 狀態**，後續 `next()` 只會拿到 StopIteration ⇒ **那個 `continue` 從來沒有讓它繼續過**，**第一個壞 entry 就是掃描的終點**。<br>容器內實測（`ck_missive_backend`）：走訪 **233 entry** 後停在 `2026/02/doc_884/…`（**與 manifest 最後一筆完全相同**），warning **只印 1 次**：`[Errno 5] Input/output error: '/app/uploads/2026/02/doc_885'`，而 `os.walk(onerror=…)` 同一棵樹可掃到 **1,550 檔**。<br>⚠️ 諷刺的是 `_safe_rglob` 的 docstring 指名的壞檔就是 **doc_885** —— **它是為了這個檔而寫的，而它沒有達成它宣稱的目的**；`attachments_latest` 最後修改 5/18（helper 寫於 5/28）也一致。<br>**② ⚠️ 原本的嚴重度判定是錯的 —— NAS 那一份是完整的**：直接清點（不看 `remote_backup.json` 的自我回報）`\CKNAS\…\missive_attachments` ＝ **1,552 檔 / 1,191 MB / 08-28 12:22 新鮮**，含 `_longname_archive`（長檔名那 2 個已打包）⇒ 與 `backend/uploads` 一致。<br>⇒ **異地備份沒有缺口**。壞掉的是**容器內的本機增量快照** `attachments_latest`（120/1,552），那是**第二份副本**。<br>**③ 這順帶回答了原待辦③**：`sync_enabled: False` 關的是 **in-app** `remote_syncer`；NAS 同步實際由 host 的 `scripts/backup/offsite-sync-nas.ps1` 直接鏡像 `uploads` —— **它不經過 manifest 機制，所以沒被這個 bug 波及**。<br>**④ 2026-08-28 晚間與 CK_Website 對帳：兩份診斷都對，解釋的是因果鏈的不同段**。<br>他們主張根因是 **檔名 UTF-8 位元組數 > Linux NAME_MAX 255**；我主張是 generator 語意。實測後**兩者是串聯的**：<br>　　`doc_885` 內正是 **2 個 268 bytes / 118 chars 的檔名**，而**全 `uploads` 只有這 2 個超過 255**，兩個都在 `doc_885`。<br>　　⇒ **NAME_MAX ＝ 觸發器**（它讓 `doc_885` 在 Linux 容器內 Errno 5 不可讀，產生那 1 個 OSError）<br>　　⇒ **generator closed ＝ 放大器**（它把「1 個壞目錄」變成「掃描終止、1,430 檔消失」）<br>**這改變了優先序**：修好 NAME_MAX **不足以防止復發** —— 任何一個檔案因任何原因讀不到（權限／I-O／鎖定／未來的長檔名）都會重演全斷；而修好放大器之後，NAME_MAX 的代價**只剩那 2 個檔**。<br>⇒ 放大器已修（本條）；觸發器（上傳時限制檔名 ≲200 bytes，或附件快照改壓縮封裝）**仍值得做，但不再是資料保護的緊急項**。<br>**判準：一個「只影響 2 個檔」的缺陷，遇上一個把局部失敗放大成全面失敗的機制，就會長得像「92% 的資料沒有備份」。先問哪一段是放大器。**<br>**判準（前一版寫反了，記在這裡）：我用 manifest（代理指標）推論異地備份的狀態，而沒有直接數 NAS。代理指標的失敗形態就是給你一個好看或難看的答案，兩個方向都會誤導。** | **已修**：`_safe_rglob` 改用 `os.walk(onerror=…)` —— 壞目錄記錄後**跳過該子樹並繼續**。<br>容器內以新邏輯實測：**120 → 1,550 檔**，涵蓋 2026/01~08 全部 ＋ `pm_attachments`／`asset_photos`／`receipts`，只損失 `doc_885` 內的 2 個（該 2 個 NAS 端已由 `_longname_archive` 處理）。<br>**回歸測試**：`backend/tests/test_attachment_backup_rglob_regression.py`（3 項）—— 把「doc_885 讀不到」這個物理故障**同時注入 rglob 與 os.walk 兩種機制**，因此與實作選擇無關；修復前 RED（掃到的集合是**空的**），修復後 GREEN。<br>⚠️ **影響面不只附件備份**：`remote_syncer.py` 有 **4 處**呼叫 `_safe_rglob`，同樣受惠。<br>**② 已實證**：08-29 02:00 無人值守執行，`attachments_files: 1559`（原 120）。<br>**① 仍待你決**：`attachments_latest` 舊快照與 7 個 2026-03 目錄快照是舊機制殘留（約 772M）—— **我不會自行刪**（可能是那個時期的唯一副本） |
| ~~**A39**~~ | ✅ **2026-08-29 owner 授權後已刪除**（`schtasks /query` 查無此任務）。原文：**`CK_Missive_Daily_Backup` 這支排程連續失敗 171 天 —— 而備份其實一直是好的，因為工作早就被別人接手了** | 2026-08-28 由 **CK_lvrland_Webmap 與 CK_AaaP 兩個 session 獨立交接同一件事**（AaaP 推得「至少兩個多月」，實際可精確到 **171 天**，見②）（`LastTaskResult=2147942667` ＝ `0x8007010B` ＝ Win32 267 `ERROR_DIRECTORY`）。<br>**① 真因＝排程指向搬家前的舊路徑**：`WorkingDirectory` 與 `-File` 都是 **`C:\GeminiCli\CK_Missive\`**，而該目錄**不存在**（專案已在 `D:\CKProject\CK_Missive`）。<br>**② 失效起點可精確定位**：commit `8a02c0b2`（**2026-03-10**）「專案遷移配置同步」把 repo 內路徑改完了，而 `logs/backup/backup_YYYYMMDD.log` 最後一份是 **2026-03-09** —— **搬家前一天** ⇒ 自 2026-03-10 起**連續失敗 171 天**。<br>⚠️ **`LastTaskResult` 只記最後一次，它答不出「前面幾天如何」** —— 能定位起點靠的是備份目錄裡的**檔案連續性**（lvrland 交接時就提醒了這一點）。<br>**③ ⚠️ 但備份沒有斷 —— 別把這支修好**：本機 DB dump 08-22~08-28 **連續 7 天無缺口**（551MB，與 `RetentionDays=7` 相符），`backup_operations.json` 有 **136 筆連續成功**。<br>**真正的執行者已實證**（不是推論）：`app.services.backup.auto_scheduler.BackupScheduler` —— **FastAPI 進程內的 asyncio task**，由 `backend/main.py:190` 於啟動時拉起，迴圈是 `asyncio.sleep(_get_seconds_until_backup())`。<br>容器日誌（08-28 12:13:51）：`✅ 備份排程器已啟動 (每日 02:00 執行，下次: 2026-08-29 02:00:00)`、`從日誌載入備份統計: 120 次 (成功: 105, 失敗: 15, 連續失敗: 0)`。<br>⚠️ **它不是 cron 也不是 APScheduler** —— CK_AaaP session 在容器內找 cron／crontab 找不到執行者，正是因為它活在應用程式進程裡。dump 檔名時間戳 `015959` 比排程觸發 `02:00:01` 早 2 秒，是 `asyncio.sleep` 醒得略早於 02:00 的精度誤差，與那支排程無關。<br>⇒ **這支是殭屍排程**：它做的事已被接手，**把路徑修好只會變成每天兩次 551MB 的 dump**。<br>**④ 這是「跨檔 SSOT」家族的新成員**：**排程定義在 repo 外，遷移時 git 帶不走它**。`8a02c0b2` 同步了 repo 內的所有路徑，而沒有任何東西會提醒你「還有 9 支 Windows 排程指著舊路徑」。（本次全機掃描：**只有這一支**仍指向 `C:\GeminiCli`。）| **待你決（我不自行刪除排程）**：<br>① 建議 **刪除**：`schtasks /delete /TN CK_Missive_Daily_Backup /F` —— 工作已由容器內 APScheduler 承擔且連續 136 次成功<br>② 或 **停用**（保守）：`schtasks /change /TN CK_Missive_Daily_Backup /DISABLE` —— ⚠️ 但 A28 的判準在這裡會反咬：稽核看到 `State=Disabled` 會報紅，而**沒有人能處理那個紅燈** ⇒ 與 A28 同一個下場，故我建議①<br>③ **配套（真正該做的）**：稽核目前只看得到「這支紅了」，看不到「它指的路徑根本不存在」。建議加一條 —— **登記排程的 `-File` 路徑必須存在，否則 FAIL**，那會在 2026-03-10 當天就叫出來，而不是 171 天後靠別的 repo 掃到 |
| ~~**A40**~~ | ✅ **①②皆已實作並實證**（狀態檔 08-29 02:01:59 `result: ok saved: 1560`；gauge + 2 告警上線）。原文：**備份守門的「解析度」不夠 —— weekly 7 天，而事故的時間尺度是 6 天** （⚠️ 本條 2026-08-28 已**自我更正**，原標題「沒有任何東西在守」是錯的，見③）| 2026-08-28 由 **CK_AaaP session 反問**「後端在跑有沒有東西在守，還是只能看檔案時間戳？」而查。<br>**① 歷史事故是真的**：`backup_operations.json` 120 次 create 有 15 次失敗 —— **2026-05-22~05-27 連續 6 天 `pg_dump failed: No such container`**（PM2 汰換期容器改名），那 6 天**真的沒有備份**，當下唯一的實體證據是 5/27 有人手動做的 `pre_pm2_deprecation` dump。<br>**② 即時層確實沒有**：後端**不 emit 任何 backup metric**；`configs/prometheus/alerts.yml` **24 條規則、零條與備份相關**（`SchedulerJobFailure` 走 `scheduler_job_failures_total`，而備份執行者是**獨立的 asyncio task 不是 APScheduler job**，守不到）。<br>**③ ⛔ 但我原本寫的「三層都沒接上」是錯的 —— 第四層存在，我沒查就下了結論**：<br>　　`scripts/checks/offsite_backup_completeness_audit.py` ＝ **weekly step 45**，commit `7620ccb8`（**2026-08-10**）。當場實測**退出碼 0、四類全 GREEN**：資料庫 dump（30 份／最新 12.4h／**尾端完整性已驗**）／里程碑快照／公文附件／金鑰憑證，而且**依 CONVENTIONS §11 分開讀 `ran_at` 與 `newest_file`**，還跨 repo 報 portfolio 9 個專案。<br>⇒ **它正是 A40 原本要求的形狀，而且早就做好了。**事故（5/22）比守門（8/10）**早 80 天**，所以「當時沒人守」為真、「現在沒人守」為假。<br>**⚠️ 我犯的錯就是我今天對三個 session 講的那件事**：我量了三個地方（metric／alerts.yml／Windows 排程）就宣稱「三層都沒接上」，**沒有問「還有沒有別的地方」** —— 而 MEMORY.md 裡 `offsite_backup_four_classes`（⭐⭐ 異地備份四類缺一不可）記的就是這支。**用「我查過的地方」代表「全部」，是 proxy metric 的另一個方向。**<br>**④ 修正後的真缺口＝解析度，不是有無**：weekly 週期 **7 天**，而 5 月那次事故長 **6 天** —— **同量級 ⇒ 整段錯過是可能的**（且 weekly 本身 08-23 rc=1，尚未逐步核）。| **修法（優先序已因③改變，不再是 🔴）**：<br>① **最便宜且立刻有效**：讓 `BackupScheduler` 成功時也寫一份 `_backup-status.json`（`ran_at`/`newest_file` 分開）—— **AaaP §41 與本 repo step 45 都已經在讀這個格式**，寫了就直接被兩邊看見，不必等 Prometheus。⚠️ 現有那份是 **host 的 `offsite-sync-nas.ps1`** 寫的，涵蓋的是**異地同步層**；**容器內 02:00 產 dump 那層仍沒有自己的狀態檔** —— 而 5/22 斷掉的正是那一層<br>② 補即時層：`backup_last_success_timestamp` gauge ＋ `time() - backup_last_success_timestamp > 26h` → critical<br>　　**判準用「距上次成功多久」而非「上次執行失敗」** —— 後者答不出「根本沒跑」（A39 是每天失敗但備份好好的；5/22 是每天有跑但每天失敗，**兩種都要被同一條規則抓到**）<br>⚠️ **AaaP 送的對稱判準，做①②時都適用**：**修假警報時要問「我是讓它量得到，還是讓它不再叫」—— 只有前者是修。** |
| ~~**A41**~~ | ✅ **已部署，四行驗證全過**（`rs256 fail` 計數會動）。⚠️ W7 判準本身仍被 hs256 探針汙染，待 CK_Website 處理——**兩件事不要混為一談**。原文：**ck_auth 0.3.0 待部署 —— 而 W7 觀察期正在跑，Missive 的資料缺席** （有時間壓力，非純技術債）| 2026-08-28 CK_Website 交接。ADR-0008 **W8（HS256 退場）**要通過 **W7：30 天觀察 RS256 verify 成功率 ≥ 95%**，Day 1 = 08-18 ⇒ **今天 Day 11**。<br>而判準用的 metric `ck_sso_verify_total` **從來沒有任何 backend emit 過** —— `SSO-METRICS-SPEC.md` 裡那段從未被實作。所有 Prometheus target up、Grafana 有 dashboard、告警 health=ok，**因為它們檢查的是「scrape 通不通」不是「那個指標存不存在」——空集合不會讓任何東西變紅**（與本 repo A40 同族）。<br>**已由 L80 的 Tier 1 共享套件一處解決**：`shared-modules/ck-auth-py` 的 `verify_ck_sso_jwt_auto()` 是唯一分流點，加 counter 後四平台同時生效（shared-modules commit `0fe8ace`，測試 12/12）。<br>**pile 與 DigitalTunnel 已部署並實證**：`pip show ck-auth` → 0.3.0、無效 cookie 打 sso-bridge → 401、`/metrics` 出現 `ck_sso_verify_total{path="rs256",result="fail"} 1.0`、Prometheus 由 0 → 2 series，AaaP 的 `CkSsoVerifyMetricAbsent` 告警同步轉 inactive。<br>⇒ **四個消費端裡 Missive 是唯一還沒有資料的**，`backend/vendor/` 仍是 **0.2.0**（落後兩版）。<br>**⚠️ 已驗證的兩個前提**：<br>　① 來源 wheel 存在：`shared-modules/ck-auth-py/dist/ck_auth-0.3.0-py3-none-any.whl`（8,279 bytes，08-28 13:42）<br>　② **舊 wheel 必須刪除不能並存** —— `backend/Dockerfile:34` 是 `RUN pip install --no-cache-dir ./vendor/*.whl`。**理由比「兩個都會被裝進去」更精確：最終生效的版本取決於 shell glob 的『字串』排序**，這次 `0.2.0 < 0.3.0` 剛好對，但那是偶然 —— 例如 `0.10.0` 字串排序小於 `0.9.0`，將來就會靜默裝到舊版。**不可依賴。** **⚠️ 但別期待部署後 W7 的判準就可信 —— 那個比例本身被汙染了**（2026-08-28 CK_Website 查出、AaaP 轉知）：<br>　`ck-sso-contract-probe` 用**自簽 HS256** 每天產約 **192 筆 `hs256 success`**，**系統性壓低 W7 的 RS256 比例**。<br>　而那支探針跑在本機共用 pm2 上，**12:11–12:49 那 38 分鐘沒跑** ⇒ **連汙染本身都有缺口**，當日窗口的比例更不可用。<br>⇒ **部署仍然值得做**（Missive 要有自己的 verify 計數，且四個消費端只剩我們沒有），**但它解的是「我們沒有資料」，不是「W7 的判準可信」** —— 後者要等 CK_Website 處理探針。**兩件事不要混為一談。** | **待你決（與 A38 修復、A40 告警同屬「要不要 rebuild」這一個決定）**：<br>① 換 wheel（`rm` 0.2.0 ＋ `cp` 0.3.0）—— **我沒有自行做**：換了卻不部署會讓 `vendor/` 與運行中容器不一致，而那正是 L51.7.1／`container_image_freshness_check`（weekly 60）要抓的狀態<br>② rebuild + 重啟 backend<br>③ **驗證四行，第 4 行才是判準**（前三行只證明「裝好了」）：<br>`docker exec ck_missive_backend pip show ck-auth \| grep -i version   # 0.3.0`<br>`curl -s http://127.0.0.1:8001/metrics \| grep ck_sso_verify_total    # HELP/TYPE`<br>`curl -s -o /dev/null -X POST http://127.0.0.1:8001/api/auth/sso-bridge \n     -H 'Cookie: ck_employee_rs=not-a-real-jwt' -w '%{http_code}'  # 401`<br>`curl -s http://127.0.0.1:8001/metrics \| grep '^ck_sso_verify_total'  # 計數真的動了`<br>⚠️ **CK_Website 踩過的坑，我們加 counter 時會遇到**：prometheus_client 對已以 `_total` 結尾的名稱會**先 strip 再補**，查 `xxx_total_total` 會讀到 0.0 而讓人以為計數壞了 —— **實際是查錯 series 名**。（A40 我建議的 `backup_last_success_timestamp` 是 **gauge**，不踩這個坑。）|

### 響應式版面（owner 2026-08-29 第 4 條）

| 項目 | 現況 |
|---|---|
| **窄螢幕判準五處全修** | `ResponsiveTable`（23 檔在用）＋四個自己寫 RWD 的頁面原本都只看 `isMobile`；而 `isMobile = !screens.md` 且 AntD 的 md 斷點**就是 768** ⇒ 恰好 768px 時走桌面分支。`EnhancedTable` 08-15 已修過，**沒有擴散**（L98）。實測表格外溢 **9 筆／8 頁 → 4 筆／3 頁** |
| **量測範圍** | 行動量測路由 13 → **31 條業務頁**。原本 18/125，`/pm/cases` 列表根本沒被量、只量詳情頁。擴大後 `/document-numbers`(612px)／`/projects`／`/staff`／`/taoyuan` 立刻上榜 |
| **走查引擎加診斷** | 溢出時一併報出**是哪個元素**（排除單純被子元素撐大的祖先）。先前只說「164px」，定位靠翻程式碼猜。改在 canonical（`shared-modules/selfaudit/src/`），五個 repo 都拿到 |
| **weekly 81** | `responsive_narrow_convergence_audit` —— 掃**全前端**的 `scroll={isMobile ? …}` 形狀。負向對照兩次才成立（首版被自己的註解騙過，L97） |
| ⚠️ **仍未解：報價明細手機編輯** | `QuotationItemsTab` 是可編輯表格（每格 Input），窄螢幕已收掉選填欄、`scroll.x` 900→620，**但 390px 下仍需橫向捲約 230px**。真正的解是窄螢幕改一列一卡的編輯器 —— 另一個工作量級，**未做** |
| ⚠️ **仍未解：/pm/cases/244 整頁溢出 164px** | 三個分頁數值相同 ⇒ 在外框不在分頁內容，非表格（`tableOverflow: 0`）。走查新增的「哪個元素」診斷正是為此加的，**下一輪量測會給出答案** |
| **未做：hideOnMobile 覆蓋率** | 77 個用共用表格的檔，26 個有做窄螢幕欄位收斂、**51 個沒有**（其中 8 個欄位 ≥7，窄螢幕會被均分擠壓到不可讀）。**刻意不自動標記** —— 哪一欄手機上可以不看是業務判斷，自動挑很容易藏掉最關鍵的那欄 |

---

## A′. 2026-08-29 晚間新增（owner 決定）

| # | 議題 | 為什麼需要你決定 | 證據 |
|---|---|---|---|
| **A29** | **91 件「已承攬但未成案」要怎麼處理** | 自動成案**只在狀態由其他狀態改變為已承攬時觸發**，那 91 件早已是 `contracted` ⇒ 觸發條件不會再滿足，需要逐件按「確認成案」。在**會回滾的交易**裡抽驗 6 筆：**沒有任何驗證擋著**（且成案流程會承接承辦、補 `project_id`）。⚠️ **它們正是 `8b5acc26` 刻意撤回、標記「待判讀」的那批** ⇒ 批次成案等於推翻那個決定，而成案不可逆。三選一：全部／只非撤回的／給你清單逐件決定 | 實測 6/6 會成功；⚠️ 我在該次試算中**誤成案了 3 件並已依裁示還原**（L107） |
| **A30** | **`max_connections` 已由 50 提到 100（已套用）—— 其餘調校值要不要一起重估** | `postgresql-tuning.conf` 標明是為「Hardware: 4-8 GB RAM」調的，**實測本機 Docker 可用 23.5 GB、postgres 常態只用 405 MiB** ⇒ `shared_buffers=512MB`／`effective_cache_size=1536MB` 等值同樣是為一台不存在的小機器調的。**我只動了 max_connections**（那是當日實際用罄的那一個），其餘沒動 —— 重估要有 owner 的維護窗 | `configs/postgresql-tuning.conf` 檔頭已記錄證據；weekly 88 守三層一致 |
| **A31** | **3 個 image 未釘版本** | `ollama/ollama:latest`（dev.yml／infra.yml）與 `vllm/vllm-openai:latest`（infra.yml）。`cross-file-ssot-governance.md` 規則 1 明列「跨 repo 共用 image 用 `latest` 會 silent 升版」。釘哪一版要看目前跑的是什麼、以及能不能接受 | 2026-08-29 設定檔整合時掃出 |
| **A32** | **廠商身分矛盾 #39：「林晉廷」vs FK「林宥廷測量技師事務所」** | 成因已查明：應付存的是**當下的名字快照**，主檔後來改名（#39/#51 主檔 3/31 更新、應付 3/17 建立）—— **那是設計如此（稽核軌跡），不是缺陷**。#47/#51 是後綴差異（事務所），可判定 FK 較完整；**#39 是兩個不同的名字**，要看原始單據才知道哪一邊對。⚠️ 外部評估建議「清洗 3 筆徹底更正」**不該做**：若 FK 才是錯的那一邊，蓋掉就等於把錯誤變成唯一事實 | `vendor_name_recorded` 機制（08-27）已讓畫面說出「名稱不符」，前端有橘色標籤 |
| **A33** | **4 筆請款／應付缺付款日期** | 我今天一度把驗證寫成「最終狀態必須有日期」，結果**存量缺日期的紀錄再也無法編輯**（已改為只在異動涉及付款欄位時才檢查）。日期本身仍需有人補 | billing 63/95、payables 72/73 |
| **A34** | **11 件承攬案件有 case_code 但沒有報價單主檔** | 外部評估說「187 案缺 case_code 導致財務空白」—— **前提不成立**，實查承攬案件 175 件、缺 case_code 的是 **0 件**。真正的缺口是這 11 件。它們沒有應收入口 | 2026-08-29 實查 |

| **A35** | **一個存在 4.5 個月的測試 scaffold：11 支 xfail、3 支 skip、只有 1 支真的在跑** | `backend/tests/integration/test_agent_evolution_loop.py`（建立 **2026-04-14**）驗的是 agent 自主進化的**完整鏈路**（orchestrator → self_evaluator → evolution_scheduler → AgentLearning 持久化 → planner inject），而三個 fixture 都是 `pytest.skip("fixture not implemented")` ⇒ **11 支測試從建立至今一次都沒執行過**。<br><br>⚠️ **它比 skip 更難發現**：`pytest.xfail()` 寫在測試主體內，報告顯示 `11 xfailed` —— 既不算通過也不算失敗，連 `-rs` 都不會列出來。而檔案在 `pytest -q` 裡貢獻「1 passed」。<br><br>⚠️ **它宣告的追蹤者沒有在追蹤它**：檔頭寫 `Owner: P1 — 依 MEMORY Pending Work Queue`，而該 queue 現有兩項都不是它，本待辦表在此之前也 0 次提及（同 L99「宣告的執行者不存在」）。<br><br>**三選一**：① 補三個 fixture（Redis／capability tracker seed API／tool executor 替身）讓 11 支真的跑 ② 判定該鏈路不需要整合測試、歸檔此檔 ③ 保留但在檔頭寫明「這是規格不是測試」並從測試蒐集中排除 | 2026-08-29 由「skip 不是通過」的複查掃出。<br>**根因已修**（同日）：weekly 24 的測試基線**原本只解析 `failed`**，`skipped`／`xfailed` 完全不看 ⇒ 「沒有失敗」與「沒有執行」在它眼裡是同一件事。已擴充為一併棘輪（存量列基線不判紅、新增即紅），並讓它 `-rs` 印出 skip 理由。⇒ **A35 之後不會再有第二個 4.5 個月沒人知道的 scaffold。** |

---

### 做不了／不該做（已核實，列此以免重複提案）

| 議題 | 為什麼 |
|---|---|
| **30/60/90 天現金流預測** | 需要「請款的預計收款日」與「應付的預計付款日」。`erp_billings` **根本沒有預計收款日欄位**（只有開單日與實收日），`erp_vendor_payables.due_date` **47 筆裡只有 1 筆有值**。⇒ 拿 1 個資料點做預測是虛構。要做得先補欄位**並且有人填** |
| **應付上限寫入時把關** | `vendor_payable_service` 確實沒有把關（只有事後的 weekly 78）。但實測 **12 張有填上限的報價單，應付合計與上限一字不差地相等** ⇒ 那兩個數字不是獨立的，把關等於拿一個數字跟自己比。要有意義得先回答「上限從哪來」 |
| **應付新增 `linked_billing_id`（收付聯動）** | 新欄位要人填，而本專案剛付過這個代價（承辦同仁欄位 122 張空白）。**一個沒人填的欄位提供的不是精確度，是假的精確度。** 已改用既有事實（同案有無未收請款）做案件層級提醒，涵蓋所有案子且不需任何人多填一格 |
| **抽 `ProjectPromotionService` 重構** | 外部評估說 `CaseCodeService` 「臃腫、難以測試」。實測 `promote_to_project` **229 行裡 84 行是註解，實際程式 145 行**，整檔 736 行。而重構對象是一個**不可逆交易**，風險全落在正確性上，換來零使用者可見效益 |
| **成案時自動初始化里程碑** | `pm_milestones` **0 筆** —— 178 件承攬案件沒有任何一件用過里程碑。自動生成等於往零使用的模組塞 178 組資料；且它建議的「預設三期款框架」是要我自己發明的業務規則，付款條件逐案不同 |
| **廠商名稱資料清洗** | 見 A32 |

---

## B. 已查明根因、尚未實作

| # | 議題 | 根因（已查證） | 規模 |
|---|---|---|---|
| ~~B1~~ | ~~**標案決標資訊全庫 0 筆**~~ | **2026-08-26 查證後根因與原記載完全不同，已修並接上排程**。原記「抓取端只抓招標公告、analytics 在分析從來沒進來的資料」—— **兩句都不準**：① dashboard 實打回 200／0.17s、`total_found=2286`、本週決標 11 筆、得標廠商 top 10 有真實公司名 ⇒ **它是活的**（即時查外部，不讀 DB）；② 真正的斷點是 **`detail_enrichment.py` 從建立起沒有任何人呼叫它**（全 repo 零 import）—— scheduler 的 `tender_pcc_enrichment_job` 跑的是名字很像的另一支（`enrichment.py`，做 ezbid↔PCC 配對）。它一跑就暴露四個 bug：`unit_id` 對 ezbid／pcc 是兩種東西（點分機關代碼 vs base64 pkPmsMain）⇒ org_ok=0；`_pick` 無優先序且命中「**是否**訂有底價」⇒ `base_price='否'`；`bidders` 收到廠商代碼與地址；SQL 參數未 CAST ⇒ 整筆 UPDATE 失敗、**且一筆壞掉後剩下全部陪葬**（統計上長得像「這些案子都沒資料」）| 四個 bug 全修，實測 `org_ok 5/5 enriched 5 errors 0`、`bidders=['合記書局','藝軒圖書','黎明書店']`（與 `tender_company_links` 一致）。已接排程 **每日 03:45**，只跑 ezbid 那一段（`unit_id` 本身就是 org_id、**不打 PCC**、零反爬風險）。⚠️ **`award_amount` 仍會是 0 且那是正確的** —— 實測該案 openfun 有 `決標資料:總決標金額是否公開` 但**沒有金額欄位**，即機關選擇不公開。L77「enrichment 死結」**完全不成立**（08-19 推翻預算那一半，今日推翻 org_id 這一半：實測 3 筆 PCC 詳情頁全 200、orgId 可取）|
| ~~B2~~ | ~~**報價單附件上傳與預覽**~~ | **2026-08-28 複核已完成**（本欄原記載過期）：`ERPQuotationDetailPage` 已有「附件」分頁，用共用 `AttachmentPanel`（抽自 pmCase/QuotationRecordsTab，全前端 9 處附件實作裡唯一四項功能齊全的一份），附件以 case_code 關聯——系統輸出（`generated_quotation`）與客戶回簽（`signed_quotation`）同處可見 | 已完成 |
| ~~B3~~ | ~~**報價單入口在 ERP 側**~~ | **2026-08-27 複核已全數收束**。三段都在 `/pm/cases` 了：新增報價（08-20）／線上填明細（08-26）／**輸出報價單與 PDF（08-27）** —— 最後一段是 owner 指出的：「為何 `/erp/quotations/150` 會輸出報價單與 PDF，此機制應在 `/pm/cases`」。輸出抽成 `useQuotationExport` 兩頁共用（空工項提醒／`Content-Disposition` 檔名／PDF 預覽／blob 釋放時機四件事容易各自演化，複製一份等於承諾兩邊都要記得改）| 已完成 |
| ~~B4~~ | ~~**`/tender/ezbid/A.47.3` 定位不到**~~ | **2026-08-26 查證後原記載只對了一半，已修**。「`A.47.3` 是機關代碼不是標案 id」正確，但它暗示的修法（改路由參數）不成立：`SourceTenderLink` 用 `encodeURIComponent(ezbid_id)` ⇒ 斜線編成 `%2F`、**單段路徑 match 得到**；`LegacyTenderRedirect` 只在純數字時才導到 ezbid，`A.47.3` 走的是 PCC 分支 ⇒ **系統自己產生的連結都沒問題**，那個 URL 來自人手動輸入或舊書籤。DB 實測 ezbid_id 兩種格式：純數字 **37,980** 筆（舊）／`{機關}/{案號}` 含斜線 **11,470** 筆（08-02 站台改版後）| 真正缺的是**查不到時什麼都沒說**：原訊息「PCC 開放資料中查無此標案」①這是 ezbid 路由卻說 PCC，來源講錯；②**沒說出真正的問題** —— 使用者會讀成「這筆資料不存在」，實際上是**編號少了一半**，而那兩件事在畫面上長得一模一樣（同 08-20「空清單退化成數字」、同日 StaffPage「空表格 vs 載不到」）。已改為：偵測「只有機關代碼」的形態並明說、給出「用這個機關搜尋」的出口、外部連結依格式分派（含斜線走改版後的 `/detail/{機關}/{案號}`）。tsc EXIT=0 |
| ~~B5~~ | ~~**08-15 標案寫入 0 筆**~~ | **2026-08-26 查證後原描述兩處不準，已收束**。逐日攤開：08-15(六)／08-16(日)／08-22(六)／08-23(日) 是 0 **而那是正常的**（政府週末不發標，實測平日 780–1939 筆）；**真異常只有 08-17 週一**，而它不在原記載裡 ——原記把正常現象當異常，真正的異常反而沒被記下來。追 `cron_events`：`pcc_today_scrape`（每 2 小時、預期 12 次/日）在 **08-16~08-17 連續 48 小時 0 次執行**，同期 `health_check_broadcast` 跑了 208 次 ⇒ scheduler 活著、只有這一支停了。⚠️ `cron_silent_dormant_check` 門檻 4 小時卻沒報，**為什麼沒報查不出來**（daily 歷史只記步驟名不記內容）| 已加**第九條生命跡象**（commit `8b9e782c`）：既有那條看 `MAX(announce_date)`（政府公告日），而**爬蟲停擺後恢復會一次補回前幾天的 announce_date ⇒ 看起來完全正常**；新條目改看 `created_at` 並只算平日，**刻意不依賴 cron 機制本身**。鑑別力：過去 14 天逐日模擬，08-18／08-19 會報，其餘 12 天 0，**零誤報含所有週末** |
| B6 | **匯出表單格式** | owner 指示「先完成前述整合再議」；已知不輸出委託單位 ID | 待 A1 完成後 |
| B9 | **`require_scope` 是裝飾性的 —— token→scope 對照從未實作** | `_ALL_SCOPES = VALID_SCOPES`，所以 `require_scope("admin:system")` 與 `require_scope("read:kg")` 效果**完全相同**：有 token 就過，從不檢查這把 token 有沒有被授予該 scope | **具體後果**：CK_Website 為了送一則通知呼叫 `/api/notify/digest`（宣告 `admin:system`），實際拿到能讀 KG、改 agent、跑備份的憑證。⚠️ **要修需要跨 repo**：`MCP_SERVICE_TOKEN` 由 Hermes／LINE／CK_Website 共用，改成多把或帶 scope 宣告要各消費端同步 ⇒ **屬 owner 決策**。2026-08-21 已先讓它出聲（每次通過都記 log 說明未做對照），不再只寫在註解裡 |
| B8 | **廠商重複（勤典工程行／勤典測量工程行）** | ⛔ **owner 2026-08-20 決定不做**：「此非系統問題，實為人為填報機制要修正」。量測支持這個判斷 —— 5 組名稱相似裡**只有 1 組是真重複**（台電三個發電廠、工務局與用地科、「楊長燁加李雅倫」「祐鴻+昱緯+建倫」都是有意義的不同），自動判重會產生 4/5 假陽性 | **不要再提議加相似度比對**。另：補建的 137 件邀標案件裡 130 件的委託單位只有文字沒有連結，而 101 個不重複客戶名裡有「何明利」「劉庚霖之繼承人(4人)」「劉進財、孫瑟花」等**自然人地主** —— 那些本來就不該建成「廠商」，自動補建會把資料模型弄錯 |
| ~~B7~~ | ~~**管理動作按鈕對一般使用者可見但按下去 403**~~ | **2026-08-26 收束**。原記的 4 頁實查後只有 `/ai/erp-graph` 真的漏（另三頁都已有 `isAdmin` 且真的用在渲染上）；接著建 `admin_action_visibility_audit.py`（weekly 68）**自動掃全**，另抓到兩個原本不在清單裡的：`/ai/db-graph`（選單權限已是 `admin:settings`、**但路由沒鎖 ⇒ 直接打網址就進得去**）與 `/staff`（選單權限 `projects:read` ⇒ **一般同仁看得到，點進去是空表格＋統計全 0，看起來像「公司沒有同仁」**）| 三頁修法各不相同且都**不放寬端點權限**：erp-graph 分頁依 `isAdmin` 顯示／db-graph 路由補 `roles={['admin']}` 與選單一致／staff **只治症狀**（載不到要說出來、不給必然失敗的按鈕），該不該對一般同仁開放仍是 owner 的產品決策。⚠️ 這支檢核自己踩了兩個坑才有鑑別力，見 `scripts/checks/README.md` weekly 68 |

| B10 | **`scripts/hooks/post-commit-code-graph.sh` 從來沒有被安裝** | `.git/hooks/post-commit` 實際跑的是知識地圖增量更新，裡面 **grep 不到任何 `code-graph`** ⇒ 這支腳本存在於 repo，但沒有任何東西會執行它 | 規模小、風險低。要嘛併進現有 post-commit，要嘛歸檔。**判準是 `scripts/checks/README.md` 已經寫過的那一句：「這支東西壞掉的時候，會有人知道嗎？」** |
| B11 | **「有產出端、沒有消費端」這個維度沒有任何檢核在管** | 2026-08-27 一輪覆盤，**五個發現的形狀完全一樣**：版本綁定沒人帶／治理檢核讀空目錄／前端埠沒人聽而探針探別的埠／CSP 違規沒人看／部署腳本重啟不存在的程序。全部都不會報錯 | ⚠️ **刻意不做成通用掃描**：實測掃 `scripts/`（`checks/` 以外）81 支，25 支完全沒被提到、13 支只有文件提到 —— 但多數是**刻意手動的工具**，逐一核實後真訊號只有 2 個（訊噪比約 1:19）。做成通用告警＝製造沒人看的噪音（同 08-20 那次「48 個 Select 我選擇不交付」）。**建議改為三個窄座標各一支**，都有明確判準、低誤報：① `ecosystem.config.js` 宣告 vs `pm2 jlist` 實際 ② Prometheus metric expose vs 有無 alert／dashboard／檢核在讀 ③ git hook 腳本 vs `.git/hooks` 實際安裝 |

| B12 | **細粒度權限只覆蓋 16 支端點，其餘 478 支是二分法** | 494 支端點裡：`require_auth` **313**（只要登入）／`require_admin` **165**（管理員）／`require_permission` **僅 16**。也就是說 `/admin/permissions/:role` 上調整的 33 個權限，**對絕大多數端點沒有任何作用** —— 真正在決定「誰能做什麼」的是「登入 vs 管理員」這個二分法 | ⚠️ **不建議大規模改造**：把 478 支逐一分權是高風險低回報，而且會產生大量「宣告了但沒有角色擁有」的新缺口（正是 A23 那個形狀）。建議只在**業務上真的需要分權的動作**上加（費用審核、廠商維護這類），其餘維持二分法並在文件寫明這是**刻意的**，不是還沒做完 |
| B13 | **`operational:*` 是前端擋、後端不擋** | `ERPOperationalDetailPage` 用 `hasPermission('operational:write'/'operational:approve')` 隱藏編輯與審批按鈕，而 `erp/operational.py` 的端點**全部只有 `require_auth`** ⇒ 任何登入者直接打 API 都能改。目前沒有實害（沒有 UI 入口），但這是「前端當安全機制」的形狀 | 修法方向：若那些動作真要限權，加在**端點**上；若不需要，前端就不該擋（現況是兩邊說法不同，而使用者看到的是「按鈕不見了」） |

---

## C. 觀察中（不阻斷，但要盯著）

| # | 現象 | 已排除 | 風險 |
|---|---|---|---|
| C1 | **排程被某個程式持續停用** | 非斷電所致（Adobe 2025-01、Zoom 2025-02 也在其中）；事件 ID 142 顯示分散在整個下午 | 輪到異地備份就是那天資料只有一份 |
| C2 | **`ui_smoke_auth.py` 間歇連線失敗** | 非埠耗盡（TIME_WAIT 212／動態埠 16384）、非 postgres 拒絕（log 無紀錄）、非 SSL（`ssl=disable` 同樣失敗） | 它是走查的基礎，壞了整套走查跑不了 |
| C3 | **`llm_quota_check` 曾沉默 3.5 天** | 手動觸發完全正常 ⇒ 排程器沒觸發它 | 已自行恢復（22:16 準時執行），根因未定 |
| C4 | **@768px 版面外溢** | 先前行動量測只看 390px，平板寬度從未量過 | 觀測不告警，屬產品決策 |
| ~~C5~~ | ~~**⭐⭐走查永遠以最高權限跑**~~（**2026-08-27 收束**，見下方說明）| 走查憑證挑的是 `is_admin AND is_active` 的帳號（`ui_smoke_auth.py`）。**一般同仁看到的畫面從來沒有被走查過** | 2026-08-20「同仁變成代碼」就在這個盲區裡：五個人員下拉對 `role='user'` 一律是空的，而走查、tsc、py_compile、模組匯入掃描**全部綠燈**。這不是檢核寫錯，是**座標系裡沒有「非管理員」這個維度** |

---

> **C5 已於 2026-08-27 收束 —— 但先前只做了一半，而那一半看起來很像做完了。**
>
> 08-24 就把身分維度做進引擎了（`ui_smoke_auth.py --role user`、`run.sh` 兩端擋無效身分、
> config 的 5 條 flow 宣告 `roles: ['admin']`）。**做得對，可是沒有任何排程在用它** ——
> `CK_Missive-SelfAudit-Flow` 的參數欄是空的，一年裡每一次走查都還是 admin。
> 「能力有了」與「有人在跑」是兩件事，而前者會讓人以為後者也成立。
>
> 08-27 補上缺席的那一半：
>   · **結果檔依身分分檔**（引擎層，五 repo 共用）。實跑 `--role user` 當場把 `ui-flow.json`
>     蓋成 user 的結果（pass 13/fail 2），而 producer 的門檻是照 admin 訂的 ——
>     **watchdog 會照別人的身分報紅，而檔案裡沒有一個欄位說得出這是誰跑的**。
>     現在 `role` 進 JSON，非 admin 寫 `ui-flow.<role>.json`；sweep 同治（那支引擎
>     先前連 role 這個概念都沒有，更難察覺）。
>   · **排程** `CK_Missive-SelfAudit-Flow-User`（每日 05:10，走 config 的 `extra_tasks`，
>     不手刻 schtasks）。
>   · **接收端** producer registry 兩筆（file_fresh 30h + json_result），門檻與 admin 分開 ——
>     適用 flow 是 15/20，混在同一個座標系會讓「這條本來就不適用」與「它壞了」長得一樣。
>   · **排程稽核** `windows_task_liveness_audit` 的 `SELFAUDIT_TASK_RE` 尾綴改為可選；
>     ⚠️ 改完立刻印出兩次 `CK_Missive flow: pass=20`（兩支任務讀同一個檔）——
>     **我自己當場示範了 L81**，已改為依身分取檔並在訊息帶 `[admin]`／`[user]`。
>
> **首跑結果：一般同仁 GREEN 15/15。** ⚠️ 前一次跑出 2 個 FAIL，逐一查證後
> **兩個都是同一次 Cloudflare 502**（截圖是 CF 的 Bad gateway 頁，`ck_missive_backend`
> 當時被另一個 session 重啟）—— 同 08-19「failure 訊息完全相同就先問是不是同一個上游」。
> 若當成兩個缺陷去修，會修出兩個不存在的問題。
>
> 仍未做：斷言分辨「這個頁面該看不到」與「該看到卻是空的」。現況是用
> `roles` 宣告把不適用的整條排除，那是**迴避**而不是分辨 —— 一條 admin-only 的 flow
> 若哪天對一般同仁開放了，不會有任何人發現它其實沒被驗過。
>
> **2026-08-28 05:10 首次無人值守執行，整條鏈驗完**（此前都是我手動觸發）：
>
> | 環節 | 實測 |
> |---|---|
> | 排程 | `CK_Missive-SelfAudit-Flow-User` 05:10 執行，result=0，下次 08-29 05:10 |
> | 產出 | `ui-flow.user.json` 05:12 寫入，`role=user`，**pass 15 / fail 0 / skip 0** |
> | **不互相覆蓋** | admin 那份仍是 04:19，**沒有被蓋掉**（這正是 08-27 手動實跑時發生的事）|
> | 接收端 | producer watchdog 兩筆皆 GREEN（`file_fresh` 0h／`json_result` pass=15 ≥10）|
> | 排程稽核 | 印 `CK_Missive flow[user]: pass=15 fail=0`，與 `flow[admin]` 分開 |
>
> ⇒ **能力 → 排程 → 產出 → 接收端 → 稽核**五段全部接上且各自可辨識。
> 依 `adr-anti-half-wired-sop` 的「真活」判準，這一條現在才算真的活。
>
> 順帶一提：這個盲區在 2026-08-10 就以另一種形態出現過（員工「看得到卻
> 用不了」，管理員判定有四份規則）。那次修的是**判定邏輯**，08-20 是
> **資料源**——同一個維度缺席，換了個地方長出來。

---

## D. 本輪確立的判準（寫進判斷，不只是紀錄）

1. **「這個東西被誰讀？」** —— 加欄位、組網址、寫規則之後都要能回答。
   答不出來就是只做了一半。本輪三個最貴的缺陷全是這一類。
2. **在有豁免的環境驗證安全機制，等於沒有驗證**（本機 `AUTH_DISABLED=true`
   讓 CSRF 中介層完全跳過，我因此得出「不是認證問題」的錯誤結論）。
3. **同一件事量兩次，兩次一致才算數**（斷電後的排程狀態、間歇性連線失敗）。
4. **查詢加了 `LIMIT` 就不能拿來證明「不存在」**。
5. **build log 說成功不代表東西在映像裡** —— 要進映像 grep 才算數。
6. **要求人先統一格式才能匯入，等於把工作推回給填表的人**
   （`B115-C017a-0` vs `B115-C017-a` 用正規化解決，而非要求改檔）。
7. **「我用什麼身分在驗？」** —— 全部用管理員跑，等於只驗了一種人的畫面。
   與判準 2（在有豁免的環境驗證安全機制等於沒驗證）是同一件事的兩面：
   **驗證環境本身若不具備該條件，結果不成立**。
8. **同一個 queryKey 用不同資料源，等於誰先載入誰說了算** ——
   key 撞號本身不是錯（同一份資料就該共用快取），源不一致才是。
   已由 `queryKey_drift_audit` 的第二種形態擋住。
9. **⭐⭐安全驗證的結論，取決於量測方法本身有沒有先被驗證**（2026-08-21）。
   同一輪有**四次**機會宣告「已經擋住了」而每一次都會是錯的：
   Cloudflare 擋掉 `Python-urllib` 預設 UA（全 403，看起來像應用層擋住）／
   bash `while read` 迴圈裡的 curl 吃掉 stdin（全 000）／連續快打觸發速率限制
   （同樣全 000）／token 解析寫壞（`token=無` 卻仍印 403）。
   **四種失敗都長得像「安全」**，這是與判準 2（在有豁免的環境驗證安全機制
   等於沒驗證）同一族的第三種形態。
10. **CSRF 不是認證** —— `/api/secure-site-management/csrf-token` 是**刻意公開**的
   （L68 自癒需要），未登入即可取得。**判準：帶著公開可取的 CSRF token 之後
   仍然 401 才算真的擋住**；只看第一輪的 403 會得到相反結論。
11. **跨 repo 套用檢核工具，必須先由該 repo 自己列白名單**（2026-08-21）。
   `public_endpoint_auth_audit` 對 lvrland 掃出 147 條無認證，而前幾條是
   `/api/auth/{login,register,refresh,logout}` —— 登入流程本來就該公開。
   ⚠️ lvrland 起初判斷「探測跑在 `enforce_route_auth` 之前」，**那不成立**：
   用與容器啟動指令完全相同的匯入方式重跑，log 印出 `hardened_routes=276`
   而結果不變。**工具沒錯，錯的是拿別人的座標系直接下結論。**
   ⚠️ **座標系有兩半**（lvrland 後續補充並經雙向重現）：白名單一半、
   **認證函式名單另一半**。他們 147 條裡 96 條白名單命中、**~49 條是
   「有認證，但走 service-token 家族」**（`require_service_scope`／
   `get_user_or_service`／`verify_telegram_secret`）而我的預設清單認不得。
   實測補上後消掉 44 條 ⇒ **只帶白名單仍會拿到 49 條假陽性，而假陽性
   正是這次外洩被淹沒的原因**。已加 `--auth-names`。
12. **⭐用 `py_compile` 驗語法，不帶 `force` 只證明 pyc 已存在**（2026-08-21）。
   先前多次回報的「829 檔 0 失敗」是這樣來的 —— 它讀既有 pyc 就回成功，
   **不代表原始碼可編譯**。帶 `force=True` 重跑才發現真相是另一回事：
   全部失敗於寫入 `__pycache__` 的 `PermissionError`（容器非 root），
   仍然不是語法檢查。**正解＝`compile(source, path, 'exec')` 編到記憶體、
   完全不寫檔**，這才真的驗語法（實測 829 檔 0 失敗）。
   與判準 9 同族：**驗證工具的副作用會決定它到底驗了什麼**。
13. **三態不是選配 —— 訊息說對了而狀態說錯了，讀報告的人只看得到狀態**
   （2026-08-21，L89 在新地方重演）。`integration_e2e_validation` 的
   `chain_3` 缺 token 時已正確附上「無法驗證（不是整合斷了）」，
   **但值仍是 `ok=False`** ⇒ 進 `broken_chains`、`all_ok=false`、
   OVERALL BROKEN。已改 `ok=None` 第三態並分開統計
   （現況 ALL PASS／1 條未驗完；注入真斷仍 BROKEN + exit 1）。
14. **⭐⭐三種發現方式，各自抓到不同的東西**（2026-08-23，與 CK_AaaP 交叉驗證後
   拿本 repo 當日紀錄逐項核實）。我原本說「真正抓到我的沒有一次是自查」，
   **那句話是錯的**，攤開來看形狀更準：

   | 方式 | 抓到的是什麼 | 本 repo 當日實例 |
   |---|---|---|
   | **自查** | 我**已經在看**的東西壞了 | NAS 掃描說「空」但稽核說 1528（**兩個數字打架**）／tar 用錯支（跑它，大聲失敗）／備份順序（稽核的新鮮度門檻報 40.6h） |
   | **互查** | 我**連那個維度都沒有** | 認證名單那一半（lvrland）／baseline 假理由（FacilityDev）／備份判準歧義（AaaP）／`doc_type` 契約斷裂（stop hook）／「67 則」實為 1 則 67 筆（owner） |
   | **⭐互查提問＋自查作答** | 對方**看不到我的系統**，但說出了值得我自己查一遍的問句 | AaaP 報「版次四個來源三個數字」→ 我查出自己**更嚴重**（`health.version` 是 `None`，事故當下無從得知線上跑哪一版）／AaaP 的 PT72H → 我查出**自己也有兩支**／AaaP 的死碼分支 → 我回頭確認自己的狀態檔分支不是死碼 |

   **自查的三個實例全都是「有第二個來源，或它會大聲失敗」** ——
   沒有第二個來源的地方，自查用的是同一個座標系，**而錯的往往就是座標系本身**。

   **第三類的槓桿最大**：發現者不需要存取被發現者的系統，也不需要雙方同時在跑
   —— 那個問句**可以留在文件裡等下一個人**。當日四次裡有三次，發現者
   看不到被發現者的系統。

   ⇒ 覆盤時要問的兩句（前者需要對方在場，後者不需要）：
   **「我有什麼是你看得到而我看不到的？」**
   **「你剛在自己身上發現了什麼，值得我去自己查一遍？」**

   ⚠️ 界限（CK_AaaP 立的，我同意）：**互查依賴對方當時剛好在跑，不能取代
   自查，也不寫成流程** —— 寫成流程就會變成一個沒有人跑得動的儀式。
15. **⭐跨 session 訊息裡的「已」只能寫已經 commit 的事**
   （CK_AaaP 2026-08-21 主動更正自己時提出，對我同樣適用）。
   他們對我說了兩句「已記進 X」，事後自查發現當時只是打算做。
   **訊息是一個完全沒有守門的紀錄面** —— 送出就進入對方的工作脈絡、
   會影響對方接下來做什麼，而沒有任何檢核會比對它與現實；
   比文件更糟的是**它無法事後修正**。
   規則：先改、先 commit、再說；必須先回覆時寫「我會」而不是「我已」。

---

## E. 相關文件索引

| 文件 | 涵蓋 |
|---|---|
| **`RETRO_AND_PLAN_20260824.md`** | **08-21～24 四天跨 8 repo 的覆盤、八條判準、權責劃分（A owner／B 各 repo／C Missive 自己）與優先序** ← 最新入口 |
| `QUOTATION_LIFECYCLE_PLAN.md` | 回簽流程、帳號對應、既有案件補件、發票架構、已完成清單 |
| `ROLE_MODEL_PLAN.md` | 人／帳號／職能三層、兩個頁面的定位、RBAC 路徑 |
| `TENDER_DATA_GAPS.md` | 決標資料 0 筆、三條取得路徑的實測、PCC 預算已解決 |
| `docs/runbooks/unexpected-shutdown-recovery.md` §0 | 排程被停用的診斷程序與指令 |
| `CLAUDE.md` v6.59 | 本輪完整里程碑 |
