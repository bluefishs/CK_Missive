#!/bin/bash
# deploy-public.sh — 公網部署一鍵腳本
#
# 執行：bash scripts/deploy/deploy-public.sh
#
# 流程：
#   1. Frontend production build (AUTH_DISABLED=false)
#   2. PM2 restart backend (載入新 dist)
#   3. 等待 health OK
#   4. 驗證公網可達
#
# Version: 1.0.0

set -e
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "╔══════════════════════════════════════╗"
echo "║   CK_Missive 公網部署               ║"
echo "╚══════════════════════════════════════╝"

# Step 1: Build
echo ""
echo "[1/4] Building frontend (production mode)..."
cd frontend
npm run build --silent 2>&1 | tail -2
cd "$PROJECT_ROOT"

# Verify AUTH_DISABLED=false in build
MAIN_JS=$(ls frontend/dist/assets/main-*.js | head -1)
if grep -q 'VITE_AUTH_DISABLED:"false"' "$MAIN_JS"; then
    echo "  ✓ AUTH_DISABLED=false confirmed in build"
else
    echo "  ✗ WARNING: AUTH_DISABLED may not be false in build!"
    echo "  Check frontend/.env.production"
fi

# Step 2: Restart
echo ""
echo "[2/4] Restarting ck-backend..."
pm2 restart ck-backend --update-env 2>&1 | tail -1

# Step 3: Wait
echo ""
echo "[3/4] Waiting for backend health..."
TRIES=0
until curl -sf http://localhost:8001/health >/dev/null 2>&1; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -gt 30 ]; then
        echo "  ✗ Backend failed to start after 60s"
        exit 1
    fi
    sleep 2
done
echo "  ✓ Backend healthy (${TRIES}x2s)"

# Step 4: Verify public
echo ""
echo "[4/4] Verifying public access..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://missive.cksurvey.tw/health 2>/dev/null)
if [ "$HTTP" = "200" ]; then
    echo "  ✓ https://missive.cksurvey.tw → 200 OK"
else
    echo "  ✗ Public check failed: HTTP $HTTP"
    echo "  Check cloudflared container"
    exit 1
fi

echo ""
echo "══════════════════════════════════════"
echo "  Deploy complete!"
echo "══════════════════════════════════════"
