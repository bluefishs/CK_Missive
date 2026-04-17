#!/bin/bash
# Health Watchdog — 偵測 backend 假死並自動重啟
#
# PM2 cron-restart 無法偵測 event loop 阻塞，此腳本補位。
# 每 2 分鐘由 PM2/cron 執行，連續 2 次失敗則 restart。
#
# Usage:
#   bash scripts/health/health-watchdog.sh
#
# Version: 1.0.0

HEALTH_URL="http://localhost:8001/health"
FAIL_FILE="/tmp/ck_backend_health_fails"
MAX_FAILS=2
TIMEOUT=10

# 檢查 health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    # 成功，重置計數
    echo 0 > "$FAIL_FILE"
    exit 0
fi

# 失敗，累加計數
FAILS=$(cat "$FAIL_FILE" 2>/dev/null || echo 0)
FAILS=$((FAILS + 1))
echo "$FAILS" > "$FAIL_FILE"

echo "[watchdog] Health check failed: HTTP=$HTTP_CODE, consecutive=$FAILS/$MAX_FAILS"

if [ "$FAILS" -ge "$MAX_FAILS" ]; then
    echo "[watchdog] Max failures reached, restarting ck-backend..."
    pm2 restart ck-backend --update-env
    echo 0 > "$FAIL_FILE"
fi
