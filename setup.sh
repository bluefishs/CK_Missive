#!/bin/bash
# =============================================================================
# 乾坤測繪公文管理系統 - 一鍵部署腳本
# =============================================================================
# 🎯 目標：自動化環境設定和系統啟動
# 🔧 功能：配置同步、依賴檢查、服務啟動
# =============================================================================

set -e  # 出錯時立即退出

# 顏色輸出函數
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 檢查是否為 Windows (Git Bash)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    IS_WINDOWS=true
    SCRIPT_EXT=".ps1"
else
    IS_WINDOWS=false
    SCRIPT_EXT=".sh"
fi

# 主函數
main() {
    log_info "=== 乾坤測繪公文管理系統 - 一鍵部署 ==="

    # 1. 配置管理
    setup_configuration

    # 2. 依賴檢查
    check_dependencies

    # 3. 清理舊配置
    cleanup_old_configs

    # 4. 啟動服務
    start_services

    # 5. 驗證部署
    verify_deployment

    log_success "🎉 系統部署完成！"
    show_access_urls
}

# 配置管理
setup_configuration() {
    log_info "🔧 設定系統配置..."

    # 檢查主配置檔案
    if [[ ! -f ".env.master" ]]; then
        log_error "主配置檔案 .env.master 不存在！"
        exit 1
    fi

    # 同步配置
    cp .env.master .env
    log_success "配置檔案已同步"

    # 建立必要目錄
    mkdir -p logs backend/logs frontend/logs backend/uploads
    log_success "目錄結構已建立"
}

# 依賴檢查
check_dependencies() {
    log_info "🔍 檢查系統依賴..."

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

    log_success "所有依賴檢查通過"
}

# 清理舊配置
cleanup_old_configs() {
    log_info "🧹 清理舊配置檔案..."

    # 清理舊的環境變數檔案（保留範例檔案）
    find . -name ".env.*" -not -name ".env.master" -not -name ".env.example" -delete 2>/dev/null || true
    find . -name ".env.backup.*" -delete 2>/dev/null || true
    find . -name ".env.development*" -delete 2>/dev/null || true
    find . -name ".env.local*" -delete 2>/dev/null || true
    find . -name ".env.production*" -delete 2>/dev/null || true

    log_success "舊配置檔案已清理"
}

# 啟動服務
start_services() {
    log_info "🚀 啟動 Docker 服務..."

    # 停止現有服務
    log_info "停止現有服務..."
    docker-compose -f docker-compose.unified.yml down --remove-orphans 2>/dev/null || true

    # 清理舊容器和映像
    log_info "清理舊容器..."
    docker system prune -f 2>/dev/null || true

    # 啟動新服務
    log_info "啟動新服務..."
    docker-compose -f docker-compose.unified.yml up --build -d

    log_success "服務啟動完成"
}

# 驗證部署
verify_deployment() {
    log_info "🔍 驗證部署狀態..."

    # 等待服務啟動
    log_info "等待服務啟動..."
    sleep 30

    # 檢查服務狀態
    if docker-compose -f docker-compose.unified.yml ps | grep -q "Up"; then
        log_success "Docker 服務運行正常"
    else
        log_warning "部分服務可能未正常啟動，請檢查日誌"
    fi

    # 檢查健康狀態
    log_info "檢查服務健康狀態..."

    # 檢查後端健康
    if curl -f http://localhost:8001/health >/dev/null 2>&1; then
        log_success "後端服務健康檢查通過"
    else
        log_warning "後端服務健康檢查失敗"
    fi

    # 檢查前端健康
    if curl -f http://localhost:3000 >/dev/null 2>&1; then
        log_success "前端服務健康檢查通過"
    else
        log_warning "前端服務健康檢查失敗"
    fi
}

# 顯示訪問網址
show_access_urls() {
    echo ""
    log_info "=== 系統訪問資訊 ==="
    echo "🌐 前端應用: http://localhost:3000"
    echo "⚡ 後端 API: http://localhost:8001"
    echo "📖 API 文件: http://localhost:8001/api/docs"
    echo "🗄️  資料庫管理: http://localhost:8080"
    echo ""
    log_info "=== 管理命令 ==="
    echo "🔧 檢查狀態: docker-compose -f docker-compose.unified.yml ps"
    echo "📝 查看日誌: docker-compose -f docker-compose.unified.yml logs -f"
    echo "🛑 停止服務: docker-compose -f docker-compose.unified.yml down"
    echo ""
}

# 錯誤處理
trap 'log_error "部署過程中發生錯誤！"; exit 1' ERR

# 執行主函數
main "$@"