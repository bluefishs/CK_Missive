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

（後續收斂逐項追加）
