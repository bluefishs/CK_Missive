# 全系統自主測試機制圖（2026-09-06）

> owner：「把現在散在各處的自主測試層（push 閘門、每日 runner、頁面走查、併發、部署態、視覺、效能探針、跨 repo 互驗）
> 盤成一張完整的機制圖——每層能看見什麼、看不見什麼、誰觸發、留痕在哪——再標出缺口與補法；另問分散的部分可否整合／統一／模組化。」
>
> 動態版（含每層留痕新鮮度）由 weekly 113 `testing_map_report.py` 產生：`docs/health/TESTING_MAP.md`。本檔是定義與判斷。

## 一、機制圖

```
                 ┌────────────── 開發者本機 ──────────────┐   ┌──────── 容器（backend） ────────┐   ┌────────── host 排程 ──────────┐
 git commit ───▶ │ pre-commit：tsc／ESLint／py_compile／   │   │ 02:00 每日 runner 17 步          │   │ 02:30 週日 weekly 113 步       │
                 │   secret guard／skills 格式             │   │   環境對齊、映像新鮮、SSOT、排程沉默、│   │   架構／規範／金流對帳／RWD／    │
                 │ commit-msg：commitlint                  │   │   八條生命跡象、知識文庫、重啟迴圈、  │   │   同步 I/O／名稱鍵／機制圖…      │
                 │ post-commit：知識地圖重生               │   │   ★業務鏈探針 32 斷言（09-06 起）    │   │ 04:15／05:10 流程走查 20 條     │
 git push ─────▶ │ pre-push：相關 pytest／vitest 對基線    │   │ 排程看門狗：cron_events／watchdog     │   │ 04:30 頁面走查 41 頁＋手機探針   │
                 └────────────────────────────────────────┘   └──────────────────────────────────┘   │ 04:50 能力使用（零流量）        │
 deploy ───────▶ deploy-public.sh 8 層：tsc 閘門 → build 身分 → 容器 health → host → 公網 200 → 認證鏈 → ★業務鏈探針      │ 03:00 異地備份（Website 驗證）  │
                                                                                                                       └────────────────────────────────┘
 手動 ─────────▶ 視覺走查 run.sh --visual --click／效能探針 route_cost_probe／SQL 剖析 pg_stat_statements
 跨 repo ──────▶ AaaP drift §40 排程 rc／§54 日誌佔比／§72 colo／契約探針每 10 分鐘（GET+POST）／health-smoke bridges；Website 備份結果；Hermes verify-bridges
```

| 層 | 誰觸發／頻率 | 看得見 | 看不見 | 留痕 |
|---|---|---|---|---|
| pre-commit（husky） | 每次 commit | 能不能編譯、有沒有洩密 | 任何行為 | 不留檔 |
| pre-push（husky） | 每次 git push（09-06 起） | 推送範圍相關的 pytest／vitest，基線外新失敗 | 沒有對應測試檔的改動、全套 | 終端 |
| 後端 pytest（307 檔；09-06 host 實跑 4,390 過／65 失敗／18 skip） | weekly 24（host）；無 commit 閘門 | 邏輯回歸、asyncpg 競態、os.kill 陷阱 | 跨表資料鏈、真實 DB | `known_failures.json` 基線（只有 2 筆 ⇒ weekly 24 每週紅 63） |
| 前端 vitest（228 檔） | **weekly 114**（09-06 起；首跑 254 失敗 → 三個共同根因修掉後 85） | 元件渲染、hook；mock 有沒有跟上 barrel | 真實 API、跨頁流程 | `frontend/tests/known_failures.json` 基線（86 項待清） |
| 每日 runner（容器 02:00，17 步） | APScheduler | 環境／SSOT／排程／生命跡象／知識文庫／重啟迴圈／**業務鏈** | 頁面、視覺、效能、跨 repo | `wiki/memory/fitness_daily_history.json`、晨報 digest |
| 每週 runner（host，114 步） | Windows 排程 | 架構規範、資料語意、金流對帳、RWD、同步 I/O、名稱鍵、慢性紅燈名冊 | 即時故障 | `fitness_weekly_last_run.json`、digest |
| 頁面走查＋手機探針 | host 04:30 | 41 頁載入錯誤／console／4xx5xx；390／768／1024 溢出 | 畫面對不對、數字對不對 | `ui-sweep.json`；weekly 109 讀 |
| 流程走查 | host 04:15／05:10 | 20 條斷言＋資料防護 | 版面、截字、顏色、遮蔽、手感 | `ui-flow.json`／`.user.json` |
| 手機品質閘門 | weekly 111 | 截字／字級／點擊目標／遮蔽／獨列／下拉塌陷，390＋1440 | 互動後畫面 | `rwd-quality*.json`＋基線 |
| 視覺走查 | 手動 | 人看圖才看得出的 | cron 沒人看圖 | `docs/health/visual/<日期>/` |
| 部署態 8 層 | 每次部署 | 編譯、身分、健康、公網、認證、**業務鏈 32 斷言** | 沒部署的日子（⇒ 探針入每日） | 部署 log |
| 效能探針 | 手動 | 每路由 API 支數／wall／同體重複 | 後端內部耗時 | 未入庫 |
| SQL 剖析 | 常駐（09-06 起） | 每句 SQL calls／mean／total | 應用層 | postgres 內 |
| 併發／事件迴圈 | weekly 112、每日 6、unit | async 路徑同步呼叫、gather 共用 session、飢餓 | 真實負載 | 基線檔 |
| 能力使用 | host 04:50 | 零流量且無呼叫者短名單 | 月週期 | `capability-usage.json` |
| 跨 repo 互驗 | AaaP／Website／Hermes 各自排程 | 排程 rc、日誌佔比、colo、契約端點存在、bridge 可達、備份錯誤碼 | 端點回什麼、還原可不可用 | 各 repo 的 blocker／drift 報告 |

