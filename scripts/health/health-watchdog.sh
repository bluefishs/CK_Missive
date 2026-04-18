#!/bin/bash
# Health Watchdog — 常駐偵測 backend 假死並自動重啟
#
# PM2 以 autorestart 常駐執行，每 2 分鐘檢查一次。
# 連續 2 次失敗則 restart ck-backend。
#
# Version: 2.0.0 — 改為 while-true 常駐模式（修復 PM2 cron 在 Windows 不穩定）

HEALTH_URL="http://localhost:8001/health"
MAX_FAILS=2
TIMEOUT=10
INTERVAL=120  # 秒

FAILS=0

echo "[watchdog] Started (interval=${INTERVAL}s, max_fails=${MAX_FAILS})"

while true; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null)

    if [ "$HTTP_CODE" = "200" ]; then
        if [ "$FAILS" -gt 0 ]; then
            echo "[watchdog] Recovered after $FAILS failures"
        fi
        FAILS=0
    else
        FAILS=$((FAILS + 1))
        echo "[watchdog] FAIL #$FAILS/$MAX_FAILS (HTTP=$HTTP_CODE)"

        if [ "$FAILS" -ge "$MAX_FAILS" ]; then
            echo "[watchdog] Restarting ck-backend..."
            pm2 restart ck-backend --update-env 2>&1 | tail -1
            FAILS=0
            # 重啟後等額外 30s 讓 backend 啟動
            sleep 30
        fi
    fi

    sleep "$INTERVAL"
done
