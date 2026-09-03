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

# ── Step 1.5: 後端真的變了嗎 ─────────────────────────────────────────
#
# 2026-08-29：CK_AaaP 的告警器對本站當日的容器重啟發了 critical
# （`ContainerRestartLoop ck_missive_backend`）。他們的門檻註解寫著
# 「部署很少在一小時內重啟同一容器兩次」—— **那個假設在開發活躍日不成立**，
# 而那正是重啟最密集的日子。
#
# 但真正該修的是我這一側：當日多次完整部署裡，有幾次**只改了
# `scripts/checks/`**（那些檔案根本不進 image）⇒ 換容器是純粹的浪費，
# 換來一次跨 repo 的假警報、一次 60 秒的啟動視窗、一次連線池重建。
#
# 判準：比對「執行中容器的 build commit」與「HEAD」之間，
# **`backend/` 底下有沒有變更**。沒有就跳過 build 與 recreate。
# ⚠️ 用 `--force-backend` 可強制（image 基底或依賴變了時需要）。
if [ "$FRONTEND_ONLY" = "0" ] && [ "${1:-}" != "--force-backend" ]; then
    # ⚠️ build 身分在 **env **，不是 label。
    # 我第一版寫 `.Config.Labels` —— 回空字串，而下面的 `-n` 守衛讓它
    # **靜靜地什麼都不做**（跳過邏輯永遠不觸發，且看不出來）。
    # 同本日反覆出現的形狀：機制看起來在，而它的輸入不存在。
    RUNNING_COMMIT="$(docker inspect ck_missive_backend         --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null         | sed -n 's/^CK_BUILD_COMMIT=//p' | head -1)"
    RUNNING_COMMIT="${RUNNING_COMMIT%%-dirty}"
    if [ -n "$RUNNING_COMMIT" ] && git rev-parse --verify -q "$RUNNING_COMMIT" >/dev/null 2>&1; then
        # ⚠️ 排除 `backend/tests/`：`.dockerignore` 已排除 `test_*.py`，
        # 而容器內沒有任何東西會 import 測試 ⇒ 改測試不需要換容器。
        # **其餘 backend/ 一律視為需要**（保守）—— 這裡判錯的代價是
        # 「以為部署了而跑的是舊碼」，那比多換一次容器嚴重得多。
        _BE_PATHS="backend/ :(exclude)backend/tests/"
        # shellcheck disable=SC2086
        if git diff --quiet "$RUNNING_COMMIT" HEAD -- $_BE_PATHS 2>/dev/null            && git diff --quiet HEAD -- $_BE_PATHS 2>/dev/null; then
            echo ""
            echo "  ⏭  backend/ 自 $RUNNING_COMMIT 以來沒有變更 —— 跳過換容器"
            echo "     （避免無謂的啟動視窗與跨 repo 假警報；要強制請帶 --force-backend）"
            FRONTEND_ONLY=1
        fi
    fi
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
# 2026-08-30：**三次抽樣，任一次非 200 即失敗。**
#
# L94(c) 記著「部署後的公網驗證要多次抽樣」，因為殭屍埠是**間歇性**的 ——
# 單次 curl 剛好通過，部署就被判成功。而 2026-08-29 兩筆公網 502 期間
# `cron_events` 顯示排程照跑無異常空窗（backend 活著、CF 打不進來），
# 那是 L76 第一次有外部證據。
#
# ⚠️ 下面那段註解一直宣稱「我們前幾天才把單次 curl 改成三次抽樣」，
#    而全 repo grep「三次抽樣」**只命中那句註解本身**，`for i in 1 2 3`
#    與 `SAMPLES` 一個都不存在 —— **宣稱的改動從未發生**（L104 形狀）。
#    這次是真的做了。
for _i in 1 2 3; do
    # 2026-09-02：原本 `... || echo 000` 在 curl 收到 200 header 後逾時（exit 28）時，
    # 會把 000 **追加**在已印出的 200 後面 ⇒ 印出「HTTP 200000」，看不出是逾時。
    # 判失敗是對的（回應不完整，使用者也會撞到），但輸出要說清楚是哪一種失敗。
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://missive.cksurvey.tw/health); _RC=$?
    if [ $_RC -ne 0 ]; then HTTP="${HTTP:-000}(curl exit $_RC)"; fi
    if [ "$HTTP" != "200" ]; then
        echo "  ✗ 公網第 $_i 次抽樣回 HTTP $HTTP（本機 health 是綠的 ⇒ 疑似 L76 殭屍埠轉發或 cloudflared 重連中）"
        echo "    間歇性失敗同樣是失敗 —— 使用者撞到的就是這一次。"
        echo "    修法見 docs/runbooks/ 與 LESSONS_REGISTRY.md#L76"
        exit 1
    fi
    # 用 if/fi 不用 `[ "$_i" -lt 3 ] && sleep 2`：後者第 3 圈條件為假 ⇒
    # 整個 && 串列回 1 ⇒ **迴圈的退出碼是 1，儘管三次抽樣全部 200**。
    #
    # ⚠️ 2026-08-30 更正（我第一版的註解把危害寫得比實際嚴重）：
    #    我原本寫「部署會在這一行中止」—— **那是錯的**。`set -e` 對 `&&`
    #    串列有豁免：失敗的若不是串列的最後一個指令就不觸發退出。實測
    #    迴圈後面的指令照常執行、當下 `$?` 是 0。只有當這個迴圈剛好是
    #    **腳本或子殼的最後一件事**時，退出碼才會變成 1。
    #    我當時看到的 exit=1 來自**我自己的測試套殼**（迴圈是那個
    #    `bash -c` 的最後一句），不是本檔的行為。
    #
    #    仍然改成 if/fi：這裡的退出碼語意不該取決於「後面還有沒有別的步驟」。
    if [ "$_i" -lt 3 ]; then sleep 2; fi
