# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.60（2026-08-21）/ ⭐⭐公網未帶憑證可取得業務資料、且可免費用我們的 GPU；而四次量測都會給出「已經擋住了」的錯誤結論＋CSRF 不是認證（帶著公開可取的 token 再打就過）＋收費設計禁令立為規範 §0＋pyflakes 掃出三個既有真缺陷（LINE 發票圖片必然 NameError、weekly fitness job 每次 return 就爆）｜前次 v6.59（2026-08-19）/ ⭐⭐斷電復原＋ERP/標案整輪：**排程被某個程式持續停用**（含三個異地備份，非斷電所致）＋**標案預算金額其實抓得到而系統只組了網址沒去抓**＋決標資料全庫 0 筆而分析功能在分析不存在的資料＋既有報價單彙整 XLS 匯入（277 列，一個入口 upsert、先預覽再寫入）＋報價單 PDF 與自動存檔＋`created_by` 從來沒被寫過（77 張全 NULL）｜前次 v6.58（2026-08-18）/ ⭐⭐ERP 三件事全部是「送出的與收到的不一致」的變形（`extra='forbid'` 造成編輯 422／清空選填欄位就 422，同型 8 支／前端型別漏欄位而 tsc 守不住）＋公司留成可設定（毛利分母改為專案可用）＋報價單正式文件輸出（以 owner 實際範本為底）＋**相容字污染全庫掃描：白名單只涵蓋 27 欄而實際 29 欄受污染，已長出重複機關與 2 組 KG 實體**＋毛利可算指標原本結構上永遠是 0%（估列成本四欄自上線後從沒人填過）｜前次 v6.57/ ⭐⭐儀器化比檢核先找到問題（八次補 detail／查證＝八個發現，含 pip-audit 在容器裡從來沒跑起來過、對帳報出不存在的百萬差額、soul_mirror_sync「成功」74 次卻從未同步）＋優先序改為 儀器化 > 提問 > 新增檢核＋測試債基線少算 3 多算 3（且我一度拿錯環境的結果改它）＋NER 存量其實是 572 不是 2000＋價值層 11 個零流量候選一個都不刪＋cron 沉默判準改扣除法（補守則時差點把死了 200 小時的 job 判成綠的）＋**19 支檢核會在「要報問題的那一刻」崩掉**（L92，host cp950；平常走綠燈分支沒事）｜前次 v6.56/ ⭐⭐自我檢核投資方向轉向（人提問 6:檢核 0，改縮小「不需要證明」的範圍而非估總量）＋消滅兩個病灶家族（模組匯入即失敗／靜態守護寫法盲區）＋履歷機制（九處散落收斂成組得出來的一頁）＋走查改記 runtime 事實＋治理強制 baseline 70→0＋stub 清理 entropy 21.1%→14.1%｜前次 v6.55/ ⭐⭐異常關機讓 12 個排程整批沒跑且不補跑，而稽核全綠（8 天門檻抓不到「這一次沒跑」）＋監控覆蓋率拿看得見的東西當分母（55 個閾值只有 15 個在畫面上）＋Windows 上容器路徑會靜靜讀寫 `D:\app\`（L90／L91）｜前次 v6.54/ ⭐⭐容器內 daily 連三天 RED 而回報的全綠是 host 結果＋wiki_compile 上週一整支失敗＋索引數字漂移納管｜前次 v6.53/ ⭐⭐公文附件與金鑰從來沒有異地備份而所有訊號都是綠的｜前次 v6.52/ ⭐⭐資料層不再對 LAN 開放（5 專案 12 埠，實測可被利用）＋分身帳號不再進人員下拉＋承攬案件兩條路徑共用防重｜前次 v6.51/ ⭐腳本存量表態全數清空（106→0）＋資料層對 LAN 開放（5 專案 12 埠）＋員工「看得到卻用不了」（管理員判定四份規則）｜前次 v6.50/ ⭐走查入口五份收斂成一份＋DT 21 個 commit 部署＋MinIO 異地備份（原本零備份）＋跨 repo 退出碼約定衝突（L89）｜前次 v6.49/ ⭐走查可信度收斂＋lvrland 線上故障＋兩起我自己造成的事故（L85/L86）｜前次 v6.48/ ⭐跨 repo 安全三項：SSO 隨活動延長＋pile 文檔端點補認證＋DT 原始碼外洩關閉（L84）｜前次 v6.47/ ⭐憑證到期改為明確要求重登（不再靜默吞掉動作）＋作業紀錄鏈語意檢核（錯了四個月無人知）＋三個「送出的與收到的不一致」（L83）｜前次 v6.46/ ⭐自走檢核程序：判定邏輯單一化＋檢核者自己納入被檢核＋排程存活哨兵＋走查第 4 個專案｜前次 v6.45/ ⭐憑證存活稽核（token 提請複查）+ 學習閉環納管（28 天零產出終於可見）+ 瀏覽器走查導入第三個專案｜前次 v6.44/ ⭐詳情頁 tab 只呈現不操作（規範歸零）+ 行動裝置檢視與填報 + 自主檢核機制實跑驗證（揪出我自己造成的半接通）｜前次 v6.43/ ⭐檢核結果沒有接收者的第三種形態（頁面層只驗新鮮度）+ 測試污染正式晨報緩衝區根治 + 價值層判定解除永久阻斷｜前次 v6.42/ ⭐LINE 訊息統整分群、07:30 一次送出 + Telegram 死管道全收斂｜前次 v6.41/ ⭐code wiki 接進 LLM wiki 管線｜前次 v6.40/ ⭐圖譜兩層職責明確化 + NER 關係失效根治｜前次 v6.39/ ⭐自我循環閉環：月度架構覆盤接回輸出端｜前次 v6.38/ ⭐三者對應檢核 + API 文件內網化｜前次 v6.37/ ⭐測試套件納入自動檢核＋清理測試債｜前次 v6.36/ ⭐測試套件改用獨立測試庫｜前次 v6.35/ ⭐kunge 架構檢視（否證異質同工、補上缺席的成長結論、人格改讀 SSOT）｜前次 v6.34/ ⭐運維頁三組結構 + 晨報與推播獨立 tab（接上零消費的既有端點）｜前次 v6.33/ ⭐檢核自身假綠根治（三支 fitness 腳本 `|| true` 恆印全綠）+ 第 5 階補裝置形態維度 + 揭發 fitness_weekly 連 9 週 RED 無人知｜前次 v6.32 第 6 階價值層起步（Prometheus 真實流量）+ 揭發 Missive 缺席觀測 3.5 月 + A2 記載更正（測試套件打生產 DB）｜前次 v6.31 自我檢核六階階梯 + 引擎跨專案共享化｜前次 v6.29「沉默成功」大掃除 — 一天四個同型缺陷根治（備份 BOM／發票辨識三路全滅／核銷 409 假重複／CF Tunnel 空跑）＋制度化（契約規則 4 + 3 護欄）— 見下方里程碑
> **最後更新**: 2026-08-24
>
> **近期重大里程碑**：
> - **v6.59 (08-18 晚) — ⭐⭐斷電復原覆盤：真正的傷害不是漏跑，是恢復窗口內量到的東西會產生假紅燈（零 app 變更、零 rebuild、五系統 200、2012 docs/49796 KG）**：15:36:44 非正常關機、16:13:36 恢復（Windows event 41/6008/6005），cron 事件斷層 33 分鐘。**Docker 全數自動拉回，62 容器 0 非健康 0 重啟中**；斷電窗口落在下午，凌晨的低頻關鍵排程全部早已跑完 ⇒ **本次無任何低頻 job 漏跑**（對照 08-12 那次凌晨關機漏掉 12 支）。① **⭐⭐有程式在持續停用排程（含異地備份），而我一開始把它誤判成斷電後遺症**：開機後 17 分鐘量測，`CK-Missive-Offsite-Backup`／lvrland／DT **三個異地備份＋PM2 Autostart 同時 `State=Disabled`、`Settings.Enabled=False`**，而當天 15:26 的 pre-flight 白紙黑字記著「27 支全部 Ready」——**看起來就是斷電把它們弄壞了**。20 分鐘後四支全部回到 `Ready`（我沒有做任何啟用操作），四小時後換 `CK_Missive-SOUL-Mirror-Sync` 被停用。**我第一版結論是「Task Scheduler 恢復期的暫態」，那是錯的**——錯在只看了 `^CK` 開頭那 27 支，把停用歸因到當下最顯眼的事件。**掃全機器 49 支非微軟排程之後事情完全不同**：Adobe Acrobat Update（**最後執行 2025-01-24**）、Zoom Update（2025-02-03）、OneDrive Startup（08-12＝**上一次**異常關機）、SoftLandingTrigger（**斷電後 2 小時**才被停用）全都是 Disabled ⇒ **與斷電無關**。事件記錄（`TaskScheduler/Operational` **ID 142=disabled**）給出決定性證據：`16:19:44 User "User1" disabled \CK-Missive-Offsite-Backup`／`16:50:53 disabled \CK_Missive-SOUL-Mirror-Sync`／`18:35:16 updated \CK-Hermes-Health-Smoke` ——**停用動作分散在整個下午，是持續行為不是單一時點**。本機裝有 IObit **Advanced SystemCare 19.4.0**（06-22 安裝、四程序常駐），其「啟動優化」正是做這件事，上表 Adobe／Zoom／OneDrive 也都是這類軟體的典型目標；⚠️ **但事件記錄只記執行身分「User1」不記程式名 ⇒ 高度相關而非確證，不得寫成已證實的因果**。**判準因此要改**：`State` 不可作單次判準（同一件事量兩次、兩次一致才算數），**真正騙不了人的是 `LastRunTime` 有沒有如期推進**。連帶第二個假訊號：lvrland `static-checks.json` 在 16:25 被寫成 `RED fail=1`，重跑是 **23 步全 PASS / exit 0** ——**恢復窗口內產生的結果檔一律要重跑覆蓋**，否則它會留在檔裡持續污染下游（`windows_task_liveness_audit` 會去讀別的 repo 的結果檔，照著它報 RED）。全部寫進 `docs/runbooks/unexpected-shutdown-recovery.md` **§0**（含診斷指令；⚠️ 查 Security log 4701 會 timeout，要查 TaskScheduler Operational）。② **⭐pile 走查 36 條全紅其實是一個已修故障的殘留**：36 個 failure 的 problems **完全一樣**（`/api/metrics/web-vitals` HTTP 502），時間戳是今晨 06:09＝pile 502 期間，而那個 502 在 pre-flight 就修好了（cloudflared originService 指到前端 3005）。**不是 36 個獨立故障，是一個故障 × 36 條路由**；重跑 **36/0 全綠**。判準：failure 的訊息若完全相同，先問「是不是同一個上游」再逐條追。③ **⭐`llm_quota_check` 自 08-15 06:53 起沉默 3.5 天（門檻 6 小時），而它跨越了兩次容器重啟都沒復活**。手動觸發**完全正常**（groq 1.8%／nvidia 11.5%／cost 0.2%，回傳完整 detail）⇒ 又一個「隔離正常≠嵌入正常」，是排程器沒觸發它而不是 job 壞了。**⚠️ 而我的診斷動作把證據抹掉了**：手動觸發帶 `@tracked_job` 會寫進 `cron_events`，把 age 從 84h 重置為 0 ——`cron_silent_dormant_check` 原本明講「再過一個週期仍未執行就會判紅」，那個訊號被我消掉了。根因未定（`max_instances=1` + 某次執行未返回是主要嫌疑，但容器 log 只有 3 小時、找不到 skip 證據），**實害目前為零**（離 80% 閾值很遠）⇒ 列為觀察項而非宣稱已解決。④ **⭐兩支稽核對同一件事有兩個門檻**：`cron_silent_dormant_check` 對 `llm_quota_check` 用 **12 小時**（抓到了，並正確地用扣除法把「重啟前已沉默 81.4h」與「這次啟動還沒輪到它」分開講），而 `scheduler_liveness_audit` 一律用 **8 天**（3.5 天不算 stale，回報 `dormant 0`）——**同一個 job，一支說有問題、一支說沒問題，而兩份都不會報錯**。⑤ **⭐兩支 Logon 觸發排程持續停用且需提權才能啟用**（`CK-Hermes-Health-Smoke`、`CK_DigitalTunnel-PostRestart-Check`，`Enable-ScheduledTask` 回 `Access is denied`）——它們在 16:16 都執行成功過（Result=0）才被停用，且**沒有 `DeleteExpiredTaskAfter`／`EndBoundary`＝不是設計成一次性的**。待 owner 提權處理。⑥ **DT celery worker/beat 曾在重啟循環**（`ImportError: cannot import name '_get_engine'`，重啟 18 次＝排程與非同步任務全停）——查 git 發現**另一個 session 正在該 repo 工作**（17:16 的 commit 標題正是「拆套件搬走了定義，卻沒有人檢查還有誰指著它」），**刻意不介入避免撞車**；複驗已恢復 healthy。⑦ **複查全綠**：五系統首頁＋API 兩層／tsc EXIT=0／py_compile **824 檔 0 失敗**／容器內 daily **14 步（判定 9 步）全過、786 模組匯入全成功**／八條生命跡象全綠（毛利可算 **23%**）／cron **53 healthy 0 RED 0 無訊號**／producer watchdog **GREEN 38 項 0 blind spot**／異地備份 NAS **33 份**（今晨 01:59）／六 repo git 全同步。**元教訓：異常關機的復原檢查，前 20 分鐘該做的不是「查有沒有壞」而是「什麼都先別查」——那段時間量到的紅燈，有很高比例是恢復過程本身造成的，而追它們的成本遠高於等 20 分鐘。**
> - **v6.59 續（08-19 全日）— ⭐⭐標案「找不到資料」查到底：資料一直都在，而系統只組了網址沒去抓；另 ERP 一條龍與既有 XLS 匯入落地（多次 rebuild 皆過 L76、五系統 200、2012 docs/49814 KG）**：① **⭐⭐標案預算金額其實抓得到**——`services/tender/search.py` 把 PCC 詳情頁的**網址**組出來給前端，卻**從來沒有去抓那一頁**；而 `budget` 取自 DB，PCC 來源 60,296 筆全是 NULL ⇒ 永遠空白。實測三筆全部 HTTP 200／0.2~1.2 秒／無驗證碼，且值可交叉驗證（`NzEzMDA1NzQ=`→4,000,000 與該案 ezbid 版本一致、`NzEyODY4Nzk=`→625,000 與該案 PM 合約金額一致）。**這推翻了 L77「enrichment 死結」的一部分**：那條講的是採購性質／底價需要 org_id（仍成立），但**預算金額就寫在詳情頁本文**。已改為沒有金額才抓、抓到寫回 DB（同一筆最多抓一次）、逾時 8 秒、失敗不擋詳情頁。② **⭐⭐既有 ezbid↔PCC 自動 link 為何補不上**：ADR-0046 用 `pg_trgm` 相似度計分、HIGH 門檻 0.85，而**實測兩筆標題與機關名完全相同、similarity 都是 0.0000**（pg_trgm 對中文無效，本專案早有記錄）⇒ **結構上永遠達不到門檻**，這就是 47,232 筆 ezbid 只 link 到 2,033 筆（4.3%）的原因。改用精確鍵（`job_number`＋標題前 20 字）即時配對，跨來源可靠配對 **14,105 組**，其中 pcc 缺 budget 而 ezbid 有的佔 **98.6%**。③ **⭐搜尋重複顯示**：去重時 `seen` 用 `unit_id`+title 建鍵、比對新項目卻用 `ezbid_id`+title ——**兩個鍵的第一段取自不同欄位，永遠不可能相等**；且三軌合併（DB／g0v／ezbid 即時）**每一段各自去重**，漏一段就漏出去。**我第一次只修了其中一段，owner 再次回報才發現**。改到唯一出口統一處理，鍵用 `job_number`＋標題（只用標題會把 B115076 公開招標與 B115077 公開取得報價單併成一筆＝兩個不同的案；只用 job_number 會撞號，實測 1,129 組同號不同標題）。④ **⭐`%3D` 讓查得到的資料變成查不到**：PCC 的 base64 `unit_id` 尾端有 `=`，在路由路徑上被編成 `%3D`，還原只要任何一段漏掉就查無。修在 schema 的 field_validator（收件端）——該欄位有多個來源（搜尋連結／書籤／外部貼入），逐一修等於維護多份判準。⚠️ **我前一版把它改成「回明確的查無訊息」，那是治標**：訊息是對的，但那筆資料本來就查得到，不該走到那條路徑。⑤ **⭐⭐決標資訊全庫 0 筆**：109,344 筆標案裡 `award_amount`／`award_result`／`bidders` **全部 0**，`tender_type` 分布印證（決標類只有 7 筆「更正決標公告」）——抓取端只抓招標公告。而 `services/tender/analytics.py` 有完整的決標分析（本週決標／得標廠商／預算vs底價vs決標金額），**分析的是從來沒進來的資料，恆為 0 而不報錯**。g0v API 現在回 HTML 不是 JSON（實測 200／2,867 bytes），三條路徑都還沒驗成 ⇒ 寫成 `docs/architecture/TENDER_DATA_GAPS.md`，建議先驗一筆 PCC 決標頁再談批次。⑥ **⭐⭐`created_by` 從來沒有被寫過**（77 張報價單全 NULL）：`service.create` 第 151 行早就在寫它，**端點卻沒把 user 傳進去**——欄位存在、service 支援、端點不傳，沒有任何一層會報錯。正式報價單的「服務人員／E-mail」正是取自它 ⇒ 一直空白。掃同型另找到 2 處（Excel 匯入、PM 案件建立）。⑦ **⭐報價單 PDF 與自動存檔**（owner 指定 LibreOffice 保版面、只留最新一份）：PDF 由同一份 xlsx 範本轉出（版面只有一份來源），實測 200／`%PDF-1.7`／1.45s／中文字型正常；存檔落在既有 `pm_case_attachments`（以 case_code 關聯）不另造表。**頁數 4→1**（範本沒設列印縮放，A~G 欄超過 A4 直式被橫向切開）。⚠️ **範本 E13 殘留 hyperlink**：openpyxl 對「有 hyperlink 但 value=None」的儲存格會把 target 當顯示值寫出去 ⇒ 每份報價單印出 `mailto:xxx@gmail.com`。⑧ **⭐既有報價單彙整 XLS 匯入**（owner：線上產出未完全上線前這是目前階段重點）：114 檔 **208 列**（跨 5 個工作表）＋115 檔 **69 列**＝277 列，而系統只有 77 張；以案名比對**系統裡沒有 179 筆** ⇒ 匯入必須支援新增（既有 `pm/cases/import-xlsx` 是拿第一欄當 id 去更新，不適用）。新增 `legacy_quotation_no` 欄位（全庫掃過沒有任何現成欄位可放，而它是 XLS／紙本／**回簽 PDF 檔名**三者共同的識別）。**一個入口做 upsert、先預覽再寫入**。⚠️ 第一版只收 8 欄，漏掉實收金額／收款日期／配合廠商／支出金額／統編／聯絡資訊／發票日——**匯入了卻少這些，等於還是得回去翻 Excel**。⚠️ 兩份檔案表頭不一致（115「發票日期」／114「發票日」），兩個都收。**⚠️ 兩份彙整表都沒有「發票號」欄位**，只有發票日期。⑨ **⭐PM 統計卡與列表對不起來**：「報價中」讀 `in_progress`（PM 案件沒有這個狀態，恆 0）、「已成案」讀 `closed`（實際是已結案）⇒ 後端回的 `contracted:2` 完全沒地方顯示。另 `statFilter` **只有定義與設定、沒有任何地方讀它篩選**——四張卡點了只變色、列表不動。⑩ **⭐匯出/匯入在公網一律 403**：四處用裸 `fetch` 不帶 `X-CSRF-Token`（PM 案件匯出入、里程碑匯出入），公網實測 `403 CSRF 驗證失敗：缺少 X-CSRF-Token header`，而前端 catch 吞成一句「匯出失敗」。⚠️ **我一度宣告「診斷錯了不是認證問題」——那句話本身才是錯的**：我在 localhost 測，而本機 `AUTH_DISABLED=true`，CSRF 中介層第一件事就是豁免 ⇒ **在有豁免的環境驗證安全機制等於沒有驗證**。⑪ **⚠️ 我自己造成的四件事**（全部由實跑或 hook 抓到，不是讀程式碼看出來的）：(a) Dockerfile 註解插在 `\` 續行中間，`libreoffice-calc` 被吞掉——build log 照樣印安裝過程、映像照樣 Built，而映像內 `dpkg -l | grep -c libreoffice` = **0**（同 v6.52 的 `COOKIE=... \`）；(b) 新 schema 沒加進 `__init__` 匯出，backend 起不來、公網 502（owner 當場遇到）⇒ 之後改為**啟動前先在映像裡驗證整條匯入鏈**；(c) **`legacy_quotation_no` 只加到 ORM 就停了**，而 `schemas/erp/quotation.py` 同一個 class 底下就寫著 08-17 為 `quotation_no` 記的同一種失敗（「產出端完成、接收端無人讀取、不拋錯、稽核仍綠、功能目的落空」）——**同一個檔案、兩天後再踩一次**，是 stop hook 抓到的；(d) 三次寫出未定義的 `logger`。⑫ **⭐owner 指出 `53a59b30` 的功能沒進 image** —— 查證屬實（容器內 `pcc_detail` grep = 0），已重建並改為**在映像內直接驗證才啟動**。**元教訓：這一輪最重要的三個發現都是「系統把事情做了一半」——組了網址沒去抓、加了欄位沒讓它到達 API、寫了去重卻用兩組不同欄位當鍵；而三者的共同點是沒有任何一方會報錯。**
> - **v6.60（08-21）— ⭐⭐公網未帶憑證可取得業務資料與免費用我們的 GPU；而「已經擋住了」是假的（多次 rebuild 皆過 L76、走查 20/20、整合鏈 5/5、五系統 200、2017 docs/49897 KG）**：① **⭐⭐實測證據**：`/api/documents-enhanced/statistics` 公網未帶任何憑證回 **200**，吐出 `{"total":2017,"current_year_count":496,"delivery_method_stats":{"electronic":459,"paper":144}}`—— 任何人都知道這家公司有多少公文、今年多少、交換方式分布。**根因不是某個端點忘了加**：`TUNNEL_GUARD_ENABLED=false`（08-03 的既有決策，它是 all-or-nothing 會擋掉整個 SPA）⇒ **所有沒有自帶認證的端點一律對外**。runtime dependency 樹：734 條裡 **71 條**沒有任何認證依賴。② **⭐⭐CSRF 不是認證 —— 我差點把假的安全感當成修好了**：第一次實測那批全回 403，看起來像擋住了；但 `/api/secure-site-management/csrf-token` 是**刻意公開**的（L68 自癒需要），未登入即可取得 43 字元 token，帶著它再打就過 —— `ai/config` 回 200 並吐出 provider 清單與 `host.docker.internal:11434` **內網位址**。**判準因此要改：帶著公開可取的 CSRF token 之後仍然 401 才算真的擋住。**③ **⭐⭐被開放的是會燒錢的那些**：`document_ai`／`voice_transcription`／`diagram_analysis` 三支**各 0 行認證**，而端點全是消耗 GPU／LLM 的（摘要／分類／關鍵字／自然語言搜尋／意圖解析／機關比對／語音轉錄／圖表與視覺分析）—— 對外開放就是**別人用、我們付費**。④ **⭐owner 立規範「不得要新增額外費用之設計」** → 寫進 `.claude/rules/development-rules.md` **§0**，把既有決策明文化（03-09 Actions 停用、06-17 維持免費、08-21 評估 `claude-code-security-review` **不導入**）。**對外開放的推論端點也屬這一類**。⑤ **⭐為什麼不導入那個安全工具（owner 指定評估）**：GitHub Action 路徑不可行（Actions 已停用、本專案不走 PR 流程、每次分析計費）；它主打「lower false positives」方向對，**但本專案的噪音來源不在它的排除清單裡** —— `security_issues` 的 **139 個誤判裡 122 個是同一條規則**（「端點缺少認證裝飾器」，認不出 `Depends(require_auth())`），而真問題只有 23 個。**今天這個外洩就淹在那 122 個噪音裡**。零成本替代＝FastAPI 的 **runtime dependency 樹**，成品 `public_endpoint_auth_audit.py`（weekly 64，白名單每條寫明理由、baseline 逐步清、**探測不到就 exit 2 不下結論**；鑑別力實測：現況 GREEN／模擬新增即 RED／還原回 GREEN）。⑥ **收斂結果**：無認證端點 **71 → 36**（其中 30 條刻意公開且各有理由），缺口 **19 → 6**。修法一律在 **router 層**而不是逐一改端點參數 —— **逐一改會漏，而漏掉的那條不會有人發現**（`documents/list.py` 就是這樣：多數端點有 `require_auth`，唯獨 by-project 與 integrated-search 漏掉）。`ai/agent/tools` 改用 **X-Service-Token**（呼叫者是 Hermes 這台機器，沒有使用者 session）。⑦ **⭐整合鏈驗證當場抓到我**：加了 service token 後 `chain_3_tools_manifest` 立刻 401。查證：**Hermes 端本來就帶**（`tools.py:_make_headers`），真正的整合沒壞 —— 壞的是**驗證腳本自己**，它的 docstring 還寫著「manifest 公開」。**L81「換了出口就要換整條鏈」**：改了端點認證，消費端之一沒跟上，而它的失敗看起來像整合斷了。已修並改為「沒有 token 就說無法驗證」。⑧ **⭐pyflakes 掃出既有真缺陷**（起因是我**第四次**寫出未匯入的名稱）：**`line_bot.py` 改用統一辨識器後 import 沒跟著換 ⇒ LINE 傳發票圖片必然 NameError**，被外層 except 吞成「圖片處理時發生錯誤」；**`scheduler.py` 的 `history_ok` 從來沒定義過**而兩處 return 都用它 ⇒ weekly fitness job 每次執行到 return 就爆；`memory_wiki_metrics.py` 缺 `logging`／`Dict`（那兩處 logger 只在**出事時**才會走到 —— 平常不爆，一出事就再爆一次並蓋掉真正的原因）。排除 `import *` 與字串型別註解的噪音後**真缺陷清零**。⑨ **⚠️ 量測方法失敗四次才拿到可信結果**（全部記在 probe 腳本裡）：urllib 預設 UA 被 **Cloudflare 擋**（全 403，看起來像應用層擋住）、bash `while read` 裡的 curl **吃掉 stdin**（全 000）、連續快打觸發**速率限制**（全 000）、token 解析寫壞（`token=無` 卻仍印 403）。**四次都會給出「已經擋住了」的錯誤結論。****元教訓：這一輪最危險的不是那 71 條端點，是我有四次機會宣告「已經擋住了」而每一次都會是錯的 —— 安全驗證的結論，取決於量測方法本身有沒有先被驗證。**
> - **v6.60 續（08-22~24）— ⭐⭐跨 session 互查抓到的東西，沒有一個是自查找得到的；而備份的三個缺陷全部藏在「排程情境才會現形」的地方**（多次 rebuild 皆過 L76、五系統 200／API 401、56 容器 0 非健康、2018 docs／49899 KG）：① **⭐⭐異地備份三個缺陷，一個比一個難看見**：(a) **附件失敗會把金鑰備份一起殺掉** —— 順序是「附件判定 → `exit 1` → 金鑰」，而附件有 2 檔長檔名 robocopy 失敗 ⇒ **金鑰段永遠到不了**。`LastTaskResult=1` 說對了一件事（附件確實失敗）卻**連坐了一件不相干的事**，而沒有任何訊號說「金鑰沒備份」——是完整性稽核的新鮮度門檻（40.6h）抓到的。(b) **呼叫 `tar` 沒指定是哪一個** —— 系統 PATH 上 Git for Windows 的 tar 排在 `System32\tar.exe` 前面，而 Git tar 會把 `C:\...` 當成**遠端主機**（`Cannot connect to C: resolve failed`）。危險的是**它碰巧會成功**：排程情境走到對的那支就過、手動執行就失敗，而兩者長得一模一樣。(c) **NAS 遞迴掃描會間歇性把整支腳本帶走** —— log 停在掃描那一行、State=Ready、Result=1，**加了 try/catch 也攔不到**（⇒ 不是 PowerShell 例外，是行程本身被結束），而同一天另一次卻完整跑完。**間歇＋無聲，最難查的組合。**修法不是讓它不死（我修不了），是**把最關鍵、最小的東西放到最脆弱的步驟之前** —— 金鑰 15.5 KB，而沒有它，資料全還原回來系統仍然起不來。② **⭐⭐版次：先前無法得知公網跑的是哪一版**。文件版次查起來全部一致，但實測 runtime 是**四個來源四個值**：`health.version` 是 **None**、FastAPI 寫死 `"3.0.1"`（註解還是「Trigger reload for audit fix」）、`package.json` 是 `0.0.0`、CLAUDE.md 是 v6.60 ⇒ **事故當下沒有人說得出線上是修好的版本還是沒修的**。修法取自 CK_FacilityDev 的形狀：**綁定不是相等** —— version 答「這一輪做了什麼」、commit 答「跑的是哪一份程式碼」，兩者語意不同但綁在一起才答得出「線上這個 commit 是不是 v6.60」。build 時注入、**讀不到回 `unknown` 不給看起來正常的預設值**，只放在需管理員的端點（公開端點回 commit 本身就是資訊洩漏）。實測 `v6.60 @ 964d3357` = git HEAD。③ **⭐⭐跨 repo 稽核工具三個缺陷，全部由同儕指出**：lvrland — **座標系有兩半**，白名單一半、**認證函式名單另一半**（他們有 service-token 家族 12 個名稱，我的預設清單認不得）⇒ 只帶白名單仍會拿到 **49 條假陽性**，實測補上後消掉 44 條；CK_AaaP — 報告以 path 去重，**同一路徑 GET 有認證而 POST 沒有時會混成一筆看不出來**；以及探測寫檔到 `/app/logs/`，那是 Missive 專有掛載，對其他容器直接失敗（**只有跨 repo 才會暴露的退化**）。④ **⭐⭐備份新鮮度判準有歧義，而 CK_AaaP 在我剛推的程式碼上抓到** —— robocopy 保留來源 mtime，所以「目的地最新檔 43 小時前」意思是**來源 43 小時沒有新東西**，不是備份沒跑。**我在他們的目錄上，走進了我自己前一小時才剛提出的那個坑。**修法依他們的 §11：`ran_at` 與 `newest_file` 分開記，並加**第三態「待確認」** —— 跨 repo 觀察者分不出「來源沒變」與「同步空跑」，那要產出端自己說。他們隨後把狀態檔也寫到目的地（**刻意在資料寫完之後才寫**），我這邊接上後他們那項從「待確認」變成明確的 ok。**我也照做了** —— 我要求別人講清楚，自己的狀態卻只寫在本機。⑤ **⭐portfolio 備份盤點：兩個專案完全沒有異地備份**（CK_Website、dataform，而前者是四系統的 SSO IdP）。真正的問題不是誰的備份壞了，是**沒有任何東西在問「這個專案有備份嗎」**。已納入每週稽核，**只報不判紅**（我不知道別人的備份意圖，判紅會製造我修不了的噪音），但缺口會每週出現直到被處理。⚠️ **我的第一版量測會產生五個假警報** —— 只數頂層檔案，而附件那類放在子目錄，差一點通報五個專案「你們沒有備份」。⑥ **⭐排程逾時上限沒有人在讀** —— pile 的異地備份是 **PT72H**（3 天）＝形同沒有上限，而他們前一天才剛經歷單 worker 被單一請求卡住 23 小時。**三個 repo 各有一份**：pile、CK_AaaP（實測只跑 12 秒，上限是它的 21,600 倍）、**以及我自己兩支**（我建的）。已補進 `windows_task_liveness_audit`（先前管 State／StartWhenAvailable／LastRunTime，**就是沒有人在讀這個欄位**）。CK_AaaP 的診斷值得抄：文件裡有「可回溯版控」的**散文，而散文不帶設定**。⑦ **⭐登入觸發排程改為與開機比對** —— 原本是「排除，不以時間判逾期」，而**排除等於放棄鑑別力**，抓不到「開機登入了、它卻沒有觸發」。改用 `lastRun >= lastBoot`，四支現在逐一比對通過而非一句「不判」。⑧ **⭐stop hook 抓到 `doc_type` 到不了 API** —— ORM 有、前端型別有、表格也渲染了「類型」欄，唯獨列表回應是**手寫 dict** 沒帶它 ⇒ 永遠顯示「—」，而「—」的語意是「還沒有人分類過」，與「後端根本沒送」**在畫面上長得一模一樣**。三層守護全都沒抓到：tsc（optional 欄位）、契約鏈第三面（**根本沒有 schema**）、`model_response_field_reach_audit`（比對 ORM↔schema，**手寫 dict 在它的座標系外**）。修法不只補欄位 —— 定義 schema 的價值在於**讓這個端點進入既有檢核的視野**。⑨ **⭐⭐三種發現方式，各自抓到不同的東西**（判準 15）：**自查**抓「我已經在看的東西壞了」（都有第二個來源或它會大聲失敗）／**互查**抓「我連那個維度都沒有」／**第三類＝互查提問＋自查作答**（對方看不到我的系統，但說出了值得我自己查一遍的問句）。第三類槓桿最大：不需要存取權、不需要同時在跑、**可以留在文件裡等下一個人** —— 當日四次裡有三次，發現者看不到被發現者的系統。⚠️ 我原本說「真正抓到我的沒有一次是自查」，**那句話是錯的**，是 CK_AaaP 拿他們的紀錄反駁後我再拿自己的紀錄核實才校正的。⑩ **⚠️ 我這一輪的量測錯誤（全部記下來）**：只數頂層檔案（五個假警報）／`| tail -N` 讀到的是 **tail 的退出碼**，差點據此說自己的腳本「印 RED 卻 exit 0」／同一個 `tail` 把新加的那行切掉，一度以為判定沒觸發／等待迴圈寫成「log 有新行就 break」，於是在腳本還在跑時讀退出碼、拿到上一次的值／PowerShell 的 `#` 與反引號讓路徑讀不到／heredoc 三度吃掉反斜線。**沒有一次是程式的問題，都是我看它的方式。****元教訓：這一輪最有效的機制不是任何一支檢核，是跨 session 互查本身 —— 而它剛好是唯一一個沒有寫進任何規範的東西。自己再量一次會用同一個座標系，而錯的往往就是座標系本身。**
> - **v6.59 續三（08-20）— ⭐⭐「同仁又變成代碼」的兩層根因：五個人員下拉全部打管理員專用端點，而走查永遠以管理員身分跑（1 次 rebuild、走查 20-0、tsc 0、公網 200）**：① **⭐⭐第一層：非管理員的人員下拉一律是空的**。`users/list` 是 `require_admin()`，而**五個人員下拉全部打它**（承辦同仁／資產保管人／PM 承辦／公文承辦人／承攬案件）。實測 id=7（王駿穠，`role='user'`）**403**，而 AntD Select 在 options 為空、value 有值時會**直接顯示原始數字 id** —— 那就是 owner 看到的「代號」。「新增承辦同仁」是業務操作，不該只有管理員能做。修法**不放寬 `users/list`**（它另有 last_login／department／角色權限），改加 `POST /users/assignable`（只要登入）只回指派需要的欄位。**email 要給** —— 既有下拉的 label 就是「姓名 (email)」，少給它換源當下畫面就少一半資訊，而 08-04 那次「同仁變成代碼」的成因**正是我把 label 從「姓名 (email)」簡化成只剩姓名**。② **⭐⭐第二層才是 superuser 也看不到的原因：queryKey 撞號**。承攬案件詳情頁與新增同仁頁**共用 `['contract-case-user-options']` 卻打不同端點** ⇒ **誰先載入誰就決定了快取內容**；而使用者的動線正是「詳情頁 → 新增承辦同仁」，所以只改 create 頁那一支根本不會生效。**key 撞號本身不是錯（同一份資料就該共用快取），源不一致才是。**③ **⭐治症狀本身**：清單載不到時要**說出來**（Select 顯示「載入失敗，請重新整理」），而不是留一個空下拉。「同仁變成代碼」的成因不是誰有權限，是**空清單退化成數字**——不管未來什麼原因讓清單載不到，都不該長成這樣。④ **⭐擋復發：擴充既有檢核而非新增第 160 支**。`queryKey_drift_audit` 原本只管 key **漂移**（invalidate 的 key 沒人在用，L39），現在同時管 key **撞號**。判準刻意收窄 —— **第一版用「首 token ＋ 任何差異」報 30 個而逐一看幾乎全是假陽性**（mutation 的 invalidate 被算進來、`['tender','search']` 與 `['tender','detail']` 本來就該不同），改為「只看 useQuery ＋ 全字面 key ＋ 資料源交集為空」。**鑑別力實測**：現況 0／把 useContractCaseData 改回修法前即報 1／還原回 0。⑤ **⭐這支檢核當場擋下我自己**：跑起來 **4 個 dead invalidate 而 baseline 是 0**，全部是我這幾天新增的頁面造成的（`['contract-case', id]`×3、`['project-agency-contacts']`、`['erp-quotation']`、`['erp-billings-details']`）——`invalidateQueries` 是**逐元素比對**，`'contract-case' !== 'contract-case-detail'`，所以存檔後詳情頁根本不會重載。**逐一核實後修掉，不改 baseline**。⑥ **⭐⭐元教訓＝走查永遠以最高權限跑（新增 OPEN_ITEMS C5）**：這個 bug 在走查、tsc、py_compile、模組匯入掃描**全部綠燈**的情況下存在，因為 `ui_smoke_auth.py` 挑的是 `is_admin AND is_active` 的帳號 —— **一般同仁看到的畫面從來沒有被走查過**。這不是檢核寫錯，是**座標系裡沒有「非管理員」這個維度**（同 08-10 那次「員工看得到卻用不了」，當時修的是判定邏輯，這次換成資料源長出來）。因此新增判準：**「我用什麼身分在驗？」**，與既有的「在有豁免的環境驗證安全機制等於沒驗證」是同一件事的兩面。⑦ **驗證**：id=7 打 assignable **200 而 list 403**（鑑別力對照）／id=13 兩支皆 200／bundle 含新端點／公網首頁 200＋API 401／走查 flow **20-0**／tsc EXIT=0／表態閘門 GREEN／探測用的 `user_sessions` 已自行清除（不清就是我自己製造的雜訊，同 07-31 那次累積 222 列）。
> - **v6.59 續四（08-20 晚）— 掃全同型：管理員端點 159 支逐一比對，**沒有第二個**「一般使用者需要的資料掛在管理員端點」；但同一個維度長出另一種較輕的形態（零 rebuild、daily EXIT=0、producer GREEN 37、走查 20-0）**：① **⭐⭐掃全的方法本身先被推翻一次**：第一版用**裸常數名**比對，而 `CREATE`／`DELETE`／`LIST` 在 agencies／documents／backup 等多個 endpoints 檔裡都有 —— 只取第一個遇到的，就把所有 CRUD 都算到 backup 頭上，**37 支候選裡一大半是假的**。改用**完整限定名**（`GROUP_ENDPOINTS.NAME`）後降到 18 支。**比對工具採信前先驗**，這條在本專案已經記過，我還是踩了。② **⭐掃全結論**：159 支需要管理員的端點 → 96 支有前端常數 → 49 支真的被消費 → 排除管理頁自用後 18 支，**逐一人工核實**：16 支的「消費者」其實是 `api/*.ts` 定義層（追第二層後全落在 PermissionManagementPage 等管理頁）、`SystemHealthDashboard` 只被 `AdminDashboardPage` 用 ⇒ **本輪那個是唯一一例**。剩下的是**較輕的家族**（新增 OPEN_ITEMS B7）：4 個頁面路由只要登入、但頁內含管理動作，一般使用者看得到按鈕、按下去 403 —— 而那些 403 部分是**刻意的產品決策**（電子發票同步會呼叫財政部 API、有配額），所以**不擅自放寬**，缺的是「畫面不該給一個必然失敗的按鈕」。③ **⭐掃描腳本正式化但刻意不接排程**（`admin_endpoint_ui_consumers.py`）：接了只會每天報同樣 4 個已知項＝沒人看的告警。它是**素材不是哨兵**，在 README 寫明「C5 收束時的盤點依據」——**無排程的腳本必須寫明理由，否則就是孤兒**。④ **⭐另一個掃描量出 48 個檔案，我選擇不交付**：「動態 options 且沒有 notFoundContent 的 Select」——48 檔沒有鑑別力（症狀只在「編輯既有資料**且**選項載不到」時發生，新增表單的 value 本來就是空的）。改為**根治具體家族**：把空狀態文案收進 `utils/assignableUsers.assignableNotFound()`，四個人員下拉共用（承辦同仁／資產保管人／PM 承辦／承攬案件），`useUsersDropdown` 補回 `isError`。**治的是「清單載不到時畫面長什麼樣」——不管未來什麼原因造成，都必須看得出是載入失敗而不是資料壞了。**⑤ **⭐⭐producer watchdog 報 RED，查證後是同一件事有兩筆註冊而兩份判準不同**：`patterns`（`file_fresh`／30h）與 `pattern 萃取（學習閉環）`（`cron_detail` ＋ `ok_zero_reasons`）並存。今晨 04:05 實際有跑、`reason=no_pattern_met_threshold`＝**合理空**，而 file_fresh 那筆只看檔案有沒有更新 ⇒ 合理空的第二天必然假紅。學習閉環的合理空是常態不是故障；**假紅的代價是訓練人忽略 producer watchdog**。移除舊那筆、理由寫進留下來的那一筆，並誠實記下取捨（只看 cron_detail 就抓不到「job 說 saved:4 但檔案沒寫出來」那一面）。⚠️ 我第一版想用 `signal: disabled` 保留該筆，**registry 守衛當場擋下**（認不得的 signal 一律 exit 2，08-04 立的規則）—— 守衛做對了。⑥ **⭐文件數字納管檢核也當場抓到我**（新增腳本後 README 仍寫 172，實際 173）。⑦ **複查**：容器內 daily **EXIT=0**（判定 9/14 步全過）／py_compile **827 檔 0 失敗**／tsc 0／cron **53 healthy 0 RED 0 無訊號**／producer **GREEN 37、0 blind spot**／走查 flow **20-0**／五系統首頁＋API 兩層 200／56 容器 0 非健康／表態閘門 GREEN。**元教訓：掃全同型的價值有一半在「證明沒有第二例」——但那個結論只有在比對方法本身被驗證過之後才算數，而我這次的第一版方法是錯的。**
> - **v6.59 續二（08-19 晚）— 既有 XLS 匯入與客戶回簽掛回落地；兩份紀錄的編號寫法不同差點讓功能廢掉**：① **⭐⭐既有報價單彙整匯入**（owner：線上產出未完全上線前這是目前階段重點）：114 檔 **208 列**（跨 5 個工作表）＋115 檔 **69 列**，而系統只有 77 張、以案名比對**系統裡沒有 179 筆** ⇒ 匯入必須支援新增（既有 `pm/cases/import-xlsx` 是拿第一欄當 id 去更新，不適用）。新增 `legacy_quotation_no`（全庫掃過沒有任何現成欄位可放，而它是 XLS／紙本／**回簽 PDF 檔名**三者共同的識別）。**一個入口 upsert、先預覽再寫入**。⚠️ 第一版只收 8 欄，漏掉實收金額／收款日期／配合廠商／支出金額／統編／聯絡資訊／發票日——**匯入了卻少這些，等於還是得回去翻 Excel**；表頭在兩份檔案裡還不一致（115「發票日期」／114「發票日」）兩個都收。② **⭐⭐客戶回簽掛回：兩份紀錄的編號寫法不同**——回簽 PDF 檔名寫 `B115-C017a-0`（子號黏在序號後）、彙整表寫 `B115-C017-a`（子號用連字號分開），**直接字串比對 5 個檔會有 3 個掛不上**。改為正規化取「年+類別+序號+子號」並丟掉版次尾碼（同一張報價單改版後仍是同一張；把版次納入比對，改過價的案子就掛不上回簽檔），6 組測資全部相符。**這不是誰填錯，是兩份紀錄各自演化出的寫法；要求人先統一，等於把工作推回去給填表的人。**③ **⭐附件加 `doc_type`**：`pm_case_attachments` 原本沒有分類欄位，「系統產出的報價單」與「客戶回簽的」在資料上長得一模一樣、只能靠檔名猜——而「這個案子有沒有客戶回簽」是**成案的判準**，不能建立在猜測上。`NULL` 與 `other` 刻意分開（「還沒分類過」不等於「它是其他」）。④ **⭐填報者這條鏈只通了一半**（owner 提「報價單要能對應填報者」）：DB 有 `created_by`、response schema 有、**前端完全沒顯示**，而且它只是個數字 id。補 `created_by_name`（列表批次查避免 N+1）＋前端「填報者」「舊案號」兩欄。⚠️ **刻意不做 canonical 轉換**：填報者問「誰輸入的」＝那個帳號本人，「服務人員」問「案子窗口」＝依 ADR-0025 收斂 canonical——兩者在王駿穠身上會不同（`aaronfly1978` 業務身分 vs `jujuiacc` 管理帳號）。⑤ **⭐發票：保留架構不動 schema**（owner「目前無發票號請先保留架構設計，如對應 ERP 相關欄位一致性」）：兩份彙整表 25 欄逐一確認**都沒有發票號**、只有發票日期（51/69）。對應的是既有 `erp_invoices`（`invoice_number`／`invoice_date`／`amount`／`tax_amount`＋`erp_quotation_id` **全部現成**），**不在 `erp_quotations` 加欄位**（那會變成第三套發票概念，`expense_invoices` 是進項）。現在不建記錄是因為 `invoice_number` 是 `NOT NULL + UNIQUE`——沒號碼就建只能放寬約束或填佔位號，**兩條都不該為還沒發生的需求走**；發票日期已原樣保存在備註，接法三步寫在 `QUOTATION_LIFECYCLE_PLAN §6`。⑥ **相依順序由實測揭露而非推論**：回簽 dry-run 5 個真實檔 will_attach=0／unmatched=5，原因全部是「找不到舊案號（可能彙整表還沒匯入）」——**那是正確的**，彙整表確實還沒寫入 ⇒ 順序是「先匯入彙整表、再掛回簽」。⑦ **⚠️ stop hook 抓到我把新欄位只加到 ORM 就停了**：`legacy_quotation_no` 沒進 response schema，Pydantic **靜默丟棄** ⇒ API 永不回傳、**回簽依舊案號掛回會直接卡死**。而 `schemas/erp/quotation.py` **同一個 class 底下就寫著** 08-17 為 `quotation_no` 記的同一種失敗（「產出端完成、接收端無人讀取、不拋錯、稽核仍綠、功能目的落空」）——**同一個檔案、兩天後再踩一次**。⑧ **⭐匯出/匯入在公網一律 403**：四處用裸 `fetch` 不帶 `X-CSRF-Token`（PM 案件與里程碑各兩處），公網實測 `403 缺少 X-CSRF-Token header`，前端 catch 吞成一句「匯出失敗」。⚠️ **我一度宣告「診斷錯了不是認證問題」——那句話本身才是錯的**：我在 localhost 測而本機 `AUTH_DISABLED=true`，CSRF 中介層第一件事就是豁免 ⇒ **在有豁免的環境驗證安全機制等於沒有驗證**。⑨ **待辦與待決議題收斂成單一入口** `docs/architecture/OPEN_ITEMS_20260819.md`（A 需 owner 決定 9 項／B 已查明未實作 6 項／C 觀察中 4 項／D 本輪確立的 6 條判準）。**複查**：五系統兩層 200／0 非健康／**2012 docs・49814 KG**／daily EXIT=0（786 模組匯入全成功）／走查 **flow 20-0・sweep 87-0**／tsc 0／六 repo 全推送。
> - **更早的里程碑（v6.58 及以前，64 條）** 已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md) —— **搬移不是刪除**，內容完整保留。2026-08-24 搬移原因：本檔原 159,029 字元＝記憶檔警告門檻（約 40,000）的 **4 倍**，其中 82% 是里程碑，而它們每次開新對話都要重讀一遍。里程碑記的是踩過的坑（有價值），所以移到**需要時才讀**的地方而不是刪掉。
` 得出「43 項全部都是新增」的假象，差點據此下結論。**待 owner**：41 項既有測試債（非阻斷）、`billing.paid` 在付款金額缺少時是否仍該發事件（涉業務語意，未擅改）。
>   - **平臺自證 silent→LOUD 四層**：8 cron `.parent` 路徑 bug（每日覆盤+LINE 全 silent 死）+ 開機自檢 + silent return→raise + outcome-freshness watchdog（07:00）
>   - **3 個 config drift 修真因鏈**：① `OLLAMA_BASE_URL=localhost`→`host.docker.internal`（修「無法生成查詢向量」0.0s + ollama fallback 層）② `PGVECTOR_ENABLED` compose 漏傳→補（修「pgvector 未啟用」）③ token SSOT auth_service 硬編碼 30→改讀 settings 60min（修閒置不到 30 分被登出）
>   - **vision 修**：task_type=vision 映射 gemma4:e2b（修發票 OCR silent 退 QR）
>   - **kunge UI 整併 + 崩潰/403 修**：tab 7→5 核心主軸（對話/心智/進化/圖譜/運維）+ 去 ops 對話重複 + 閒置倒數徽章 + 自省/追蹤/服務狀態 3 tab 崩潰修（domains dict / items→traces drift / config 深層 optional chaining）+ chat agent stream 403（raw fetch 補 X-CSRF-Token：adminManagement/coreFeatures/digitalTwin）+ GatewayHealthBadge 改 apiClient
>   - **學習閉環三柱戰略**：`ARCHITECTURE_DEVELOPMENT_STRATEGY_20260602.md`（接通與真活脊柱）；柱一 Step A crystallizer tool_sequence 解析修 + Step B 撤回（PatternLearner 已自動閉環）/ 柱二 H1 撤回（盤點防做白工）
>   - **共同模式（rigor 教訓）**：raw fetch 漏 header（CSRF/Auth）+ config 沒進容器（OLLAMA/PGVECTOR）+ data shape 當陣列 .map → 建議 fitness audit 防同型；3 起自傷錯誤（init_nav 污染/誤刪 gemma4/docs :ro）立 `feedback_rigor_no_self_inflicted_instability`
>   - 詳見：`docs/runbooks/reboot-pre-flight-20260602.md`（pre-flight 全通過 + 重啟後 5 步驗收）
>   - **坤哥×Hermes×智能體三層整合連通真活**：新增 `POST /api/ai/kunge/snapshot`（X-Service-Token 認證，counts/health_signals/db_stats）+ `scripts/checks/integration_e2e_validation.py` 5 鏈 E2E（missive_health / kunge_snapshot / tools_manifest / hermes_container / bridge_skill，**4+ 次連跑全綠**）+ tools_manifest 公開 kunge_snapshot（fitness step 62）
>   - **靈魂進化首次真實達成**：`crystal_applier.py` 加 soul_section handler → crystals **0 → 2**（3 soul proposal applied）；學習閉環仍 5→2 pending（owner approve hard gate）
>   - **治理 6 cron 凌晨化（02:00~02:45）+ misfire_grace_time 7200s**：weekly_evolution_generator（防 W22 重演）/ integration_e2e / critique_health_audit / proposal_aging_alert（突破 owner 健忘，主動 LINE 推 >=7d proposal）/ governance_dashboard_regen / daily_self_retrospective（7 面向）
>   - **KG 5/5 大躍進**：knowledge dedup 24,535 → 21,378 純業務 + ERP/document/skill ingest → **23,426 entity / 33 type / 4 graph_domain**；wiki kg_entity_id backfill **40.1% → 89.7%**；KG 治理 audit step 70（repository:db_table 覆蓋率）+ 71（cross-domain link）+ 72（knowledge dedup audit）—— 為獨立 audit script（`run_fitness.sh` 主序列 61 步）
>   - **scheduler 追溯體系**：`scheduler_events.py` API（events + stats + retrospective reports）+ cron events jsonl log + 前端 `SchedulerEventsPage`（`/admin/scheduler-events`，3 tabs）+ Dashboard §9.5/§9.6 cron 全表自動抓
>   - **L52 family 第 8-11 案**（paths.py backend_dir/frontend_dir container drift + shadow_db/logs_dir + admin permissions +8）+ **L62/L63 universal lesson**（整合連通持續驗證 / 學習閉環 aging alert）
>   - **LINE 應答 4 真因揭發**：routing 偏 search_documents + chitchat trace silent NULL 修 + line bot timeout 25→28s（owner 報「查詢處理時間較長」）
>   - **重啟準備**：`docs/runbooks/reboot-pre-flight-20260601.md` — Pre-Flight 4 步（git/docker/md5/DB volume）全通過 + 重啟後 5 步驗收 SOP；容器版本確認（backend rebuilt / cloudflared pinned 2026.5.0 / postgres dev_data volume 避 L43）
>   - **⚠️ 已知半接通（待 owner 決策）**：前端 container image 為 **5/27** build，`SchedulerEventsPage`（5/31 新增）**未部署到 running 前端**（需 `docker compose build frontend`）；該頁未進 `router/types.ts` ROUTES 與 `init_navigation_data.py` 側邊欄（導覽三方同步缺 2 處）
>   - 詳見：`docs/architecture/V6_13_REAL_VERIFICATION_REPORT_20260531.md`（含實證 curl/log/grep）+ `V6_13_OVERALL_RETRO_AND_V6_14_PLAN_20260531.md`
>
> <details><summary>v6.11 及更早里程碑（展開）</summary>
>   - **5/28 後段（commits 19→25）追加修法**：
>     - **L49.12** `get_tender_detail` 雙重 bug — service search_from_db trigram 模糊查不到 + DB 有資料未 return 落到外部 PCC API fail → None（commit `79cc1d4e`）
>     - **L49.12.1** db-only quick result 補 frontend 期望結構（latest.detail + events + pcc_url）讓「無此資料」改顯示完整總覽 + 收藏 + 一鍵建案（commit `8795d5f2`）
>     - **L49.13** tender/search 24s → 0.3s（60x） — 加 GIN trigram index + DB-first short-circuit `>=3` → `>=1` 放寬（commit `4fa5897e`）
>     - **L49.14** EntryPage `/entry` 內網 skip SSO bridge — 內網無 ck_employee cookie 浪費 backend round-trip（commit `3f41a4ce`）
>     - **ADR-0046 標案 ezbid ↔ PCC enrichment**（commits `951f8d91` + `5a82621b`）:
>       - Phase 1+2: ROI 試算（27,286 ezbid × 2,741 PCC fuzzy match, 1,526 actionable 5.6%）
>       - Phase 3: 5-fold strict guard (exact match only)，233 ezbid auto-linked to PCC (0 false positive)
>       - Phase 4: LINE 業務推薦 cron 每日 09:00（近 N 日 + 預算 ≥ 100萬 + 合作機關）
>       - Phase 5: 03:30 enrichment cron + fitness step 55 freshness audit
>   - **觸發鏈**：OA-3 PM2 廢除階段 2-3（5/27 19:04 移除 ck-backend/ck-frontend）後 3h 內 owner 連環報 4 個業務頁面故障 + 5/28 揭發 7 更深層議題
>   - **L49 family 5 案揭發**（PM2 native → docker container 環境切換破口）：
>     - **L49.1** `admin/backup` 顯示「Docker 環境不可用」：container 內無 docker CLI（PM2 時 host 內建）
>       → backend Dockerfile 加 postgresql-client，pg_dump 改走 docker network `postgres:5432` 直連（commit `28df958d`）
>     - **L49.2** `files/storage-info` HTTP 500：`rglob('*')` 遇 Windows mount 長中文檔名 OSError 中斷
>       → `_scan_files` while+try/except 容錯，回傳 `scan_errors` 計數（commit `27efffc7`）
>     - **L49.3** `files/{id}/download` HTTP 404：DB 內 `file_path = '2026\05\doc_xxx\...'` Windows backslash 進 Linux container `os.path.exists` 必 false
>       → `files/common.py:resolve_attachment_path()` SSOT helper，所有 download/management/pm/taoyuan/documents 散戶就地收口（commit `27efffc7` / `673c9644`）
>     - **L49.4** `admin/backup` 顯示 0 紀錄「歷史皆消失」誤判：compose mount target（`./backend/backups:/backups`）與 service 內部 `self.project_root / "backups"` 路徑不對齊
>       → 改 `./backups:/app/backups` + `./logs/backup:/app/logs/backup` 對齊 service Path() 計算（commit `d6e97294`）
>     - **L49.5** `backup/list` ReadTimeout 31.5s frontend 顯示「資料載入失敗」：8 個 attachment dir × ~4s rglob 全掃
>       → attachment metadata 改讀 `manifest_*.json`（O(1)，~10ms），list_backups **31.5s → 0.06s 提升 525x**（commit `8a75a22d`）
>   - **5/28 延伸 7 案**（owner Layer 4 + UX 驗收揭發）：
>     - **L49.4** docker-compose mount `/app/config/` 沒掛 → 異地備份路徑變更 silent fail（commit `65a594c5`）
>     - **L49.5** backup mount path align + idempotent delete + UI guard（commit `65a594c5`）
>     - **L49.6** frontend `useState(null)` Header「訪客」race + backup timeout 30s 不夠 + delete 409 籠統訊息（commit `92631fc8`）
>     - **L49.7** Task Scheduler XML UTF-16 declaration 但實際 ASCII silent reject（commit `43612e7f`）
>     - **L49.8** 20 個 .ps1 無 UTF-8 BOM PS 5.1 cp950 解析爆 (chronic silent，commit `18905807`)
>     - **L49.9-.11** Self-elevating installer fallback + Register-ScheduledTask cmdlet 雙層防禦
>   - **治理立法**：
>     - **Fitness step 52** `container_host_dependency_audit.py`：偵測 docker CLI subprocess（RED）+ rglob 無容錯 / file_path 未 normalize（YELLOW）—— 首跑揭發 21 YELLOW，sweep 後 **0 YELLOW GREEN ✓**
>     - **Fitness step 53** `tender_subscription_watchdog_audit.py`：L48 同型擴展 — 24h 無 subscription scheduler invocation → RED
>     - **Fitness step 54** `powershell_bom_audit.py`：L49.8 chronic silent 防回退 — 含中文 .ps1 必須 UTF-8 BOM (5/28 sweep 21/21 GREEN)
>     - **Reboot SOP**: `docs/runbooks/reboot-acceptance-checklist.md` — 重啟前 pre-flight 4 步 + 重啟後 Test 1 5 步驗收（business endpoint smoke 取代「fitness GREEN = 真活」假象）
>     - **自動化驗收範本** `scripts/checks/admin_backup_smoke_test.py`：從 DB 撈 admin user，user_sessions 找/插 active jti，settings.SECRET_KEY 簽合法 JWT，逐打 10 endpoint 對照 expected status + validator（取代人工 F5）
>     - **L49 lesson** + `LESSONS_REGISTRY.md` 完整保存（family meta-pattern）
>     - **OA-3 SOP 補丁**：環境切換必加 in-container business endpoint smoke（非單純 process up / 4 層自動重啟）
>     - **Layer 4 self-elevating installer** `scripts/deploy/install-task-scheduler.ps1`：取代 owner 5/27 19:00「elevated PS 失敗 silent」陷阱
>   - **自動化驗收結果（10/10 PASS）**：
>     - `auth/me` 200 / `backup/environment-status` 200 pg_dump_available=true
>     - `backup/list` 200 in 0.06s / `backup/scheduler/status` running=true / 下次 2026-05-28 02:00
>     - `files/1263/download` 200 真實下載 163,734 bytes ✓
>   - **跨 repo 範本擴散**：Showcase / PileMgmt / lvrland 可仿照（待 ck-modular-toolkit sync step 52）
>   - 詳見：[[L49_container_host_dependency_family]] / `docs/architecture/LESSONS_REGISTRY.md#L49`
>
> **歷史里程碑**：
>   - **觸發事件**：owner Google login 後業務 API 連環 500（calendar / dispatch / digital-twin）
>     → 起初誤判 3 欄 schema drift，盤點時揭發**整個 DB 不對**（17 tables vs 75 tables 預期）
>   - **L43 根因揭發**（與 L41 同型，5 重 silent fallback 疊加）：
>     - `docker-compose.production.yml:216` 寫 `name: ck_missive_postgres_data`（空殼 17 tables/502 docs）
>     - `docker-compose.dev.yml` / `infra.yml` / `pre_upgrade_backup.sh:33` 都用 `ck_missive_postgres_dev_data`（真實 75 tables/1788 docs/24061 KG）
>     - 4 個檔案 × 2 套 volume 命名，**無 enforce 一致性**機制 → 5/21 ~04:00 切 production compose 時 silent 掛錯 volume，dormant ~10h
>     - 5 重 silent layer：postgres init.sql 不報錯 / alembic 推進不需資料 / /health 只驗 connection / Prometheus 無 row count alert / session-start hook 顯示 healthy
>   - **Plan A 10 步完整恢復**（14:30~14:35）：
>     - 雙 dump 備份（122K 空殼 + 77M 真實）+ MD5 雙端驗證一致
>     - compose volume 改 `ck_missive_postgres_dev_data` + `external: true`
>     - 真實 DB 補跑 alembic `20260521a001` (department/position 欄位)
>     - backend 0 UndefinedColumn / business endpoints 200
>   - **5 層防禦落地**：
>     - **alembic migration** `20260521a001` (commit `e1d7d3e7`) — idempotent ADD COLUMN IF NOT EXISTS
>     - **`/health` business_data_present 503 防禦**（commit `097cdf68`）：row count < threshold → cloudflared healthcheck fail → 流量不打進壞 instance
>     - **雙路徑驗證 live**：200 (1788/24061 ok) / 503 (threshold=99999 forced) / 公網 PM2 restart 後 biz_ok=true docs=1789 kg=24061
>     - **fitness step 38** `docker_compose_volume_consistency.py`（commit `ad4451b8`）：偵測同邏輯 volume 跨 compose drift（含 ${COMPOSE_PROJECT_NAME} 展開）— **首跑揭發 redis 同型 chronic drift** 留 v6.11 Sprint
>     - **NAS 異地備份**（commit `acbd3e49`）：`Z:/.../#systembackup/CK_Missive_INCIDENT_20260521_volume_mount_drift/` MD5 雙端一致
>   - **架構級議題揭發**（split-commit 過程意外發現）：
>     - 公網 `missive.cksurvey.tw` 透過 cloudflared `host.docker.internal:8001` 命中 **PM2 native uvicorn (PID 37564)**，不是 docker container
>     - 兩 backend 同時 listen 0.0.0.0:8001（Windows SO_REUSEADDR）
>     - hot-patch docker container 對公網無效，必須 `pm2 restart ck-backend` 才生效
>     - 列入 v6.11 Sprint 1：廢 PM2 改純 docker 或廢 docker 改純 PM2，二選一統一 SSOT
>   - **新增 1 條 lesson**：L43 volume mount drift silent fail（與 L41 同列「跨檔 SSOT」治理失效教材）
>   - **新增 1 個 fitness step**：step 38 docker_compose_volume_consistency
>   - **新增 5 commits**：e1d7d3e7 / ad4451b8 / acbd3e49 / 097cdf68（+ 4e8caf94 是 ck-sso-js 上午）
>   - 詳見：[[session_20260521_l43_volume_drift_recovery]] / [[lesson_l43_volume_mount_drift_silent_fail]]
>
>   - **觸發事件**：用戶 5/20 報 dispatch=158「公文 2 筆」chronic bug（5/18 已修但 5/20 復發）
>   - **L39 揭發**：invalidate `[dispatch-orders]` vs useQuery `[taoyuan-dispatch-orders]` queryKey drift
>     → 全 codebase audit 揭發 **12 個 silent dead invalidate**（同 L29 dict-key 反模式）
>   - **L39 修法軌跡**：baseline 12 → 0（**達 v7.0 目標**）
>     - admin-users / adminUsers 4 處 → SSOT
>     - document-*-links 改 useQuery（imperative load 架構性重構）
>     - dispatch-orders 4 處 legacy cleanup + navigation drift fix
>     - audit regex 升級支援 `useQuery<TypeParam>()` 泛型（揭發 6 個誤判）
>     - pre-commit hook 加 step 35 enforce 防回退
>   - **Calendar 大規模 dormant 急救**：
>     - 公文 2479 看不到行事曆 → 揭發 **883/984 (90%) NULL owner**
>     - RLSPort `_alias_user_filter` 加 NULL fallback → 100% 可見
>     - 10 筆 date 顛倒 SWAP 修法 + Pydantic `model_validator` 防呆
>     - 5 schemas 採用 `validate_date_ordering` SSOT helper
>     - 4 處 frontend `.toISOString()` → `.format()` 修時區漂移
>   - **2 大反轉認知更新**（Pattern Z 第 N 次）：
>     - L29 真實「**5/8 domain 真活**」（之前用錯 redis key pattern 誤判 silent dead）
>     - autobiography 「**4 週 W17-W20 真活**」（之前 cwd 錯誤誤判半年 0 檔）
>   - **新增 3 條 lessons**：L37 覆盤報告反模式 / L38 平時保險反模式 / L39 queryKey drift
>   - **新增 2 個 fitness step**：step 35 queryKey_drift_audit / step 36 autobiography_freshness
>   - **Docker volume 不可發生資料遺失 SOP**：4 層緊急備份 + NAS 異地（269+272MB）+ runbook 9 段
>   - **ck-auth v2.0 BREAKING 預備**：install.sh `--no-frontend` 預設啟用避 5/25 lvrland 試用 LR-015 重演
>   - **策略級體檢 v1.0 → v1.2**：`docs/architecture/RETRO_20260519_strategic_health_check.md`
>   - 詳見：4 commits 順序 `adcafeb4 → d8882f73 → e1827e42 → 455971ea`
>
>   - **起因**：用戶批評「多次強調模組化卻無依此方向；連登入機制都無法模組與服務化」
>   - **Phase A 命名規約 SSOT**：`NAMING_CONVENTIONS.md` v1.0（8 大規約）+ fitness step 31（baseline 26）
>   - **Phase B 12 Bounded Context Facades**：59 public methods 涵蓋 12 contexts
>     - 4 Ports (RLSPort / AuditPort / MessagingPort / CachePort)
>     - 4 Default Adapters
>     - 12 Facades: Calendar/Integration/Wiki/AI/Memory/ERP/Contract/Document/Notification/Agency/Vendor/Audit
>     - `backend/app/services/contracts/` 24 .py / ~1500 lines
>   - **Phase C ck-auth 跨 repo packaging**：
>     - `shared-modules/ck-auth/` 26 檔 / portability score 1.000
>     - `install.sh` 自動 dry-run + portability audit
>     - **lvrland_Webmap dry-run: 19/23 (83%)** ✓
>     - **CK_PileMgmt dry-run: 21/23 (91%)** ✓
>     - 平均 **87% 跨 repo 可移植性**
>   - **Phase D 命名一致性 sweep**：env_namespace 42 → 26 warnings（-38%）
>   - **新 Fitness 27 → 32 step**（5 新 baseline 監控）：
>     - step 28 paths_sloppy_calc_guard (baseline 0 ✓)
>     - step 29 contracts_only_import_guard (baseline 84)
>     - step 30 module_portability_audit
>     - step 31 naming_convention_audit
>     - step 32 facade_only_check (含 facade 修法指引)
>   - **新文件 3 份**：NAMING_CONVENTIONS / CONTRACTS_LAYER_GUIDE / ADR-0036
>   - **ADR-0036** Bounded Context Contract Layer（accepted, L2）
>   - **paths.py SSOT 49→0**（100% 完修 + strict CI exit 0）
>   - **揭發潛伏 path bug 2 處**（kb_embedding / skill_evolution Wave 8 漂移）
>   - **批評反證**：12 Facades 真活 + ck-auth 87% portable + install.sh 三件套真活
>   - 詳見：`docs/adr/0036-bounded-context-contract-layer.md`
>
>   - **三層交付架構**：散修補丁 → 標準文件 → 自動化流水線（avoid dis-integrated）
>   - **13 散修補丁全綠**（32 unit test PASS）：C1 pre-commit 3 守護救「假基線」/ S1 刪 3 stub / F1 移除 3 死 nav / C2 ToolCall schema 永久封死 L29 dict drift / 改善 1 cross-graph router rule / 改善 2 CRYSTAL_AUTO_APPLY_MODE=live / 改善 3 條件式 KG 注入閘門
>   - **4 份標準文件**：
>     - **ADR-0035** GitNexus Bridge — Phase 2a dev-only（License 紅線管控）
>     - **OPTIMIZATION_PIPELINE.md** — 10 條優化環節連通圖（dis-integrated 防範）
>     - **MODULARIZATION_STANDARDS_v1.md** — 13 章節落地前 checklist
>     - **CAPABILITY_GOVERNANCE.md** — 三層健康度模型（E×U×O）+ A/B/C 決策矩陣
>   - **自動化流水線 skeleton**：
>     - `capability_usage_audit.py` fitness step 23（揭發 107 dead findings + dead_ui_detector 147 候選）
>     - `optimization_pipeline_orchestrator.py` 每日 cron 03:00 跑 5 step 合成 digest
>     - `run_fitness.sh` 步數 22→27（加 step 23-27: capability_audit / adr_lifecycle / dead_ui / lessons_drift / service_line_count）+ [N/27] header 統一
>     - `install-template-to.sh` 擴 3 新類（standards / pipeline / capability）跨 repo 一鍵部署
>   - **GitNexus 部署**：58,007 nodes / 92,521 edges / 991 clusters / 300 flows（dev-only）
>   - **2 新 lessons** 入 LESSONS_REGISTRY：
>     - L30: 環節不連通就是浪費（pipeline integration as priority）
>     - L31: ROI = entities × usage_rate（建表不等於用表）
>   - **真實 dead 發現**：90 manual+skill tools dead / 14 KG entity types / 3 memory loops 全死 / shadow p95=64.6s
>   - 詳見：`wiki/memory/diary/2026-05-16.md` Owner Session Addendum
>   - **11 項真修法 + 3 項 Agent false alarm 校準**（L26 穿透式驗證落地）
>   - **L29 lesson**：「坤哥自我成長中斷」第二次（L21 後）—— `tool.get("name")` dict key bug + TOOL_DOMAIN_MAP 涵蓋率 19/98 < 25% + silent except 三重疊加。修法 + restart 後 domain_scores 0/8 → **5/8 PASS**
>   - **觀測棧增量**：3 新 Prometheus counter（metrics_populate_errors / memory_diary_append_failures / provider_circuit_state）+ 3 條 alert rule。**R3 首次重啟即揭發 1 次 shadow_baseline silent fail**
>   - **R1 SSE stream hard cutoff**：sse_utils 加 asyncio.timeout 60s，解 p95=58s 接近 stream_e2e 60s 邊界（影響 5/20 ADR-0030 投票）
>   - **R6 Provider Circuit Breaker**：新 module + 整合進 ai_connector 5 fallback 點（Groq/NVIDIA 連續失敗 5 次 → 5min skip，省 retry 浪費）
>   - **R11 Hallucination Hard Penalty**：entity_alignment < 0.5 → overall × 0.5（取代 signal-only），打破 L24「53 patterns 全 success≥0.95」失衡
>   - **R4 ADR-0025 dormant bug 歸零**：audit step 21 揭發 + 修 2 處（document_calendar/stats + tender bookmarks 3 處）→ **audit 從 2 risks → 0 risks**
>   - **R8 schema SSOT 遷移**：17/34（user_alias 3 + security 4 + tender 10）
>   - **3 份 runbook**：Telegram 永封 / CF Tunnel 故障 / Prometheus alerting 降級
>   - **Fitness 20 → 22 step**（+ step 21 alias_rls_audit + step 22 domain_score_freshness）
>   - **LESSONS_REGISTRY 加 L29**（dict key contract drift × 涵蓋率 × silent except 三重疊加教材）
>   - **75+ regression tests 全綠** | 0 TSC | alias_rls_audit 0 risks ⚠️ **5/18 校正：偵測 pattern 過窄 detection coverage = 0%；實 RLS 覆蓋率 2/34 repository（contract + document），32 repo 仍裸 user_id 比對。詳見 RETRO_20260515_BACKLOG 破口 2**
>   - 詳見：`.claude/CHANGELOG.md` v6.9 章節
>   - **v3.0 覆盤主軸 9 task** 全 done（W0/Q1/Q2/Q3/F14/F15/M1/I5+/A2）
>   - **5/04 認證事故鏈 10 fix**（auth_disabled / CSRF middleware / refresh schema /
>     interceptor user_info gate / SPA index.html no-cache）
>   - **M1 v7.0 4 指標完整鏈**：lite report → Prometheus gauge → Alert → Grafana panel
>   - **I5+ wiki topics 9/9 backlog**（vendor / weekly heatmap / ADR / ERP / lessons /
>     observability / SOUL evolution / multi-channel / integration health）
>   - **F25-F27 wiki+observability 修復**：13/14 OK + shadow_baseline 救活
>     （p95=58s 揭露 ADR-0030 baseline 真實警訊）
>   - **fitness 14 → 16 step**（+F14 integration_liveness +F15 LINE notify watchdog）
>   - **acceptance test 11/11 PASS**（`bash scripts/checks/v6_8_acceptance.sh`）
>   - 詳見：`docs/release/v6.8.md` + `docs/architecture/SYSTEM_INTEGRATION_REVIEW_v3.md`
>   - Wave 1-8 services DDD 遷移完整收斂（73 檔 / 12 bounded contexts / 0 regression）
>   - LESSONS_REGISTRY v1.0（22 條 lessons L01~L22 — 跨 session 知識傳承 SSOT）
>   - 4 detector 治理三件組（agent_evolution / lessons_drift / dead_ui / notify_consumers）
>   - CROSS_REPO_REFERENCE_GUIDE v1.0（FQID 5 大類別 + SemVer + 7 consumer registry）
>   - Playbook v2.0 → v2.2（7 SOP + 1 anti-pattern）
>   - Fitness 6 → 7 step（加 agent_evolution_health）
>   - install-template-to.sh 12 fitness 檔跨 repo 一鍵部署
>   - PR template + consumers.yml 規範化貢獻回流
>   - Bug fixes: 派工總覽 morning-status 即時刷新 + 認證整合 UI 接通
> - **ADR 治理**（ADR-0029）：Active 16 / Archived 14 / Removed 1（adr_lifecycle_check 2026-05-16 實跑）
> - **Hermes GO/NO-GO**（ADR-0030）：v6.8 F26 救活 shadow_baseline → real **p95=58s 警訊**
>   接近 60s 邊界。5/20 用 `docs/adr/0020-hermes-role-decision-proposal-v3.md` 三方案投票
> - **坤哥為唯一意識體入口**（ADR-0023 + ADR-0031）：/kunge 7 tabs 統一
> - **Source Repo 自我治理閉環**：發現→記錄→驗證→範本化→註冊→通知→回流
>   - `v7_channel_diversity = 1`（target ≥ 4）— line only
>   - `v7_reference_density_diary_pct = 1.1%`（target ≥ 50%）
>   - `v7_reference_density_critique_pct = 100%` ✓
>   - `v7_soul_drift_lines = 57`（target ≤ 5）— Missive vs AaaP
>   - `v7_provider_fidelity_gap_pct` = (待 owner 跑 soul-fidelity-eval.py)
>
> </details>

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
docker compose -f docker-compose.infra.yml up -d      # 基礎設施
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm run dev
pm2 start ecosystem.config.js

# === 公網部署 ===
bash scripts/deploy/deploy-public.sh     # 一鍵：build → restart → verify

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