## 二、缺口與補法

| # | 缺口 | 代價（實例） | 補法 | 狀態 |
|---|---|---|---|---|
| 0 | **後端 pytest 65 失敗而基線只登 2**：失敗集中在本週改過的服務（quotation／quotation_items／case_code／auth／digital_twin／financial_dashboard 的 mock 測試）＋測試庫 schema 漂移（UndefinedColumnError ×10，weekly 87）；weekly 24 每週紅但沒人收 | 改了服務沒跑它的單元測試 ⇒ 測試在改動當下就過期 | ①先修本週改動造成的（同一 session 內修）；②測試庫 `alembic upgrade`（weekly 87）；③其餘進基線名冊，新增才紅；④pre-push 跑 `tests/unit -x` | ①②③ **09-06 已辦**：本週改動造成的 mock 失敗修 7 支、基線重錄 38→31、weekly 87 排除備份表後 GREEN；④ 待 A46 |
| 1 | **前端 vitest 沒有人跑**：254 失敗／41 檔，主因是 mock 沒跟上新 export（`ClickableStatCard`、`useCaseCodeMap`、`useTaoyuanDispatchOrders`…） | 前端邏輯回歸完全靠走查與人；測試腐爛到修不動 | ①mock 改 `importOriginal` 展開再覆蓋（一次修一類）；②接進 weekly 24 同一支「基線比對」（新失敗才紅）；③跑得起來之後才談 pre-push | ①② **09-06 已辦**：三個共同根因修掉（254→85）、weekly 114 基線比對；③ 待 A46 |
| 2 | 沒有 pre-push | 壞掉的提交推到 main、部署閘門才擋（每次 10 分鐘） | **09-06 已接**：`prepush_related_tests.py` 只跑推送範圍相關測試（`tests/unit` 全跑實測 >10 分鐘，太慢），對兩份基線只擋新失敗 | ✅ |
| 3 | 業務鏈探針只在部署時跑 | 沒部署的日子資料漂移沒人走鏈 | **09-06 已補**：每日第 16 步 | ✅ |
| 4 | 視覺走查、效能探針只有手動 | 回歸靠人想起來 | 視覺：週一次 report-only 拍代表頁（人在 session 讀）；效能：weekly report-only 存 `route_cost.json` 看趨勢 | 建議，未做 |
| 5 | 沒有壓測、沒有 RUM | 併發行為與真實使用者體感都是推的 | locust 已在 requirements（未用）；RUM 接 web-vitals 兩支（lvrland 有） | 建議 |
| 6 | 留痕分散、格式各異 | 「哪一層沒人在跑」要人逐一翻 | 統一結果契約（見三）＋ weekly 113 機制圖照新鮮度 | 機制圖 ✅；契約待做 |
| 7 | 跨 repo 結果只在各 repo | 同一件事三個 repo 三份量測 | AaaP 已在做跨站對照表；本 repo 提供探針口徑 | 進行中 |

## 三、能不能整合／統一／模組化（owner 第二問）

**結論：引擎不合併，契約要統一。**

- 這些層跑在**四種執行環境**（開發者本機的 git hook、容器內 Python、host 上的 Playwright／PowerShell、別的 repo），
  硬併成一個服務只會多一層轉發，而且會把「容器內量到的」和「host 量到的」混在一起——L57／L52 家族就是這樣出事的。
- 真正分散的不是引擎，是**三件事各自為政**：①誰在跑（宣告在 README「誰在跑它」、settings.json hooks、Windows 排程、scheduler.py 四處）
  ②結果長什麼樣（json 鍵名各異：`checked_at`／`captured_at`／`ts`；rc 語意 0/1/2 各 repo 不同）③誰在看（digest、dashboard、blocker、人）。
- 統一的最小切口是一份**結果契約**：每層跑完寫 `wiki/memory/integration-health/<layer>.json`，固定鍵
  `{layer, checked_at(ISO/UTC), verdict(GREEN|YELLOW|RED|REPORT), rc, summary, evidence}`；
  weekly 113 只讀契約就能畫出完整機制圖，GOVERNANCE_INTEGRATED_DASHBOARD 也只讀契約。
  已有 `lib/` 共用層（paths／docker／db）可放 `result_contract.py` 一支 writer；新層一律用它，存量層在動到時順手改（同 lib 採用率的節奏）。
- 模組化到「可搬去別的 repo」的部分只有 selfaudit 引擎（已 vendored，A106 回流）與探針口徑；業務鏈探針本質上是 repo 專屬的，不該抽。

## 四、09-06 這一輪做了什麼

- 每日 runner 第 16 步：業務鏈探針（32 斷言，含 09-06 修掉的工項含稅／回寫 PM／自動應付掛 billing_id 三個斷點）。
- weekly 113：機制圖產生器（留痕新鮮度）。
- 後端 pytest：`test_asyncpg_race_lint` 的 allowlist 指到 09-05 改成套件前的舊檔名 ⇒ 紅，已修。
- 前端 vitest 首次完整跑：254 失敗／2,664 過，記 A111。
- 過期的一次性排程 `CK_Missive-Deploy-Once-20260831` 刪除需要管理員權限（owner 已授權，提權視窗待確認）。
- 09-06 晚：前端 vitest 三個共同根因（barrel 部分 mock／第二份 React／`responsiveValue`）修掉 254→85，接 weekly 114 基線比對；後端 mock 測試修 7 支、基線 38→31。
