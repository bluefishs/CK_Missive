#!/bin/bash
# =============================================================================
# CK_Missive NAS 部署腳本
# =============================================================================
# 目標: QNAP NAS Container Station (192.168.50.41)
# 用法: ./scripts/deploy-nas.sh
# =============================================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# NAS 配置
NAS_HOST="192.168.50.41"
NAS_USER="${NAS_USER:-admin}"
NAS_DEPLOY_PATH="${NAS_DEPLOY_PATH:-/share/Container/ck-missive}"

# 函數
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }
step() { echo -e "${CYAN}📌 $1${NC}"; }

echo ""
echo -e "${CYAN}=========================================="
echo "   CK_Missive NAS Production 部署"
echo "=========================================="
echo -e "目標: ${NAS_HOST}${NC}"
echo ""

# 檢查必要檔案
step "步驟 1/7: 檢查本地檔案..."
required_files=(
    "docker-compose.production.yml"
    ".env.production"
    "backend/Dockerfile"
    "frontend/Dockerfile"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        error "缺少必要檔案: $file"
    fi
done
success "本地檔案檢查完成"

# 確認部署
echo ""
warning "您即將部署到 Production 環境!"
echo -e "  NAS: ${NAS_HOST}"
echo -e "  路徑: ${NAS_DEPLOY_PATH}"
echo ""
read -p "確定要繼續嗎？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    info "部署已取消"
    exit 0
fi

# 生成安全金鑰 (如果未設定)
step "步驟 2/7: 檢查安全配置..."
if grep -q "CHANGE_THIS" .env.production; then
    warning "偵測到預設 SECRET_KEY，正在生成新金鑰..."
    NEW_SECRET=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/CHANGE_THIS_TO_RANDOM_64_CHAR_HEX_STRING_USE_OPENSSL/$NEW_SECRET/" .env.production
    else
        sed -i "s/CHANGE_THIS_TO_RANDOM_64_CHAR_HEX_STRING_USE_OPENSSL/$NEW_SECRET/" .env.production
    fi
    success "已生成新的 SECRET_KEY"
fi

# 建立部署套件
step "步驟 3/7: 打包部署檔案..."
DEPLOY_PACKAGE="ck-missive-deploy-$(date +%Y%m%d%H%M%S).tar.gz"

tar -czf "$DEPLOY_PACKAGE" \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/*' \
    --exclude='uploads/*' \
    backend/ \
    frontend/ \
    configs/ \
    docker-compose.production.yml \
    .env.production

success "部署套件已建立: $DEPLOY_PACKAGE"

# 上傳到 NAS
step "步驟 4/7: 上傳到 NAS..."
echo "正在連接 ${NAS_USER}@${NAS_HOST}..."

# 建立遠端目錄
ssh "${NAS_USER}@${NAS_HOST}" "mkdir -p ${NAS_DEPLOY_PATH}"

# 上傳檔案
scp "$DEPLOY_PACKAGE" "${NAS_USER}@${NAS_HOST}:${NAS_DEPLOY_PATH}/"
success "檔案已上傳"

# 在 NAS 上執行部署
step "步驟 5/7: 在 NAS 上部署..."
ssh "${NAS_USER}@${NAS_HOST}" << ENDSSH
    set -e
    cd ${NAS_DEPLOY_PATH}

    echo "📦 解壓部署套件..."
    tar -xzf ${DEPLOY_PACKAGE}

    echo "📝 設定環境變數..."
    cp .env.production .env

    echo "🐳 停止舊服務..."
    docker-compose -f docker-compose.production.yml down 2>/dev/null || true

    echo "🔨 建構映像檔..."
    docker-compose -f docker-compose.production.yml build --no-cache

    echo "🚀 啟動服務..."
    docker-compose -f docker-compose.production.yml up -d

    echo "⏳ 等待服務啟動 (60秒)..."
    sleep 60

    echo "🏥 健康檢查..."
    docker-compose -f docker-compose.production.yml ps

    echo "🧹 清理部署套件..."
    rm -f ${DEPLOY_PACKAGE}
ENDSSH

success "NAS 部署完成"

# 健康檢查
step "步驟 6/7: 驗證服務..."
sleep 10

echo "檢查後端 API..."
if curl -sf "http://${NAS_HOST}:8001/health" > /dev/null; then
    success "後端 API 正常運行"
else
    warning "後端 API 尚未就緒，請稍後手動檢查"
fi

echo "檢查前端..."
if curl -sf "http://${NAS_HOST}/" > /dev/null; then
    success "前端服務正常運行"
else
    warning "前端服務尚未就緒，請稍後手動檢查"
fi

# 執行資料庫遷移
step "步驟 7/7: 執行資料庫遷移..."
ssh "${NAS_USER}@${NAS_HOST}" << ENDSSH
    cd ${NAS_DEPLOY_PATH}
    docker-compose -f docker-compose.production.yml exec -T backend alembic upgrade head || echo "遷移可能已是最新"
ENDSSH

# 清理本地套件
rm -f "$DEPLOY_PACKAGE"

# 完成
echo ""
echo -e "${GREEN}=========================================="
echo "   🎉 Production 部署完成!"
echo "=========================================="
echo -e "${NC}"
echo "服務位址:"
echo -e "  📱 前端:     ${CYAN}http://${NAS_HOST}/${NC}"
echo -e "  🔌 API:      ${CYAN}http://${NAS_HOST}:8001/api${NC}"
echo -e "  📖 API 文件: ${CYAN}http://${NAS_HOST}:8001/docs${NC}"
echo -e "  🗄️ Adminer:  ${CYAN}http://${NAS_HOST}:8080${NC} (需手動啟用)"
echo ""
echo "管理指令 (SSH 到 NAS 後執行):"
echo "  cd ${NAS_DEPLOY_PATH}"
echo "  docker-compose -f docker-compose.production.yml logs -f      # 查看日誌"
echo "  docker-compose -f docker-compose.production.yml ps           # 服務狀態"
echo "  docker-compose -f docker-compose.production.yml restart      # 重啟服務"
echo ""
