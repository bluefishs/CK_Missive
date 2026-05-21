# 2026-05-21 Volume Mount Drift Incident Backup

**事故 ID**：L43（與 L41 同型 — 4 重疊加 silent dormant）
**發生時間**：2026-05-21 ~04:00（切換 production compose 時點）
**發現時間**：2026-05-21 14:22（用戶 Google login 後業務 API 連環 500）
**修復時間**：2026-05-21 14:35（Plan A 10 steps 全綠）
**Dormant 時長**：約 10 小時

## 根因摘要

`docker-compose.production.yml:216` 寫 `name: ck_missive_postgres_data`，但真實資料一直在 `ck_missive_postgres_dev_data`（dev/infra compose 用）。
切換到 production compose 時 postgres 掛到空殼 volume → init.sql 建少數 base table → alembic upgrade head 推進 schema → backend `healthy` 假面 → 業務 API 全 500。

詳見：`memory/lesson_l43_volume_mount_drift_silent_fail.md` 與 `docs/architecture/RETRO_20260521_volume_drift.md`（如已寫）。

## 檔案說明

| 檔案 | Size | MD5 | 內容 |
|---|---|---|---|
| `real_data_ck_missive_postgres_dev_data.dump` | 77 MB | `65bfb3b73ed739e865bb222091e7cd11` | **真實生產 DB**（75 tables / 1788 docs / 24061 KG / 5/20 15:18 收尾資料）— `ck_missive_postgres_dev_data` volume |
| `wrong_volume_ck_missive_postgres_data.dump` | 122 KB | `8c1772027efc3a63022c9217184ec030` | **錯誤掛載期間的空殼 DB**（17 tables / 502 docs / 5/21 SSO debug 殘留）— `ck_missive_postgres_data` volume，作為事故證物保留 |

兩份均為 `pg_dump -Fc`（PostgreSQL custom format v1.14-0）。

## 還原指令範本

```bash
# 還原真實 DB 到指定 volume
docker run --rm -i \
  -v ck_missive_postgres_dev_data:/var/lib/postgresql/data \
  -v "$(pwd)":/backup \
  --network ck_missive_network \
  pgvector/pgvector:0.8.0-pg15 \
  pg_restore -h postgres -U ck_user -d ck_documents \
    --clean --if-exists \
    /backup/real_data_ck_missive_postgres_dev_data.dump
```

## 防禦措施（已落地）

1. `docker-compose.production.yml` patch：volume name 改為 `ck_missive_postgres_dev_data` + `external: true`
2. `backend/main.py` `/health` 加 `business_data_present` 檢查 — 業務表 row count 低於門檻時回 503
3. （規劃）fitness step 38 `docker_compose_volume_consistency.py`

## 異地備份

- 本地：`D:/CKProject/CK_Missive/backup/incident_20260521_volume_mount_drift/`
- NAS：`Z:/03.專案管控專區/00.公司公文紀錄/#systembackup/CK_Missive_INCIDENT_20260521_volume_mount_drift/`
- MD5 已雙端驗證一致
