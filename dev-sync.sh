#!/bin/bash
# =============================================================================
# 乾坤測繪公文管理系統 - 開發環境快速同步工具
# =============================================================================
# 🎯 目標：快速同步程式碼變更，無需重建容器
# 🔧 功能：熱重載、服務重啟、變更檢測
# =============================================================================

set -e

# 顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

show_usage() {
    echo -e "${GREEN}=== 乾坤測繪開發同步工具 ===${NC}"
    echo ""
    echo "用法："
    echo "  $0 backend          # 重啟後端服務"
    echo "  $0 frontend         # 重啟前端服務"
    echo "  $0 db               # 重啟資料庫"
    echo "  $0 all              # 重啟所有服務"
    echo "  $0 logs [service]   # 查看日誌"
    echo "  $0 shell [service]  # 進入容器 shell"
    echo "  $0 install          # 安裝新依賴後重建"
    echo "  $0 reset            # 重置開發環境"
    echo ""
}

restart_service() {
    local service=$1
    log_info "重啟 $service 服務..."

    case $service in
        "backend")
            docker-compose -f docker-compose.dev.yml restart backend
            log_success "後端服務已重啟"
            ;;
        "frontend")
            docker-compose -f docker-compose.dev.yml restart frontend
            log_success "前端服務已重啟"
            ;;
        "db"|"database")
            docker-compose -f docker-compose.dev.yml restart postgres
            log_success "資料庫服務已重啟"
            ;;
        "redis")
            docker-compose -f docker-compose.dev.yml restart redis
            log_success "Redis 服務已重啟"
            ;;
        "all")
            docker-compose -f docker-compose.dev.yml restart
            log_success "所有服務已重啟"
            ;;
        *)
            log_error "未知服務: $service"
            show_usage
            exit 1
            ;;
    esac
}

show_logs() {
    local service=${1:-""}

    if [[ -z "$service" ]]; then
        log_info "顯示所有服務日誌..."
        docker-compose -f docker-compose.dev.yml logs -f
    else
        log_info "顯示 $service 服務日誌..."
        docker-compose -f docker-compose.dev.yml logs -f $service
    fi
}

enter_shell() {
    local service=${1:-"backend"}

    log_info "進入 $service 容器 shell..."

    case $service in
        "backend")
            docker-compose -f docker-compose.dev.yml exec backend /bin/bash
            ;;
        "frontend")
            docker-compose -f docker-compose.dev.yml exec frontend /bin/sh
            ;;
        "db"|"database")
            docker-compose -f docker-compose.dev.yml exec postgres psql -U ck_user -d ck_documents
            ;;
        *)
            docker-compose -f docker-compose.dev.yml exec $service /bin/sh
            ;;
    esac
}

install_dependencies() {
    log_info "檢測到新依賴，重建容器..."

    # 停止服務
    docker-compose -f docker-compose.dev.yml down

    # 重建並啟動
    docker-compose -f docker-compose.dev.yml up --build -d

    log_success "依賴安裝完成，服務已重啟"
}

reset_environment() {
    log_warning "這將重置整個開發環境！"
    read -p "確定要繼續嗎？(y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "重置開發環境..."

        # 停止所有服務
        docker-compose -f docker-compose.dev.yml down -v

        # 清理映像和網路
        docker system prune -f

        # 重新啟動
        docker-compose -f docker-compose.dev.yml up --build -d

        log_success "開發環境已重置"
    else
        log_info "取消重置操作"
    fi
}

check_file_changes() {
    log_info "檢查最近的文件變更..."

    # 檢查最近5分鐘修改的文件
    echo "最近修改的後端文件："
    find ./backend -name "*.py" -mmin -5 2>/dev/null || echo "  無最近變更"

    echo ""
    echo "最近修改的前端文件："
    find ./frontend/src -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" -mmin -5 2>/dev/null || echo "  無最近變更"
}

# 主邏輯
case "${1:-help}" in
    "backend"|"frontend"|"db"|"database"|"redis"|"all")
        restart_service $1
        ;;
    "logs")
        show_logs $2
        ;;
    "shell")
        enter_shell $2
        ;;
    "install")
        install_dependencies
        ;;
    "reset")
        reset_environment
        ;;
    "check")
        check_file_changes
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "未知命令: $1"
        show_usage
        exit 1
        ;;
esac