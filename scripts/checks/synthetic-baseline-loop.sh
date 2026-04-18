#!/bin/bash
# Synthetic Baseline Loop — 常駐執行合成流量注入，累積 Hermes Phase 0 shadow baseline
#
# 仿 health-watchdog.sh v2.0 模式（常駐 while-true，避免 PM2 cron 在 Windows 不穩定）。
# 每 INTERVAL 秒跑一次 synthetic-baseline-inject.py，每次 COUNT 筆查詢。
#
# 排程建議（用 PM2）：
#   cd CK_Missive
#   pm2 start scripts/checks/synthetic-baseline-loop.sh --name synthetic-baseline \
#       --interpreter bash --no-autorestart
#   pm2 save
#
# 或獨立執行：
#   nohup bash scripts/checks/synthetic-baseline-loop.sh >> logs/synthetic-out.log 2>&1 &
#
# 停止：
#   pm2 stop synthetic-baseline
#
# Version: 1.0.0
# Created: 2026-04-18

set -u

# ── 可調參數 ────────────────────────────────────────────
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"
INTERVAL="${INTERVAL:-14400}"    # 預設 4 小時一輪（每日 6 輪 × 20 筆 = 120 筆）
COUNT="${COUNT:-20}"             # 每輪注入筆數
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_SCRIPT="${SCRIPT_DIR}/synthetic-baseline-inject.py"

echo "[synthetic-loop] Started"
echo "[synthetic-loop]   BACKEND_URL = $BACKEND_URL"
echo "[synthetic-loop]   INTERVAL    = ${INTERVAL}s"
echo "[synthetic-loop]   COUNT       = $COUNT per round"
echo "[synthetic-loop]   SCRIPT      = $INJECT_SCRIPT"

# 啟動時先等 30 秒讓 backend 就緒（避免 PM2 同時拉起時搶先）
sleep 30

ROUND=0
while true; do
    ROUND=$((ROUND + 1))
    echo "[synthetic-loop] === Round #$ROUND at $(date -Iseconds) ==="

    if ! python "$INJECT_SCRIPT" --count "$COUNT" --base-url "$BACKEND_URL"; then
        echo "[synthetic-loop] WARN: inject exited non-zero — 不中斷迴圈"
    fi

    echo "[synthetic-loop] Round #$ROUND done. Sleeping ${INTERVAL}s..."
    sleep "$INTERVAL"
done
