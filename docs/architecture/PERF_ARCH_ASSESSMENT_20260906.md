# 服務效能、模組化與服務架構評估（2026-09-06）

> owner 09-06：「服務效能優化、模組化與服務架構等評估」。
> 本文只寫**量到的**與**從量到的推出來的**；沒有量的（真實使用者 RUM、SQL 逐句剖析）會明說沒有。
> 數字全部是 2026-09-05～06 實測，方法附在每一節。

## 一句話

後端不是瓶頸：24 小時 4,245 支請求、p50 多在 100ms 以內；使用者感受到的慢幾乎全是 **每支 API 固定 0.4～0.55 秒的 Cloudflare 往返**（colo=SJC，五站一致），乘上每頁 8～15 支。
模組化的實況是「方向對、落地六成」：Repository 覆蓋 43/72 張表、共用層採用率低、單體單進程。
**能在本 repo 做的最大兩件事**：整頁載入 9 支 layout 級 API 合併（等平台 colo 決策後做，A109）、開 `pg_stat_statements` 讓 SQL 剖析不再盲。

## 1. 效能

### 1.1 往返成本（平台級）

| 量什麼 | 值 | 方法 |
|---|---|---|
| `cdn-cgi/trace` | colo=SJC、loc=TW | curl |
| `/api/health` 公網 vs 容器內 | 0.56s vs 0.009s | curl time_total（新連線含握手） |
| 五站 TTFB（AaaP 實測） | 0.398～0.404s，離散 6ms | curl time_starttransfer |
| 同頁 12 支端點（暖切換、連線復用） | 0.40～0.49s，**零例外**，後端各 10～55ms | `scripts/perf/route_cost_probe.cjs` |

兩組不同切法（橫向五站、縱向同頁 12 支）指向同一個常數 ⇒ 往返時間與端點無關，連線復用也消不掉。這是平台決策（CF Pro/Argo 或 split-horizon），登記在 `CK_AaaP` `B-CF-EDGE-COLO-SJC`。

### 1.2 每頁 API 支數

| 頁 | 冷載入（整頁重載） | 暖切換（SPA） |
|---|---|---|
| /dashboard | 10 | — |
| /documents | 12 | 0 |
| /contract-cases | 12 | 5 |
| /erp/quotations | 10 | 3 |
| /erp/financial-dashboard | 15 | 7 |
| /kunge/ops | 12 | 5 |
| /erp/expenses | 11→10 | 4→3 |

冷載入固定的 **layout 級 9 支**：csrf-token、auth/check、auth/me、navigation/action、unread-count、filing-gaps/mine、calendar-events、**ai/config**（`syncAIConfigFromServer` 開站即打）、**taoyuan-dispatch/dispatch/contract-projects**（`Layout.tsx` 的 `useDispatchProjectIds` 為了模組旗標抓全部桃園承攬案）。後兩支是 09-06 從 24 小時「最常被叫」名單看出來的（各 324 次，與 auth/check 同數 ⇒ 每次整頁載入必打）。
SPA 暖切換 React Query 快取有效、同體重複 0 —— lvrland 找到的「同頁多元件打同一支設定 API」放大器，這裡沒有。

### 1.3 後端耗時（24 小時 REQUEST_END 4,245 筆）

| 端點 | n | p50 | p95 | 判讀 |
|---|---|---|---|---|
| POST files/storage-info | 7 | 1,066ms | 1,096ms | 唯一破秒；疑為每次掃 uploads 目錄，**待查** |
| POST ai/digital-twin/dashboard | 13 | 885ms | 903ms | 09-05 已修：不打廢止的 NemoClaw、鏡像背景回填；公網複量 1.19→0.47s |
| POST projects/{id}/detail | 26 | 61 | 478 | p95 尖峰，可能是同時載入分頁 |
| POST project-vendors／agency-contacts／staff list | ~29 | ~55 | ~420 | 同上，承攬案詳情頁四支平行 |
| POST projects/list | 52 | 56 | 336 | 正常 |
| POST documents-enhanced/list | 14 | 94 | 293 | 正常（容器直打 451→73ms 冷／暖） |

其餘 p50 全在 100ms 以內。狀態碼：200 ×3,543、401 ×276（登入頁輪詢與 sso-bridge）、405 ×189（AaaP 契約探針刻意 GET 一個 POST-only 端點，每 10 分鐘一次）、404 ×114。

