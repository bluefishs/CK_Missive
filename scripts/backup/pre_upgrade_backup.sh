#!/usr/bin/env bash
# CK_Missive Docker Desktop 升級前緊急備份（4 層保險）
#
# 建立日期：2026-05-19（觸發事件：發現 Docker Desktop 升級會清 named volume + cron 任務不在）
# 用法：bash scripts/backup/pre_upgrade_backup.sh
# 產出：
#   1. backups/database/ck_missive_PREUPGRADE_<TS>.dump    — PG custom format（restore 推薦）
#   2. backups/database/ck_missive_PREUPGRADE_<TS>.sql.gz  — PG plain SQL（人類可讀）
#   3. backups/redis/redis_PREUPGRADE_<TS>.rdb              — Redis RDB snapshot
#   4. backups/volumes/pg_volume_PREUPGRADE_<TS>.tar.gz    — PG volume bit-perfect
#   5. backups/volumes/redis_volume_PREUPGRADE_<TS>.tar.gz — Redis volume bit-perfect
#   6. 異地同步到 NAS Z:/03.專案管控專區/00.公司公文紀錄/#systembackup/CK_Missive_PREUPGRADE_<DATE>/
#
# 任一層失敗時其他層仍能還原（diverse-redundancy）

set -euo pipefail

TS=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Env vars（從 .env 讀取）
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi
PG_USER="${POSTGRES_USER:-ck_user}"
PG_DB="${POSTGRES_DB:-ck_documents}"
PG_CONTAINER="${PG_CONTAINER:-ck_missive_postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ck_missive_redis}"
PG_VOLUME="${PG_VOLUME:-ck_missive_postgres_dev_data}"
# 2026-05-21 L43 收斂：對齊 compose 的 redis volume name（dev_data orphan 後）
REDIS_VOLUME="${REDIS_VOLUME:-ck_missive_redis_data}"
NAS_PATH="${NAS_BACKUP_PATH:-Z:/03.專案管控專區/00.公司公文紀錄/#systembackup}"

mkdir -p backups/database backups/volumes backups/redis

echo "============================================"
echo "CK_Missive Pre-Upgrade Emergency Backup"
echo "TS: $TS"
echo "PG: $PG_CONTAINER ($PG_USER / $PG_DB)"
echo "Volume: $PG_VOLUME / $REDIS_VOLUME"
echo "============================================"

# ---- Layer 1: PG custom dump (recommended restore source) ----
echo ""
echo "[1/6] PostgreSQL custom dump..."
MSYS_NO_PATHCONV=1 docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -F c -Z 5 \
    > "backups/database/ck_missive_PREUPGRADE_${TS}.dump" \
    2> "backups/database/pg_dump_err_${TS}.log"
PG_DUMP_SIZE=$(du -h "backups/database/ck_missive_PREUPGRADE_${TS}.dump" | cut -f1)
echo "    OK: backups/database/ck_missive_PREUPGRADE_${TS}.dump ($PG_DUMP_SIZE)"

# ---- Layer 2: PG plain SQL (gzipped, diffable) ----
echo "[2/6] PostgreSQL plain SQL (gzipped)..."
MSYS_NO_PATHCONV=1 docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" 2>/dev/null \
    | gzip > "backups/database/ck_missive_PREUPGRADE_${TS}.sql.gz"
SQL_GZ_SIZE=$(du -h "backups/database/ck_missive_PREUPGRADE_${TS}.sql.gz" | cut -f1)
echo "    OK: backups/database/ck_missive_PREUPGRADE_${TS}.sql.gz ($SQL_GZ_SIZE)"

# ---- Layer 3: Redis RDB snapshot ----
echo "[3/6] Redis RDB snapshot..."
docker exec "$REDIS_CONTAINER" redis-cli SAVE >/dev/null
MSYS_NO_PATHCONV=1 docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "backups/redis/redis_PREUPGRADE_${TS}.rdb"
docker exec "$REDIS_CONTAINER" redis-cli --scan 2>/dev/null > "backups/redis/redis_keys_${TS}.txt" || true
RDB_SIZE=$(du -h "backups/redis/redis_PREUPGRADE_${TS}.rdb" | cut -f1)
REDIS_KEYS=$(wc -l < "backups/redis/redis_keys_${TS}.txt" | tr -d ' ')
echo "    OK: backups/redis/redis_PREUPGRADE_${TS}.rdb ($RDB_SIZE / $REDIS_KEYS keys)"

# ---- Layer 4: PG volume tar (bit-perfect) ----
echo "[4/6] PG volume bit-perfect tar..."
MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${PG_VOLUME}":/data \
    -v "//d/CKProject/CK_Missive/backups/volumes":/backup \
    alpine tar czf "/backup/pg_volume_PREUPGRADE_${TS}.tar.gz" -C /data . 2>&1 | tail -3
PG_TAR_SIZE=$(du -h "backups/volumes/pg_volume_PREUPGRADE_${TS}.tar.gz" | cut -f1)
echo "    OK: backups/volumes/pg_volume_PREUPGRADE_${TS}.tar.gz ($PG_TAR_SIZE)"

# ---- Layer 5: Redis volume tar ----
echo "[5/6] Redis volume bit-perfect tar..."
MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${REDIS_VOLUME}":/data \
    -v "//d/CKProject/CK_Missive/backups/volumes":/backup \
    alpine tar czf "/backup/redis_volume_PREUPGRADE_${TS}.tar.gz" -C /data . 2>&1 | tail -3
REDIS_TAR_SIZE=$(du -h "backups/volumes/redis_volume_PREUPGRADE_${TS}.tar.gz" | cut -f1)
echo "    OK: backups/volumes/redis_volume_PREUPGRADE_${TS}.tar.gz ($REDIS_TAR_SIZE)"

# ---- Layer 6: 異地同步到 NAS Z ----
echo "[6/6] Offsite sync to NAS..."
NAS_TARGET="${NAS_PATH}/CK_Missive_PREUPGRADE_${DATE}"
if [[ -d "$(dirname "$NAS_TARGET")" ]]; then
    mkdir -p "$NAS_TARGET"
    cp "backups/database/ck_missive_PREUPGRADE_${TS}.dump" "$NAS_TARGET/"
    cp "backups/database/ck_missive_PREUPGRADE_${TS}.sql.gz" "$NAS_TARGET/"
    cp "backups/redis/redis_PREUPGRADE_${TS}.rdb" "$NAS_TARGET/"
    cp "backups/volumes/pg_volume_PREUPGRADE_${TS}.tar.gz" "$NAS_TARGET/"
    cp "backups/volumes/redis_volume_PREUPGRADE_${TS}.tar.gz" "$NAS_TARGET/"
    echo "    OK: NAS synced to $NAS_TARGET"
    ls -lh "$NAS_TARGET"
else
    echo "    SKIP: NAS path 不可達（離線時可後補手動同步）"
fi

echo ""
echo "============================================"
echo "✅ Pre-Upgrade Backup 完成"
echo "本機備份：D:/CKProject/CK_Missive/backups/"
echo "異地備份：${NAS_PATH}/CK_Missive_PREUPGRADE_${DATE}/"
echo "============================================"
echo ""
echo "⚠️  升級 Docker Desktop 前再執行一次本腳本確保最新狀態！"
echo "⚠️  升級後若 volume 消失，用：bash scripts/backup/restore_from_volume_tar.sh ${TS}"
