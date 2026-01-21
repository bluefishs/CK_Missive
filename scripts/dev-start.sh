#!/bin/bash
# =============================================================================
# 乾坤測繪公文管理系統 - 開發環境啟動腳本
# =============================================================================
# 🎯 目標：一鍵啟動開發環境，支援熱重載
# 🔧 功能：自動同步配置、啟動開發服務、監控狀態
# =============================================================================

set -e  # 出錯時立即退出

# 顏色輸出函數
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_dev() { echo -e "${PURPLE}🔧 $1${NC}"; }

# 主函數
main() {
    log_dev "=== 乾坤測繪開發環境啟動 ==="

    # 1. 環境檢查
    check_dev_environment

    # 2. 配置同步
    sync_dev_config

    # 3. 清理舊容器
    cleanup_dev_containers

    # 4. 啟動開發服務
    start_dev_services

    # 5. 驗證服務狀態
    verify_dev_services

    # 6. 顯示開發資訊
    show_dev_info
}

# 環境檢查
check_dev_environment() {
    log_info "🔍 檢查開發環境..."

    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝！請先安裝 Docker Desktop"
        exit 1
    fi

    # 檢查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安裝！"
        exit 1
    fi

    # 檢查開發配置文件
    if [[ ! -f "docker-compose.dev.yml" ]]; then
        log_error "開發配置文件 docker-compose.dev.yml 不存在！"
        exit 1
    fi

    log_success "開發環境檢查通過"
}

# 配置同步
sync_dev_config() {
    log_info "🔧 同步開發配置..."

    # 確保主配置存在
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.master" ]]; then
            cp .env.master .env
            log_success "已從 .env.master 創建 .env"
        else
            log_error "配置文件不存在！"
            exit 1
        fi
    fi

    # 建立開發目錄
    mkdir -p logs backend/logs frontend/logs backend/uploads
    log_success "開發目錄結構已建立"
}

# 清理舊容器
cleanup_dev_containers() {
    log_info "🧹 清理舊的開發容器..."

    # 停止開發環境容器
    docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

    # 清理未使用的映像（可選）
    read -p "是否清理未使用的 Docker 映像？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -f
        log_success "Docker 映像已清理"
    fi
}

# 啟動開發服務
start_dev_services() {
    log_info "🚀 啟動開發服務（支援熱重載）..."

    # 使用開發配置啟動
    docker-compose -f docker-compose.dev.yml up --build -d

    log_success "開發服務啟動完成"
    log_dev "開發模式特色："
    log_dev "  • 後端：支援 uvicorn --reload 熱重載"
    log_dev "  • 前端：支援 Vite HMR 熱更新"
    log_dev "  • 資料庫：獨立開發資料"
    log_dev "  • 程式碼：即時同步不需重建"
}

# 驗證服務狀態
verify_dev_services() {
    log_info "🔍 驗證開發服務狀態..."

    # 等待服務啟動
    log_info "等待服務啟動完成..."
    sleep 20

    # 檢查容器狀態
    if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        log_success "開發容器運行正常"
    else
        log_warning "部分開發容器可能未正常啟動"
        docker-compose -f docker-compose.dev.yml ps
    fi

    # 檢查後端健康
    log_info "檢查後端服務..."
    for i in {1..6}; do
        if curl -f http://localhost:8001/health >/dev/null 2>&1; then
            log_success "後端開發服務健康檢查通過"
            break
        else
            if [ $i -eq 6 ]; then
                log_warning "後端服務可能還在啟動中，請稍後手動檢查"
            else
                log_info "等待後端服務啟動... ($i/6)"
                sleep 10
            fi
        fi
    done

    # 檢查前端健康
    log_info "檢查前端服務..."
    for i in {1..6}; do
        if curl -f http://localhost:3000 >/dev/null 2>&1; then
            log_success "前端開發服務健康檢查通過"
            break
        else
            if [ $i -eq 6 ]; then
                log_warning "前端服務可能還在啟動中，請稍後手動檢查"
            else
                log_info "等待前端服務啟動... ($i/6)"
                sleep 10
            fi
        fi
    done
}

# 顯示開發資訊
show_dev_info() {
    echo ""
    log_dev "=== 🔧 開發環境資訊 ==="
    echo ""
    echo "🌐 前端開發伺服器: http://localhost:3000"
    echo "   • 支援 Vite HMR 熱更新"
    echo "   • 程式碼變更即時反映"
    echo ""
    echo "⚡ 後端開發 API: http://localhost:8001"
    echo "   • 支援 uvicorn --reload 熱重載"
    echo "   • 程式碼變更自動重啟"
    echo ""
    echo "📖 API 開發文檔: http://localhost:8001/api/docs"
    echo "   • Swagger UI 介面"
    echo "   • 即時 API 測試"
    echo ""
    echo "🗄️  開發資料庫管理: http://localhost:8080"
    echo "   • 獨立開發資料庫"
    echo "   • 不影響生產資料"
    echo ""
    log_dev "=== 🛠️  開發管理命令 ==="
    echo ""
    echo "📊 查看開發狀態: docker-compose -f docker-compose.dev.yml ps"
    echo "📝 查看開發日誌: docker-compose -f docker-compose.dev.yml logs -f"
    echo "🔄 重啟某服務: docker-compose -f docker-compose.dev.yml restart [service]"
    echo "🛑 停止開發環境: docker-compose -f docker-compose.dev.yml down"
    echo ""
    echo "📂 程式碼同步資訊:"
    echo "   • 後端：./backend → /app (即時同步)"
    echo "   • 前端：./frontend → /app (即時同步)"
    echo "   • 修改程式碼後無需重建容器"
    echo ""
    log_success "🎉 開發環境啟動完成！開始愉快的開發吧！"
}

# 錯誤處理
trap 'log_error "開發環境啟動過程中發生錯誤！"; exit 1' ERR

# 執行主函數
main "$@"