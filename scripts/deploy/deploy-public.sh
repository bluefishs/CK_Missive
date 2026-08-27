#!/bin/bash
# deploy-public.sh — 公網部署一鍵腳本
#
# 執行：bash scripts/deploy/deploy-public.sh [--frontend-only]
#
# ──────────────────────────────────────────────────────────────────────
# 2026-08-27 重寫。前一版（v1.0.0）做的是 PM2 時代的事，而現在不成立：
#
#   * 它跑 `pm2 restart ck-backend` —— 但 `pm2 jlist` 裡**根本沒有 ck-backend**
#     （只剩 showcase / tunnel-viewer 那幾支）。後端 2026-05 起就跑在
#     `ck_missive_backend` 容器裡，8001 由 docker 轉發。
#   * 而那一行寫成 `pm2 restart ck-backend 2>&1 | tail -1` ⇒ `set -e` 看到的是
#     **tail 的退出碼**（永遠 0）⇒ 重啟失敗不會中斷，腳本照樣印
#     「Deploy complete!」。本專案 08-24 才記過同一個 `| tail` 陷阱。
#   * 它從來不 build backend image ⇒ 後端改動用這支腳本部署，**完全不會生效**；
#     前端改動則是「碰巧會動」（frontend/dist 是 bind mount，FastAPI 直接讀硬碟）。
#   * 也因此它從沒機會 source build-args.sh ⇒ 映像身分永遠是 unknown。
#
# 所以這一版的原則：**每一步都要能失敗**，而且失敗要停下來。
# ──────────────────────────────────────────────────────────────────────
#
# 流程：
#   1. Frontend production build（驗 AUTH_DISABLED=false 真的進了 bundle）
#   2. Backend image build（帶 build-args 綁定 version @ commit）
#   3. up -d 換新容器
#   4. 等 health
#   5. 驗身分：runtime 回報的 commit 必須等於這次 build 的 commit
#   6. 驗公網 200（L76：Windows Docker recreate 會留殭屍埠轉發 socket）
#   7. 部署後四層驗證 deploy_verify.py（L93：三層 200 而 ORM mapper 壞掉＝無法登入）
#
# Version: 2.0.0

set -euo pipefail
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)
COMPOSE="docker compose -f docker-compose.production.yml"
FRONTEND_ONLY=0
[ "${1:-}" = "--frontend-only" ] && FRONTEND_ONLY=1

echo "╔══════════════════════════════════════╗"
echo "║   CK_Missive 公網部署 v2.0.0        ║"
echo "╚══════════════════════════════════════╝"

# ── Step 1: Frontend build ────────────────────────────────────────────
echo ""
echo "[1/7] Building frontend (production)..."
( cd frontend && npm run build --silent )   # 不接 pipe，build 失敗就是失敗

MAIN_JS=$(ls frontend/dist/assets/main-*.js 2>/dev/null | head -1 || true)
if [ -z "$MAIN_JS" ]; then
    echo "  ✗ 找不到 frontend/dist/assets/main-*.js —— build 沒有產出"
    exit 1
fi
if grep -q 'VITE_AUTH_DISABLED:"false"' "$MAIN_JS"; then
    echo "  ✓ AUTH_DISABLED=false confirmed in bundle"
else
    # 這不是警告而已 —— 帶著 AUTH_DISABLED=true 的 bundle 上公網
    # 等於前端自己把認證關掉。寧可停在這裡。
    echo "  ✗ bundle 內 AUTH_DISABLED 不是 false，拒絕部署"
    echo "    檢查 frontend/.env.production"
    exit 1
fi

if [ "$FRONTEND_ONLY" = "1" ]; then
    echo ""
    echo "  （--frontend-only：dist 是 bind mount，FastAPI 直接讀硬碟，不需重啟後端）"
fi

# ── Step 2: Backend image build（帶身分）──────────────────────────────
if [ "$FRONTEND_ONLY" = "0" ]; then
    echo ""
    echo "[2/7] Building backend image (帶 build 身分綁定)..."
    # shellcheck source=/dev/null
    source scripts/deploy/build-args.sh    # 會印出「build 綁定：vX @ <commit>」
    $COMPOSE build backend

    echo ""
    echo "[3/7] Recreating backend container..."
    $COMPOSE up -d backend
else
    echo ""
    echo "[2/7] (skipped) backend image build"
    echo "[3/7] (skipped) backend recreate"
    CK_BUILD_COMMIT="${CK_BUILD_COMMIT:-}"
fi

