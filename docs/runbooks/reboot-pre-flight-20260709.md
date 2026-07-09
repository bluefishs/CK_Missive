# Reboot Pre-Flight Checklist — 2026-07-09（v6.24+）

> 本輪重點：LINE 主題合併晨報驗收真活／KG embedding `await is_available()` silent bug 掃全同型根治（5 處）／connector=None 第二層 hand-off（重啟後 P1）。

## Pre-Flight 結果（重啟前，全通過）

| 項 | 檢查 | 結果 |
|---|---|---|
| ① | git working tree | **clean**（僅 wiki runtime 產物＋remote_backup 時戳）；origin **無 ahead**（全 push）✅ |
| ② | DB volume（L43 防呆） | `ck_missive_postgres_dev_data`（真實庫，非空殼）✅ |
| ③ | 容器 restart policy | backend/postgres/redis/frontend=`always`、cloudflared=`unless-stopped` → 重啟自動復原 ✅ |
| ④ | 業務量基線 | **docs 1909 / KG 46141 / biz_ok True**（重啟後須 ≥ 此值；KG 因 lvrland 聯邦持續貢獻而漲）|
| ⑤ | 前端部署 | dist `index-6su_9un9.js`（07-08 build，含派工 invalidate SSOT 修）公網 200 ✅（本輪前端未改）|
| ⑥ | backend image | 已 rebuild+force-recreate（含 5 處 await 修），容器內 0 殘留 await、baked 存活重啟 ✅ |
| ⑦ | 異地備份排程 | `CK-Missive-Offsite-Backup` State=Ready；每日 03:00 robocopy → NAS ✅ |
| ⑧ | L76 | host 8001 healthy + 公網 200（0.66s）✅ |

## 本輪 commits（本地→origin 已同步）
```
afa0eebe docs: v6.24+ 里程碑（07-09 晨報驗收＋await 掃全＋connector P1）
ae7c74d6 fix(ai): 修 5 處 await EmbeddingManager.is_available() silent bug（L79）
4e5e8797 fix(governance): wiki-kg link audit 誠實化（彙總頁不入分母）
c16319e0 fix(scheduler): kg embedding batch 200→2000（訂正：非真根因）
b5588517 fix(frontend): useDeleteDocument 派工 invalidate 走 SSOT
9151642f feat(governance): fitness step 65 收尾完整性審計＋L79
05bdeddf feat(integration): 推播主題合併至晨報＋LINE 月度軟上限
```

## ⚠️ 重啟後 P1（owner 有空時執行，非重啟阻斷）

**KG embedding connector=None 第二層**（詳見 memory `kg_embedding_pipeline_silent_failure`）：
await 已修（cron 不再 crash），但 `get_embeddings_batch(connector=None)` 回空 → `embedded 仍=0`。修法明確（5 處 `connector=None` → `connector=get_ai_connector()`，同檔 `embedding_manager.py:310` 有範例），但會**啟用語意匹配/去重**（行為變化需觀察），故 defer。步驟：①5 處補 connector ②rebuild L76 ③手動觸發 backfill 驗 embedded>0 ④觀察 canonical entity 合併行為 ⑤手動 `backfill_kg_embeddings_all.py` 清 ~9000 存量 ⑥複驗覆蓋率。覆蓋率現 81.6% GREEN、不阻斷重啟。

## 重啟後驗收 SOP（5 步）

1. **容器復原**：`docker ps` → 5 missive 容器 healthy（Docker 自動拉回，**勿 --force-recreate**）。ck-ollama GPU 起不來（NVIDIA hook 崩潰）→ `wsl --shutdown` 重啟 Docker 引擎（非 `docker restart`）。
2. **業務量**：`curl http://localhost:8001/health` → docs ≥ 1909 / KG ≥ 46141 / biz_ok true。
3. **公網（L76）**：`curl https://missive.cksurvey.tw/api/health` → 200。不通則 `docker restart ck_missive_backend`（Windows 殭屍埠轉發）。
4. **晨報主題合併**：次日 08:00 後查 backend log `Morning digest tail attached` + `Morning report pushed`（LINE 收單一則含「昨日主題摘要」尾段）。
5. **KG embedding cron**：次日 04:30 後查 log——若見 `KG Embedding 回填早退（未執行）: reason=...` warning ＝ connector P1 尚未修（預期）；修 P1 後應見 `回填完成 processed>0`。