### 1.4 資料層

| 項 | 值 |
|---|---|
| DB 大小 | 663 MB；`canonical_entities` 419 MB（63%，KG 向量）、`tender_records` 115 MB、`documents` 23 MB |
| 連線 | 17 條（pool_size／max_overflow 走設定），活躍 1 |
| 大表全表掃描為主 | 0 張（`pg_stat_user_tables` seq_scan > idx_scan 且 >1 萬列） |
| **`pg_stat_statements`** | **未啟用** ⇒ SQL 逐句剖析目前是盲的；啟用零成本，是 §5 建議 #3 |

### 1.5 前端資產與日誌

- 覆蓋式部署保留 24 小時舊 assets（避免 09-04 的 chunk 404 空窗）；09-05 連跑 15 次部署後 `dist/assets` 191 MB、31 份 main，隔日自動修剪，**不是洩漏**。
- 單次 build 最大 chunk：`antd-core` 1.29 MB、`swagger-ui` 1.21 MB（後者 lazy，只有 API 文件頁載）。
- 日誌：09-05 降噪後 10 分鐘 1,243→119 行（−90%）；每一行的 `version` 欄此前寫死 `3.0.1`（runtime v6.73），09-06 改讀 `build_info`。

## 2. 模組化

### 2.1 規模

| | 後端 | 前端 |
|---|---|---|
| 程式行數 | 188k Python | 251k TS/TSX |
| 單元 | 167 個 endpoint 檔、409 個 service 檔、61 個 repository、28 個 model 檔、72 張表 | 113 頁、210 元件、59 hook |
| 最大檔 | `services/wiki/compiler.py` 2,043 行、`morning_report_service.py` 1,112、`quotation_legacy_import.py` 996 | — |

### 2.2 分層落地程度

| 判準 | 值 | 來源 |
|---|---|---|
| Repository 對 table 覆蓋率 | **43/72（60%）** | weekly 70 `repository_coverage_audit` |
| service 直接 `db.execute(select(...))` | 08-28 量 435 處／74 檔（寬判準）；09-06 精確字面 15 處／7 檔 | grep；兩個數字判準不同，**不可相減** |
| endpoints 本地 BaseModel | 存量 18 走基線、新增 0 | weekly 59 |
| 業務實體建構只在授權處 | GREEN | weekly 57 |
| 名稱／鍵成對欄位 | 可連未連 0、漂移 12 待判 | weekly 107 |
| 腳本共用層採用率 | 3.3%；09-01 新增的兩支自己重造 paths／docker（RED） | weekly 93 |
| shared-modules 消費 | vendored 複本（`.shared-selfaudit/`）09-05 本地改了 `--click`，來源未回流（A106） | toolkit sync |

判讀：**規範是對的、守門也在**（weekly 57／59／70／93），但落地是「新增才守、存量慢慢清」——這是 08-28 就寫進 `development-rules.md §5` 的刻意選擇（一天 435 個紅點會讓訊號失效）。實際代價已付過一次：`_get_creator_names_batch` 繞過 repository ⇒ 單元測試 mock 蓋不到 ⇒ 壞了一段時間沒人發現。

### 2.3 這週剛落地的共用元件

`EnhancedTable.mobileCard`／`MobileCard`／`FilterBar`／`ClickableStatCard`／`financeTerms`：五個列表頁改走同一套，weekly 108／111 守。這是模組化在前端最有感的一段——同一個缺陷（統計卡不篩、下拉塌陷）現在改一處。

## 3. 服務架構

```
Cloudflare Tunnel（colo=SJC）─ cloudflared ─ nginx(frontend :3000) ─ uvicorn 單進程(:8001)
                                                                       ├ APScheduler（同進程，Postgres jobstore）
                                                                       ├ 程序內快取（孿生快照 60s、熔斷器走 redis）
                                                                       ├ 限流 slowapi（無 storage_uri，A51）
                                                                       ├ PostgreSQL 15 + pgvector（663 MB）
                                                                       └ Redis（AOF）
```