# ── Step 4: Health ────────────────────────────────────────────────────
echo ""
echo "[4/7] Waiting for backend health..."
TRIES=0
until curl -sf http://localhost:8001/health >/dev/null 2>&1; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -gt 45 ]; then
        echo "  ✗ Backend 90s 內沒有回到 healthy"
        echo "    docker logs --tail 50 ck_missive_backend"
        exit 1
    fi
    sleep 2
done
echo "  ✓ Backend healthy (${TRIES}x2s)"

# ── Step 5: 身分驗證 ──────────────────────────────────────────────────
# 「內容有沒有進去」與「跑的是哪一份」是兩個問題。前者由
# container_image_freshness_check 的 md5 比對回答，後者只有這裡回答得了。
echo ""
echo "[5/7] Verifying build identity..."
RUNTIME_JSON=$(curl -sf --max-time 15 http://localhost:8001/api/health/detailed || echo '{}')
RUNTIME_COMMIT=$(printf '%s' "$RUNTIME_JSON" | python -c "
import json,sys
try: print(json.load(sys.stdin).get('build',{}).get('commit','unknown'))
except Exception: print('unknown')
")
RUNTIME_VERSION=$(printf '%s' "$RUNTIME_JSON" | python -c "
import json,sys
try: print(json.load(sys.stdin).get('build',{}).get('version','unknown'))
except Exception: print('unknown')
")
echo "  runtime: ${RUNTIME_VERSION} @ ${RUNTIME_COMMIT}"

if [ "$FRONTEND_ONLY" = "0" ]; then
    if [ "$RUNTIME_COMMIT" = "unknown" ]; then
        echo "  ✗ runtime 回報 unknown —— build-args 沒有進到映像"
        exit 1
    fi
    if [ "$RUNTIME_COMMIT" != "${CK_BUILD_COMMIT}" ]; then
        # 跑的不是剛剛 build 的那一份 = 換容器沒成功（舊容器還在）
        echo "  ✗ runtime commit (${RUNTIME_COMMIT}) ≠ 本次 build (${CK_BUILD_COMMIT})"
        echo "    舊容器可能還在服務；檢查 docker ps -a --filter name=ck_missive_backend"
        exit 1
    fi
    echo "  ✓ runtime 就是這次 build 的那一份"
fi

# ── Step 6: 公網 ──────────────────────────────────────────────────────
# L76：Windows 上 recreate 後常留殭屍埠轉發 socket ⇒ 容器 healthy 但公網 502。
# 所以本機 health 綠**不能**當作部署成功。
echo ""
echo "[6/7] Verifying public access..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://missive.cksurvey.tw/health || echo 000)
if [ "$HTTP" = "200" ]; then
    echo "  ✓ https://missive.cksurvey.tw/health → 200"
else
    echo "  ✗ 公網回 HTTP $HTTP（本機 health 是綠的 ⇒ 疑似 L76 殭屍埠轉發）"
    echo "    修法見 docs/runbooks/ 與 LESSONS_REGISTRY.md#L76"
    exit 1
fi
API=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://missive.cksurvey.tw/ || echo 000)
echo "  ✓ 公網首頁 → $API"

# 2026-08-27：上面三層**擋不住 L93**。
#
# 2026-08-16 加 `approved_by` 後 `ExpenseInvoice` 有兩個外鍵指向 users，
# SQLAlchemy mapper 初始化失敗 ⇒ `POST /api/auth/google` 回 500，
# **owner 回報「系統無法登入」** —— 而當時 `/health` 與首頁**全部 200**
# （它們不觸發 ORM mapper 設定）。
#
# `deploy_verify.py` 就是為了這件事寫的（多一層走 ORM 與認證鏈的 `/api/auth/check`），
# 而它**先前沒有任何東西在呼叫它**：README 把它列在「每日 fitness_daily」底下，
# 而 `run_fitness_daily.sh` 一次都沒提到它。寫好了、擺著、沒人跑。
#
# ⚠️ 第 4 層的正確答案是 **401 不是 200**（未帶憑證本來就該被拒絕）——
# 把 401 當失敗會讓它永遠紅，把 500 當通過則等於沒有這一層。判準在該腳本內。
echo ""
echo "[7/7] 部署後四層驗證（含 ORM／認證鏈，L76 + L93）..."
if python "$(dirname "$0")/../checks/deploy_verify.py"; then
    echo "  ✓ 四層皆通過"
else
    echo "  ✗ 部署後驗證失敗 —— 公網 200 不代表系統能用（見上方逐層結果）"
    exit 1
fi

echo ""
echo "══════════════════════════════════════"
echo "  Deploy complete — ${RUNTIME_VERSION} @ ${RUNTIME_COMMIT}"
echo "══════════════════════════════════════"
