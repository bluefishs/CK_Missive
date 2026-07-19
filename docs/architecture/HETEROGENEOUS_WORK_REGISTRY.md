# 異質同工登記表（Heterogeneous-Same-Work Registry）

> **建立日期**：2026-07-16
> **觸發**：整體架構覆盤揭發「兩大反覆回歸 bug 家族的結構根源＝異質同工」
> **精神延伸**：`.claude/rules/cross-file-ssot-governance.md` 把「單一**資源** SSOT」延伸到「單一**實作** SSOT」
> **強制等級**：中——新增異質同工前須登記；治本須 owner 授權 + 完整 regression + L76 驗證

---

## 為何需要這份登記表

「異質同工」＝**不同實作各自做同一件事**。它比單純重複更危險，因為：

1. 改一條路徑會漏另一條 → **修法永遠不完整**
2. 一條路徑休眠時另一條撐著 → **silent，直到兩條同時失效才暴雷**
3. 兩條邏輯漂移（重試/冷啟動/攔截器/模型選擇不一致）→ **邊角行為不可預測**

**本專案實證**：兩大反覆回歸家族的根源正是異質同工——

| Bug 家族 | 反覆次數 | 異質同工根源 |
|---|---|---|
| **SSO L74/L78** | 7 週 ~10 次「根治」 | 前端**兩個 axios 實例**各有攔截器/復原邏輯，改一漏一 |
| **KG embedding L79** | 三層 silent failure | Embedding **雙路徑**（cron 走 EmbeddingManager 休眠、手動腳本走直 httpx 撐著） |

→ **減少異質同工＝拔除反覆回歸的結構根源**（不只是清冗餘）。

---

## 登記表

> 狀態圖例：🔴 治本候選（正在製造 bug）｜🟡 列管 + audit 防增量｜🟢 觀察｜✅ 已收斂

| # | 異質同工項 | 實測（2026-07-16） | SSOT 決定 | 收斂計劃 | 對應 audit | 狀態 |
|---|---|---|---|---|---|---|
| H1 | **前端 HTTP client 雙實例** | `api/interceptors.ts`（主 client）+ `services/authService.ts:100`（779L auth 核心，自帶 req/resp 攔截器 + 401 處理） | ⚠️ **修正 SSOT 目標＝單一「攔截器邏輯」，非單一實例**——authService 獨立實例**部分刻意**（登入/refresh 須不觸發主 client 401→bridge→redirect，否則登入本身無限迴圈＝L74/L78 迴圈根源）；天真合併會復發迴圈 | 抽 CSRF/401 守衛/user_info 持久化為**共用 helper**，兩實例引用同一套邏輯（不漂移）；**非合併實例** | fitness step 66 `heterogeneous_work_audit`（watch，禁增第 3 實例）；step 64 auth_state_ssot | 🔴（需獨立設計 session） |
| H2 | **Embedding 直 httpx 繞過** | 核實後：公文路徑 `backfill_embeddings.py` 已走 `ai_connector.generate_embedding` ✅；KG cron 走 EmbeddingManager→connector ✅（07-15 修）；**真異質同工僅 2 支 host 緊急腳本**（`backfill_dispatch_embeddings.py`/`backfill_kg_embeddings_all.py`）直呼 `localhost:11434/api/embed` 繞過 SSOT | 容器內 `cross_domain_contribution_service.backfill_embeddings`（EmbeddingManager，含暖機閘門）為 SSOT | ✅ **已文件化處置（2026-07-16）**：2 host 腳本加 SSOT 指標 + 繞過警告頭；不重寫（host 緊急工具、07-10/07-15 止血賴以復原）；訂正 backfill_embeddings.py 過時「384維→768維」+ dispatch docstring 誤稱 ai_connector | 待補 `embedding_httpx_bypass_audit`（禁 scripts 新增直呼 /api/embed） | ✅ |
| H3 | **後端 stub 轉發檔** | 81 個 Wave 1-8 向後相容 stub（同服務兩條 import 路徑） | bounded context 子包為權威路徑 | 既定 2026-Q3 移除計劃 | 待補「禁新增 stub」audit（凍結增量） | 🟡 |
| H4 | **wiki frontmatter 連結腳本** | 核實後：`backfill_wiki_dispatch_kg.py`/`backfill_wiki_project_kg.py` 補 kg_entity_id（**非 embedding、非異質同工**，一次性遷移工具） | — | 遷移完成後可歸檔 scripts/archive/ | — | 🟢 |
| H5 | **compose 檔** | 5 個（dev/infra/infra.secrets/multichannel/production） | production 為公網權威 | 維持（已有 audit 防漂移） | step 38 volume / step 40 healthcheck | 🟡 |
| H6 | **圖譜元件** | `ForceGraphLazy` 統一 wrapper 存在，但 `GraphCanvas`/`KnowledgeGraph` 疑殘留舊實作 | `ForceGraphLazy` | 查殘留、可併則併（低優先，無 bug） | — | 🟢 |
| H7 | **Facade trial 層** | Memory 3 / Wiki 3 / Integration 4 caller（trial 閾值邊緣） | 7/30 重評決定 | 未達 ≥5 則升 C 全廢（天然去異質同工） | facade caller 計數 | 🟢 |