done
echo "  ✓ https://missive.cksurvey.tw/health → 200（三次抽樣皆通過）"
API=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://missive.cksurvey.tw/ || echo 000)
echo "  ✓ 公網首頁 → $API"

# 2026-08-29（CK_Website 跨平台探針指出，四個平台都適用）：
# **首頁 200 不代表 sso-bridge 健康**。他們的探針打的是 sso-bridge、
# 巡檢 curl 的是首頁，於是三天的 502 沒被發現 —— 那是「換個端點」
# 的問題，不是「多抽幾次」能解的（三次抽樣解的是另一半 —— 見上方 Step 6，
# 2026-08-30 才真的做上去；在那之前這句話是空的）。
# ⚠️ **它只接受 POST**（openapi 實查 `methods=['post']`）。
# 我第一版用 GET 打，回 404 —— 差點把「方法用錯」寫成一條每次部署都
# 發警告的檢查。無 cookie 的 POST 應回 401。
SSO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20       -X POST -H "Content-Type: application/json" -d '{}'       https://missive.cksurvey.tw/api/auth/sso-bridge || echo 000)
if [ "$SSO" = "401" ] || [ "$SSO" = "403" ]; then
    echo "  ✓ 公網 sso-bridge → $SSO（無憑證應被拒，代表它活著）"
elif [ "$SSO" = "502" ] || [ "$SSO" = "000" ]; then
    echo "  ✗ 公網 sso-bridge → $SSO —— **使用者從 www 跳轉進來會撞到這個**"
    echo "    首頁是 200 而它不是 ⇒ 不是入口問題，是這條路徑本身"
    exit 1
else
    echo "  ⚠ 公網 sso-bridge → $SSO（預期 401/403；非致命但值得看一眼）"
fi

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
echo "[7/8] 部署後四層驗證（含 ORM／認證鏈，L76 + L93）..."
if python "$(dirname "$0")/../checks/deploy_verify.py"; then
    echo "  ✓ 四層皆通過"
else
    echo "  ✗ 部署後驗證失敗 —— 公網 200 不代表系統能用（見上方逐層結果）"
    exit 1
fi

# ── Step 8: 業務鏈實測（第五層，2026-09-03 G4）──────────────────────
# 四層驗的是「服務起來了」；這一層在容器內打端點走整條鏈（建案→報價→成案→第一期→同步→409），
# 全部 __PROBE__ 標記、跑完硬刪。今天三次「部署後才發現」都是這一層抓到的形狀。
echo ""
echo "[8/8] 業務鏈實測（容器內端點，scripts/verify/post_deploy_probe.py）..."
_PROBE_OUT=$(MSYS_NO_PATHCONV=1 docker exec -i -w /app ck_missive_backend python - < "$(dirname "$0")/../verify/post_deploy_probe.py" 2>/dev/null | grep -v '^{"event"')
printf '%s
' "$_PROBE_OUT" | grep "✅\|❌\|殘留" | sed 's/^/  /'
_PROBE=$(printf '%s
' "$_PROBE_OUT" | grep "^RESULT" | tail -1)
case "$_PROBE" in
    RESULT*) _P=${_PROBE#RESULT }; if [ "${_P%%/*}" = "${_P##*/}" ]; then echo "  ✓ 業務鏈 $_P"; else echo "  ✗ 業務鏈 $_P —— 服務起來了但流程斷了"; exit 1; fi ;;
    *) echo "  ✗ 業務鏈實測沒有回傳 RESULT（腳本崩潰）"; exit 1 ;;
esac

echo ""
echo "══════════════════════════════════════"
echo "  Deploy complete — ${RUNTIME_VERSION} @ ${RUNTIME_COMMIT}"
echo "══════════════════════════════════════"
