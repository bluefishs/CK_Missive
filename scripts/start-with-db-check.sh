#!/bin/bash
# ===================================================================
# 啟動服務並自動檢查資料庫初始化
# 解決每次重啟後資料庫為空的問題
# ===================================================================

echo "=== 啟動服務並檢查資料庫 ==="
cd "$(dirname "$0")"

echo
echo "1. 啟動 Docker 服務..."
docker-compose -f configs/docker-compose.yml --env-file .env up -d

echo
echo "2. 等待服務啟動完成..."
sleep 20

echo
echo "3. 檢查並初始化資料庫..."
python3 database-auto-init.py

if [ $? -eq 0 ]; then
    echo
    echo "✅ 系統啟動成功！"
    echo
    echo "服務地址："
    echo "  前端: http://localhost:3000"
    echo "  後端: http://localhost:8001"
    echo "  管理: http://localhost:8080"
    echo
else
    echo
    echo "❌ 資料庫初始化失敗"
    echo "請檢查 Docker 服務狀態"
fi