---

## 治本紀律（動核心路徑必守）

此專案為範本，須守穩定觀察期紀律（[[feedback_rigor_no_self_inflicted_instability]]）：

1. **不做一次性大重構**——H1/H2 各自獨立 session、分次進行
2. **完整 regression**——治本前先攤開受影響檔案清單 + regression 範圍
3. **L76 部署驗證**——backend 任何 rebuild/recreate 後必驗 host 200 + 公網 200
4. **帶殘留狀態的復原路徑必測**——happy-path 過 ≠ 治本（L78 教訓）
5. **收斂後補 audit**——防止異質同工重新長出來

---

## 程式圖譜自我優化（2026-07-17 立法 — 回應「圖譜為何不能自我追蹤異質同工」）

**背景**：owner 質疑「花那麼多時間建程式圖譜，難道不能自我優化與追蹤異質同工？」

**誠實診斷——為何過去沒自動發現**：
1. 程式圖譜一直當「結構地圖」用（L71），沒人對其 embedding 下**語意查詢**
2. fitness/audit 是 pattern/whitelist 型（L71「寫死清單漏網」），無法發現**未知**重複
3. 學習閉環（crystallizer）只優化對話路由，**無架構通道**
4. embedding 早就在（code entity 100% 覆蓋），差的只是「把語意去重查詢接成機制」

**已落地機制**：`scripts/checks/code_semantic_duplication_audit.py`（fitness **step 67**）
- 用 pgvector 餘弦相似度，自動找「跨模組、語意近乎相同」的函式對 → 聚合為鏡像模組對
- 一次查詢即 surface 真候選（證明圖譜**能**自我發現異質同工）
- 性質＝discovery：**自動撈 → 人/LLM triage → 登記表**（非全自動重構）

**能力邊界（誠實）**：圖譜能 surface 候選，但「真重複 vs 合理領域拆分」需判斷。

### 首跑候選（2026-07-17，待 owner triage）
| 鏡像模組對 | 共享近重複 | 初判 | 待辦 |
|---|---|---|---|
| `erp.expenses` ⇄ `erp.expenses_io` | 9 | 疑似刻意拆分（CRUD vs IO），但同名函式重疊需查 | triage |
| `role_permissions` ⇄ `role_permissions_admin` | 7 | 需查是否真重複 | triage |
| `tender` ⇄ `tender_module.analytics` | 6 | **假陽性＝stale orphan**（tender.py 已是 12L wrapper，圖譜殘留舊函式） | 見下 prune |
| `tender` ⇄ `tender_module.subscriptions` | 5 | 同上 stale orphan | 見下 prune |
| `erp.expenses` ⇄ `erp.operational` | 4 | 需查（expense CRUD 泛化） | triage |

