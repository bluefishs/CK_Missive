# Reboot Pre-Flight Checklist — 2026-07-10（重啟後覆盤＋KG embedding ①止血）

> 本輪重點：重啟後整體架構×服務流程覆盤（全綠自癒）／KG embedding 覆蓋率單日侵蝕實測（81.6%→74.0%）／**①安全止血執行**（backfill 12071 embedded → 95.7%，零行為變化）／②connector 治本 owner 決定 defer（未改碼、未 rebuild）。

## 重啟後 live 複驗結果（本 session＝前次重啟後首次覆盤，全綠）

| 面向 | 實測 | 判定 |
|---|---|---|
| 容器 | 56 全 Up、**0 非健康**（missive 5＋hermes 3＋lvrland/pile/tunnel/sw/platform 全棧） | ✅ |
| 公網 | `missive.cksurvey.tw/api/health` **200 / 0.32s** | ✅ |
| 業務量 | `/health` docs **1910**、canonical_entities **46476→48550**、pool 15/14 idle、biz_ok true | ✅ |
| 整合鏈 | 5 鏈 E2E `all_ok:true`（03:00 cron） | ✅ |
| 每日巡檢 | 🟡 無紅燈（架構 39/9/0、能力全在用、學習閉環 flow 100%、AI baseline 60q avg 19s p95 48.8s 成功率 100%） | 🟡 |
| 自省 6 面向 | 全面 **GREEN**（ADR active 5/stale 0、SOP fail 0、L4x 0、pending proposals 0） | ✅ |
| cron | 近期事件全 success、晨報/巡檢/自省 07-10 皆產出 | ✅ |

## Pre-Flight 結果（本次重啟前，可安全重啟）

| 項 | 檢查 | 結果 |
|---|---|---|
| ① | git working tree | 僅 wiki runtime 產物＋remote_backup／GOVERNANCE 時戳；**無未提交程式碼變更**；origin 無 ahead（4 commits 全 push）✅ |
| ② | DB volume（L43 防呆） | `ck_missive_postgres_dev_data`（真實庫）✅ |
| ③ | 容器 restart policy | backend/postgres/redis/frontend=`always`、cloudflared=`unless-stopped` → 自動復原 ✅ |
| ④ | 業務量基線 | **docs 1910 / KG 48550 / biz_ok True**（重啟後須 ≥ 此值；KG 因 lvrland 聯邦持續貢獻而漲）|
| ⑤ | 前端部署 | dist（07-08 build）公網 200 ✅（本輪前端未改）|
| ⑥ | backend image | **本輪已 rebuild+force-recreate**（含 5 處 connector 治本），容器內 0 殘留 connector=None、baked 存活重啟；L76 host 200 + 公網 200 ✅ |
| ⑦ | 異地備份排程 | `CK-Missive-Offsite-Backup` State=Ready；每日 03:00 robocopy → NAS ✅ |
| ⑧ | L76 | host 8001 healthy + 公網 200 ✅ |

## 本輪處置：KG embedding ①止血（已執行）／②治本（defer）

**①安全止血（✅ 執行）**：`python scripts/sync/backfill_kg_embeddings_all.py --apply --all`
- 結果：**12071 embedded / 1 failed / 7.2 min**，覆蓋率 **74.0% → 95.7%**（48550 total / 46477 embedded）
- 各 type 近 100%（transaction 18800/18800、org 5204/5204、project 239/239、py_* 全滿）
- 直接 httpx 打 ollama、繞過 EmbeddingManager、**零行為變化**（不啟用語意合併），屬既有維持機制

**②connector 根治（✅ 已執行，commit `7101ee3c`）**：5 處 `connector=None → get_ai_connector()`
- cross_domain_contribution_service ×2、cross_domain_matcher、canonical_entity_resolver、canonical_entity_service
- **端到端驗證**：容器內 `backfill_embeddings(batch=50)` → `processed=50 embedded=50 skipped=0`（過去 embedded=0）
- regression `TestKGEmbeddingConnectorWiring` 2 案（source guard 防回退 connector=None）、22 passed；rebuild L76 通過
- **⚠️ 行為變化待觀察**：啟用 resolver/matcher 語意匹配/去重（ingest 時實體解析），需觀察 canonical entity 合併率是否異常
- 詳見 memory `kg_embedding_pipeline_silent_failure`；標準修法範例 `embedding_manager.py:310-311`

## 重啟後驗收 SOP（5 步）

1. **容器復原**：`docker ps` → 5 missive 容器 healthy（Docker 自動拉回，**勿 --force-recreate**）。ck-ollama GPU 起不來（NVIDIA hook 崩潰）→ `wsl --shutdown` 重啟 Docker 引擎（非 `docker restart`）。
2. **業務量**：`curl http://localhost:8001/health` → docs ≥ 1910 / KG ≥ 48550 / biz_ok true。
3. **公網（L76）**：`curl https://missive.cksurvey.tw/api/health` → 200。不通則 `docker restart ck_missive_backend`（Windows 殭屍埠轉發）。
4. **KG 覆蓋率**：`SELECT ROUND(100.0*COUNT(embedding)/COUNT(*),1) FROM canonical_entities;` → 止血後 ~95%；治本後 cron 04:30 起自動維持（非空轉）。若日後跌破 80% 且趨勢向下＝查 cron log 是否又 `embedded=0`（回歸）。
5. **KG embedding cron 治本驗證**：次日 04:30 後查 log——應見 `回填完成 processed>0 embedded>0`（非 207ms 空轉）。
6. **晨報主題合併**：次日 08:00 後查 backend log `Morning digest tail attached` + `Morning report pushed`（LINE 收單一則含「昨日主題摘要」尾段）。

## Git 狀態（重啟前，已全數 push origin）
```
9cc2e58f chore(checks): 新增 KG 實體合併率監測查詢
a6e07b94 docs(runbook): 07-10 重啟後覆盤＋pre-flight（含治本結果）
7101ee3c fix(ai): 根治 KG embedding connector=None 空轉（L79 第二層）
```
`main...origin/main` 無 ahead、無未提交程式碼變更（工作樹僅 wiki runtime 產物）✅

## 待 owner（非重啟阻斷）
- **⭐ KG embedding 治本行為觀察**：connector 治本啟用 resolver/matcher 語意匹配/去重，需觀察 canonical entity 合併率是否 over-merge。監測查詢 `scripts/checks/kg_merge_rate_monitor.sql`（`docker exec -i ck_missive_postgres psql -U ck_user -d ck_documents < ...`）；基線 2026-07-15：entities 48551 / new_semantic_aliases_24h **0** / alias_per_entity 0.4445 / 覆蓋率 95.8%。**治本後 3-5 工作日每日跑 Query A 對照**，首查點＝下一個有 ingest 活動工作日（純 backfill 不觸發語意路徑）。詳見 memory `kg_merge_rate_observation`。
- v6.24 遺留：facade 60 天 trial 2026-07-30 重評。
