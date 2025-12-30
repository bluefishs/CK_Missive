#!/bin/bash

# Docker 清潔構建腳本
# 避免快取問題，確保使用最新配置

set -e  # 遇到錯誤立即退出

echo "🚀 開始清潔構建流程..."

# 1. 環境變數驗證
echo "📋 驗證環境變數配置..."
cd frontend && node scripts/env-manager.js validate

# 2. 清理舊容器和映像
echo "🧹 清理舊的Docker資源..."
docker-compose --env-file .env -f configs/docker-compose.yml down frontend 2>/dev/null || true
docker rmi ck_missive-frontend 2>/dev/null || true

# 3. 清理Docker構建快取
echo "🔄 清理Docker構建快取..."
docker builder prune -f

# 4. 清理前端構建產物
echo "🧽 清理前端構建產物..."
rm -rf frontend/dist
rm -rf frontend/node_modules/.vite

# 5. 重新構建
echo "🔨 重新構建前端容器..."
docker-compose --env-file .env -f configs/docker-compose.yml build --no-cache frontend

# 6. 啟動並驗證
echo "🚀 啟動前端服務..."
docker-compose --env-file .env -f configs/docker-compose.yml up -d frontend

# 7. 驗證構建結果
echo "✅ 驗證構建結果..."
sleep 3
docker exec ck_missive_frontend sh -c "find /usr/share/nginx/html -name 'config-*.js' -exec grep -l '8002' {} \; || echo '無8002硬編碼 ✅'"

echo "🎉 清潔構建完成！"
echo "🌐 請訪問: http://localhost:3000"