### 🔴 meta 發現：程式圖譜累積 stale orphan（阻礙自我優化的真因）
`tender.py` 現為 12L wrapper（v5.5.2 已拆到 tender_module/），但程式圖譜（07-15 才更新）**仍存 `tender::analytics_dashboard` 等舊函式 entity** → **增量 ingest 只新增/更新、不修剪已刪除符號** → 累積 orphan → 污染語意去重（tender 候選即假陽性）。

**已建 DRY-RUN 偵測器**：`scripts/checks/code_graph_orphan_audit.py`（fitness **step 68**，只報不刪）
- ground truth 對照：entity 宣稱的 symbol 是否還定義在其 file_path 檔中（**非**靠 last_seen_at）
- ⚠️ **為何不能靠 last_seen_at**：incremental ingest 只更新重解析的檔，未變更檔的**存活** entity 也是舊 last_seen_at（最新僅到 07-10，但 cron 07-15/16 有跑）→ 照 last_seen_at 剪會**誤刪存活**
- **首跑（2026-07-17）：2032 orphan（Python，17%）**——1062 file-missing（檔搬移）+ 970 symbol-absent
- **主因＝Wave 1-8 DDD 遷移搬檔舊路徑未修剪**：`base_ai_service`→`ai/core/`、`ts_extractor`→`ai/graph/`、`morning_report_service`→`ai/domain/`、`tender_search_service`→`tender/`（symbol 仍在、只是新路徑，舊 entity 成 orphan＝與新路徑 entity 並存的異質同工源頭）
- ⚠️ **偵測踩坑（元教訓）**：初版對 method（`Class.method`）誤判 → 5055 假陽性；修為取最後點分量後 2032（正確）

**安全 prune 設計（下一步，需 owner 授權）**：
1. **soft-delete 優先**：set `valid_to=now()`（非硬刪），保留可回溯；驗證無誤數週後再硬刪
2. **雙重確認再剪**：orphan 且「該 symbol 不在專案任何檔」才剪（防搬移誤剪——搬移者 symbol 仍在別處，應**重指路徑**而非刪）
3. **grace period**：連 2 次偵測皆 orphan 才動（防單次 ingest 異常）
4. **根治**：`code_graph_ingest` 加 full-sweep mark-and-sweep（全掃後標本輪未見者），使 last_seen_at 可信 → 未來 prune 可自動化
- 屬 pipeline + 資料變更、中風險，**須獨立 session + soft-delete + 完整驗證**（[[feedback_rigor_no_self_inflicted_instability]]）

## 收斂進度日誌

