# Ghost Volume Cleanup — 2026-05-22

> 觸發：L43 volume drift 後續 audit 揭發兩個 orphan volumes
> 操作：tar 留底 + `docker volume rm`

## 背景

5/21 L43 incident（[[lesson_l43_volume_mount_drift_silent_fail]]）修復過程中，
owner 與 fitness step 38 對 docker volume 做完整盤點，揭發兩個不在任何
compose 引用內的 ghost orphan volumes：

| Volume | 大小 | 創建 | 最後 mtime | 性質 |
|---|---|---|---|---|
| `CK_Missive_postgres_data` | 63.1 MB raw / 7.4 MB tar.gz | 2025-09-10 | 2025-09-12 | 早期專案大寫前綴遺留（label `project=ck_missive` 但 volume name 混合大小寫）— 8 個月未動 |
| `ck_missive_redis_dev_data` | 512 KB raw / 244 KB tar.gz | 2025-10-08 | 2026-05-21 04:16 | 5/21 切 production compose 前的 dev redis cache 殘留 |

兩個都不在 3 個 compose（production / dev / infra）的 `name:` 宣告中，純 orphan。

## 備份檔案

| 檔案 | MD5 |
|---|---|
| `CK_Missive_postgres_data_20260522.tar.gz` | `63516ebe22031bbada912b3e08d1cb67` |
| `ck_missive_redis_dev_data_20260522.tar.gz` | `94bb94265edd69acc79d53db8fbda19e` |

## 還原（如果發現需要）

```bash
# Restore CK_Missive_postgres_data
docker volume create CK_Missive_postgres_data
docker run --rm -v CK_Missive_postgres_data:/d \
  -v "$(pwd):/backup" alpine \
  sh -c "cd / && tar xzf /backup/CK_Missive_postgres_data_20260522.tar.gz"

# Restore ck_missive_redis_dev_data (cache, usually no need)
docker volume create ck_missive_redis_dev_data
docker run --rm -v ck_missive_redis_dev_data:/d \
  -v "$(pwd):/backup" alpine \
  sh -c "cd / && tar xzf /backup/ck_missive_redis_dev_data_20260522.tar.gz"
```

## 為何安全刪除

1. **CK_Missive_postgres_data**：8 個月未寫入。與當前活躍的 `ck_missive_postgres_dev_data`（75 tables / 1788 docs / 24061 KG）無關。早期 schema 可能 incompatible，僅留檔案系統 dump 保險。
2. **ck_missive_redis_dev_data**：redis cache，內容會 5 分鐘內被應用重建。當前活躍的是 `ck_missive_redis_data`（11.3 MB / DBSIZE=19 keys）。

## 教訓

- **step 38 audit 設計盲點**：原只掃 compose `name:` 宣告對齊，不掃 orphan。
  本次 cleanup 後加強為 `--strict` 模式（task #10）。
- **跨檔資源 SSOT** L43 family 第 5 例（前 4：L41/L43/L44/L45）— 「volume 已存在但沒人 reference」是「健康假面」變種：`docker volume ls` 看似充滿活力，實際多為廢墟。
