# 災難還原 Runbook —— D 槽壞掉的時候該怎麼辦

> 建立：2026-08-10（owner 問「確認 NAS 有完整備份」，查證後發現答案是「沒有」而寫）
> 上次完整還原測試：**2026-08-10**（發現 2 個缺陷，皆已修，見 §4）
> 下次應演練：2026-09-10（月度）

---

## 0. 先看這一句

**「有 DB dump」離「能完整還原」還有距離。** 還原一套能跑的系統需要四類東西，
缺任何一類的後果都不是「少一點資料」，而是整套起不來或悄悄壞掉：

| 類別 | 在哪裡 | 沒有它會怎樣 |
|---|---|---|
| 程式碼 | GitHub `origin/main` | 什麼都做不了 |
| 資料庫 | NAS `missive_databsae/` 30 份 | 公文、案件、圖譜全失 |
| **公文附件** | NAS `missive_attachments/` | DB 還原得回來，然後得到 1441 筆**指向不存在檔案**的紀錄 |
| **金鑰與憑證** | NAS `missive_secrets/secrets_*.enc`（加密） | 資料全在但系統起不來；Groq/NVIDIA/LINE/Google/CF 金鑰要逐一重新申請 |

2026-08-10 之前，**後兩類一份都沒有**。附件的本機備份還停在 2026-05-18（84 天），
落後 317 檔 / 362MB —— 也就是那 317 個附件當時在全世界只有一份。
而這三個缺口沒有任何一個會報錯：`remote_backup.json` 寫著 `success`、
排程 `LastTaskResult=0`、NAS 檔案一天比一天多，全都是綠的。

---

## 1. 解密金鑰（第一步，因為後面都要用）

加密備份的密碼**同時**存在兩個地方：

- 本機 `C:\Users\<user>\.ck\missive-secrets.key`（給每日排程用）
- **你的密碼管理器** ← D 槽壞掉時唯一的來源

```bash
# 從 NAS 取最新一份
cp "\\CKNAS\CK_Project\#Project_data\missive_secrets\secrets_YYYYMMDD.enc" .

openssl enc -d -aes-256-cbc -pbkdf2 -in secrets_YYYYMMDD.enc -out secrets.tar
tar -xf secrets.tar
# 得到 .env / GoogleCalendarAPIKEY.json / remote_backup.json
```

> ⚠️ 解出來的是明文金鑰。用完立刻刪除暫存副本，不要留在共享或暫存目錄。

---

## 2. 還原資料庫

### 2.1 先設 shm_size，否則會悄悄少一個索引

`docker-compose.production.yml` 的 postgres 服務已設 `shm_size: 1gb`。
**確認它在**，不要用舊版 compose 起容器：

```bash
grep -n "shm_size" docker-compose.production.yml   # 應看到 1gb
```

原因見 §4 缺陷 2 —— 少了它，還原會「成功」但 HNSW 索引建不起來，
而 psql 退出碼仍是 0。

### 2.2 還原

```bash
# 建立空資料庫（正式庫名 ck_documents；先還原到暫存庫再切換更安全）
docker exec ck_missive_postgres psql -U ck_user -d postgres \
  -c "CREATE DATABASE ck_restore OWNER ck_user;"

# ⚠️ 不要加 ON_ERROR_STOP=1，原因見 §4 缺陷 1
docker exec -i ck_missive_postgres psql -U ck_user -d ck_restore -q \
  < ck_missive_backup_YYYYMMDD_HHMMSS.sql
```

### 2.3 驗證（**這一步不能跳**）

還原完成不等於還原正確。逐一比對：

```sql
-- 表數與索引數（2026-08-10 基準：77 tables / 403 indexes）
select (select count(*) from information_schema.tables where table_schema='public') tables,
       (select count(*) from pg_indexes where schemaname='public') indexes;

-- 關鍵索引必須在（少了它語意搜尋會退化成全表掃描而不報錯）
select 1 from pg_indexes where indexname = 'ix_canonical_entities_embedding_hnsw';

-- 業務量（與備份當日的數字比對，不是與今天比）
select (select count(*) from documents), (select count(*) from canonical_entities),
       (select count(*) from document_attachments), (select count(*) from contract_projects);
```

---

## 3. 還原附件

```bash
robocopy "\\CKNAS\CK_Project\#Project_data\missive_attachments" \
         "D:\CKProject\CK_Missive\backend\uploads" /E /R:2 /W:5
```

