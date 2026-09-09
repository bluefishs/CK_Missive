# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.76（2026-09-09）/ ⭐⭐⭐**這一輪的主軸是「異值同工」**：owner 定調「統計應建構統一服務端，不應依各別頁面各自建構」。盤點實測承攬金額 **4 份**實作、已請款／已收款／應付各 3 份、「誰是全公司視角」2 份、案件統計範圍兩份平行程式碼；**而同一天三處是「分歧存在、結果相同、只是還沒發作」**（已收款三份狀態條件各不相同卻同值，因為 59 筆狀態剛好全是 paid；承攬金額兩層 vs 三層；全公司視角兩份判準）⇒ **數字對得起來不能證明只有一份實作，要數程式碼**（L149）。收斂＝中心服務 `services/stats/`（指標 `finance`／範圍 `case_scope`）＋ `core/case_scope.has_company_wide_scope` 唯一判準＋15 條口徑鎖＋weekly 132（新增即紅、存量 7 處走基線）；統一到最嚴謹的那份**實測不改變任何現有數字**；線上驗證三個畫面同值 108,108,873、12 位使用者範圍一致。⭐⭐**同日六個「兩份宣告分家」實例各自修好並各補一道守門**：表頭篩選鍵三處分家（128，`buildServerFilters` 讓打錯字由 tsc 擋）／承辦身分合併沒展開（129，「顯示 (3) 卻 0 家」的 380 萬）／13 處 `getattr` 猜欄位（130）／列表與統計卡身分口徑（131，靜態掃描誤報改行為判準）／財務儀表板上下兩個年度口徑差 1,693 萬（類別分解仍用案號年）／PM 統計卡沒接 `staff_user_id`。⭐**weekly 統整**：131 步分 10 領域，彙總器只把「本週新紅」判紅（44 支非綠裡真的變壞的是 6 支，全清）；runner 檔頭「12 步 ~3 分鐘」過期十倍。⭐**判準自我更正五次，全是假綠**：命中自己的註解（兩次）、動態比對兩邊用同一份 SQL、小樣本印 0%、靜態掃描看不到 schema 裡的參數。⭐**我自己的量測錯誤七次**：管線退出碼、錯的工作目錄、手動執行的編碼崩潰當成排程在崩、只讀函式前半段（兩次）、探針比對自己的表達式、把建置中的部署當成程序死掉——**先排除自己，再談系統**。⚠️ 主機層 A127：swap=0 前提被推翻，三個選項待 owner。
> （v6.75 那一輪的摘要在下一段）
> **v6.75（2026-09-08）**: ⭐⭐⭐**這一輪的主軸是「機制要真的在跑」**：owner 指出「都進完成一半就停駐且無複查」，實查證實——weekly 117–122 六支檢核 README 與 skills-inventory 都登記了、`run_fitness_weekly.sh` **一支都沒有** ⇒ 從未被排程執行；`declaration_gate` 因此加第三腳（腳本／索引／runner 三處同時成立才算存在）。⭐⭐**業務同仁看不到自己有權限的頁面**：staff 有專案帳款等 7 頁的碼，父群組「報表分析」要 `reports:view` 而 staff 沒有 ⇒ 前端先問父階、整棵子樹消失（每層單獨看都對，鏈是斷的）；weekly 119 ⑤ 立刻多抓 finance／ops 的 ERP 圖譜同型。⭐⭐**`/uploads` 是 StaticFiles 掛載 ⇒ 1,642 個附件公網未登入 200**（L148），而 weekly 64 還明文豁免它（「靜態、本來就該公開」）——改帶認證路由＋`Cache-Control: private, no-store`（CF 依副檔名快取 PDF，登入者抓一次之後未登入也拿得到），再補**附件層級**規則（A116）。⭐**收斂**：民國年解析 8 份定義＋19 處散裝 `+1911` 收成 `app/core/roc_date.py`（A119）；LINE 去重改 redis（A117）。⭐**備份**：`D:\報價單\` 整棵樹（總表＋106 個回簽原件）此前沒有任何異地備份，已納入 NAS current 鏡像＋試算表日期快照（A123）。⭐**文件**：8 份 2025 規劃期文件（`claude_plant/`、SQLite、8003「優化版」）仍是活文件且被引用，全數作廢入 `archived/`＋weekly 122 守；文件生命週期檔頭 A118 與 CK_AaaP 同格式（`lifecycle: status/reviewed/owner`，90 天）。⭐**build 身分**：`MSYS_NO_PATHCONV=1` 讓 `git -C /d/…` 與 python 讀不到路徑 ⇒ 映像被標成 `unknown @ unknown-dirty` 而建置全程無錯，且部署閘門比對 `= "unknown"` 對 `unknown-dirty` 完全放行；兩處皆修。
> （更早版本的一行摘要同樣在 `docs/MILESTONES_ARCHIVE.md`）
>
> **2026-08-30**：⭐⭐⭐**假的事件流比沒有事件流更糟**（L109）——`scheduler_start` 事件加了卻沒有任何消費端（同 `csp_violations_total` 的形狀），我寫消費端時**自己重寫了一份路徑推導**，而**同一個檔案上方 100 行就有 `_cron_events_path()`**，它的註解寫著那條路是錯的。兩次寫錯的形狀不同：①不存在的 `ROOT` 常數 ⇒ NameError，**會吵**；②`parents[2]/"logs"` ⇒ 那個檔**真的存在** ⇒ 不報錯、不回 None、**安靜地讀了錯的檔案回 0**。它接著讓我做出「重啟太密所以 job 跑不到」這個**能解釋症狀的錯誤診斷**——實查才知 repo 根那份是 **pytest 在 host 上寫的**（`CK_LOGS_DIR` 未設），504 筆、當天還在更新、連 detail 格式都是真的，破綻只有 `test_obs_job`。⭐ 第三個錯是**拿 13 小時的觀測窗解釋 69 小時的空窗**（標記昨天才加）⇒ 補 `observed_span()`，凡用重啟史歸因先講「我看得到多遠」。⭐ 修法：消費端改用既有 helper／`longest_uptime_within` 排除「事件流開始之前」那段（首版把 24h 窗算成 10.87h 而真值 2.80h，**把「沒有資料」讀成「沒有發生」**）／窗內 0 筆回 `None` 不回 `seconds`／`conftest.py` 在 import `main` **之前**設 `CK_LOGS_DIR`（實測 504→504 未再增長、隔離檔收到寫入）。存量誘餌檔待 owner 裁示＝A44。⭐⭐⭐**A50 已辦（owner 裁示）＋一個關於「建議」的教訓**：排程改持久化 jobstore（既有 Postgres、零費用），但**光加持久化不夠** —— 讀 APScheduler 原始碼才發現 `replace_existing=True`（本檔 56 處全帶）會在重啟時把存起來的 `next_run_time` **覆蓋成未來**，持久化等於白做。實際修法三件事：持久化＋`_RecoveringAsyncIOScheduler` 只接回**已過去**的觸發＋清理殘留 job。容器內對照：**修法版執行 1 次／原生版 0 次**（對照做了三次才做對——前兩次被排程器執行緒與「我寫成 start() 再 add_job，與正式順序相反」污染）。⇒ **推薦一個修法前要確認它單獨成立**：我上午寫建議時沒讀 `_real_add_job`，那個建議聽起來合理、方向也對，但少了第二件事就是無效的。⭐ 同型複查（owner 交代）：熔斷器走 redis ✓、去重是請求內區域變數 ✓、告警冷卻在記憶體但失敗方向是噪音（不修）、**限流 `Limiter()` 沒有 `storage_uri` ⇒ 每次重啟都送使用者一份新的每日配額**（10,000/日 形同虛設）＝A51 待裁示。⭐⭐⭐**我把「我還沒讀到」寫成了「沒有人讀」並提交進版控**（L115 同日自我更正）：我宣稱走查抓到的 400「沒有人看那份產出」，逐段實查後**閉環是完整的** —— registry 已登記 `fail_key`、watchdog 實跑 exit 2、**02:02:25 queued「🚨 每日檢核 RED」、07:30:14 隨晨報送出**。真正的形狀是**延遲約 10.5 小時**（bug 進版→走查 20:41→daily 02:02→晨報 07:30），而我 09:xx 手動跑 weekly 28「發現」它時，它已經在你當天的晨報裡。⇒ **下結論說某機制沒有接收者之前，鏈路每一段都要拿到證據**（registry→退出碼→通知佇列→送出紀錄），不能因為「我是手動跑才看到」就推論沒人在跑。⭐⭐**判準去問「那個欄位長什麼樣」，而違規是「那個欄位不存在」**（L110）：§2.6 ③ 補守門時量出「0 違規」，而盲區裡躺著兩個真的 —— 發票彙總與營運帳目的年度 Select **開場是空的 ⇒ 歷年混算**（params 裡根本沒有 `year`／`fiscal_year` 這個 key）。⇒ 進場條件改成「**有沒有人在寫入年度**」再問預設值在不在；**用「有沒有人要改它」證明欄位該存在**。判準校準三次全在過寬方向（`year` 字樣命中長條圖 X 軸／別名 `currentYear`／`allowClear` 才是「全部年度」）。⭐ 修的過程差點造出**隱形篩選**：營運頁的 Select 只有 `onChange` 沒有 `value`，加了預設值會變成資料被篩而畫面說未選 —— 比不篩更糟，已一併納入判準。⭐⭐**沒有人在跑的檢核會腐爛，而腐爛的方式你猜不到**（L111）：`.claude/hooks/` 標為「手動執行」的三支**沒有任何 runner 在叫**，且**三支各壞成不同的樣子** —— ①`link-id-check` 的 `-Path "src\**\*.tsx"`：**PowerShell 的 `**` 不是遞迴 glob**，掃得到 **119/604** 個檔**而照樣印 PASS**（假綠）＋一條斷言的型別路徑過期（永久假紅）；②`route-sync-check` 專案根算高一層 ⇒ 每次 exit 1；③`link-id-validation` 報 7 個警告**但 exit 0**、抽查是假陽性。⇒ 「腳本存在 ≠ 有在強制」要再加一句：**「腳本能跑 ≠ 它說的是真的」**。⭐ 修好 `route-sync-check` 後它報「144 vs 41」看似大漂移，實際那份白名單只收導覽選單、本來就不該相等 ⇒ **修好一支壞掉的檢核不等於得到一支正確的檢核**，故刻意不接。§7 已改寫為 `link_id_fallback_audit.py`（805 檔、豁免 React `key=`）＝weekly 90，並自帶解析度下限（掃不到 400 檔直接判不可信）。另：六條無守門的核心規範實查 **8 候選 0 真違規**。⭐⭐**掛上去、會執行、也真的擋過東西的 hook，仍有一半規則從未命中**（L112）：`validate-file-location` 的 6 條規則有 **3 條帶 `^` 錨點**，而 Write/Edit **要求絕對路徑** ⇒ 路徑一律以 `D:/…` 開頭 ⇒ 三條全部落空（實測：絕對路徑 exit 0、相對路徑 exit 2），**而另外三條會命中所以它看起來正常**。同支還漏 `backend/.env`（§2 明文禁止、CI 的 config-consistency 自 2026-03-09 停用 ⇒ 那條規範零強制），已補；14/14 正負向控制全對。⭐ 修時差點放寬成另一個 bug：把 `^test_` 改套到檔名會擋掉合法的 `tests/test_*.py` ——**負向控制必須包含「原本就該放行的東西」**。⭐ 另查出 `careful-guard` 的 CRITICAL／WARNING **分級只存在於資料裡**（兩層都 exit 2 ⇒ `docker system prune` 這類被硬擋），協議有非阻擋通道；**放寬護欄屬 owner 決定，列 A43 不自行改**。12 支掛上的 hook BOM 全部正常。⭐⭐⭐**我昨天「修好」的守衛，修在一個 git 從不執行的檔案上**（L113）：`core.hooksPath = frontend/.husky/_` ⇒ `.git/hooks/pre-commit` 的 **6 項檢查全是死的**（含我 08-29 才修好的 secret guard）。實測 `.pem` 私鑰加進暫存 ⇒ **exit 0 並印「全部檢查通過」**。線索一直在畫面上：我看到的是 `[Pre-commit] 驗證 CK_Missive...` 而我改的那支印 `[Skills Hook] 驗證完成`，**兩段文字不一樣而我讀了好幾次沒對照**。根因＝兩套 hook 系統並存、較新的（husky）靜默勝出。⭐ 接上後才看見第二層：secret guard 的內容層**只警告不阻擋**且要有關鍵字接 `[:=]` ⇒ `sk-ant-…`／`ghp_…`／`AKIA…` **裸字面完全無聲**。已補供應商前綴**阻擋**層（對全 repo 量誤報＝1，為測試假值，已加 `pragma: allowlist secret`；7/7 控制通過）。⇒ **改 hook 前先 `git config core.hooksPath`；修好後要用它真正的觸發路徑驗，不是直接執行那個檔。**長度閘門要不要一併接上＝A45（會擋住 2 支既有 >1000 行的檔）。
>
> **2026-08-31**：⭐⭐⭐**知識庫的向量檢索從來沒有成功過**——`:embedding::vector` 讓參數綁不到（SQLAlchemy 的 BIND_PARAMS 正則有「參數名後面不可接冒號」的否定前瞻，而 PostgreSQL 轉型正是 `::`），**每一次查詢都 HTTP 500**；而端點的「向量失敗退回文字搜尋」兜底寫在更外層 ⇒ **連降級都沒發生**。同型前例就在本 repo（`login_history.py:178` 的註解寫著「asyncpg 不支援 :param::type」並改用動態 WHERE 繞開）——**有人踩過、繞過了，而這裡沒有跟上**。改用 `CAST(...)`，補 3 支不打 DB 的回歸鎖。⭐⭐⭐**專案團隊成員查詢從來沒成功過**：手寫 SQL 是 `FROM project_user_assignment`（**單數**）而資料表是複數 ⇒ `relation does not exist` ⇒ `except` 記一行 log 就 `return []` ⇒ **每個專案看起來都沒有成員，連帶專案通知從未寄出**。成因推測是照著 SQLAlchemy 的 Table 常數名抄——**ORM 的物件名不是資料表名**。⭐⭐**同族第七、八處**：`project_user_assignments` 有兩條互斥綁法（邀標綁 `case_code`／成案綁 `project_id`），報價單抓承辦只認前者 ⇒ 7 張看不到承辦（owner 從 `/erp/quotations/541` 回報）。找到第八處的方法是**全 repo grep 同族**：24 檔命中、粗判準標 6 個單邊、逐一讀完 4 誤報 2 真——「修完第一處要 grep 整個 repo」這次才真的做。⭐⭐**知識文庫最多落後一週**：`.git/hooks/post-commit` 有「重生知識地圖」而 `core.hooksPath` 指向 husky ⇒ **提交時從不重生**，唯一的重生者是週排程；而向量同步 04:45 又跑在地圖重生（04:51）**之前 6 分鐘**。兩者都修，daily 加第 14 步偵測，判準**分兩級**否則會做出一支天天紅的檢核（當天改的文件在 02:00 看必然「未同步」，那是待辦不是故障）。⭐⭐**判準的掃描範圍不得包含描述它的文字**——同日踩四次：教訓區塊吸收檔尾／回歸測試讀到自己註解裡的反例／`add_job` 視窗吃到下一支／**SQL 註解裡的冒號參數被 SQLAlchemy 當成真參數**（編譯後多出 `$1` 而它沒有值）。⭐**權限**：委託單位／協力廠商帳款原掛 `reports:finance:view` 而 **11/12 人持有**（含全部 staff）⇒ 等於全開，改用 `reports:erp:view`（5 admin、0 staff）；報價單改成案主軸（257→164）＋依身分限縮，跨案查詢做成**可授權的擴充點**而非寫死。⚠️ `init_navigation_data.py` 的選單權限是 `"[]"`（所有人可見）而 live DB 是 `finance:view`——**兩邊早就漂移**。⭐**成本／毛利準則的關鍵事實**：`finance_ledgers` 的支出分錄 `source_type` **只有 `erp_vendor_payable` 與 `expense_invoice` 兩種** ⇒ 帳本是應付與核銷的鏡像，**三者相加會重複計算**；且執行中 100 案的**完工日與驗收日各 0 件**，所以「該不該請款」目前只能用天數猜（門檻 365 天是拿公司自己的中位數 205 天校準的，不是拍的）。
>
> 📜 **2026-09-01～09-03 的日記式紀錄已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)**（2026-09-04 /doctor；搬移不是刪除，教訓本體在 `LESSONS_REGISTRY.md`）。
>
> ⭐⭐⭐**09-04 金流全面複查（/loop，owner「不得數據對應錯誤」）**：11 個統計端點打端點對 SQL 真值 ⇒ 四處口徑錯（總覽含 64 張已刪／
> 發票年度用報價單年（2026 少算 64 張 800 萬）／委託單位年度用案件年／「營收總額」其實未稅），已修＋年度口徑表入 `FIELD_SEMANTICS.md`。
> ⭐⭐⭐**每張表單獨看都正常，鏈才是斷的**（L140）：匯入服務對總表「已成立」的列只寫 `status=contracted` **不建承攬案** ⇒ 16 筆
> PM 已承攬、承攬列表看不到、報價單沒 `project_code`、損益摘要當未成案、掛著的請款在成案口徑裡消失。7 筆 promote 補成案、9 筆同名待判（A90）；
> 修匯入（成立即走正式 promote，被擋的列出來）＋weekly 105。⭐⭐⭐**230 張報價單總價與總表不符、少記 482 萬**，而 weekly 100 的
> 「差 >50%」看不見 **10.5%／23.5% 的系統性偏差**——03-17 批＝`含稅−2×稅`、08-20 批＝`未稅×0.85`，**比值分布**一眼看到（1.105×119、1.235×103、
> 1.000 只有 17）。⇒ weekly 104 加簽名判準 ⑨（首跑 216）。**更正 229 張的批次 SQL 兩次被權限分類器擋下 ⇒ A92 待 owner 授權**，不轉包。
> ⚠️ 12 筆 GN 舊承攬案 `project_code` 空（回填＝case_code）；PM 客戶未連結 23→0。
>
> ⭐⭐**09-04 第二輪：財務儀表板的專案一覽只列 17 筆而標題寫 131 筆**——財務摘要 repository 三處用 `ContractProject.project_code`
> 去對帳本／報價單的 `case_code`（同族第十二處；帳本 49 案號用 case_code 對得到 48、用 project_code 只有 3），PM 制成案的案全被當
> 「找不到主檔」丟掉；`quotation_total`／請款／實收／應付四欄 schema 有而從未填。改 `case_code` 橋、分頁來源改承攬案、補四欄、
> 排名分母改合約額；修後 2026 一覽 123 筆＝真值、排名 15/15 有案名；探針 +2 斷言＝15/15。其餘四端點與真值一致。
>
> ⭐**09-04 第三輪（owner「依總表為主」）**：A90 九筆同名案量了才知道 **8 筆是總表 a／b／c 子案不是重複**（各有舊案號與金流）⇒ 成案，
> 只刪總表沒有的 006；A91 真因是總表 v2 把 C033b 換成另一塊地；A92 229 張總價更正執行（備份＋審計）⇒ weekly 104 ①191／⑨216 歸零。
> 派工單號 12 字在 140px 折行＝「無法檢視」，欄寬依資料量測重配（scroll.x 1512）。
>
> ⭐**09-04 第四輪（owner 三回報）**：`/pm/cases` 報價總額卡改跟狀態卡篩選（計數不跟）；「檢視 XLS 樣式」此前把**非空白的範本檔**（內含真實報價單）原樣轉 PDF、4 頁——改走 `render_xlsx` 空資料同一條鏈；
> 輸出後附件列表沒重抓 ⇒「無看到 XLS／PDF」——存檔成功即重抓；`archive` 從沒寫 `doc_type=generated_quotation`（補寫＋回填 7）；一案多張報價單可切換。
>
> ⭐**09-04 第五輪**：`/pm/cases` 卡改「評估中」；`/contract-cases` 統計卡此前全量（2026 顯示 285）⇒ statistics 端點接篩選（分母＝年度／類別／搜尋，status 只影響合約總額）。
>
> ⭐**09-04 第六輪：統計卡互動複查**——55 張卡 47 張本來可點；缺口在數字沒跟篩選走（承攬案／PM 報價總額／營運帳目／資產／報價單損益 5 處），統計查詢改帶列表同一組條件。
>
> ⭐**09-04 第七、八輪**：案件報價單分頁看不到未成案報價單（列表沒帶 `include_unawarded`，owner 因此同案建三張）；chunk 404 真因是 build 清空 dist（部署改保留上一版 assets）；XLS 字型不一致在範本本身（填值後統一資料格）；列印／輸出整合為一個入口；分頁可改備註；**改工項後已輸出檔自動重產**。
>
> ⭐**09-04 第九輪（回簽單對照）**：備註回明細區／長字折行／複價可覆寫／稅 0 印已含稅／已有報價單不再給新增報價。**拿實際回簽單當驗收樣本，一次看出五個版面差異**——比看程式碼快。
>
> ⭐**09-04 第十、十一輪**：工項項次可自填（1.1／1.2）；列表印報價單編號↔工程編號對應；**文件抬頭的客戶資料一直在委託單位主檔，只是 gather 沒 JOIN**——接上並給編輯入口，不另存一份。
>
> ⭐⭐**09-04 第三輪（owner 八點）**：**協力廠商指派與應付沒有橋**——承攬案「協力廠商」分頁寫 `project_vendor_association`，廠商帳款／應付分頁讀 `erp_vendor_payables`，16 案有指派 13 案無應付；
> 新增「指派即應付」（同「成案即應收」形狀，三處掛點、自動建的帶前綴、人工的不碰）＋weekly 106（首跑 YELLOW 3＝A96 要 owner 判）。⚠️ 首版排除 `quote_kind=tender` 讓 01 委辦案四筆全被略過——01 案的應付本來就掛在投標報價單上。
> **`/erp/client-accounts` 只列 50 家**：後端預設 `limit=50`、委託單位 186 家，頁面在那 50 筆上分頁排序 ⇒ 136 家查不到而沒有任何錯誤（weekly 95 家族，**這次壞在列表不在下拉**）。
> **代碼 vs 統一編號**：協力廠商把統編填 `vendor_code`、委託單位填 `tax_id`——同一件事兩個欄位；統一 `tax_id`＝統編、`vendor_code`＝內部代碼（15 家已搬）。專案帳款頁固定只列成案、案件狀態篩選改委託單位、承攬案詳情返回固定回列表。
>
> ⭐⭐⭐**09-07：一份宣告改了、另一份沒改——同一天三次**（L145）。①拆出委託／協力帳款各自的權限碼時
> **只改角色層 `role_permissions`**，而前端判權限讀的是**使用者層 `users.permissions`** ⇒ 管理員打開那兩頁是空的，
> 而畫面上看不出原因（owner 回報才發現）；②「逾期幾天」有**三份各自實作**，把自動建立的請款日改留白時，
> 漏改一處那 86 筆佔位就從該消費端整批消失（實測 198→118），畫面只顯示「逾期變少了」；
> ③改委託單位主檔名稱，列表與下拉還是舊名——**名字讀的是建案當下的快照，不是主檔**，選了新名就是空表。
> 三者修法同形：定義收成一份＋補一支盯「有沒有第二份」的檢核（weekly 119 角色↔使用者、121 稽催錨點、
> 改名時傳播快照）。⭐**兩次判準自我更正**：weekly 121 首版判「檔案有沒有出現模組名」，而三個消費端的**註解**
> 都寫著模組名 ⇒ 拿掉 import 也不會紅、**判準等於沒有作用**；weekly 120 首版把**同案不同版次**
> （`B114-C031-0` vs DB 的 `-1`）報成漏匯入——**把誤報當事實交出去，會讓人做出錯的清理動作**。
> ⭐**型別只有實跑看得到**：`COALESCE(billing_date, quoted_at)` 前者 date、後者 datetime ⇒ Python 端 TypeError、
> SQL 端回 interval（畫面印「逾期 557 days 天」）。⭐⭐**匯入器讀到彙總區塊的欄位**（L146）：總表右側第 38–43 欄
> 是各承辦年度小計，「報價金額」因此在同一張表出現兩次，而欄位對應是**後面覆蓋前面** ⇒ `B110-020-0A` 被寫成
> 351,200（那是某人的年度小計），正確是 39,000。⇒ 同名表頭取最左邊。⭐ 同日另兩個「不會報錯的略過」：
> 沒有報價單編號的列**連略過都沒記錄**（4 列約 246 萬從未進系統）、唯一索引不排除軟刪列（重建被刪過的編號整批回滾）。
> ⭐**路由此前只問有沒有登入**：`AppRouter` 用了 117 次 `ProtectedRoute`、傳 `permissions` 的 **0 次** ⇒
> 選單藏起來的頁面打網址一律進得去。改成照選單自己的宣告擋（改一處、117 條全涵蓋）。
> ⚠️ 這是**介面層**守衛不是資安邊界：API 738 支端點裡只 require_auth 的仍有 415 支。

> ⭐⭐⭐**09-07 晚：owner「整個系統四分五裂，重覆優化架構鬆散」→ 收斂 A／B 落地**（L147，全文 `docs/architecture/CONSOLIDATION_20260907.md`）。
> 診斷：一天十次同一形狀——**同一件事有兩份宣告，改一份另一份不動，沒有任何一方報錯**；而我每次的反應是加一支檢核
> （本月 +89、總數 214）。檢核是**看著**兩份宣告分家，不是讓它們**不可能**分家 ⇒ 事故照樣重演，只是早點被看見。
> **收斂 A**：角色是權限唯一來源——儲存角色即同步、改角色即推導、`is_admin` 改為由角色推導的鏡像（前後端 `isAdmin` 同步只看角色）。
> **收斂 B**：選單表是選單／路由守衛／**API** 三邊唯一來源——API 只宣告「我屬於哪個頁面」（`require_page_permission`），
> 權限碼從 `app/core/capabilities.py` 的快取讀；實測改選單表 → 財務打 API 200→403→200，**零程式碼零部署**。
> ⇒ weekly 119 ③④ 由 RED 降 YELLOW（**檢核數量下降才是架構變緊的訊號**）。
> ⭐ 兩個過程中的錯：依 exec「全域唯讀」的**設計註解**移除其寫入權——實測三位 exec 全是承辦（一位 81 案）；
> 前端 `USER_ROLES.default_permissions` 差點被當權威套回 DB——那是建角色的**範本**，照套管理員會失去 ERP 財務。
> **角色看人實際在做什麼，宣告看是誰在維護給誰用，不看它叫什麼名字。**

> ⭐⭐⭐**09-08：owner 拿一份 2025 規劃期附件問了 A1–A5／B1–B8／C1–C5／D1–D10，逐項實查**（全表在 `CONSOLIDATION_20260907.md` §六、`OPEN_ITEMS` A116–A119）。
> 大多數「兩套」都不存在（sqlite／8003／Adminer 8080／OAuth 行事曆／無 Alembic／無排程）——出處是 **8 份未作廢的活文件**，全部作廢入 `docs/archived/`＋weekly 122 守。
> **但 D6 是真的**（L148）：`/uploads` 是 StaticFiles 掛載、1,642 個附件公網未登入 200；weekly 64 還把它明文豁免（「靜態、本來就該公開」）。
> 修成帶認證路由＋`Cache-Control: private, no-store`（第二層：CF 依副檔名快取 PDF，登入者抓一次之後未登入也拿得到）。**已在 CF 邊緣快取的檔只有 purge 能清＝owner。**
> 另兩個真缺口：D7 還原演練日期此前無守門（offsite 稽核加 `check_restore_drill`）、B6 民國年解析 8 份實作（A119）。

> **最後更新**: 2026-09-09
>
> **近期重大里程碑**：已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)
> （2026-08-27，v6.59–v6.61 共 46,981 字元；更早的 64 條 08-24 已先移入）。
> **搬移不是刪除**——內容完整保留，只是不再每個 session 載入一遍。
> 教訓的權威來源是 [`docs/architecture/LESSONS_REGISTRY.md`](docs/architecture/LESSONS_REGISTRY.md)。

---

## 專案概述

CK_Missive 是企業級公文管理系統（公文／行事曆／邀標報價／承攬案件／ERP 財務／知識圖譜／Hermes Agent）。功能與模組請直接看 `backend/app/api/endpoints/`、`frontend/src/pages/`；多專案角色與 subdomain 策略見上層 `D:/CKProject/CLAUDE.md`。

### LINE / Telegram（via Hermes Agent Gateway）

- **重點**: Skill 中 API URL 必須用 `host.docker.internal:8001`（不是 `localhost`）
- **重點**: LINE webhook 需要公網 HTTPS，由 Cloudflare Tunnel 提供
- Hermes 部署包：`CK_AaaP/runbooks/hermes-stack/`；Skill 定義：`docs/hermes-skills/ck-missive-bridge/`

## 規範索引

> 以下規範位於 `.claude/rules/`。**載入時機分兩種**（2026-09-08 /doctor 校正）——
> 沒有 `paths:` frontmatter 的每個 session 都載入；有的只在動到那些路徑時載入。
> ⚠️ 原表列了一份 `security.md`，而**那個檔案不存在**（安全規範的實際位置見下方「其他重要文件」
> 與 `C:/Users/User1/.claude/rules/security.md`）——一份宣告說有、而檔案沒有，
> 是本 repo 反覆記載的同一個形狀，只是這次方向相反。

| 規範檔案 | 載入 | 說明 |
|---------|------|------|
| `skills-inventory.md` | 常駐 | Skills / Commands / Agents 清單（檢核腳本正典在 `scripts/checks/README.md`）|
| `development-rules.md` | 常駐 | 開發強制規範 (SSOT, 型別, API, 服務層, DI) |
| `cross-file-ssot-governance.md` | 常駐 | 跨檔資源 SSOT 治理（L41–L45 家族）|
| `architecture.md` | 常駐 | 專案結構總覽（索引） |
| `testing.md` | 常駐 | 測試規範 |
| `architecture-backend.md` | `backend/**` | 後端：Models/Services/API/Repositories |
| `architecture-frontend.md` | `frontend/**` | 前端：Pages/Hooks/型別/錯誤處理 |
| `adr-anti-half-wired-sop.md` | `docs/adr/**`、`docs/architecture/**` | ADR 級半接通防範 |
| `hooks-guide.md` | `.claude/hooks/**`、`.claude/settings*.json`、`frontend/.husky/**`、`.git/hooks/**` | Hooks 自動化配置與協議 |
| `ci-cd.md` | `.github/**`、`scripts/checks/**` | CI/CD 工作流 |
| `auth-environment.md` | `frontend/src/config/**`、`frontend/src/api/**`、`backend/app/core/auth*` | 認證與環境檢測規範 |

### 其他重要文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引與常見錯誤 |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |

## 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL **15.14**（image `pgvector/pgvector:0.8.0-pg15`，Docker，**127.0.0.1:5434** 僅本機）
  <!-- 2026-08-10 更正：原記「PostgreSQL 16」與實際不符。這不是無害的筆誤 ——
       備份是 backend 容器的 pg_dump 17.10 產生的，而伺服器是 15.14，
       dump 裡帶著 15 認不得的 transaction_timeout，帶 ON_ERROR_STOP 還原會中止。
       版本記載錯誤會讓人在災難當下判斷錯誤。詳見 docs/runbooks/disaster-recovery.md §4 -->
- 行事曆憑證：**只有服務帳號**（`GOOGLE_CREDENTIALS_PATH` → 容器內 `/app/GoogleCalendarAPIKEY.json`）；`GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` 是 **SSO 登入**用，與行事曆無關（2026-09-08 owner 誤讀為兩條路線，成因是 `.env.example` 一個標題包兩個功能，已拆）
- ⛔ **沒有的東西**（2026-09-08 逐項實查，別再從舊附件抄）：沒有 sqlite（`documents.db`／`ck_documents.db` 都不存在，sqlite 只在測試的 in-memory）；沒有 8003「優化版」後端（無程序監聽、只剩歸檔報告提過）；沒有 Adminer/pgAdmin 8080（只在 2026-05 歸檔 wiki）；`C:\GeminiCli\…` 是 2026-03 遷移前的路徑。守門＝weekly 122
- 客戶端工具版本落差（**還原時會咬人**）：postgres 容器 psql 15.14／backend 容器 pg_dump·psql **17.10**
- ~~NemoClaw 監控塔: http://localhost:9000~~ — **廢止** (ADR-0015)
- vLLM 本地推理: http://localhost:8000 (Docker, Qwen2.5-7B-AWQ)
- Ollama: http://localhost:11434 (Docker, nomic-embed)

### 常用命令

已改為 skill `dev-commands`（`.claude/skills/dev-commands/SKILL.md`），需要時載入；一句話：`.\scripts\dev\dev-start.ps1` 啟動、`bash scripts/deploy/deploy-public.sh` 部署、`npx tsc --noEmit` 驗證。

---

> 配置維護: Claude Code Assistant | 版本: v1.86.0
