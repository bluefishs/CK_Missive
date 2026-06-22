# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.21（2026-06-18）/ 整體覆盤後完善 — 每日巡檢 LINE 中文化(+修 overall 誤標 INFO 真 bug) + 治理 metric 完整性(L73 非 clobber/Hermes·wiki 正名/§9.5 誠實化) + SSO 公網導向護欄 + CK_Website 跨專案拓樸閉環(純 docker 單 backend)
> **最後更新**: 2026-06-18
>
> **近期重大里程碑**：
> - **v6.21 (06-18) — 整體覆盤後完善（7 commits push origin、backend rebuild+L76 驗證 host/公網 200、DB volume L43 安全、業務量 1858 docs/28010 KG 未減、重啟 pre-flight 通過 `docs/runbooks/reboot-pre-flight-20260618.md`）**：① **每日巡檢 LINE 推播中文化 + 修真 bug（已部署 live `bbdc91e6`）**：owner 回饋「[Pipeline INFO] 每日巡檢 (5 steps)」英文+raw dict 不友善 → 抓出 `overall` 計算缺 `info` 狀態 + `.get(s,4)` 預設值 → precommit 的 info(容器略過) 被算最高優先**蓋過 RED**，管理端誤見 INFO（底下其實有紅燈）；修 info 最低優先。中文標籤(架構健檢/能力使用稽核/記憶學習閉環/AI回應品質基線/提交守門)+白話解讀+三區(🔴需處理｜🟡注意｜ℹ️已知限制)；shadow_baseline 僅延遲紅(成功率OK)=本地模型上限歸「無需處理」不誤報(display-overall 不訓練成忽略紅燈)；scheduler.py title 中文化 body 改 LINE 友善 digest；測試 9/9 綠。② **治理 metric 完整性（`3e276f0b`）**：L73 非 clobber(生成器容器內無 git/memory 時保留前次 host 寫的 §3 commits/§4 sessions，根治每日 silent 回退空白)；§8.5 Hermes baseline #4 err/#5 p95 標「已接受結構性限制」(本地模型 TPM 牆、免費策略不列待辦)；§2 wiki_pages_total 範疇正名(全 wiki md vs LLM wiki 頁)+soul_drift=-1 sentinel 說明。③ **§9.5 表頭誠實化（`7a21b4c7`）**：「所有 47 cron」→「近期活躍 cron」+ 註明只含重啟後已 fire 的(週級 job 缺非中斷)、指向 scheduler_liveness_audit(持久 cron_events 對賬)。④ **SSO 公網導向護欄（`c8e6b5f4`）**：補 EntryPage 公網宣告式 `<Navigate>` 元件測試(鎖 L74/L66 修法行；既有測試只覆蓋 localhost imperative)，2/2 綠。⑤ **CK_Website 跨專案閉環**：missive 拓樸矛盾——docker 實證**純 docker 單 backend**(PM2 無 Missive 進程、host:8001=com.docker.backend→容器、公網 200)，舊「PM2 native vs docker 雙 backend 同 listen」矛盾已根除；cloudflared=token tunnel(ingress 在 CF dashboard)；DR drill #4 需第二裝置登入=owner-only。**查證更正（誠實）**：週自傳(weekly_evolution/memory_weekly_autobiography)與其他 cron 推播**早已納管/中文**，先前「盲區/待做」判斷有誤已更正、只做真正缺的小修。**待 owner**：SSO+reload 端到端真人複驗(L74 最終驗收)、DR drill #4、`/tender` UI 體感。
> - **v6.20 (06-17) — 標案 tender 整輪整合優化（多 commits push origin、前後端全綠、DB volume L43 安全、業務量 1855 docs/27407 KG 未減、重啟 pre-flight 通過 `docs/runbooks/reboot-pre-flight-20260617.md`）**：① **統計口徑 SSOT**：`/tender/dashboard` 全卡改週(近7日)單元（唯今日標案為日）+ DB 同源去重，修「本週招標 544 嚴重低估→8020」「決標停留 3 月→DB 新鮮」「最新決標重複卡」；`/tender/search`「今日最新」用真 count（= dashboard 今日標案，解 list limit 1000 截斷≠1237）；共用 `count/fetch_complete_tenders`(kind=opportunity/award/failed/rfp) 杜絕兩頁漂移。② **業務推薦 Option B 完整化**（L75.x）：關鍵字優先(權重10、**只比對 title**、**不受預算門檻**〔圖根點測量小案 NULL budget 不被擋〕)；機關精準局/所級窄通道(排裸府級+unicode 正規化+限工程類)；**排除機制**(財物 category + 負面關鍵字，非 AI——PoC 證實 nomic-embed 對短中文標題區分力不足、L2/L3 向量篩選會劣化故否決)；同義詞展開(UAV→無人機/空拍機)。③ **🆕 自維 UI（治本特例無窮，L75.4）**：「關鍵訂閱→推薦規則設定」面板——排除關鍵字/同義詞群組/💡承攬史建議工項一鍵加入，**即時生效、免 rebuild、owner 自維**（規則存可寫設定檔 `backend/config/tender_keyword_rules.json`，端點 `/tender/keyword-rules/{list,save,suggest}`）。④ **PCC 官方直連修**：`searchTenderDetail?pkPmsMain=<unit_id>`(我方 unit_id 即 PCC pkPmsMain)，base64 尾 `=` 須原樣(`quote(safe='=')`；%3D 落 stub)；取代失效 atmAwardAction 404。⑤ **Enrichment 死結定論（勿重試爬蟲路徑）**：openfun 需點分 org_id、org_id 只在**端點層反爬限流**的 PCC 詳情頁、無替代源 → server 端採購性質/底價取不到；**非全面 IP 封**(今日清單頁/爬蟲資料源正常)；DB 加 enrichment 欄位備用(遷移 `20260617a001`，ADD COLUMN IF NOT EXISTS 零刪除)、服務 best-effort 不掛 cron。詳見 `docs/architecture/TENDER_RECOMMENDATION_FLOW.md`(附錄B) + `LESSONS_REGISTRY.md#L75/#L77`。⑥ **L76 部署關卡落地**：後端任何 rebuild/recreate 後必驗 host→8001 + 公網 200(Windows 殭屍埠轉發風險)，本輪多次 rebuild 皆通過。**待 owner**：真實瀏覽器複驗 SSO+reload(06-16⑦) + `/tender` UI 體感(自維面板/卡片週單元/官方直連)。
> - **v6.19 (06-15~16) — 覆盤揪兩個作用中斷鏈根治 + SSO 不穩定結構性治本 + SSO bootstrap 競態真根因修（6 commits push origin，前後端全綠、DB volume L43 安全、重啟 pre-flight 通過；06-16 整體覆盤實證 52 容器 healthy / 1,852 docs / 26,935 KG / 公網 200 / 7 repo clean）**：① **wiki↔KG 反覆回歸結構性根因根治（`22f8a424`）**：揭發 `WikiService.ingest_entity`（`service.py`）每次重建 frontmatter **無條件 `created=now` + `kg_entity_id=None` 即省略該行** → 每週一 wiki_compile（wiki rw bind-mount 寫穿 host）沖刷 backfill 補的連結（212→86 反覆回歸，這是歷次「38.3% 回歸」真因）；v6.15 created-preserve 只補 `compiler._write_page`（topic/index）**漏 entity 路徑**。修：ingest_entity preserve created+kg_entity_id（+3 regression）+ `git checkout` 還原 154 entity（→**213**）。② **graph_domain 源頭自癒部署 + heal**：06-12 寫好未部署的 `code_graph_persistence` graph_domain=code（insert + on_conflict 自癒）rebuild 落地 + heal 13 新誤標 → **audit GREEN**。③ **SSO「停在 entry/閃訪客跳回」止血（`a66d410b`）**：log 證後端 sso-bridge 200（owner 已進系統用 AI），瞬態 race＝`validateTokenOnStartup` 首個 /auth/check 撞 reload cookie/csrf race→401→立即 clearAuth→跳回；修＝重試一次（600ms）僅重試仍失敗才清（不削弱安全）。④ **🏗️ SSO 不穩定結構性治本（`17373757`，owner 問「為何一直無法穩定」→ /plan A）**：根因＝前端**無單一權威登入狀態**（散在 localStorage/csrf/httpOnly cookie/auth.check/auth.me，5+ 元件各自推導+各自 redirect → 時機錯即 race；每次只補一處故持續開新洞）。治本＝新 `store/sessionStore.ts`(Zustand status=resolving|authenticated|anonymous 為唯一 is-authenticated 真相，單一 bootstrap)+`components/common/SessionGate.tsx`(App 根 resolving 顯 loading **禁所有守衛 redirect**→源頭消滅迴圈)+`useAuthGuard`/`AppRouter` 改讀 store+`EntryPage` 淘汰 `window.location.replace` 改 SPA navigate+store 監聽既有 user-logged-in/out 事件(5 派發點自動同步)。驗證 tsc 0 / useAuthGuard 19+sessionStore 3 測試綠 / **匿名載入 e2e 煙霧 PASS**（公網實測 SessionGate 不卡、入口渲染、0 致命 error，`scripts/checks/sso_entry_smoke.cjs`）/ dist bind-mount 即時 serve。**待 owner**：真實瀏覽器複驗 SSO+reload 不跳回 + Playwright 跨 subdomain E2E（獨立增量）+ lint guard 禁新元件自行 isAuthenticated+redirect。⑤ **桃園派工兩修（`74340416`）**：`/taoyuan/dispatch` 進站 tab 預設 `'1'`(派工紀錄)→`'0'`(派工總覽)；**總覽分母差異根治**＝morning-status `_ACTIVE_DISPATCHES_SQL` `WHERE deadline IS NOT NULL` **靜默排除無 deadline 欄位的派工**（project 21：30 筆中 3 筆 deadline 欄位空被排除→total 顯 27 但看板顯 30 不一致）。**正解（`c9d0e712`，取代 `74340416` 粗暴歸闕漏）**：端點放寬 `WHERE 1=1`（scope 於 local sql，不動共用晨報 SQL）讓無 deadline 欄位的派工走**相同真實 closure 計算**（closure 由 work_records/doc_links/events 決定，非 deadline 欄位）→ 158/159 有 work_record 未來 deadline_date→「排程中」、157 實為 delivered→「已完成/交付」、闕漏僅剩真實缺資料 2 筆；total 27→**30**、sum=30 一致。**刷新**：失效鏈本就完整（useDispatchCacheInvalidator 各法皆經 _invalidateAllListFamily 含 dispatch-morning-status），先前「填了不變」是本 bug 症狀非失效漏接。⑥ **SSO「停在 entry 重整才好」真根因修（`9e229a36`，owner 06-16 復報）**：④ 的 SSO 治本**自己引入回歸**——把 `window.location.replace`(強制整頁、不理 React 狀態)換成 ssoBridge async callback 內 imperative `navigate()`，被 `if(!mounted)return` 守衛擋住（EntryPage useEffect dep 不穩定 re-run→cleanup 設 mounted=false→ssoBridge resolve 回來 navigate 被跳過；重整會好＝重載 bootstrap 同步 resolve）。正解＝**宣告式導向**（EntryPage 訂閱 sessionStore，authenticated+公網即 `<Navigate>`；markAuthenticated 移出 mounted 守衛）。**元教訓**：導向勿放在會被 effect cleanup 中斷的 async callback，應宣告式依權威狀態 render；「治本」重構務必驗證原症狀真消失（匿名煙霧過≠authed 導向過）。**其他平台/www.cksurvey.tw 不需同步**（bug 純在 CK_Missive 前端 EntryPage；www.cksurvey=IdP 正常、lvrland/pile 未採此重構不受影響）。⑦ **SSO「第一次停在 entry、重刷才好」真根因修（`b2b6ae26`，owner 06-16 重開機後復報，⑥ 仍未治本）**：`sessionStore.status` 被兩個獨立 async 解析器 **last-writer-wins 競寫**：(1) `bootstrap()` 重開機後 localStorage.user_info 持久殘留→走 `validateTokenOnStartup`，舊 token 失效時**內部 `clearAuth()` 清資料**+回 false→`anonymous`；(2) EntryPage `ssoBridge()` 用 ck_employee cookie 建立**全新 session**→`markAuthenticated`→`authenticated`→`<Navigate>` 進 dashboard。**bug 時序**＝ssoBridge 先贏設 authenticated→bootstrap 的 validate **遲到失敗** (a)`clearAuth` 清掉剛建立的新 session (b) status 覆寫回 anonymous→dashboard 被踢回 entry；**重刷會好**＝前次 clearAuth 已清 user_info→重刷 cached=null→bootstrap 早退不再 validate→ssoBridge 乾淨贏（精確解釋「第一次失敗、重刷成功」）。**正解（SSOT 層，非再補 EntryPage）**＝`validateTokenOnStartup` 改**非破壞性**（不再內部 clearAuth，唯一 caller 是 bootstrap）+ `bootstrap` 加**競態防護**（await validate 後若 status 已被升級為 authenticated 則尊重、不降級不清；真失效才 `clearAuthData`+anonymous）；規則＝**markAuthenticated（明確成功事件）優先於被動舊 token 檢查**。驗證 sessionStore 競態 regression + useAuthGuard 19 測試綠 / tsc 0 / build 部署 `main-DRLxZRio.js` / 匿名煙霧 resolved+entryRendered+0 fatal。**P1-① 結構性護欄（`1dc75776`）**＝新 `scripts/checks/auth_state_ssot_audit.cjs`（fitness step 64）偵測非 auth 基礎設施元件自行『推導登入+導向認證頁』，baseline 掃 793 檔 **0 violation GREEN**。**元教訓（補 L74）**：單一狀態欄被多個 async 來源 last-writer-wins 競寫、且其一帶破壞性副作用（clearAuth）＝經典 race；治本＝讓「明確事件」優先於「被動檢查」+ 把破壞性副作用收歸唯一決策點。**待 owner**：真實 ck_employee cookie 瀏覽器複驗 SSO+reload 不再停 entry（headless 無法代行）。詳見 `session_20260615_wiki_kg_regression_root_fix_sso_diag` + `docs/runbooks/reboot-pre-flight-20260616.md`。
> - **v6.18 (06-12) — 圖譜治理體系擴大成型（8 audit 57b-57h）+ 真因根治連發 + 57e/57f/57g 完整辦理**：延續 v6.17 圖譜治理，擴大為**8 維持續自我稽核 + 真因根治**（皆 push origin、前後端全綠、DB volume L43 安全）。① **治理 8 audit**：57b config drift(AST 衍生)/57c 命名 SSOT/57d runtime 對賬/57e 重複樣態/57f 排程真活/57g 導覽鏈接線/57h 對話學習覆蓋 + **全部 cp950 host 韌性化**(sys.stdout.reconfigure，L49.8 同族)。② **L72 排程「註冊≠真在跑」根治**：scheduler_liveness 揪 cleanup_events/security_scan/fitness_daily **缺 misfire_grace_time → 02:00 壅塞 skip 從不執行** + security_scan 內部 `rglob('/app/backups')` [Errno 5] crash 被吞(L49.2 同族)→ 補 misfire_grace_time=7200 + scanner 改 os.walk 只掃源碼 → **驗證今日 02:00 全 fire success/掃到 9 issues** + id 對齊(code_graph/optimization)→ 0 DORMANT/0 命名不符。③ **坤哥 self_diagnosis hollow 誤報修**：gauge restart 歸零誤報→fallback 直數 diary 檔(live gauge 實 51)。④ **L70 calendar 後續**：deadline 訖點單日呈現(會議保留時間)+1044 in-place 更新 + **397 重複孤兒清理**(保留 owner 手動 122)+ GOOGLE_REDIRECT_URI/MAX_OVERFLOW/DB 池同型 drift 標準化(RED→0)。⑤ **L71 圖譜治理策略**：圖譜=結構地圖≠治理，須 AST 橋接 fitness。⑥ **57g 完全排除**：17 處 apiClient 硬編路徑全遷端點常數 SSOT(tsc 0/0 RED 0 YELLOW)。⑦ **57e 重複收斂 5 SSOT**：get_cached_redis/grouped_count/get_by_ids/normalize_name/parse_tools(真重複 125 噪音→8 精準、5 收斂、3 域特定保留，不過度抽象)。⑧ **坤哥/Hermes 驗活**：學習閉環/LINE push 3/agent 對話 60筆 皆真活。**殘留待 owner**：57h 對話學習扎根真實需 owner 用坤哥 chat(機器已備好、近7日 204 synthetic/0 real)。詳見 `LESSONS_REGISTRY.md#L70`/`#L71`/`#L72` + fitness step 57b-57h。
> - **v6.17 (06-11) — Google Calendar 同步真因根治（L70 config-drift）+ nav CSRF（L69）+ 覆盤三修法**：① **🔴 揭發 1044 事件「同步成功卻無人看得到」根因＝L70 config-drift**：owner 報公司日曆(cksurvey0605)看不到任何 Missive 事件；服務帳號直查證 DB 記 synced+有 google_event_id 但共享日曆 `6a3478...` 抽樣 6/6 全 404。真因＝`docker-compose.production.yml` **未注入 `GOOGLE_CALENDAR_ID`**（無 env_file，逐項注入卻漏）→ 容器退回 config 預設 `'primary'`＝**服務帳號私人隱形日曆** → 1044 事件全推進去（「之前皆正常」其實從未對人類生效）。修：compose 補 `GOOGLE_CALENDAR_ID` + recreate（`--no-build` 保 baked code）→ **全量 reset 1043 + 經 app 重推到 6a3478 → 1044/1044 synced、抽樣 Google 端真存在、owner 確認看到 6/15**。② **start==end timeRangeEmpty 修**：`google_client.create_event` 正規化 all-day end 排他(+1天)/定時 end>start(+1hr)→原 15 筆 failed 重推全成功（rebuild backend 部署）。③ **治本防回退**：擴充 fitness step 1 `container_env_alignment_audit` GOOGLE 群組納 `GOOGLE_CALENDAR_ID`（現 GREEN）。④ **L69 nav 選單 403**：`secureApiService` L49 single-flight 讓並發 caller 共用同一張「單次」Redis CSRF token（特定頁面同時載側欄+設定重現「點選單出錯、重整可運作」）→ 移除 dedupe 各拉獨立 token（build 部署）。⑤ `.env` `GOOGLE_CREDENTIALS_PATH` Windows 絕對路徑被 mojibake 註解吞掉(從未生效)→ 拆乾淨行+改相對(.env gitignored 不入版控)。⑥ `_shared` 5 agent 檔正規修法（shared-modules 來源 role→description；該 repo 有他人 WIP 故來源僅磁碟修正不 commit）。**殘留**：1043 筆舊事件仍在服務帳號 primary 隱形日曆（孤兒、無害，待 owner 決定是否清）；calendar-sync 診斷頁待補（`/google-auth-diagnostic` 只診斷 OAuth 登入非同步）。詳見 `LESSONS_REGISTRY.md#L70`/`#L69`。⑦ **名稱類別規則 a+b+c**（owner 決議）：開會通知單抽取真實時段→meeting 設 all_day=False 保留時間（9 regression tests）/ 弱關鍵字 meeting 精確化降級 / 43 筆遺留「公文提醒:」正規化（44→1）。⑧ **🔭 強化圖譜治理（owner 目標：不限日曆、擴大系統標準化）→ L71 + 治理三支柱**：揭發「程式圖譜是結構地圖，抓不到 config/語意/runtime 三類問題、真正防線是 fitness 但用寫死清單漏網」→ 建立 **AST 衍生 config drift 全域審計**（`config_settings_drift_audit.py` step 57b，掃全 settings 讀取×.env×compose）立即補抓 **GOOGLE_REDIRECT_URI**(容器用 localhost 預設、prod 應 missive.cksurvey.tw)+**MAX_OVERFLOW**(.env20≠預設30) 同型 drift 並標準化注入（RED→0）+ **命名 SSOT 強制**（57c）+ **runtime 狀態對賬**（57d 抽樣 synced 驗 Google 真存在、0% drift GREEN）。**殘留待 owner**：Google 日曆 397 筆早期同步重複孤兒待清（owner 手動 93 筆保留）。
> - **v6.16 (06-10~11) — 3 認證/前端 bug 根治並部署（SSO 顯示 race + 排程追溯 double-prefix + CSRF refresh 死結）+ /doctor**：① **SSO「停在訪客」實為前端顯示 race（後端 100% 健康）→ L66**：跨 repo 追查（www.cksurvey=CK_Website IdP、dashboard 純 cookie/JWT 不寫 localStorage；那行 `[Header]…訪客` 字面源自 Missive `Header.tsx:169`）+ **後端 log 鐵證 owner Chrome 同源 sso-bridge 08:47/08:52/09:08 三次 200 登入成功**（cookie 帶到、RS256 JWKS 驗過、session 建立）；`POST 200×4/401×84`，401 全為**每 15 分鐘 curl 探針 noise**。根因＝EntryPage SSO 成功後 `window.location.replace('/dashboard')`，但 `useNavigationData` self-heal gate **只看 localStorage JWT**，SSO token 在 httpOnly cookie → 不觸發 → 整頁重載瞬間 lazy-init 偶發漏讀 user_info 無兜底 → 手動 reload 才好。修：self-heal gate 擴納 `csrf_token` cookie（non-httpOnly、SSO 亦設）→ 競態下用 `/auth/me` 補水免 reload（`useNavigationData.tsx:87`）。後端 `sso_bridge.py` 不動（健康）。② **「排程追溯仍無紀錄」實為前端 double-prefix 404（半接通）→ L67**：`cron_events.jsonl` **9454 筆寫入正常** + router 掛載（`routes.py:59-60`）+ 容器內實測 `events/stats=200`，斷點在前端 `SchedulerEventsPage` 4 處硬編 `/api/admin/...`（apiClient baseURL 已含 `/api`）→ `/api/api/...` 404 → 表格空。修：移除 4 處 `/api` 前綴對齊 endpoints 慣例（`:55/64/73/90`）。③ /doctor：5 個 `_shared` agent 檔 `role:`→標準 `description:`（內容不動）；heptabase/claude.ai MCP 待 owner 自跑 `/mcp` 認證。**部署＝`npm run build`（公網 backend 經 bind mount `./frontend/dist:ro` serve SPA，零容器 rebuild；`docker-compose.production.yml:249-254`）**，2 次 build exit 0、backend dist 16:34 更新確認。④ **手機「權限不足」根治（L68 — CSRF refresh 死結）**：owner 報手機登入報「**權限不足**」（OWASP CSRF 關注點）。伺服器端模擬 4 情境 + `[CSRF]` warning log 鐵證：DB 證兩帳號（jujuiacc superuser/luke admin）**皆 admin → 403 與權限無關**。死結＝`csrf_token` cookie 固定 `max_age=3600`(1h)，`access_token` 可 refresh 續命兩者生命週期不對齊；csrf 過 1h 後前端要 refresh，但 (1)`/api/auth/refresh` 不在 `CSRF_EXEMPT_PATHS` (2) 前端 refresh 用**裸 axios 繞過 interceptor** 從不帶 X-CSRF-Token (3) 此刻 csrf cookie 已消失 → refresh 被 `CSRFMiddleware` 403 → token 無法續 → csrf 無法重發 → 全站 mutating 403 → `GlobalApiErrorNotifier` 誤標「權限不足」；iOS Safari cookie 易丟加劇。修：**(後端)** `/api/auth/refresh` 加入 `CSRF_EXEMPT_PATHS`（`csrf.py`；refresh_token cookie 為 `httpOnly+samesite=strict` 跨站不帶 → 已自帶 CSRF 防護，OWASP 認可 token-less，非放寬）；**(前端)** request interceptor 改 async 自癒（`interceptors.ts`）：mutating 遇 csrf 缺失且已登入時先補打已豁免的 `/secure-site-management/csrf-token` 重取再送（裸 axios 防遞迴、same-origin 才能補→不削弱防護）。**部署＝`npm run build`（公網 backend 經 bind mount `./frontend/dist:ro` serve SPA，零容器 rebuild；`docker-compose.production.yml:249-254`）**；**06-11 複驗：前端 dist rebuild 00:43（含 L66/L67/L68 三檔）+ 後端容器 `csrf.py` 確含 refresh 豁免 live + `tsc 0` + 5 容器 healthy + pipeline INFO/self-retro GREEN**。詳見 `session_20260610_sso_race_scheduler_doctor` + `LESSONS_REGISTRY.md#L66`/`#L67`/`#L68`。⚠️**全數已部署且 live 驗證，唯一缺口＝git 未 commit/push（待 owner 決定）+ 殘留：① `GlobalApiErrorNotifier` 仍把 403-CSRF 誤標「權限不足」（L68 Prevention(c) 未做）② 跨 repo lvrland/pile 同型檢查未做（L66/L68 Prevention）**。
> - **v6.15 (06-09) — 覆盤 + 學習閉環收斂 + 路由 false-positive 修（6 commits push origin，backend rebuild 2 次）**：① **wiki `created` preserve**（`5f47f326`）：`compiler.py` 17 處 `created:{datetime.now()}` 無條件改寫 → 集中式 `_write_page` helper 覆寫前讀既有 frontmatter preserve（regression 3 案）。② **failure tracker 收斂（L59 倒置具體化）**（`b6347d3c`）：`pattern_extractor` 加 `_is_chitchat_question` 過濾（閒聊「好的」誤觸工具不形成 tool-sequence 信號）+ `expire_stale_failures`（last_seen >21d→active:false，`FAILURE_EXPIRE_DAYS` 可調，每日 extract 末尾呼叫）→ **live 觸發 7 筆過期，active_failures 13→6**（regression 22 案）。③ **a18f229167 路由真因修**：「桃園市工務局相關公文」三命中 agency+doc+相關 → Layer 1.6 誤觸 `search_across_graphs` 6/6 fail；加 **agent_router Layer 1.55 `doc_related_filter_rule`**（相關+公文類名詞→search_documents），live 驗證 PASS、真跨域不波及（regression 4 案 + 76 既有無回歸）。④ **退回 crystal 提案 713394**（同 sibling 缺陷 + 同 hash failure 記 50% 打臉「100%」）。⑤ Groq 免費 tier 評估：agent 層 99.4% 健康、synthesis 超時已有結構化 fallback；零成本最佳槓桿＝解 gemma4:e2b 7.2GB VRAM 保溫矛盾（非升 Groq）。⚠️ 既有 2 test isolation 失敗（讀真實 FAILURES_DIR）非本次造成。詳見 `session_20260609_review_deploy_failures_triage`。
> - **v6.14 進行中 (06-04) delta — routing/integration 補強（8 commits 全 push）**：⑤ agent_router 新增 **Layer 1.7** finance/tender 單域確定性快路由（補 Layer 1.5/1.6 缺口；「未付請款」原誤落 search_documents → 工具細分 get_unpaid_billings/get_expense_overview/get_financial_summary，對 synthesis 35s budget 友善；工具名同 `_INTENT_TOOL_MAP` SSOT，commit `6e51bcef`）+ tools_manifest v1.2→1.3（9→12 工具，補 finance_query/tender_search/project_query，H1）+ **synthesis 超時 fallback 改輸出結構化工具結果摘要**（`_timeout_fallback` 用 build_synthesis_context，取代「AI 回答生成超時」空訊息；正常路徑零變更、僅超時分支改善，commit `e840f644`）+ crystallizer **L1** 從 example_questions 滑動 2-3gram 推導 intent_rule 候選 regex（取代寫死 `pattern=""`，commit `517cdd5f`）+ fitness step 19 註冊 LN1 routing keyword false-positive audit（finance 0%/tender 3% ≤ 8%，commit `280f61cb`）+ `docs/runbooks/deployment-effect-ssot.md` 部署生效機制 SSOT（commit `07eadee6`）。詳見 `session_20260603_04_routing_synthesis_integration`。
> - **v6.14 進行中 (06-03) delta — synthesis 超時根因鏈（L64）**：① `ai_connector.py TASK_MODEL_MAP` 補 `synthesis`/`vision`→`gemma4:e2b`（漏映射 → 原落 qwen2.5:7b p50 52.8s → synthesis 35s budget 必超時；與 vision 發票 OCR silent 退 QR 同型）+ synthesis 路徑 NVIDIA timeout 縮 30→8s（`NVIDIA_SYNTHESIS_TIMEOUT`）保證本地 fallback 有時間（commit `28a29939`/`dc9b6f98`/`42bdf2ea` + regression `test_synthesis_fallback_model.py`）。② **LINE 推播鏈交易污染復發修（L64 子案 A）**：`broadcast_to_admins` 缺方法 + except 吞錯不 rollback 污染 self.db + scheduler 重複掃 ERP（dormant ~9 天 silent）→ 補方法 + rollback + 移除重掃 + regression `test_line_push_chain_regression.py` + fitness step 63 `transaction_pollution_audit.py`（commit `8b5dd584`）。③ **殘留（owner 層，非 code 可解）**：Groq 429 高頻 + GPU semaphore=3 併發 burst 下 gemma4 達 ~24–32s 仍擦 35s 邊，治本＝Groq TPM quota 升級。④ intent→tool 確定性映射 `_INTENT_TOOL_MAP`（commit `a33a0bbc`，取代 LLM 幻覺建議工具）。詳見 `docs/architecture/LESSONS_REGISTRY.md#L64` + `docs/architecture/V6_14_INTEGRATION_OPTIMIZATION_AGENDA_20260601.md`
> - **v6.13 (06-02) 真因鏈大掃除**（23 commits 全 push / 重啟 pre-flight 通過 `docs/runbooks/reboot-pre-flight-20260602.md`）：
>   - **平臺自證 silent→LOUD 四層**：8 cron `.parent` 路徑 bug（每日覆盤+LINE 全 silent 死）+ 開機自檢 + silent return→raise + outcome-freshness watchdog（07:00）
>   - **3 個 config drift 修真因鏈**：① `OLLAMA_BASE_URL=localhost`→`host.docker.internal`（修「無法生成查詢向量」0.0s + ollama fallback 層）② `PGVECTOR_ENABLED` compose 漏傳→補（修「pgvector 未啟用」）③ token SSOT auth_service 硬編碼 30→改讀 settings 60min（修閒置不到 30 分被登出）
>   - **vision 修**：task_type=vision 映射 gemma4:e2b（修發票 OCR silent 退 QR）
>   - **kunge UI 整併 + 崩潰/403 修**：tab 7→5 核心主軸（對話/心智/進化/圖譜/運維）+ 去 ops 對話重複 + 閒置倒數徽章 + 自省/追蹤/服務狀態 3 tab 崩潰修（domains dict / items→traces drift / config 深層 optional chaining）+ chat agent stream 403（raw fetch 補 X-CSRF-Token：adminManagement/coreFeatures/digitalTwin）+ GatewayHealthBadge 改 apiClient
>   - **學習閉環三柱戰略**：`ARCHITECTURE_DEVELOPMENT_STRATEGY_20260602.md`（接通與真活脊柱）；柱一 Step A crystallizer tool_sequence 解析修 + Step B 撤回（PatternLearner 已自動閉環）/ 柱二 H1 撤回（盤點防做白工）
>   - **共同模式（rigor 教訓）**：raw fetch 漏 header（CSRF/Auth）+ config 沒進容器（OLLAMA/PGVECTOR）+ data shape 當陣列 .map → 建議 fitness audit 防同型；3 起自傷錯誤（init_nav 污染/誤刪 gemma4/docs :ro）立 `feedback_rigor_no_self_inflicted_instability`
>   - 詳見：`docs/runbooks/reboot-pre-flight-20260602.md`（pre-flight 全通過 + 重啟後 5 步驗收）
> - **v6.13 三層整合 + 靈魂進化 + 重啟準備**（2026-05-31 → 06-01 / **5/30-6/1 跨日 82 commits 全 push origin**）：
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
> - **v6.12 進化 4 原則 + Facade B 方案**（2026-05-30 / 21+ commits）：進化 4 原則（修法掃全範圍 audit / fitness 3 層 daily+weekly+monthly / 治理 metric 化 / 元覆盤 cron）+ Facade B 方案 13→3 收口（-1509L）+ 整合 SSOT Dashboard 4 道防線 + fitness 51→65 step + 8 句立法 + L57/L58/L59/L60 lesson；詳見 `docs/architecture/RETRO_20260530_31_TWO_DAY_CONSOLIDATION_AND_V613_BLUEPRINT.md`
>
> <details><summary>v6.11 及更早里程碑（展開）</summary>
> - **v6.11 完整收尾**（2026-05-27 → 28 / **25 commits 已 push origin** / L49 family 14 案 + ADR-0046 標案模組）：
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
> - **v6.11 早期里程碑**（2026-05-27 → 28 早段 / 19 commits / 4 層自動重啟 + 自動化驗收 10/10 PASS）：
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
> - **v6.10.3 L43 Volume Mount Drift 災難級事故恢復**（2026-05-21 下午 4h / 4 commits）：
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
> - **v6.10.1 + v6.10.2 慢性 Bug 大掃除**（2026-05-19~20 兩日 / 4 commits / +4299 lines）：
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
> - **v6.10 P1 真模組化**（2026-05-18 下午 — 8 輪 dynamic /loop 收尾）：
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
> - **v6.10 候選**（2026-05-16~18 整合治理交付）：
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
> - **v6.9**（5 輪 dynamic /loop，2026-05-08 → 05-12）：
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
> - **v6.8**（36 commits，2026-05-04，5 小時內完成）：
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
> - **v5.10.0 ~ v5.10.2**（42 commits，2026-04-27~04-28）：
>   - Wave 1-8 services DDD 遷移完整收斂（73 檔 / 12 bounded contexts / 0 regression）
>   - LESSONS_REGISTRY v1.0（22 條 lessons L01~L22 — 跨 session 知識傳承 SSOT）
>   - 4 detector 治理三件組（agent_evolution / lessons_drift / dead_ui / notify_consumers）
>   - CROSS_REPO_REFERENCE_GUIDE v1.0（FQID 5 大類別 + SemVer + 7 consumer registry）
>   - Playbook v2.0 → v2.2（7 SOP + 1 anti-pattern）
>   - Fitness 6 → 7 step（加 agent_evolution_health）
>   - install-template-to.sh 12 fitness 檔跨 repo 一鍵部署
>   - PR template + consumers.yml 規範化貢獻回流
>   - Bug fixes: 派工總覽 morning-status 即時刷新 + 認證整合 UI 接通
> - **v5.9.3 ~ v5.9.9**（37 commits）：ADR-0028~0033 + Qwen 零成本整合 + KG 100% / Wiki 85% / SLO SSOT
> - **ADR 治理**（ADR-0029）：Active 16 / Archived 14 / Removed 1（adr_lifecycle_check 2026-05-16 實跑）
> - **Hermes GO/NO-GO**（ADR-0030）：v6.8 F26 救活 shadow_baseline → real **p95=58s 警訊**
>   接近 60s 邊界。5/20 用 `docs/adr/0020-hermes-role-decision-proposal-v3.md` 三方案投票
> - **坤哥為唯一意識體入口**（ADR-0023 + ADR-0031）：/kunge 7 tabs 統一
> - **Source Repo 自我治理閉環**：發現→記錄→驗證→範本化→註冊→通知→回流
> - **v7.0 baseline 量化**（v6.8 取代「成熟度 %」）：
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
missive.cksurvey.tw   →  公文系統 (UI + API)，已上線
hermes.cksurvey.tw    →  Hermes Agent gateway (Phase 1 後啟用)
lvrland.cksurvey.tw   →  土地查估 (Phase 2+)
pile.cksurvey.tw      →  基樁管理 (Phase 2+)
kg.cksurvey.tw        →  聯邦知識圖譜 Hub (選用)
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
- 資料庫: PostgreSQL 16 (Docker, port 5434)
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
