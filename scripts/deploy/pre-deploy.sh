#!/bin/bash
# =============================================================================
# CK_Missive - 部署前置檢查腳本 (Linux/macOS)
# =============================================================================
# 用途: 在部署前檢查環境配置、目錄權限、端口可用性
# 使用: chmod +x pre-deploy.sh && ./pre-deploy.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.production"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Counters
ERRORS=0
WARNINGS=0

echo "=============================================="
echo "🔍 CK_Missive 部署前置檢查"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# 1. 檢查必要檔案
# -----------------------------------------------------------------------------
echo "📁 檢查必要檔案..."

check_file() {
    if [ -f "$1" ]; then
        echo -e "  ${GREEN}✓${NC} $2"
    else
        echo -e "  ${RED}✗${NC} $2 - 檔案不存在: $1"
        ((ERRORS++))
    fi
}

check_file "$PROJECT_ROOT/docker-compose.production.yml" "docker-compose.production.yml"
check_file "$BACKEND_DIR/Dockerfile" "backend/Dockerfile"
check_file "$BACKEND_DIR/requirements.txt" "backend/requirements.txt"
check_file "$BACKEND_DIR/alembic.ini" "backend/alembic.ini"
check_file "$PROJECT_ROOT/frontend/Dockerfile" "frontend/Dockerfile"

echo ""

# -----------------------------------------------------------------------------
# 2. 檢查環境變數檔案
# -----------------------------------------------------------------------------
echo "🔧 檢查環境變數..."

if [ -f "$ENV_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} 環境變數檔案存在"

    # Required variables
    REQUIRED_VARS=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "SECRET_KEY"
        "CORS_ORIGINS"
        "VITE_API_BASE_URL"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" "$ENV_FILE" && ! grep -q "^${var}=$" "$ENV_FILE"; then
            echo -e "  ${GREEN}✓${NC} $var 已設定"
        else
            echo -e "  ${RED}✗${NC} $var 未設定或為空"
            ((ERRORS++))
        fi
    done

    # Security checks
    if grep -q "POSTGRES_PASSWORD=.*password" "$ENV_FILE" || \
       grep -q "POSTGRES_PASSWORD=.*123456" "$ENV_FILE"; then
        echo -e "  ${YELLOW}⚠${NC} POSTGRES_PASSWORD 使用弱密碼"
        ((WARNINGS++))
    fi

    if grep -q "SECRET_KEY=.*change.*me" "$ENV_FILE" || \
       [ "$(grep "SECRET_KEY=" "$ENV_FILE" | cut -d= -f2 | wc -c)" -lt 32 ]; then
        echo -e "  ${YELLOW}⚠${NC} SECRET_KEY 可能不夠安全 (建議 64 字元)"
        ((WARNINGS++))
    fi
else
    echo -e "  ${RED}✗${NC} 環境變數檔案不存在: $ENV_FILE"
    echo -e "  ${YELLOW}提示${NC}: 複製 .env.production.example 並修改"
    ((ERRORS++))
fi

echo ""

# -----------------------------------------------------------------------------
# 3. 檢查目錄結構
# -----------------------------------------------------------------------------
echo "📂 檢查目錄結構..."

create_dir_if_not_exists() {
    if [ -d "$1" ]; then
        echo -e "  ${GREEN}✓${NC} $2 已存在"
    else
        echo -e "  ${YELLOW}!${NC} $2 不存在，正在建立..."
        mkdir -p "$1"
        chmod 777 "$1"
        echo -e "  ${GREEN}✓${NC} $2 已建立"
    fi
}

create_dir_if_not_exists "$BACKEND_DIR/logs" "backend/logs"
create_dir_if_not_exists "$BACKEND_DIR/uploads" "backend/uploads"
create_dir_if_not_exists "$BACKEND_DIR/backups" "backend/backups"
create_dir_if_not_exists "$BACKEND_DIR/backup-logs" "backend/backup-logs"

echo ""

# -----------------------------------------------------------------------------
# 4. 檢查端口可用性
# -----------------------------------------------------------------------------
echo "🔌 檢查端口可用性..."

check_port() {
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "  ${RED}✗${NC} Port $1 ($2) 已被佔用"
            ((ERRORS++))
        else
            echo -e "  ${GREEN}✓${NC} Port $1 ($2) 可用"
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$1 "; then
            echo -e "  ${RED}✗${NC} Port $1 ($2) 已被佔用"
            ((ERRORS++))
        else
            echo -e "  ${GREEN}✓${NC} Port $1 ($2) 可用"
        fi
    else
        echo -e "  ${YELLOW}?${NC} Port $1 ($2) - 無法檢查 (缺少 lsof/netstat)"
        ((WARNINGS++))
    fi
}

check_port 3000 "Frontend"
check_port 8001 "Backend API"
check_port 5434 "PostgreSQL"
check_port 6380 "Redis"

echo ""

# -----------------------------------------------------------------------------
# 5. 檢查 Docker
# -----------------------------------------------------------------------------
echo "🐳 檢查 Docker..."

if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker 已安裝: $(docker --version | cut -d' ' -f3)"

    if docker info &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Docker daemon 運行中"
    else
        echo -e "  ${RED}✗${NC} Docker daemon 未運行"
        ((ERRORS++))
    fi
else
    echo -e "  ${RED}✗${NC} Docker 未安裝"
    ((ERRORS++))
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker Compose 已安裝"
else
    echo -e "  ${RED}✗${NC} Docker Compose 未安裝"
    ((ERRORS++))
fi

echo ""

# -----------------------------------------------------------------------------
# 6. 驗證 Docker 建置 (可選)
# -----------------------------------------------------------------------------
if [ "$1" == "--build-test" ]; then
    echo "🔨 測試 Docker 建置..."

    cd "$PROJECT_ROOT"

    if docker compose -f docker-compose.production.yml build --dry-run 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Docker 建置配置有效"
    else
        echo -e "  ${YELLOW}⚠${NC} 無法驗證 Docker 建置 (需要 Docker BuildKit)"
        ((WARNINGS++))
    fi

    echo ""
fi

# -----------------------------------------------------------------------------
# 結果摘要
# -----------------------------------------------------------------------------
echo "=============================================="
echo "📊 檢查結果摘要"
echo "=============================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有檢查通過！可以開始部署。${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  檢查完成，有 $WARNINGS 個警告。${NC}"
    echo "   建議處理警告後再部署。"
    exit 0
else
    echo -e "${RED}❌ 檢查失敗：$ERRORS 個錯誤，$WARNINGS 個警告。${NC}"
    echo "   請修正錯誤後再執行部署。"
    exit 1
fi
