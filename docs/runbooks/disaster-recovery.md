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

---

## 7. 三種災難情境與各自的可行性（2026-08-10 評估）

**RPO（會丟多少）＝ 24 小時**：備份每日 02:00，最壞情況丟失前一天 02:00 之後的公文與附件。
**RTO（多久恢復）** 依情境差異很大：

### 情境 A：只有 D 槽壞（最可能）

機器還在、C 槽還在 → 加密密碼就在 `C:\Users\<user>\.ck\`，NAS 也還在。

| 步驟 | 時間 |
|---|---|
| 換碟、裝 Docker Desktop | 1–2h |
| `git clone` 專案（五個 repo） | 10min |
| 解密 secrets → 還原 `.env` 等 | 5min |
| `docker compose up -d`（含 `shm_size: 1gb`） | 20min（拉映像） |
| 還原 DB（509MB，見 §2） | 5min |
| 還原附件（1.1GB 從 NAS） | 2min |
| §2.3 驗證 + 公網復通 | 30min |

**RTO ≈ 2–4 小時，且已實測過每一步。**

### 情境 B：整台機器毀（火災／竊盜／主機板）

C 槽一起沒了 → **本機那份密碼價值為零**，只能靠密碼管理器或紙本那一份。

除情境 A 的步驟外還要：準備新機器、裝 Windows/驅動/GPU、
Cloudflare Tunnel 重新連線（token 在 secrets 裡，或 CF Dashboard 重新產生）。

**RTO ≈ 1–2 天**，瓶頸是硬體取得與環境安裝，不是資料。

### 情境 C：勒索軟體 ⚠️ **目前無法還原**

這是現況最大的洞，且它不是理論風險：

```
本機對 NAS 備份目錄：可寫入 True、可刪除 True   ← 2026-08-10 實測
```

異地備份靠 robocopy 寫入 SMB，代表這台機器對 NAS 有完整寫入與刪除權限——
**勒索軟體拿到的權限跟備份腳本一模一樣**。它會連 NAS 上那 30 份 dump、
1486 個附件、加密的 secrets 一起加密掉。

NAS 在同一個區網（192.168.50.250）、同一棟建築，也擋不住火災與竊盜。

**結論：目前防得住「磁碟壞掉」，防不住「有人／有程式主動破壞」。**

---

## 8. 3-2-1 原則達成度（不合格）

| 原則 | 要求 | 現況 |
|---|---|---|
| **3** 份副本 | 正本 + 2 份備份 | **2**（本機 + NAS）✗ |
| **2** 種媒體 | 不同儲存型態 | 2（內接 SSD + NAS）✓ |
| **1** 份離線／異地 | 不可被本機寫入、不在同一地點 | **0** ✗ |

補齊「1 份離線」的三個選項，依成本排序：

| 方案 | 成本 | 擋得住什麼 | 備註 |
|---|---|---|---|
| **NAS 端快照**（Synology/QNAP 內建） | 0 元，設定 10 分鐘 | 勒索軟體（快照唯讀、本機改不到） | **CP 值最高，優先確認 NAS 型號是否支援** |
| **外接硬碟月度輪替** | 一顆 2TB ≈ 2000 元 | 勒索軟體 + 火災/竊盜（拔掉帶走） | 需要人記得插拔 → 排程提醒 |
| **雲端**（Backblaze B2 / R2） | 15GB ≈ 每月數十元 | 全部 | 需處理加密與頻寬 |

**建議：先確認 NAS 有沒有快照功能。** 若有，開啟即可，是唯一「零成本且不需人記得做」的選項。

---

## 9. 加密密碼要放哪（C 槽也在同一台機器上）

**本機那份（`C:\Users\<user>\.ck\missive-secrets.key`）在情境 B/C 價值為零** ——
它只是給每日排程用的。真正救命的是機器以外的那一份。

### 先認清一件事：金鑰大多可以重新申請

2026-08-10 逐一盤點 `.env` 的 18 個敏感項：

| 類別 | 項目 | 可否重建 |
|---|---|---|
| 平台重新產生 | CF Tunnel／Google／Groq／NVIDIA／LINE×3／Telegram | ✅ **只要帳號還在** |
| 自行重設 | `POSTGRES_PASSWORD`／`SECRET_KEY`／`MCP_SERVICE_TOKEN`／webhook secrets | ✅ 代價是全員重登一次 |
| ⚠️ 特別麻煩 | **`CK_SSO_JWT_SECRET`** | 可重設，但要**同步五個系統**（CK_Website IdP + Missive/lvrland/pile/DT），漏一個 SSO 就全斷（L41 家族） |
| 不可重建 | **無** | — |

→ **`.env` 備份的價值是「省掉數小時逐一重新申請」，不是「不可替代」。**
真正不可替代的是**那些平台帳號的登入能力**（Google / Cloudflare / LINE Developers），
尤其是 **2FA 備援碼**——如果 2FA 綁在手機上而手機跟著沒了，那才是真的回不去。

### 建議：三層，各擋不同故障

1. **紙本（最重要，也最被低估）**
   一張紙寫下加密密碼，放在**與電腦不同建築**（家裡／保險箱／公司文件櫃）。
   擋得住勒索軟體、火災、雲端帳號被鎖、密碼管理器主密碼忘記。
   密碼不常變，維護成本近乎為零。

2. **密碼管理器（便利層）**
   Bitwarden 免費版即可（雲端同步、手機可查）。建立一則「安全筆記」，內容：
   加密密碼 + 本 runbook 的網址 + 「解密指令」那三行。
   ⚠️ **它的主密碼與 recovery code 本身也要走第 1 層**，否則只是換一個單點。

3. **本機（自動化用）** —— 保留現狀，但認知它在真災難時無用。

### 另一個值得考慮的改動：把隨機密碼換成你記得住的

目前的密碼是我產生的隨機 base64，**沒有人記得住 → 必然依賴儲存**。
換成你自選的 20 字元以上詞組（中英數皆可），強度足夠，
而且**人腦是唯一不會被勒索軟體加密、也不會跟機器一起壞的儲存媒體**。

更換方式（舊的 `.enc` 檔會無法用新密碼解開，故需重新產生一份）：

```powershell
Remove-Item "$env:USERPROFILE\.ck\missive-secrets.key"
# 改為手動寫入你自選的密碼（不要用 -InitPassphrase，那會產生隨機值）
Set-Content "$env:USERPROFILE\.ck\missive-secrets.key" "你的密碼" -Encoding ascii -NoNewline
powershell -File scripts\backup\secrets-offsite-nas.ps1   # 產生新的 .enc 並自我驗證
```

---

## 10. 建議的執行順序（依「擋掉多少風險 ÷ 花多少力氣」排序）

| # | 動作 | 時間 | 擋掉 |
|---|---|---|---|
| 1 | **平台帳號 2FA 備援碼印出來**（Google／Cloudflare／LINE Developers） | 30min | 真正不可替代的那一層 |
| 2 | **加密密碼寫紙本，放不同建築** | 5min | 情境 B/C 的解密能力 |
| 3 | **確認 NAS 有無快照功能，有就開啟** | 10min | **情境 C 勒索軟體** |
| 4 | 密碼管理器建一則安全筆記 | 15min | 便利性 |
| 5 | 外接硬碟月度離線副本（若 NAS 無快照） | 一次採購 + 每月 10min | 情境 C + 火災/竊盜 |
| 6 | pg_dump 版本對齊（rebuild backend） | 1h | 還原時少一個絆腳石 |

**第 1 項排最前面不是筆誤**：金鑰都能重新申請，但前提是進得去那些平台。