| 日期 | 項 | 動作 | 結果 |
|---|---|---|---|
| 2026-07-16 | — | 建立登記表（藍圖） | 7 項列管 |
| 2026-07-16 | H2 | 核實 5 腳本真實用途（元教訓：逐一核實不假設）→ 範圍大幅縮小；2 host 緊急腳本加 SSOT 指標頭、訂正 2 處誤導 docstring | ✅ 收斂（文件化，零 runtime 風險）；**避開了「重寫 live pipeline」的過度工程** |
| 2026-07-16 | H4 | 核實 wiki backfill 非 embedding（誤列）→ 移出異質同工、降為一次性遷移工具 | ✅ 校正 |
| 2026-07-16 | 防增量 | 新增 `heterogeneous_work_audit.py`（fitness step 66）watch H1/H2/H3 baseline，成長即 RED；strict exit 0 | ✅ 交付 |
| 2026-07-16 | H1 | 影響評估揭發「獨立實例部分刻意」（防登入迴圈）→ 修正 SSOT 目標為「單一攔截器邏輯」而非合併實例；**不在覆盤 session 倉促動 SSO**（守 feedback_rigor） | ⏸ 待獨立設計 session |
| 2026-07-17 | 自我優化 | 回應「圖譜為何不能自我追蹤」→ 建 `code_semantic_duplication_audit.py`（step 67）；實測一次查詢 surface 5 候選（證圖譜**能**自我發現）；揭發 meta 真因＝圖譜累積 stale orphan（無 prune） | ✅ 機制交付 + 5 候選待 triage + prune 建議 |
| 2026-07-17 | prune 前置 | 建 `code_graph_orphan_audit.py`（step 68，DRY-RUN 只報不刪）；ground truth 對照 source；首跑 2032 orphan（主因 Wave 1-8 搬檔）；元教訓修 method 假陽性 5055→2032；出安全 prune 設計 | ✅ 偵測器交付（不刪）；prune 待 owner 授權（獨立 session） |
| 2026-07-17 | prune 執行（owner 選 A） | `code_graph_orphan_prune.py` 剪**最保守子集 62 筆**（真刪除＝symbol 全專案不存在，如 NemoClawAgent 改名、morning_report 重構方法）；6/6 抽驗確認真消失；CSV 備份 + 今晨全庫雙保險；cascade 全 0（孤立 orphan）；**11779→11717**、orphan **2032→1970**、系統 200/business ok | ✅ 保守批完成 |
| 2026-07-17 | prune 剩餘 | 1970 為**搬移型**（symbol 在新路徑，如 tender::analytics→tender_module/）——非刪除、需**重指路徑或根治全掃**；tender 語意候選仍在（屬此批） | ✅ 根治全掃處理（見下） |
| 2026-07-17 | 根治全掃（owner 選 A） | `code_graph_reconcile.py` mark-and-sweep：安全閘救場（揭發 ts_* 容器無源→改僅 Python）；**12253→10012 sweep 2241**；orphan **1970→0**、語意 **5→2**（tender 假陽性消）；+`scheduler.py` 遞迴 job 每週日 03:15、rebuild L76 通過 | ✅ 圖譜乾淨 + 自動維護上線 |

**✅ 根治全掃已執行（2026-07-17，owner 選 A）**：`scripts/sync/code_graph_reconcile.py`（容器內跑）
- 機制＝mark-and-sweep：記 sweep_start → 全掃 ingest（`incremental=False`，stamp 現存 symbol last_seen_at、**保留 embedding**）→ sweep 掉 last_seen_at < sweep_start 的 Python entity。
- **安全閘救場**：首版全掃只 stamp 7655（< 9000）ABORT——揭發 **backend 容器無 frontend/src → ts_* 前端 entity（2294）無法 stamp、會被誤判 stale**。修為**僅 Python 型 sweep**（容器有 backend 源）。
- 全掃已建正確新路徑 entity（tender_module.analytics::analytics_dashboard 等 stamp 今日），舊路徑成 stale（last_seen_at=3-4 月 Wave 期）→ 刪之安全。
- **結果：12253→10012（sweep 2241 Python stale）**；ts_ 2294 完好、系統 200、embedding 95.3%（新路徑待 cron backfill）。
- **驗證：orphan audit 1970→0、語意去重 5→2 候選**（tender stale 假陽性全消，剩 role_permissions/expenses 真候選待 triage）。備份 CSV `backups/code_graph_prune/reconcile_stale_20260717.csv` + 今晨全庫雙保險。

**✅ 遞迴自動維護（root fix，已上線）**：`scheduler.py` 加 `code_graph_reconcile_job`（**每週日 03:15**，@tracked_job 觀測 swept 數）
- 含同一安全閘（Python stamp < 3500 ABORT）；rebuild L76 通過（host+公網 200）、啟動 log 確認 job 註冊。
- → **圖譜未來自動保持乾淨**，orphan 不再累積。**程式圖譜「自我優化」閉環站穩。**

**已知限制（誠實）**：ts_* 前端 entity 的 reconcile 需 frontend 源可見環境（backend 容器無）→ 前端 orphan 待另建 host-run 或前端可見的 reconcile（本輪未做，前端 orphan 目前不阻礙語意去重主用途）。

