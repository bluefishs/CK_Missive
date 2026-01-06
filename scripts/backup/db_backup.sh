#!/bin/bash
# =============================================================================
# 乾坤測繪公文管理系統 - PostgreSQL 每日備份腳本 (Linux/Git Bash)
# =============================================================================
# 用途：自動備份 PostgreSQL 資料庫
# 執行：bash db_backup.sh [--retention-days N] [--verbose]
# 排程：使用 cron 設定每日執行
#       0 2 * * * /path/to/db_backup.sh >> /var/log/ck_backup.log 2>&1
# =============================================================================

set -e

# 預設設定
RETENTION_DAYS=7
VERBOSE=false

# 解析參數
while [[ $# -gt 0 ]]; do
    case $1 in
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "未知參數: $1"
            exit 1
            ;;
    esac
done

# 取得腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# 目錄設定
BACKUP_DIR="$PROJECT_ROOT/backups/database"
LOG_DIR="$PROJECT_ROOT/logs/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_ONLY=$(date +"%Y%m%d")
LOG_FILE="$LOG_DIR/backup_$DATE_ONLY.log"

# 預設資料庫設定
DB_USER="ck_user"
DB_PASSWORD="ck_password_2024"
DB_NAME="ck_documents"
DB_PORT="5434"
CONTAINER_NAME="ck_missive_postgres"

# 從 .env 讀取設定
ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    while IFS='=' read -r key value; do
        case "$key" in
            POSTGRES_USER) DB_USER="$value" ;;
            POSTGRES_PASSWORD) DB_PASSWORD="$value" ;;
            POSTGRES_DB) DB_NAME="$value" ;;
            POSTGRES_HOST_PORT) DB_PORT="$value" ;;
            COMPOSE_PROJECT_NAME) CONTAINER_NAME="${value}_postgres" ;;
        esac
    done < <(grep -v '^#' "$ENV_FILE" | grep -v '^$')
fi

# 日誌函數
log() {
    local level="${2:-INFO}"
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    if [[ "$VERBOSE" == "true" ]] || [[ "$level" == "ERROR" ]]; then
        echo "[$timestamp] [$level] $message"
    fi
}

# 確保目錄存在
ensure_dir() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

# 主要備份程序
do_backup() {
    log "========== 開始資料庫備份 =========="
    log "備份目錄: $BACKUP_DIR"
    log "保留天數: $RETENTION_DAYS"

    ensure_dir "$BACKUP_DIR"
    ensure_dir "$LOG_DIR"

    # 檢查 Docker 容器
    if ! docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
        log "錯誤：Docker 容器 $CONTAINER_NAME 未運行" "ERROR"
        return 1
    fi

    log "Docker 容器 $CONTAINER_NAME 運行中"

    # 備份檔案
    BACKUP_FILE="$BACKUP_DIR/ck_missive_backup_$TIMESTAMP.sql"
    COMPRESSED_FILE="$BACKUP_FILE.gz"

    # 執行 pg_dump
    log "執行 pg_dump..."
    export PGPASSWORD="$DB_PASSWORD"

    if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl > "$BACKUP_FILE" 2>&1; then
        log "SQL 備份完成: $BACKUP_FILE"

        # 壓縮備份
        if command -v gzip &> /dev/null; then
            gzip -f "$BACKUP_FILE"
            local file_size=$(du -h "$COMPRESSED_FILE" | cut -f1)
            log "壓縮完成: $COMPRESSED_FILE ($file_size)"
        else
            local file_size=$(du -h "$BACKUP_FILE" | cut -f1)
            log "備份大小: $file_size (未壓縮)"
        fi

        return 0
    else
        log "pg_dump 執行失敗" "ERROR"
        cat "$BACKUP_FILE" | while read line; do log "$line" "ERROR"; done
        rm -f "$BACKUP_FILE"
        return 1
    fi
}

# 清理舊備份
cleanup_old_backups() {
    log "清理超過 $RETENTION_DAYS 天的舊備份..."

    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm -f "$file"
        log "已刪除舊備份: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "ck_missive_backup_*" -type f -mtime +$RETENTION_DAYS -print0 2>/dev/null)

    log "清理完成，共刪除 $deleted_count 個舊備份"
}

# 主程序
echo "=== 乾坤測繪公文管理系統 - 資料庫備份 ==="
echo ""

ensure_dir "$LOG_DIR"

if do_backup; then
    cleanup_old_backups
    log "========== 備份程序完成 =========="
    echo "✅ 備份完成"
    exit 0
else
    log "========== 備份程序失敗 =========="
    echo "❌ 備份失敗，請查看日誌: $LOG_FILE"
    exit 1
fi
