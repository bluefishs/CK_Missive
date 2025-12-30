#!/bin/bash
# ===================================================================
# 簡單的系統重啟後檢查腳本 - 避免複雜化
# ===================================================================

echo "=== 系統重啟後基本檢查 ==="
cd "$(dirname "$0")"

echo
echo "1. 檢查必要檔案是否存在..."
if [ ! -f .env ]; then
    echo "[ERROR] .env 檔案不存在"
    if [ -f .env.master ]; then
        cp .env.master .env
        echo "[FIX] 已從 .env.master 復原"
    else
        echo "[ERROR] .env.master 也不存在，請檢查配置"
        exit 1
    fi
fi

if [ ! -f docker-compose.unified.yml ]; then
    echo "[ERROR] docker-compose.unified.yml 不存在"
    exit 1
fi

echo "[OK] 基本檔案檢查完成"

echo
echo "2. 啟動服務..."
docker-compose -f docker-compose.unified.yml up -d
if [ $? -ne 0 ]; then
    echo "[ERROR] Docker 服務啟動失敗"
    exit 1
fi

echo
echo "3. 等待服務就緒 (30秒)..."
sleep 30

echo
echo "4. 檢查服務狀態..."
docker-compose -f docker-compose.unified.yml ps

echo
echo "5. 簡單連通性測試..."
if curl -s http://localhost:8001/health > /dev/null; then
    echo "[OK] 後端 API 可連接"
else
    echo "[WARN] 後端 API 無法連接，可能需要更多時間啟動"
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "[OK] 前端服務可連接"
else
    echo "[WARN] 前端服務無法連接，可能需要更多時間啟動"
fi

echo
echo "=== 基本檢查完成 ==="
echo "如果服務無法正常訪問，請等待 1-2 分鐘後再試"
echo
echo "服務地址："
echo "  前端: http://localhost:3000"
echo "  後端: http://localhost:8001"
echo "  管理: http://localhost:8080"
echo
echo "按 Enter 鍵結束..."
read