| 2026-07-17 | 語意候選 triage | 剪乾淨後剩 3 候選逐一核實：①`role_permissions`⇄`role_permissions_admin`＝**真異質同工**（見下）②`expenses`⇄`expenses_io`＝合理拆分（CRUD vs IO，函式名全不同）③`expenses`⇄`operational`＝合理拆分（不同 model）→ ②③加白名單 | ✅ 候選降至 1 真 |
| 2026-07-17 | LLM 閉環驗證 | 實際呼叫 app LLM（gemma4/planning）triage role_permissions → 回 `TRUE_DUPLICATE conf=0.9`，與人工核實一致 → **證「發現→LLM 判定→決策」閉環可運作** | ✅ 自我檢核閉環證實 |

## 真候選 C1：role_permissions ⇄ role_permissions_admin（待 owner 定奪收斂）
**核實（前後端服務正確性）**：
- `role_permissions_admin.py`（`/admin/role-permissions/*`）＝**活躍**：list/get/update/available 4 端點皆被 `rolePermissionsApi.ts` 呼叫。
- `role_permissions.py`（`/admin/user-management/*`）＝**大部分死碼**：`roles/{role}/permissions/detail`、`.../update`、`roles/list` **三端點前端 0 + 後端 0 + 測試 0 呼叫**；僅 `permissions/available` 仍被 `adminUsersApi.ts` 用。
- 人工 + LLM 雙重判定＝真重複（兩套平行 role 權限管理 API）。
**收斂方案（⚠️ 屬 auth 破壞性變更，依 feedback_rigor 待 owner 明確授權）**：
- 保守：移除 3 個 verified-dead 端點（+對應前端死常數 ROLE_PERMISSIONS_DETAIL/UPDATE/ROLES_LIST +測試）→ 降 auth 攻擊面、消異質同工；`permissions/available` 保留（live）。影響：backend rebuild + frontend build + 1 測試更新。
- 徹底：再把 adminUsersApi 的 `permissions/available` 遷到 admin 端點，整檔退役 `role_permissions.py`（行為變化，風險較高）。

## 程式圖譜自我優化的「真自我成長」現況（回應 owner 提問）
**閉環三步的自動化程度（誠實）**：
| 步 | 機制 | 自動化 |
|---|---|---|
| 發現 | fitness step 67/68（語意去重 + orphan） | ✅ 全自動（每次 fitness） |
| **orphan 修復** | `code_graph_reconcile_job` 每週日 03:15 | ✅ **全自動自我修復**（無需人） |
| 重複判定 | LLM triage（已驗可運作）+ 人工 | 🟡 半自動（**刻意 gate**：C2/C3 證自動合併會破壞合理拆分） |
| 重複收斂 | 移除死碼/重指 | 🔴 人審 gate（auth 等破壞性須授權） |
| 學習 | LEGIT_SPLIT_WHITELIST 每次 triage 永久記錄 → detector 漸靜、漸準 | ✅ 自動累積 |
**結論**：orphan 面＝**真自我修復閉環**（每週自動清、已上線）；重複面＝**自我檢核 + 判定可自動（LLM 已證）+ 收斂人審**（安全設計，非缺陷——語意相似≠重複，C2/C3 為證）。

### ✅ LLM-triage 自動判定 job 已上線（2026-07-17，Part B）
`scheduler.py` `code_dup_triage_job`（**每月 1 號 04:00**，@tracked_job）——閉合迴圈：
1. pgvector 撈鏡像模組對候選（sim>0.95、共享≥4）→ 排除 LEGIT 白名單
2. 每個新候選呼叫 app LLM（planning/gemma4）判定 TRUE_DUPLICATE vs LEGIT_SPLIT + 信心 + 理由
3. verdict 寫 `backend/logs/code_dup_triage.jsonl`（持久）；TRUE_DUPLICATE 額外 LOUD log 提報 owner（收斂動作人審 gate）
- **端到端實證**：手動觸發 → 撈 1 候選（expenses 白名單正確排除）→ LLM 判 role_permissions=TRUE_DUPLICATE conf=0.9 → log + warning；detail `{candidates:1, true_duplicates:1}`。
- rebuild L76 通過、job 註冊確認。