| 面向 | 現況 | 風險／判讀 |
|---|---|---|
| 進程模型 | **單 uvicorn 進程**（Dockerfile CMD 無 `--workers`） | 4k 請求/日綽綽有餘；但一切「程序內狀態」（排程、快取、限流計數、去重）都假設單進程。**要開第二個 worker 之前**限流與快取必須先搬到 Redis（A51 是第一個） |
| 事件迴圈 | 09-05 抓到一個同步 HTTP（4 秒 DNS 失敗）卡住整個迴圈，同時所有請求一起 4.5 秒 | 同型風險：任何 `requests`／同步 `httpx.Client`／`subprocess` 在 async 路徑上。建議 weekly 加一支靜態掃描「async def 內的同步 I/O」 |
| 死整合 | NemoClaw（ADR-0015 廢止）的 Registry URL 還是預設值 ⇒ 每 60 秒 DNS 失敗；`/document-numbers` 棄用 router 帶著 607 行跑了半年 | 兩者 09-05 已除。**廢止決策沒有配套的程式碼下線清單**是結構性缺口——ADR 歸檔時應附「哪些預設值／路由／排程要一起拿掉」 |
| 認證鏈 | csrf→auth/check→auth/me→nav 有依賴鏈 | 這條鏈是 layout 合併時最敏感的部分；在 colo 未定前不動（AaaP 同意） |
| 觀測 | Loki/Prom/Grafana 在 AaaP；本容器日誌佔比 09-05 從 53.8% 降到第一名以外 | 日誌 `version` 欄過期半年沒人看到 ⇒ 「每一行都帶」的欄位反而沒人核對 |
| 備份 | 每晚 robocopy；09-05 部署撞備份視窗 678 筆 NOT_FOUND | `dist_next` 暫時目錄已請 CK_Website 排除、本 repo 入 gitignore |

## 4. 已在本輪做掉的（09-05～06）

| 項 | 效果 |
|---|---|
| 孿生儀表板：不打廢止註冊表、鏡像補參數、背景回填 | 冷 4,069→1,204ms（容器）；公網 4.5→0.47s；迴圈延遲 4,079→15ms |
| 請求日誌降噪 | 10 分鐘 1,243→119 行 |
| 費用頁帳本查詞條件化 | 每次少一支往返 |
| 棄用 router／孤兒頁／殘留 schema 刪除 | −1,150 行 |
| 日誌 version 欄改讀 build_info | 與 /health 同源 |
| 探針 `scripts/perf/route_cost_probe.cjs` | 冷／暖兩模式、口徑寫在檔頭 |

## 5. 建議排序（每項附「省多少、花多少、誰決定」）

| # | 建議 | 省 | 花 | 誰 |
|---|---|---|---|---|
| 1 | **平台 colo**（CF Pro/Argo 或 split-horizon） | 每支 API 0.4s ⇒ 整頁 2～4 秒 | 平台費用或架構 | AaaP／owner |
| 2 | **layout 級 9 支合併成 1～2 支**（A109） | 整頁載入 0.4×(4～7)s；與 #1 效益互相稀釋，不相加 | 認證鏈重塑，中 | 等 #1 定案後做 |
| 3 | **啟用 `pg_stat_statements`** | 讓 SQL 剖析有數字，現在是盲的 | postgres 一行設定＋重啟，零費用 | 本 repo，建議立即 |
| 4 | `files/storage-info` 1 秒 p95 | 單支破秒 | 查一下是否每次 `du`，加快取 | 本 repo，小 |
| 5 | weekly 加「async 路徑上的同步 I/O」靜態掃描 | 防 09-05 那型（一支卡全站） | 半天 | 本 repo |
| 6 | Repository 覆蓋 60%→ 只在動到某支 service 時順手補 | 可測性 | 零額外專案 | 規範已有，維持 |
| 7 | 限流／快取搬 Redis（A51） | 開第二 worker 的前置 | 中 | **現在不需要**：4k/日單進程夠；先記著 |
| 8 | ADR 歸檔配套「程式碼下線清單」 | 防死整合再活半年 | 流程 | CONVENTIONS（AaaP） |

刻意**不建議**的：拆微服務（4k 請求/日、單機、往返已是主成本，拆了只會多幾層往返）；前端全面重寫 bundle 策略（antd-core 1.29MB 是 AntD 的形狀，lazy 已做）。

## 6. 沒有量到的

- 真實使用者的端到端時間（沒有 RUM；lvrland 有 web-vitals 兩支，missive 沒接）。
- SQL 逐句（`pg_stat_statements` 未啟用）。
- 多使用者併發下的行為（今天所有量測都是單一探針）。
