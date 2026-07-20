# Reboot Pre-Flight Checklist — 2026-07-20（系統管理×平臺資訊×業務模組 整合優化程序）

> 本輪重點：**三輪架構複查與標準化收斂**——①治理端點抽 service 層（4 端點：scheduler_events/security/system_monitoring/knowledge_base 全標準化）②平臺資訊群組清理（隱藏 2 dev/demo 頁）③業務模組審計（HH-1 派工文號非確定性 bug 治本、HH-3 財務聚合搬遷、低風險 schema 標準化）④程式圖譜↔資料庫圖譜整合強化（schema 反射 SSOT + model→db_table maps_to 橋 + 治本每日洗關係圖 bug）⑤owner 回報 3 組 bug 修復（建案 409 訊息、帳本 400、發票/帳本金額字串串接）。18 commits 全 push、多次 backend rebuild+frontend build 皆 L76 host/公網 200。

## Pre-Flight 結果（本次重啟前，可安全重啟）

| 項 | 檢查 | 結果 |
|---|---|---|
| ① | git working tree | **無未提交程式碼**（工作樹僅 wiki runtime 產物＋remote_backup/GOVERNANCE 時戳＋非本專案工具 config `.agents`/`.codex`/`AGENTS.md`）；origin 無 ahead（18 commits 全 push）✅ |
| ② | DB volume（L43 防呆） | `ck_missive_postgres_dev_data`（真實庫，非空殼 `_data`）✅ |
| ③ | 容器 restart policy | backend/postgres/redis/frontend=`always`、cloudflared=`unless-stopped` → 自動復原 ✅ |
| ④ | 業務量基線 | **docs 1944 / KG 47425 / biz_ok True**（重啟後須 ≥ 此值）|
| ⑤ | 前端部署 | dist（07-20 11:02 build，含發票/帳本金額串接修）公網 200 ✅ |
| ⑥ | backend image | **本輪多次 rebuild+force-recreate**（治理 service 抽取×4、HH-1/HH-3 收斂、ledger schema 修、409 dedup），baked 存活重啟；L76 host 200 + 公網 200 ✅ |
| ⑦ | 異地備份排程 | `CK-Missive-Offsite-Backup` State=Ready；每日 03:00 robocopy → NAS ✅ |
| ⑧ | 容器 | 55 全 Up、**0 非健康/exited** ✅ |
| ⑨ | 回歸測試 | 治理端點 service 抽取 unit 16 passed（scheduler_events/security/schema_reflector）✅ |
| ⑩ | L76 | host 8001 healthy + 公網 200 ✅ |

## 本輪主要變更（重啟後行為）

**A. 治理端點標準化（DDD，行為保真）**：4 端點邏輯下沉 `services/system/`——scheduler_events→SchedulerEventsService、security→SecurityRepository+SecurityAdminService（統一 score SSOT）、system_monitoring→SystemMonitoringService（順修 review-dashboard code_graph 恆 0 bug：code_module→py_module）、knowledge_base→KnowledgeBaseService。**行為不變**，僅標準化。

**B. 程式圖譜整合強化（每日自維護）**：
- **schema 反射單一源 SSOT**：消除 2 套 SchemaReflector Inspector。
- **model→db_table maps_to 橋**：ORM `__tablename__` 建 py_class→db_table edge（72 條）。
- **⚠️ 治本每日洗關係圖 bug**：`code_graph_incremental_job` 原 incremental=True 每日 03:00 把關係圖洗成僅 FK（9669→85）→ 改 **incremental=False 全量重建 + db_url**。**重啟後次日 03:00 應見關係數維持 ~9670（非塌成 85）**。
- **db_row_count watchdog**：producer registry 新增「程式圖譜關係」min 5000 監測（塌陷即 RED）。

**C. HH-1 派工文號非確定性 bug 治本（顯示變更）**：`get_document_dispatch_links` 端點原用 link `LIMIT 1 無 ORDER BY` → 117 筆多 link 派工單顯示**隨機文號**。改委派 TaoyuanLinkService 用**確定性 canonical 衍生**（FK 主要公文優先、null 則最早 link）。**⚠️ 多 link 派工單顯示的機關/乾坤文號會改為「主要公文」（語意正確），owner 可於函文紀錄 Tab 複覽**。

**D. owner 回報 bug 修復**：
- 建案 409：前端顯示真實訊息「此標案已建案: CK2026_PM_01_005」（原吞成通用「建案失敗」）+ 後端 dedup 防空 job_number 誤判/多筆崩潰。
- 帳本 400：`LedgerResponse` amount 覆寫 ge=0（原繼承 create 的 gt=0 → 讀 0 元分錄整列 400）。
- 金額字串串接（4 處掃全）：發票彙總/帳本收支/電子發票待核銷加總補 `Number(i.amount)`（原 JS 字串串接→NaN「非數值」）。

## 重啟後驗收 SOP

1. **容器復原**：`docker ps` → 5 missive 容器 healthy（Docker 自動拉回，**勿 --force-recreate**）。ck-ollama GPU 起不來（NVIDIA hook 崩潰）→ `wsl --shutdown` 重啟 Docker 引擎（非 `docker restart`）。
2. **業務量**：`docker exec ck_missive_backend curl -s http://localhost:8001/health` → docs ≥ 1944 / KG ≥ 47425 / biz_ok true。
3. **公網（L76）**：`curl https://missive.cksurvey.tw/api/health` → 200。不通則 `docker restart ck_missive_backend`（Windows 殭屍埠轉發）。
4. **ERP 修復複驗**：帳本頁（/erp/ledger）正常載入（非 400）、發票彙總（/erp/invoices/summary-view）銷項/進項/淨額顯示**正確數字**（非「0222048…」串接、非「非數值」）。
5. **程式圖譜關係（次日 03:00 後）**：`SELECT COUNT(*) FROM entity_relationships WHERE relation_label='code_graph';` → **應 ~9670（非 85）**。若塌成 85＝每日 job 又走 incremental（回歸），查 scheduler。
6. **HH-1 複覽**：任一多 link 派工單的函文紀錄，機關/乾坤文號應為「主要公文」且每次一致。

## 待 owner（非重啟阻斷）
- **HH-1 顯示語意複覽**：多 link 派工單文號改顯示「主要公文」（FK），若業務上期望顯示「最新往來函」請告知（可調 fallback 排序）。
- 業務模組低優先 backlog：同檔 link mutation/其他 link 端點直 SQL（無 bug）、圖譜 2 套渲染元件統一、PM 匯出入 xlsx blob（半正當）。
- facade 60 天 trial 2026-07-30 重評；KG 語意匹配 merge-rate 續觀察。