### 🎯 完整閉環端到端自我修正（實證）
C1 收斂全流程證明迴圈閉合：**偵測**（step 67 撈 role_permissions）→ **LLM 判定**（TRUE_DUPLICATE）→ **收斂**（owner 授權移除 3 死端點）→ **reconcile**（清 6 個 stale KG entity）→ **偵測器轉 GREEN**（自我修正、不再誤標）。orphan audit 0、語意 audit GREEN。
→ **「真自我檢核與成長」落地**：自動偵測 + 自動判定 + 自動清理（orphan/reconcile）+ 收斂人審 gate（安全）+ 白名單學習（漸靜漸準）。

| 2026-07-17 | admin 選單檢視 | Explore agent 掃 12 admin 選單前後端 + 人工核實：**D1/D2 死常數收斂**（SYSTEM STATUS/METRICS 指向不存在路徑）+ **C4 刪逾期 deprecated site_management.py**（`4fff666d`，rebuild L76）；其餘見下 owner 待決 | ✅ 2 安全項收斂 |

## admin/site-management 選單異質同工檢視（2026-07-17，Explore + 人工核實）
| # | 發現 | 核實 | 處置 |
|---|---|---|---|
| C2 | 「可用權限」三份漂移（role_permissions.py 硬編 / role_permissions_admin DB SSOT / 前端 constants）+ 前端檢查 operational:write/approve 卻未宣告 | 真異質同工，實測 DB 缺 operational:*、非超集 | ✅ **已遷移（`084c0834`）**：_BUSINESS_PERMISSIONS 補 operational:*→all 33→36 超集；role_permissions.py 委派 DB SSOT；前端 constants 補 operational→三方一致 |
| C3 | users.py（/users，Staff）vs user_management.py（/admin/user-management，Admin）雙套 user CRUD | **核實：不是重複——已共用 UserRepository（資料層統一）；端點層是不同網域的不同建立語意**（Staff role=專案PM 無 permissions 預設 vs Admin role=user 有 permissions/auth_provider 預設） | ✅ **驗證＝合理網域分離、不強收斂**（強收斂會破壞網域專屬 user 建立語意＝有害過度工程，元教訓） |
| C4 | site_management.py deprecated 逾期 | 已核實 helper 自足、前端 0 呼叫 | ✅ 已刪（`4fff666d`） |
| C5/G3+G1 | 「系統監控」(/system) redirect 到 dashboard；system_monitoring 後端 9 端點僅 1 有前端入口 | 導覽語意不符 + 後端能力無入口 | ✅ **已補（`f863ee6f`）**：新 SystemMonitoringPage（系統指標/健康/錯誤/日誌 4 tab）消費 5 端點；/system 改指新頁 |
| D1/D2 | SYSTEM STATUS/METRICS 死常數指向不存在路徑 | 確認死碼 | ✅ 已移除（`4fff666d`） |
| D3/D4/D5 | database/health、backup/config、backup/status 前端半接通（常數有、頁面改用他常數） | 後端活、前端僅測試引用 | 🟢 低優先（後端活無害，可擇期清常數） |
| G1 | 系統監控後端 9 端點僅 1（review-dashboard）被前端消費，8 個無入口 | 後端有功能前端無入口 | ✅ **已補頁**（併 C5/G3，`f863ee6f`）：SystemMonitoringPage 接 5 端點 |
| G2 | security/scans/create 後端孤兒（前端無常數） | 後端有前端無 | 🟢 低優先 |
| G4 | Google 認證診斷純前端頁無後端 | by-design 客戶端工具 | ✅ 非缺陷 |
| G5 | ROUTE_META 缺 7 admin 路由元資料 | cosmetic（breadcrumb/title） | 🟢 低優先 |

**元教訓再證**：Explore agent 產出經人工核實——D1/D2/C4 確為真（已收斂）；C2/C3/G1 需 owner 決策（auth SSOT / 網域收斂 / 產品方向），不擅自動。

## 程式圖譜↔資料庫圖譜 schema 反射異質同工（2026-07-20，`0386f7c1`）