**別忘了 `_longname_archive/`**：原始檔名超過 255 bytes（中文約 85 字，
公文標題常見）的附件存不進 Linux/Samba，是以 zip 形式備份的。
解開後放回對應目錄：

```bash
# 例：doc_885_longname.zip → backend/uploads/2026/02/doc_885/
```

還原後對帳：DB 的 `document_attachments` 筆數應與磁碟檔案對得起來。

---

## 4. 2026-08-10 實測發現的兩個缺陷（會再遇到）

### 缺陷 1：`transaction_timeout` —— pg_dump 17 對 PG 15

備份是 backend 容器的 **pg_dump 17.10** 產生的，但伺服器是 **15.14**
（backend 容器的 `postgresql-client` 是 L49.1 修法時裝的，Debian 13 預設就是 17）。
dump 開頭有 `SET transaction_timeout = 0;`，而那是 PG 17 才有的參數：

```
ERROR: unrecognized configuration parameter "transaction_timeout"
```

**影響**：帶 `ON_ERROR_STOP=1` 還原會在第 12 行就中止。不帶則印一行錯誤後繼續，
資料完整（2026-08-10 實測：1991 docs / 49648 KG，與備份當時一致）。

**繞法**：還原時不要加 `ON_ERROR_STOP=1`，或先剝掉那一行：
```bash
sed -i '/^SET transaction_timeout/d' backup.sql
```

**根治**（未做，需 rebuild backend）：把 backend 的 `postgresql-client` 釘成 15.x
讓 pg_dump 版本與伺服器對齊。在此之前，這個繞法必須被記得 —— 所以寫在這裡。

### 缺陷 2：`/dev/shm` 64MB —— HNSW 索引悄悄沒建起來

```
ERROR: could not resize shared memory segment ... to 131109152 bytes: No space left on device
```

**這是最危險的一個**，因為它不像失敗：
- psql 退出碼 **0**
- 資料完整、表數相同
- 只有 `ix_canonical_entities_embedding_hnsw`（49,648 筆向量）**沒建起來**
- 後果是語意搜尋退化成全表掃描，慢到不可用，而**沒有任何訊息會說**

2026-08-10 是靠「比對正式庫與還原庫的索引數（403 vs 402）」才發現的。
**所以 §2.3 那三個查詢不能跳。**

**已修**：compose 加 `shm_size: 1gb`。⚠️ 但**尚未重建 postgres 容器**
（避免 L43 家族風險），目前運行中的容器仍是 64MB。
災難還原時是新起容器，會套用新設定；若要在平時生效需 recreate，
recreate 前務必確認 volume 名為 `ck_missive_postgres_dev_data`（L43）。

---

## 5. 月度演練程序（不要等到真的需要才第一次做）

每月一次，約 15 分鐘：

```bash
# 1. 素材齊不齊（也在 weekly step 45 自動跑）
python scripts/checks/offsite_backup_completeness_audit.py

# 2. 真的還原一次到暫存庫
docker exec ck_missive_postgres psql -U ck_user -d postgres \
  -c "DROP DATABASE IF EXISTS ck_restore_verify;" \
  -c "CREATE DATABASE ck_restore_verify OWNER ck_user;"
docker exec -i ck_missive_postgres psql -U ck_user -d ck_restore_verify -q \
  < backups/database/<最新>.sql

# 3. 比對（表數／索引數／關鍵索引／業務量）—— 見 §2.3

# 4. 金鑰解得開嗎
openssl enc -d -aes-256-cbc -pbkdf2 -in secrets_YYYYMMDD.enc -out /tmp/s.tar
tar -tf /tmp/s.tar    # 應列出 .env / GoogleCalendarAPIKEY.json / remote_backup.json
rm -f /tmp/s.tar

# 5. 清乾淨
docker exec ck_missive_postgres psql -U ck_user -d postgres \
  -c "DROP DATABASE IF EXISTS ck_restore_verify;"
```

演練結果記在本檔頂端的「上次完整還原測試」，並更新 §2.3 的基準數字。

---

## 6. 還沒做的事（誠實列出）

| 項目 | 現況 |
|---|---|
| pg_dump 版本對齊 | 未做（需 rebuild backend）。在此之前依 §4 缺陷 1 的繞法 |
| postgres 容器套用 `shm_size` | 設定已進 compose，容器**未重建**（避 L43 風險） |
| NAS 本身的冗餘 | **未查證**。若 NAS 是單顆磁碟，那它只是把單點從 D 槽換個位置 |
| Redis 快照異地 | 未做。session/cache 可重建，但 `line_digest_buffer` 等狀態會遺失（影響小） |
