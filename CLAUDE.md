# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.69（2026-08-29 晚）/ ⭐⭐⭐**同一個資源被讀取端只認一條路——同族六處，我在同一天內修了四處還漏掉兩處**：指派表的 `project_id` 是 nullable（邀標階段沒有專案可綁，只能寫 `case_code`），而讀取端 `quotation_document`(08-21)／`filing_gap`／`project_repository`／`get_user_accessible_project_ids`／**`check_user_project_access`／`apply_project_rls`** 各自只比 `project_id`。最嚴重的是最後一處是**權限過濾**：實測洪慶忠有 77 件案子而系統只讓他看到 **23** 件（admin 走短路所以看不出來）。⇒ **修完第一處要 grep 整個檔案，不是憑印象數**＋⭐⭐⭐**外層 rollback 擋不住內部自己 commit 的函式**：我在自稱「已回滾」的試算裡**真的成案了 3 件**（owner 刻意撤回待判讀的那批），是 **weekly step 28 的基線 91→88** 抓到的，已依裁示逐表還原（含還原被棘輪的基線，否則錯誤狀態會被記成新常態）＋⭐⭐⭐**公網探的那支 health 根本不查 DB**：`/api/health` 是靜態 dict，postgres 掛掉照樣回 healthy —— 而 L43 的「面向公網必須驗業務量」做在 `/health` 上。**我自己整天拿它當部署驗證**，那個綠燈比我以為的弱＋⭐⭐**「我這條路徑找不到」不等於「資料不存在」**：我 08-20 宣告「115 檔沒有承辦人資訊」，而代碼一直躺在 `legacy_quotation_no` 裡（A坤樹/B慶忠/C元宏/D廷睿/Y慶忠，**owner 講過多次而系統沒記**）⇒ 回填後報價單有承辦 **135 → 250 張**＋⭐⭐**註解指名了來源檔，不代表值是從那裡來的**：手抄的 `TEMPLATE_ITEM_CAPACITY=5` 叫使用者去合併後端輸出得出來的工項，而 tsc 全綠；**同一小時內我還漏掉同檔案的第二份**＋⭐⭐**後端算對了、前端又自己算一次**：報價單詳情頁的總計只顯示稅額，**235 張、9,206 萬元**＋⭐**設定檔整合**：三份 compose 的 14 個 postgres 參數只有 `max_connections` 不一致（而 dev/infra 定義**同一個容器**），且 `postgresql-tuning.conf` 掛載了卻**從未被讀**（Dead Config）—— 已對齊、已重新定位為規格書、weekly 88 三層守門（compose 之間／對規格／**對執行時**）＋⭐**測試庫 schema 落後正式庫 20 個欄位**且**根本沒有 `alembic_version`**（weekly 87）
> （更早版本的一行摘要同樣在 `docs/MILESTONES_ARCHIVE.md`）
>
> **2026-08-30**：⭐⭐⭐**假的事件流比沒有事件流更糟**（L109）——`scheduler_start` 事件加了卻沒有任何消費端（同 `csp_violations_total` 的形狀），我寫消費端時**自己重寫了一份路徑推導**，而**同一個檔案上方 100 行就有 `_cron_events_path()`**，它的註解寫著那條路是錯的。兩次寫錯的形狀不同：①不存在的 `ROOT` 常數 ⇒ NameError，**會吵**；②`parents[2]/"logs"` ⇒ 那個檔**真的存在** ⇒ 不報錯、不回 None、**安靜地讀了錯的檔案回 0**。它接著讓我做出「重啟太密所以 job 跑不到」這個**能解釋症狀的錯誤診斷**——實查才知 repo 根那份是 **pytest 在 host 上寫的**（`CK_LOGS_DIR` 未設），504 筆、當天還在更新、連 detail 格式都是真的，破綻只有 `test_obs_job`。⭐ 第三個錯是**拿 13 小時的觀測窗解釋 69 小時的空窗**（標記昨天才加）⇒ 補 `observed_span()`，凡用重啟史歸因先講「我看得到多遠」。⭐ 修法：消費端改用既有 helper／`longest_uptime_within` 排除「事件流開始之前」那段（首版把 24h 窗算成 10.87h 而真值 2.80h，**把「沒有資料」讀成「沒有發生」**）／窗內 0 筆回 `None` 不回 `seconds`／`conftest.py` 在 import `main` **之前**設 `CK_LOGS_DIR`（實測 504→504 未再增長、隔離檔收到寫入）。存量誘餌檔待 owner 裁示＝A44。⭐⭐⭐**A50 已辦（owner 裁示）＋一個關於「建議」的教訓**：排程改持久化 jobstore（既有 Postgres、零費用），但**光加持久化不夠** —— 讀 APScheduler 原始碼才發現 `replace_existing=True`（本檔 56 處全帶）會在重啟時把存起來的 `next_run_time` **覆蓋成未來**，持久化等於白做。實際修法三件事：持久化＋`_RecoveringAsyncIOScheduler` 只接回**已過去**的觸發＋清理殘留 job。容器內對照：**修法版執行 1 次／原生版 0 次**（對照做了三次才做對——前兩次被排程器執行緒與「我寫成 start() 再 add_job，與正式順序相反」污染）。⇒ **推薦一個修法前要確認它單獨成立**：我上午寫建議時沒讀 `_real_add_job`，那個建議聽起來合理、方向也對，但少了第二件事就是無效的。⭐ 同型複查（owner 交代）：熔斷器走 redis ✓、去重是請求內區域變數 ✓、告警冷卻在記憶體但失敗方向是噪音（不修）、**限流 `Limiter()` 沒有 `storage_uri` ⇒ 每次重啟都送使用者一份新的每日配額**（10,000/日 形同虛設）＝A51 待裁示。⭐⭐⭐**我把「我還沒讀到」寫成了「沒有人讀」並提交進版控**（L115 同日自我更正）：我宣稱走查抓到的 400「沒有人看那份產出」，逐段實查後**閉環是完整的** —— registry 已登記 `fail_key`、watchdog 實跑 exit 2、**02:02:25 queued「🚨 每日檢核 RED」、07:30:14 隨晨報送出**。真正的形狀是**延遲約 10.5 小時**（bug 進版→走查 20:41→daily 02:02→晨報 07:30），而我 09:xx 手動跑 weekly 28「發現」它時，它已經在你當天的晨報裡。⇒ **下結論說某機制沒有接收者之前，鏈路每一段都要拿到證據**（registry→退出碼→通知佇列→送出紀錄），不能因為「我是手動跑才看到」就推論沒人在跑。⭐⭐**判準去問「那個欄位長什麼樣」，而違規是「那個欄位不存在」**（L110）：§2.6 ③ 補守門時量出「0 違規」，而盲區裡躺著兩個真的 —— 發票彙總與營運帳目的年度 Select **開場是空的 ⇒ 歷年混算**（params 裡根本沒有 `year`／`fiscal_year` 這個 key）。⇒ 進場條件改成「**有沒有人在寫入年度**」再問預設值在不在；**用「有沒有人要改它」證明欄位該存在**。判準校準三次全在過寬方向（`year` 字樣命中長條圖 X 軸／別名 `currentYear`／`allowClear` 才是「全部年度」）。⭐ 修的過程差點造出**隱形篩選**：營運頁的 Select 只有 `onChange` 沒有 `value`，加了預設值會變成資料被篩而畫面說未選 —— 比不篩更糟，已一併納入判準。⭐⭐**沒有人在跑的檢核會腐爛，而腐爛的方式你猜不到**（L111）：`.claude/hooks/` 標為「手動執行」的三支**沒有任何 runner 在叫**，且**三支各壞成不同的樣子** —— ①`link-id-check` 的 `-Path "src\**\*.tsx"`：**PowerShell 的 `**` 不是遞迴 glob**，掃得到 **119/604** 個檔**而照樣印 PASS**（假綠）＋一條斷言的型別路徑過期（永久假紅）；②`route-sync-check` 專案根算高一層 ⇒ 每次 exit 1；③`link-id-validation` 報 7 個警告**但 exit 0**、抽查是假陽性。⇒ 「腳本存在 ≠ 有在強制」要再加一句：**「腳本能跑 ≠ 它說的是真的」**。⭐ 修好 `route-sync-check` 後它報「144 vs 41」看似大漂移，實際那份白名單只收導覽選單、本來就不該相等 ⇒ **修好一支壞掉的檢核不等於得到一支正確的檢核**，故刻意不接。§7 已改寫為 `link_id_fallback_audit.py`（805 檔、豁免 React `key=`）＝weekly 90，並自帶解析度下限（掃不到 400 檔直接判不可信）。另：六條無守門的核心規範實查 **8 候選 0 真違規**。⭐⭐**掛上去、會執行、也真的擋過東西的 hook，仍有一半規則從未命中**（L112）：`validate-file-location` 的 6 條規則有 **3 條帶 `^` 錨點**，而 Write/Edit **要求絕對路徑** ⇒ 路徑一律以 `D:/…` 開頭 ⇒ 三條全部落空（實測：絕對路徑 exit 0、相對路徑 exit 2），**而另外三條會命中所以它看起來正常**。同支還漏 `backend/.env`（§2 明文禁止、CI 的 config-consistency 自 2026-03-09 停用 ⇒ 那條規範零強制），已補；14/14 正負向控制全對。⭐ 修時差點放寬成另一個 bug：把 `^test_` 改套到檔名會擋掉合法的 `tests/test_*.py` ——**負向控制必須包含「原本就該放行的東西」**。⭐ 另查出 `careful-guard` 的 CRITICAL／WARNING **分級只存在於資料裡**（兩層都 exit 2 ⇒ `docker system prune` 這類被硬擋），協議有非阻擋通道；**放寬護欄屬 owner 決定，列 A43 不自行改**。12 支掛上的 hook BOM 全部正常。⭐⭐⭐**我昨天「修好」的守衛，修在一個 git 從不執行的檔案上**（L113）：`core.hooksPath = frontend/.husky/_` ⇒ `.git/hooks/pre-commit` 的 **6 項檢查全是死的**（含我 08-29 才修好的 secret guard）。實測 `.pem` 私鑰加進暫存 ⇒ **exit 0 並印「全部檢查通過」**。線索一直在畫面上：我看到的是 `[Pre-commit] 驗證 CK_Missive...` 而我改的那支印 `[Skills Hook] 驗證完成`，**兩段文字不一樣而我讀了好幾次沒對照**。根因＝兩套 hook 系統並存、較新的（husky）靜默勝出。⭐ 接上後才看見第二層：secret guard 的內容層**只警告不阻擋**且要有關鍵字接 `[:=]` ⇒ `sk-ant-…`／`ghp_…`／`AKIA…` **裸字面完全無聲**。已補供應商前綴**阻擋**層（對全 repo 量誤報＝1，為測試假值，已加 `pragma: allowlist secret`；7/7 控制通過）。⇒ **改 hook 前先 `git config core.hooksPath`；修好後要用它真正的觸發路徑驗，不是直接執行那個檔。**長度閘門要不要一併接上＝A45（會擋住 2 支既有 >1000 行的檔）。
>
> **2026-08-31**：⭐⭐⭐**知識庫的向量檢索從來沒有成功過**——`:embedding::vector` 讓參數綁不到（SQLAlchemy 的 BIND_PARAMS 正則有「參數名後面不可接冒號」的否定前瞻，而 PostgreSQL 轉型正是 `::`），**每一次查詢都 HTTP 500**；而端點的「向量失敗退回文字搜尋」兜底寫在更外層 ⇒ **連降級都沒發生**。同型前例就在本 repo（`login_history.py:178` 的註解寫著「asyncpg 不支援 :param::type」並改用動態 WHERE 繞開）——**有人踩過、繞過了，而這裡沒有跟上**。改用 `CAST(...)`，補 3 支不打 DB 的回歸鎖。⭐⭐⭐**專案團隊成員查詢從來沒成功過**：手寫 SQL 是 `FROM project_user_assignment`（**單數**）而資料表是複數 ⇒ `relation does not exist` ⇒ `except` 記一行 log 就 `return []` ⇒ **每個專案看起來都沒有成員，連帶專案通知從未寄出**。成因推測是照著 SQLAlchemy 的 Table 常數名抄——**ORM 的物件名不是資料表名**。⭐⭐**同族第七、八處**：`project_user_assignments` 有兩條互斥綁法（邀標綁 `case_code`／成案綁 `project_id`），報價單抓承辦只認前者 ⇒ 7 張看不到承辦（owner 從 `/erp/quotations/541` 回報）。找到第八處的方法是**全 repo grep 同族**：24 檔命中、粗判準標 6 個單邊、逐一讀完 4 誤報 2 真——「修完第一處要 grep 整個 repo」這次才真的做。⭐⭐**知識文庫最多落後一週**：`.git/hooks/post-commit` 有「重生知識地圖」而 `core.hooksPath` 指向 husky ⇒ **提交時從不重生**，唯一的重生者是週排程；而向量同步 04:45 又跑在地圖重生（04:51）**之前 6 分鐘**。兩者都修，daily 加第 14 步偵測，判準**分兩級**否則會做出一支天天紅的檢核（當天改的文件在 02:00 看必然「未同步」，那是待辦不是故障）。⭐⭐**判準的掃描範圍不得包含描述它的文字**——同日踩四次：教訓區塊吸收檔尾／回歸測試讀到自己註解裡的反例／`add_job` 視窗吃到下一支／**SQL 註解裡的冒號參數被 SQLAlchemy 當成真參數**（編譯後多出 `$1` 而它沒有值）。⭐**權限**：委託單位／協力廠商帳款原掛 `reports:finance:view` 而 **11/12 人持有**（含全部 staff）⇒ 等於全開，改用 `reports:erp:view`（5 admin、0 staff）；報價單改成案主軸（257→164）＋依身分限縮，跨案查詢做成**可授權的擴充點**而非寫死。⚠️ `init_navigation_data.py` 的選單權限是 `"[]"`（所有人可見）而 live DB 是 `finance:view`——**兩邊早就漂移**。⭐**成本／毛利準則的關鍵事實**：`finance_ledgers` 的支出分錄 `source_type` **只有 `erp_vendor_payable` 與 `expense_invoice` 兩種** ⇒ 帳本是應付與核銷的鏡像，**三者相加會重複計算**；且執行中 100 案的**完工日與驗收日各 0 件**，所以「該不該請款」目前只能用天數猜（門檻 365 天是拿公司自己的中位數 205 天校準的，不是拍的）。
>
> **2026-09-01**：⭐⭐⭐**我驗的是服務層，而使用者走的是端點**（L124，同日錯三次）——
> owner 回報 `/documents/2748` 選不到某個承攬案件，我改了三次、「驗證通過」三次，
> 而三次都打在 `ProjectService.get_projects()` 上。服務層與端點之間隔著
> **Pydantic 驗證、參數轉換、回應包裝**三樣東西：①`limit=1000` 在服務層會過而端點
> `le=100` 回 **422** ②那個 422 讓 `useQuery` 失敗 ⇒ `?? []` ⇒ **整個下拉變空**，
> 症狀從「少了某些」惡化成「完全無法篩選」（**是我弄壞的**）③改分頁後讀 `resp.total`
> 而端點回 `pagination.total` ⇒ **迴圈一次都沒跑**。⇒ 前端打端點，**驗證就要打端點**；
> 容器內用 `httpx.ASGITransport(app=app)` 一次就讓 `100→100 筆／1000→226 筆／1001→422`
> 全部現形。⭐⭐**上限不會壞在你改它的那天，會壞在資料長過它的那天**（L125）：
> 那筆案件排第 144 名，而**前一天排第 93、剛好在界內** —— 是當天成案 51 筆把它擠出去的。
> 沒有 commit、沒有部署、沒有錯誤，也沒有人在看。而 Select 的搜尋是在**已取得的那 100 筆**
> 上做的 ⇒「搜尋不到」看起來像「案件不存在」。盤點 45 檔／68 個 Select／19 個前端過濾，
> **逐一對照資料表筆數後只有 2 處真的會壞** —— 掃樣式給你 46 個候選，量資料才知道要修哪 2 個。
> ⭐⭐**我用壞掉的量測產出斷言，還拿它去指責別人**（L126）：`find -name "*_probe*"`
> 要求 probe 前有底線 ⇒ 漏掉 `probe-today-events.py` 這類，我卻據此宣告「全庫只有兩個」
> 並說對方憑空捏造 —— 而我自己上一段才剛引用 L120「磁碟狀態必須查」。**查了，但用錯工具查，
> 比沒查更有說服力。**⇒ 宣告「全庫只有 N 個」前先用已知目標驗那個樣式。
> ⭐**本日產出**：成案 51 筆（已承攬未成案 91→40，剩下的是**同一件工作建了兩次案**，
> 逐組對照表見 `docs/runbooks/quotation_revision_dups_20260901.md`）／
> 報價單匯入的版次分身偵測（03-17 那批 48 張裡 **42 張在 08-20 被重建**，
> 重複 47 張、NT$6,144,188）／weekly 95（下拉取數上限）與 96（設定目錄 SSOT）
> 兩支守門，**都做過負向對照**／設定目錄收斂 P1 標記完成，P2 排 09-15。
>
> ⛔ **2026-09-01 晚：全機 Python 行程隨機 segfault，`wsl --shutdown` 無效**（A66，P1 跨 repo）——
> `ck_missive_backend` 一天重啟 17 次、使用者遇間歇 502，而**公網探針／healthcheck／blackbox 全綠**
> （它是「反覆重啟後恢復」，綠燈之間的空窗才是使用者踩到的）。三層證據：三種死法
> **136(SIGFPE)/1(TypeError)/139(SIGSEGV)**／8 分鐘內**三個 repo 的 HTTP 後端全部 SIGSEGV**（P=3.5×10⁻⁵）／
> dmesg 顯示故障在 `libpython3.11.so`、`libc.so.6`、`python3.13` 裡。
> **⭐ 最關鍵的一筆：`runc` 也在 `libc.so.6` 裡 segfault —— runc 不是 Python，所以這是整個 WSL2 VM 的問題**，
> 不是任何語言執行期或套件。逐項排除：我們的原生擴充（沒裝的 repo 照樣崩）／httptools・uvloop
> （版本不同、我們沒裝 uvloop）／共用基底映像（3.11 與 3.13 都中）／記憶體壓力／容器 OOM／
> 單一壞核心／**VM 累積狀態（重啟後 4 小時內又 6 筆）**。剩下：WSL2 核心 `6.6.87.2-1`／
> Docker Desktop `29.7.2` 的缺陷，或**硬體記憶體**（WHEA 近 3 天 0 筆，但**消費級非 ECC 常常不產生 WHEA**，未排除）。
> ⇒ **下次重開機請順便跑 `mdsched`**，那是唯一還沒被檢驗的候選。
> ⚠️ 判讀：dmesg 只涵蓋開機後，**「沒有故障」在頭幾小時內同時相容於「修好了」與「還沒輪到」**
> （重啟前最長間隔 109 分鐘）。守門＝daily 15；樣本＝`backend/logs/container_die_events.log`。
> 重啟指引＝`docs/runbooks/reboot-pre-flight-20260901.md`。
>
> **2026-09-02**：⭐⭐⭐**公網全站下線 10 小時，而真相不在任何一個綠燈或紅燈裡，
> 在 VM 的 dmesg 裡**（A67／L130）—— `docker_data.vhdx`（356 GB，**PostgreSQL volume 就在裡面**）
> 的 **ext4 journal 損毀**：`JBD2: Invalid checksum recovering data block 231768510`
> ⇒ engine 拿不到資料磁碟 ⇒ cloudflared 沒跑 ⇒ CF 1033。
> ⭐ **最該記住的一件事：`docker desktop status` 一路顯示 `starting`，從來沒有顯示過 `error`。**
> 它在無限重試掛載一顆掛不起來的磁碟，而對外的表述是「還在啟動中」——
> **一個永遠不會完成的啟動，與一個很慢的啟動，在狀態欄裡長得一模一樣**。
> 我第一時間讀成「機器 8 分鐘前才開機，還沒起來」，**那個判讀的每一項事實都是對的**，
> 而它讓我決定「先做別的、稍後再看」。⇒ **`starting` 超過 5 分鐘就不要再等，去看 dmesg。**
> ⚠️ 既有記憶檔 `docker_engine_wedge_1033_recovery` 記的是**另一個成因**（`docker-mcp.exe` 卡住），
> 症狀一模一樣而修法完全不適用（本機根本沒有那個行程）——**一份 runbook 涵蓋一個成因時，標題就要講清楚是哪一個**。
> ⭐ 修法：唯讀 `e2fsck -fn` 先量範圍（損壞**全為良性**：3 殘留 inode／2 目錄 checksum／bitmap 偏差，
> **無 illegal block、無 unattached inode**）→ `e2fsck -fy` → **驗 `needs_recovery` 旗標從 features 消失**
> （「fsck 沒報錯」與「旗標已清除」是兩回事，要驗後者）→ 58 容器全起、**documents 2047／KG 50189**、公網 **8/8 200**、**零資料遺失**。
> ⭐⭐**我寫進 runbook 的裝置代號，12 分鐘後就指向另一顆磁碟**（L131）：寫的當下 `/dev/sdd` 確實是 docker_data
> （UUID 驗過），一次重啟後 sdd 變成 main distro，再一次後 docker_data 成了 `sdf` ——
> **三次開機、同一顆磁碟、三個代號**。照著寫死代號跑 `e2fsck -fy` 會**對錯的磁碟做寫入修復，而且不會報錯**
> （那顆是好的，fsck 愉快跑完回 0）⇒ **修錯對象的失敗形態是綠燈**。已改 `$DEV` ＋ 加辨識程序。
> ⇒ 一般形式：**凡是「開機時由核心依偵測順序指派」的識別碼都不是身分**（`/dev/sdX`、`ethN`、PCI 順序）。
> ⭐⭐⭐**檢核報出了會殺死它自己的那個問題，而沒有人收**（L132）：`fitness_daily_history` 的
> 09-01／09-02 連兩天 `rc=2` 而 `red_steps` 是空的。**我的第一個診斷是錯的** —— 我判成
> 「容器被 segfault 打斷」（A66 最嚴重正是那兩天），**它能解釋每一個現象、時間也吻合**。
> 真相是 `run_fitness_daily.sh` 變成 **CRLF 行尾**，容器內 bash 直接 syntax error、**一行都沒跑過**；
> 揭穿它的不是推理，是**手動在容器內跑一次**（三行 `$'CR': command not found` 就結案）。
> ⇒ **能解釋症狀的假說，在旁邊剛好有大事發生時最危險。**
> ⭐ 真正的形狀：**daily 的 step 10 就是 CRLF 偵測**，註解白紙黑字寫著「守住本 runner 自己能不能執行」，
> 且記著 08-07 踩過同一件事；而 **08-30／08-31 兩天的 red_steps 裡就有這一條** ——
> **報了兩天沒有人收，第三天 CRLF 蔓延到 runner 自己，檢核就死了。**
> ⭐ 第三層：死法 `rc=2` 被 `"RED" if rc != 0` 記成 RED，接著被「連續相同紅燈」的去重判成
> 「跟昨天一樣」而抑制 ⇒ **連兩天沒跑而沒有人收到通知**（去重的前提是「同一個紅燈」，
> 而這裡連紅燈是什麼都不知道）。⚠️ `git status` **看不見**這個差異（比較時會正規化行尾），
> 而 **host 的 Git Bash 容忍 CRLF** ⇒ 手動跑永遠全綠，這就是它藏得住的原因。
> 已改三態（0/1/**其他=ERROR**、一律出聲不去重、weekly 同步修）＋ `scripts/` **13 支 CRLF 轉 LF**
> （含 `run_fitness_weekly.sh` 607 個、**`deploy-public.sh` 257 個**——跑在 host 所以還活著，是下一次的地雷）。
> **容器內複驗：exit 2 → exit 1、16 步全跑完。**
> ⚠️ 兩次都是**斷言／複驗**救的不是判斷力：下錨點命中 2 次才發現 weekly 同族；
> 首次用 `grep -q $'CR'` 掃出 **0 支**（量測工具在待測對象上失效，同 L126），改讀位元組才看到 17 支。
> ⭐⭐**檢核跑在容器裡，而它要的東西不在容器裡**（L133，CRLF 修好後才暴露）＝**A68 待裁示**：
> ①step 0「腳本強制表態閘門」判 13 個檔案未表態，**而它們全都登記在 `skills-inventory.md` 裡** ——
> 它自己印著「讀到 **1/3** 份索引；此環境不含 `.claude/rules/skills-inventory.md`」（容器沒掛 `.claude/`）
> ⇒ **它分不出「沒表態」與「我看不到表態」而選擇報 RED**；
> ②**daily 15（A66 的守門）自己是啞的** —— 五個容器全「取不到（未驗）」，且狀態檔寫入失敗
> （`scripts` 是 rw=false 掛載）⇒ **從上線第一天起就存不了基準**。
> 兩者都不是寫錯，是**放錯地方**；拿不到依賴時正確行為是 **YELLOW（未驗）**，不是 RED 也不是 GREEN。
> ⭐ **A66 的證據換了類別但結論未定**：此前全是「行程崩潰」，本次新增**「靜態資料的校驗碼對不上」**——
> `directory passes checks but fails checksum`（內容對、校驗碼錯）是單一位元翻轉的簽名；
> 崩潰率停機前**單調加速**（1/hr → 19/hr，軟體缺陷通常是穩定速率）。
> ⚠️ 但 **`mdsched` 從未執行過**，而 09-02 早上重開機兩次（皆正常關機、無 Kernel-Power 41）**兩次都錯過**
> ⇒ 硬體**仍未排除**（WHEA 0 筆不足以排除，消費級非 ECC 常不產生 WHEA）。**A66-P3 待下次重開機。**
>
> ⭐**多 session 協同權責**（09-02 建立，owner 同時開 6 個 session）＝
> [`docs/architecture/SESSION_COLLABORATION_RESPONSIBILITY.md`](docs/architecture/SESSION_COLLABORATION_RESPONSIBILITY.md)。
> 三條界線：①**只動自己的 repo**（跨 repo 一律改成通知，理由是可追溯性——
> 你的寫入會出現在別人的 `git status` 裡而他不知道來源）②**共用資源（宿主層）要有指定的記錄者、
> 但不是指揮者**（A66 就是兩個 session 各自讀到同一個誤導欄位、各自往錯方向找數小時＝L127）
> ③⛔**權限邊界不可轉包**——在你這裡被擋下的操作不可請別的 session 代做，那是繞過 owner 的權限決定；
> 本日實例：我的 `git push` 被擋，**不可以**請 ck-aaap-58 代推，只能退回 owner。
>
> **最後更新**: 2026-09-02
>
> **近期重大里程碑**：已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)
> （2026-08-27，v6.59–v6.61 共 46,981 字元；更早的 64 條 08-24 已先移入）。
> **搬移不是刪除**——內容完整保留，只是不再每個 session 載入一遍。
> 教訓的權威來源是 [`docs/architecture/LESSONS_REGISTRY.md`](docs/architecture/LESSONS_REGISTRY.md)。

---

## 專案概述

CK_Missive 是一套企業級公文管理系統，搭載 Hermes Agent 智慧助理：

1. **公文管理** - 收發文登錄、流水序號自動編排、附件管理
2. **行事曆整合** - 公文截止日追蹤、Google Calendar 雙向同步、批次操作
3. **邀標/報價管理** - 案件建案(case_code)、報價紀錄上傳、承攬狀態追蹤、成案觸發
4. **承攬案件管理** - 成案專案(project_code)、人員配置、里程碑/甘特圖、公文關聯
5. **委託單位/協力廠商** - vendor_type 分離管理、inline 新增、ERP 關聯
6. **AI 代理人** - 26 真工具、自省閉環、主動推薦、Hermes Agent gateway (via ck-missive-bridge skill)
7. **ERP 財務模組** - 費用報銷、統一帳本、財務彙總、電子發票同步
8. **知識圖譜** - Code-graph 5,721 實體、DB/TS/Python AST 入圖

### 多專案架構 (v5.5.6, 2026-04-15 重整)

```
CK_Missive          (本專案·核心) — 公文 AI 引擎 + Hermes Agent 公網入口
CK_lvrland_Webmap   (兄弟專案)    — 土地查估 Webmap (Phase 2+ 接入)
CK_PileMgmt         (兄弟專案)    — 基樁管理 (Phase 2+ 接入)

[已廢止]
CK_OpenClaw         → ADR-0014 Hermes Agent 取代（2026-05-12 歸檔）
CK_NemoClaw         → ADR-0015 Cloudflare Tunnel 取代（2026-05-12 歸檔）
```

### 平台級 Subdomain 策略 (ADR-0016)

```
missive.cksurvey.tw     →  公文系統 (UI + API)，已上線
hermes.cksurvey.tw      →  Hermes Agent gateway (Phase 1 後啟用)
lvrland.cksurvey.tw     →  土地查估，🟢 已上線（SSO 整合）
pilemgmt.cksurvey.tw    →  基樁管理，🟢 已上線（SSO 整合）⚠️ 實際 hostname；規劃曾標 pile.cksurvey.tw 但未部署
digitaltwin.cksurvey.tw →  數位孿生/隧道，🟢 已上線（SSO 整合）
kg.cksurvey.tw          →  聯邦知識圖譜 Hub (選用)
```

> **架構原則**: Cloudflare Tunnel 統一公網入口；Cloudflare Access SSO 跨專案；
> 各專案獨立 DB；Hermes 共用 gateway 跨專案聯邦。零費用全 Free 方案。

### LINE / Telegram 多頻道整合（via Hermes Agent Gateway）

```
LINE 小花貓Aroan → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Telegram @Aaron_ckbot → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Discord → Interactions Endpoint → Missive Agent API (直連)
```

- Hermes 部署指南: `CK_AaaP/runbooks/hermes-stack/`
- Skill 定義: `docs/hermes-skills/ck-missive-bridge/`
- **重點**: Skill 中 API URL 必須用 `host.docker.internal:8001`（不是 `localhost`）
- **重點**: LINE webhook 需要公網 HTTPS，由 Cloudflare Tunnel 提供

> **歷史**: OpenClaw 整合已於 ADR-0014 廢止（2026-05-12），由 Hermes Agent 取代。
> 舊運維指南: `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md`（僅供參考）

---

## 規範索引

> 以下規範位於 `.claude/rules/`，啟動時**自動載入**，無需手動引用。

| 規範檔案 | 說明 |
|---------|------|
| `skills-inventory.md` | Skills / Commands / Agents 完整清單 |
| `hooks-guide.md` | Hooks 自動化配置與協議 |
| `ci-cd.md` | CI/CD 工作流 |
| `auth-environment.md` | 認證與環境檢測規範 |
| `development-rules.md` | 開發強制規範 (SSOT, 型別, API, 服務層, DI) |
| `architecture.md` | 專案結構總覽（索引） |
| `architecture-backend.md` | 後端：Models/Services/API/Repositories |
| `architecture-frontend.md` | 前端：Pages/Hooks/型別/錯誤處理 |
| `directory-structure.md` | `.claude/` 配置目錄結構 |
| `security.md` | 安全規範 |
| `testing.md` | 測試規範 |

### 其他重要文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引與常見錯誤 |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |

### 架構標準化（v5.9.6 ~ v5.9.8, 2026-04-25）

| 文件 | 說明 |
|------|------|
| `docs/architecture/STANDARD_REFERENCE.md` | 📘 **跨 repo 架構標準** — DDD/SSOT/Hermes/觀測棧 12 章 + §13 AI-Native UX |
| `docs/architecture/SERVICE_CONTEXT_MAP.md` | 🗂 services/ 頂層 85 散戶 × 16 bounded context 映射（漸進 DDD）|
| `docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` | 🧠 坤哥意識體 5 整合面向 + O1-O6 路線（v5.9.7/v5.9.8 落地紀錄）|
| `docs/architecture/WIKI_KG_BACKFILL_STRATEGY.md` | 📋 Wiki↔KG 三方案 ROI（已執行 X，連結率 30%→86%）|
| `docs/ops/baseline-fix-patch-preview.md` | ⚙️ Hermes baseline 修復 patch 預覽（Patch A+B 三路徑）|
| `scripts/checks/run_fitness.sh` | 🧪 本地 fitness runner — **6 step**（零 CI 費用）|
| `scripts/checks/service_dir_entropy.py` | 📊 services/ 頂層散戶比例（閾值 20%）|
| `scripts/checks/config_dead_reader_scan.py` | 🔍 yaml config dead reader 偵測（含 module function）|
| `scripts/checks/soul_mirror_drift_check.py` | 🔄 SOUL.md 跨 repo drift（fitness step 3）|
| `scripts/checks/wiki_kg_link_audit.py` | 🔗 Wiki↔KG 連結率 by entity_type（fitness step 4）|
| `scripts/checks/kg_embedding_coverage_check.py` | 🎯 KG pgvector 覆蓋率（fitness step 5）|
| `scripts/sync/sync_soul_to_hermes.sh` | 🔁 SOUL.md 跨 repo 手動同步（--apply gate）|
| `scripts/sync/dispatch_kg_ingest.py` | 🆕 方案 X Phase 1 — dispatch → KG ingest |
| `scripts/sync/backfill_wiki_*.py` | 🆕 wiki frontmatter 補 kg_entity_id（dispatch/project）|
| `scripts/sync/backfill_kg_embeddings_all.py` | 🎯 KG embedding 通用 backfill（critical/types/all 模式）|
| `/arch-fitness` slash command | 本地月度架構覆盤觸發 |

### v5.9.8 落地里程碑

- ✅ Wiki↔KG 連結率 **30% → 86%**（dispatch 0% → 100%, project 56% → 86%）
- ✅ KG pgvector embedding 業務 entity **0% → 100%**（10,792 筆 / 5 分鐘 / zero cost）
- ✅ SOUL.md 跨 repo 同步（CK_Missive ↔ CK_AaaP）+ Soul fidelity groq 75% → 80%
- ✅ ADR-0030 GO 條件 4/5 達標（#5 P95 待 5/20 會議重訂方案）

---

## 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL **15.14**（image `pgvector/pgvector:0.8.0-pg15`，Docker，**127.0.0.1:5434** 僅本機）
  <!-- 2026-08-10 更正：原記「PostgreSQL 16」與實際不符。這不是無害的筆誤 ——
       備份是 backend 容器的 pg_dump 17.10 產生的，而伺服器是 15.14，
       dump 裡帶著 15 認不得的 transaction_timeout，帶 ON_ERROR_STOP 還原會中止。
       版本記載錯誤會讓人在災難當下判斷錯誤。詳見 docs/runbooks/disaster-recovery.md §4 -->
- 客戶端工具版本落差（**還原時會咬人**）：postgres 容器 psql 15.14／backend 容器 pg_dump·psql **17.10**
- ~~NemoClaw 監控塔: http://localhost:9000~~ — **廢止** (ADR-0015)
- vLLM 本地推理: http://localhost:8000 (Docker, Qwen2.5-7B-AWQ)
- Ollama: http://localhost:11434 (Docker, nomic-embed)

### 常用命令
```powershell
# === 推薦：統一管理腳本 ===
.\scripts\dev\dev-start.ps1              # 混合模式啟動（推薦）
.\scripts\dev\dev-start.ps1 -Status      # 查看所有服務狀態
.\scripts\dev\dev-start.ps1 -Restart     # 重啟 PM2 服務
.\scripts\dev\dev-start.ps1 -FullDocker  # 全 Docker 模式
.\scripts\dev\dev-stop.ps1               # 停止所有服務
.\scripts\dev\dev-stop.ps1 -KeepInfra    # 僅停 PM2，保留 DB/Redis

# === 手動啟動 ===
docker compose -f docker-compose.infra.yml --profile tunnel up -d
# ⚠️ `--profile tunnel` 不可省：`cloudflared` 有 `profiles: ['tunnel']`，
#    不帶它 `up -d` **不會把公網入口建回來**（`config --services` 也不列它）。
#    `restart: unless-stopped` 只救重啟，救不了「容器被移除」。
#    2026-08-26 由 CK_AaaP 指出容器不在 `config --services` 裡而查出。
      # 基礎設施
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm run dev
pm2 start ecosystem.config.js

# === 公網部署 ===
bash scripts/deploy/deploy-public.sh     # v2.0.0 一鍵：前端 build → 後端 image build（帶 build 身分）
                                         #   → 換容器 → health → 驗 runtime commit → 驗公網 200
                                         # 只改前端：bash scripts/deploy/deploy-public.sh --frontend-only

# === 驗證 ===
cd frontend && npx tsc --noEmit          # TypeScript 檢查
cd backend && python -m py_compile app/main.py  # Python 語法檢查

# === Skills/知識地圖 ===
node .claude/scripts/validate-all.cjs            # Skills/Agents 格式驗證
node .claude/scripts/generate-index.cjs          # 索引重建
node .claude/scripts/generate-knowledge-map.cjs  # 知識地圖生成（全量重建）
node .claude/scripts/generate-knowledge-map.cjs --diff      # 差異報告（Heptabase 增量更新）
node .claude/scripts/generate-knowledge-map.cjs --if-stale  # 僅在源檔案更新時重建
node .claude/scripts/promote-learned-patterns.cjs # 學習模式升級
```

---

## 整合來源

本配置整合以下最佳實踐：

- [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) - Skills/Hooks/Agents/Commands 架構
- [superpowers](https://github.com/obra/superpowers) (v4.0.3) - TDD、系統化除錯、子代理開發
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) - 生產級工作流自動化

**核心理念**: 測試驅動開發 | 系統化優於臨時性 | 簡潔為首要目標 | 證據優於聲稱

---

> 配置維護: Claude Code Assistant | 版本: v1.86.0