owner 提問「程式圖譜對應資料庫圖譜應可進一步整合強化 是否也有類似異質同工架構與設計」→ **確證有**。

| 項 | 發現 | 核實 | 處置 |
|---|---|---|---|
| DB schema 反射 | code_graph ingest 每次反射 DB schema **兩次**：①`code_graph_ast_analyzer.SchemaReflector` 自建 sync Inspector（產 db_table 實體）②`schema_reflector.SchemaReflectorService`（`_ingest_fk_relations` 用，cached）| 兩套 SQLAlchemy Inspector 讀同一 PostgreSQL、FK 亦雙重計算（reflect_tables 產 `references_table` 但 DB 只留 `_ingest_fk` 的 `references`＝前者實質浪費）| ✅ **已整合單一反射源 SSOT**：新純建構器 `build_table_entities_from_schema(schema)` 從 SchemaReflectorService dict 建 db_table 實體（description 保真）；兩 ingest 路徑改走它；FK 交由 `_ingest_fk_relations` 單一源；舊 reflect_tables 標 DEPRECATED |

**驗證**：TDD 4+回歸 8（12/12）；新舊建構器對同一 live DB 皆 77 tables/零差異/documents description 完全一致；live full ingest tables=77/fk=85/errors=0/4.26s、DB db_table 63→78·FK 74→85（統一源反射更完整）；rebuild L76 過。

**SchemaReflectorService 成單一 DB-schema SSOT**（consumer：graph_entity/graph_unified/system_monitoring/db_graph_refresh cron/code graph db_table 實體）。

## 程式圖譜↔資料庫圖譜 整合強化：model→db_table 橋 + 治本每日洗關係 bug（2026-07-20，`a2a00fc8`）

承上「消除異質同工」後，owner「應可進一步整合**強化**」→ 發現 code 與 DB 為**兩座孤島**（0 code→table 連結）+ 揭發**重大靜默降級 bug**。

### ① 橋接兩圖（整合強化）
- **缺口**：78 個 db_table 只有 db_table→db_table（FK），**0 個 code→table 連結** → 「哪些程式碼碰 documents 表」圖譜無法回答。
- **修**：純函式 `extract_tablename(ClassDef)` 從 ORM model `__tablename__` 確定性建 `py_class→db_table maps_to` edge（Pydantic 無 __tablename__＝自我 gate、非幻覺）；`_extract_class` 注入；註冊 relation_type。**72 maps_to、70/78 表獲 code 連結**。documents←OfficialDocument 可經圖譜查。

### ② 🔴 治本重大靜默降級 bug（揭發於整合驗證，圖譜低價值隱因）
- **bug**：`incremental=True` 每次 `_recreate_relations` **無條件全刪** code_graph 關係、只重插「本次變更檔」的關係 → 未變更檔跳過 → 關係圖每日塌成僅 FK（**9669→85**）。
- **每日 03:00 `code_graph_incremental_job` 洗、僅週日 reconcile 還原 → 一週 6 天圖譜殘缺**。
- **第二層**：兩 scheduled job 皆未傳 db_url → db_table 從不刷新、maps_to 從不由 cron 生成（L79 半接通：存在硬碟不存在系統）。
- **修**：daily job 改 `incremental=False` 全量重建（6.1s 可接受）+ 傳 db_url；reconcile 補 db_url；`incremental=True` 加 LOUD warning（現無 job 用，防未來誤用）。
- **驗證**：daily job live 9670 關係（不再塌）+ maps_to 72 + 6.1s 冪等；TDD 8+回歸 8（16/16）；rebuild L76。

**元教訓**：整合驗證（實測 incremental 前後關係數）揭發了肉眼看不到的每日靜默摧毀——與「沉默成功」同族（job 報 success 但產物被自己洗掉）。「花時間建圖譜卻低價值」的真因之一在此。

## 系統管理模組架構複查 + 標準化/異質同工收斂（2026-07-20，`e5977ef8`）

