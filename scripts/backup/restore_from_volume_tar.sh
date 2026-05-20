#!/usr/bin/env bash
# CK_Missive Docker volume bit-perfect 還原（給升級後 volume 消失時用）
#
# 建立日期：2026-05-19
# 用法：
#   bash scripts/backup/restore_from_volume_tar.sh <TIMESTAMP>
#   # 例：bash scripts/backup/restore_from_volume_tar.sh 20260519_154508
#   # TIMESTAMP 取自 backups/volumes/pg_volume_PREUPGRADE_<TS>.tar.gz 檔名
#
# 也可不傳參數 — 自動找最新 PREUPGRADE tar：
#   bash scripts/backup/restore_from_volume_tar.sh latest
#
# 還原流程：
#   1. STOP 既有容器（若在跑）
#   2. REMOVE 既有 volume（若存在）
#   3. CREATE 同名空 volume
#   4. EXTRACT tar 到該 volume
#   5. 不自動 start container — owner 手動 docker compose up -d 驗證
#
# 安全：使用前確認 timestamp 是預期的版本，誤用會覆蓋現有資料

set -euo pipefail

TS_ARG="${1:-}"
if [[ -z "$TS_ARG" ]]; then
    echo "Usage: bash scripts/backup/restore_from_volume_tar.sh <TIMESTAMP|latest>"
    echo ""
    echo "Available PG volume tars:"
    ls -lt backups/volumes/pg_volume_PREUPGRADE_*.tar.gz 2>/dev/null | head -5 | awk '{print "  " $NF}'
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi
PG_CONTAINER="${PG_CONTAINER:-ck_missive_postgres_dev}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ck_missive_redis_dev}"
PG_VOLUME="${PG_VOLUME:-ck_missive_postgres_dev_data}"
REDIS_VOLUME="${REDIS_VOLUME:-ck_missive_redis_dev_data}"

# 解析 TS（latest 自動取最新）
if [[ "$TS_ARG" == "latest" ]]; then
    LATEST_TAR=$(ls -t backups/volumes/pg_volume_PREUPGRADE_*.tar.gz 2>/dev/null | head -1)
    if [[ -z "$LATEST_TAR" ]]; then
        echo "[!!!] No PREUPGRADE volume tar found in backups/volumes/"
        exit 1
    fi
    TS=$(basename "$LATEST_TAR" | sed 's/pg_volume_PREUPGRADE_\(.*\)\.tar\.gz/\1/')
    echo "Auto-detected latest TS: $TS"
else
    TS="$TS_ARG"
fi

PG_TAR="backups/volumes/pg_volume_PREUPGRADE_${TS}.tar.gz"
REDIS_TAR="backups/volumes/redis_volume_PREUPGRADE_${TS}.tar.gz"

if [[ ! -f "$PG_TAR" ]]; then
    echo "[!!!] PG tar not found: $PG_TAR"
    exit 1
fi

PG_SIZE=$(du -h "$PG_TAR" | cut -f1)
REDIS_SIZE=$(du -h "$REDIS_TAR" 2>/dev/null | cut -f1 || echo "missing")

echo "============================================"
echo "CK_Missive Volume Restore (BIT-PERFECT)"
echo "TS: $TS"
echo "PG tar:    $PG_TAR ($PG_SIZE)"
echo "Redis tar: $REDIS_TAR ($REDIS_SIZE)"
echo "============================================"
echo ""
echo "[WARNING] 此操作將：（1）停 $PG_CONTAINER / $REDIS_CONTAINER（若在跑）"
echo "                   （2）刪除既有 volume $PG_VOLUME / $REDIS_VOLUME"
echo "                   （3）從 tar 還原"
echo ""
read -r -p "確定要還原？輸入 'YES' 繼續: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
    echo "Aborted."
    exit 1
fi

# ---- Stop containers ----
echo ""
echo "[1/4] Stop containers..."
docker stop "$PG_CONTAINER" "$REDIS_CONTAINER" 2>/dev/null || true
docker rm "$PG_CONTAINER" "$REDIS_CONTAINER" 2>/dev/null || true

# ---- Remove existing volumes ----
echo "[2/4] Remove existing volumes (if any)..."
docker volume rm "$PG_VOLUME" 2>/dev/null || true
docker volume rm "$REDIS_VOLUME" 2>/dev/null || true

# ---- Create empty volumes ----
echo "[3/4] Create empty volumes..."
docker volume create "$PG_VOLUME"
docker volume create "$REDIS_VOLUME"

# ---- Extract tars into volumes ----
echo "[4/4] Extract tar into volumes..."
MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${PG_VOLUME}":/data \
    -v "//d/CKProject/CK_Missive/backups/volumes":/backup \
    alpine sh -c "cd /data && tar xzf /backup/pg_volume_PREUPGRADE_${TS}.tar.gz"
echo "    PG volume restored from $PG_TAR"

if [[ -f "$REDIS_TAR" ]]; then
    MSYS_NO_PATHCONV=1 docker run --rm \
        -v "${REDIS_VOLUME}":/data \
        -v "//d/CKProject/CK_Missive/backups/volumes":/backup \
        alpine sh -c "cd /data && tar xzf /backup/redis_volume_PREUPGRADE_${TS}.tar.gz"
    echo "    Redis volume restored from $REDIS_TAR"
fi

echo ""
echo "============================================"
echo "✅ Volume Restore 完成"
echo "============================================"
echo ""
echo "下一步："
echo "  1. docker compose -f docker-compose.infra.yml up -d"
echo "  2. 驗證："
echo "     docker exec ck_missive_postgres_dev psql -U ck_user -d ck_documents -c 'SELECT COUNT(*) FROM official_documents;'"
echo "     docker exec ck_missive_redis_dev redis-cli DBSIZE"
echo "  3. 若計數對得上，restart backend：pm2 restart ck-backend"
