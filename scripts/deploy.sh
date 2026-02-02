#!/bin/bash
# =============================================================================
# CK_Missive 本地部署腳本
# =============================================================================
# 用法: ./scripts/deploy.sh [staging|production]
# =============================================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函數：顯示訊息
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# 檢查參數
ENV=${1:-staging}
if [[ "$ENV" != "staging" && "$ENV" != "production" ]]; then
    error "無效的環境: $ENV (使用 staging 或 production)"
fi

info "=========================================="
info "CK_Missive 部署腳本"
info "=========================================="
info "目標環境: $ENV"
info "時間: $(date)"
info "=========================================="

# 檢查 Docker
if ! command -v docker &> /dev/null; then
    error "Docker 未安裝"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose 未安裝"
fi

# 確定 docker-compose 命令
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# 檢查配置檔案
if [ ! -f ".env" ]; then
    error ".env 檔案不存在，請複製 .env.example 並設置"
fi

if [ ! -f "docker-compose.unified.yml" ]; then
    error "docker-compose.unified.yml 不存在"
fi

# 確認部署
if [ "$ENV" == "production" ]; then
    warning "您即將部署到 PRODUCTION 環境！"
    read -p "確定要繼續嗎？ (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        info "部署已取消"
        exit 0
    fi
fi

# 步驟 1: 備份資料庫 (僅 production)
if [ "$ENV" == "production" ]; then
    info "步驟 1/6: 備份資料庫..."
    BACKUP_FILE="backup-$(date +%Y%m%d%H%M%S).sql"
    if docker ps | grep -q "ck_missive.*postgres"; then
        docker exec ck_missive_postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > "/tmp/$BACKUP_FILE" 2>/dev/null || warning "資料庫備份失敗（可能是首次部署）"
        if [ -f "/tmp/$BACKUP_FILE" ]; then
            success "資料庫已備份到 /tmp/$BACKUP_FILE"
        fi
    else
        warning "PostgreSQL 容器未運行，跳過備份"
    fi
else
    info "步驟 1/6: 跳過資料庫備份 (staging)"
fi

# 步驟 2: 拉取最新程式碼
info "步驟 2/6: 拉取最新程式碼..."
git fetch origin
git pull origin $(git branch --show-current)
success "程式碼已更新"

# 步驟 3: 建構 Docker 映像檔
info "步驟 3/6: 建構 Docker 映像檔..."
$COMPOSE -f docker-compose.unified.yml build --no-cache backend frontend
success "映像檔建構完成"

# 步驟 4: 停止舊服務
info "步驟 4/6: 停止舊服務..."
$COMPOSE -f docker-compose.unified.yml stop backend frontend
success "舊服務已停止"

# 步驟 5: 執行資料庫遷移
info "步驟 5/6: 執行資料庫遷移..."
$COMPOSE -f docker-compose.unified.yml up -d postgres
sleep 10  # 等待資料庫啟動
$COMPOSE -f docker-compose.unified.yml run --rm backend alembic upgrade head || warning "遷移可能已是最新"
success "資料庫遷移完成"

# 步驟 6: 啟動新服務
info "步驟 6/6: 啟動新服務..."
$COMPOSE -f docker-compose.unified.yml up -d
success "服務已啟動"

# 等待服務就緒
info "等待服務就緒..."
sleep 30

# 健康檢查
info "執行健康檢查..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null; then
        success "健康檢查通過！"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    warning "健康檢查失敗，重試 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    error "健康檢查失敗，請檢查日誌: docker logs ck_missive_backend"
fi

# 顯示服務狀態
info "=========================================="
info "服務狀態:"
info "=========================================="
$COMPOSE -f docker-compose.unified.yml ps

# 完成
echo ""
success "=========================================="
success "🎉 部署完成！"
success "=========================================="
success "環境: $ENV"
success "版本: $(git rev-parse --short HEAD)"
success "時間: $(date)"
success "=========================================="
echo ""
info "前端: http://localhost:3000"
info "後端 API: http://localhost:8001/api"
info "API 文件: http://localhost:8001/docs"
info "Adminer: http://localhost:8080"