owner「複查系統管理模組(admin/knowledge-base 等)架構標準化與縱橫向整合及維護更新」→ 完整盤點 ~16 admin 路由,發現三類問題,owner 授權三項全辦。

### 複查發現
| 類 | 發現 | 判定 |
|---|---|---|
| 標準化 | `security.py`/`system_monitoring.py`/`scheduler_events.py` 端點內直接 SQL/psutil/讀檔,繞過 service/repository DDD;`knowledge_base.py` tree/adr/diagrams 半邊直讀檔 | ❌ 治理端點標準化盲區(業務端點已 DDD＝雙標準) |
| 異質同工 | ①兩套 health-detailed(`health.py` DDD vs `system_monitoring.py` 自組)②`WikiGraphTab` 同掛 KnowledgeBasePage+WikiPage | ❌/⚠️ |
| 維護 | KB `scan_and_embed` delete-then-reinsert 無 embedding 守衛;`kb_coverage_check_job` 名為 kb 實測 OfficialDocument(命名混淆) | 🟡 |
| 導覽 | `/admin/case-nature` 頁面存在但**無側邊欄入口**(真孤立) | ❌ |

### 已辦第一批（`e5977ef8`）
- **① KB 安全守衛**：`scan_and_embed` embedding 不可用時跳過破壞性全重建(防用空向量覆蓋既有＝KG 冷啟動 silent 同族);校正 `kb_coverage_check_job` 命名(實測 OfficialDocument 非 kb_chunks,kb_chunks 實 2343/2343=100% 健康)——**元教訓:原擬自癒錯接目標,實測揭發後訂正為監測**
- **② health-detailed 收斂**：`system_monitoring` POST /health-detailed 委派 canonical SystemHealthService(消除重複 psutil/SQL、修 uptime placeholder),保留 error_summary;前端僅依賴 status→契約不破
- **③ scheduler_events DDD**：讀 jsonl+聚合抽至 `SchedulerEventsService`(system/ context),端點薄委派;TDD aggregate_stats 3 passed;live 46099 events/52 jobs
- 驗證:rebuild L76 host+公網 200

### 待續辦（較大重構/需 owner 決策，聚焦續辦）
- `security.py`(447L CRUD+OWASP)→ SecurityRepository+Service 抽取
- `system_monitoring.py`(9 端點)其餘 8 端點 psutil/log_manager/inline SQL 抽 service
- `WikiGraphTab` 雙掛載去重(低價值,frontend build)
- `/admin/case-nature` 補側邊欄(需寫 live nav DB＝init_navigation live 污染教訓,產品決策待 owner)

### 已辦第二批（治理端點抽 service 層全完成，2026-07-20 /loop）
4 個治理端點標準化收斂，邏輯下沉 `services/system/` bounded context（行為保真 + TDD）：
| 端點 | 前→後行數 | 抽出 | commit |
|---|---|---|---|
| `scheduler_events.py` | 207→84L | `SchedulerEventsService`(讀 jsonl+聚合) | `e5977ef8` |
| `security.py` | 447→182L | `SecurityRepository`+`SecurityAdminService`;**統一 score SSOT**(原 3 套漂移公式) | `343f92f9` |
| `system_monitoring.py` | 410→148L | `SystemMonitoringService`;**順修 code_graph 恆0 bug**(entity_type code_module→py_module=834) | `6fa70660` |
| `knowledge_base.py` | 434→197L | `KnowledgeBaseService`(檔案系統瀏覽/解析/搜尋) | `8eb2b557` |

**最終複查**：4 端點零真實 endpoint-direct SQL/psutil/檔案邏輯（殘留掃描全假陽性=註解/範例字串）;TDD 8 passed;每批 rebuild L76 host+公網 200。**治理端點標準化盲區消除**（與業務端點對齊 DDD）。

### 待 owner 決策/低優先（本輪未動）
- `WikiGraphTab` 雙掛載去重（frontend build，低價值）
- `/admin/case-nature` 補側邊欄（需寫 live nav DB＝init_navigation 污染教訓，是否上側邊欄屬產品決策）

（後續收斂逐項追加）
