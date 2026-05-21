#!/usr/bin/env bash
# ck-sso-js install.sh v1.0 (2026-05-21)
#
# 安裝 ck-sso-js 到 consumer frontend repo (lvrland/pile/digitaltwin/...)。
# 含 L41 + L43 教訓制度化：5 acceptance check（Check 5 是 ground-truth log 防 dormant）。
#
# Usage:
#   bash install.sh --target=<consumer-frontend-dir> --framework=<react|vue|vanilla> [--dry-run] [--force]
#
# Example:
#   bash D:/CKProject/CK_Missive/shared-modules/ck-sso-js/install.sh \
#     --target=D:/CKProject/CK_lvrland_Webmap/frontend \
#     --framework=react

set -euo pipefail

TARGET=""
FRAMEWORK=""
DRY_RUN="false"
FORCE="false"

for arg in "$@"; do
  case $arg in
    --target=*)    TARGET="${arg#*=}" ;;
    --framework=*) FRAMEWORK="${arg#*=}" ;;
    --dry-run)     DRY_RUN="true" ;;
    --force)       FORCE="true" ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

if [[ -z "$TARGET" || -z "$FRAMEWORK" ]]; then
  echo "Usage: $0 --target=<consumer-frontend-dir> --framework=<react|vue|vanilla>"
  exit 1
fi

[[ ! -d "$TARGET" ]] && { echo "❌ TARGET dir not exist: $TARGET"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$TARGET/src/lib/ck-sso-js"

echo "═════════════════════════════════════════════════════════"
echo " ck-sso-js v1.0 install"
echo "─────────────────────────────────────────────────────────"
echo "  Source:    $SCRIPT_DIR"
echo "  Target:    $DST"
echo "  Framework: $FRAMEWORK"
echo "  Dry-run:   $DRY_RUN"
echo "  Force:     $FORCE"
echo "═════════════════════════════════════════════════════════"

if [[ -d "$DST" && "$FORCE" != "true" ]]; then
  echo "⚠️  $DST exists. Use --force to overwrite."
  exit 1
fi

# ─── 拷貝 src/ ────────────────────────────────────────────────
if [[ "$DRY_RUN" == "true" ]]; then
  echo "🔍 DRY-RUN: would copy $SCRIPT_DIR/src/ → $DST/"
else
  mkdir -p "$DST"
  cp -r "$SCRIPT_DIR/src/." "$DST/"
  echo "✅ COPIED src/ → $DST"
fi

# 框架不是 react → 移除 React hook 避免 missing peer dep
if [[ "$FRAMEWORK" != "react" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 DRY-RUN: would remove $DST/react/ (framework=$FRAMEWORK)"
  else
    rm -rf "$DST/react"
    echo "✅ Removed react/ (framework=$FRAMEWORK)"
    # 同時改 index.ts 不 re-export
    sed -i.bak "/useSSOBridge/d" "$DST/index.ts" 2>/dev/null || true
  fi
fi

# ─── 5 acceptance check ──────────────────────────────────────

echo ""
echo "═════════════════════════════════════════════════════════"
echo " L41 + L43 教訓：5 acceptance check"
echo "═════════════════════════════════════════════════════════"

FAIL=0

# Check 1: consumer 環境是 React/Vite/Webpack？(看 package.json)
echo ""
echo "🔍 Check 1: package.json 有 react/vue 依賴？"
if [[ -f "$TARGET/package.json" ]]; then
  if [[ "$FRAMEWORK" == "react" ]] && grep -q '"react"' "$TARGET/package.json"; then
    echo "  ✅ react found"
  elif [[ "$FRAMEWORK" == "vue" ]] && grep -q '"vue"' "$TARGET/package.json"; then
    echo "  ✅ vue found"
  elif [[ "$FRAMEWORK" == "vanilla" ]]; then
    echo "  ✅ vanilla (skipped framework check)"
  else
    echo "  ⚠️  framework=$FRAMEWORK but $TARGET/package.json 不含對應依賴"
  fi
else
  echo "  ⚠️  $TARGET/package.json not found"
fi

# Check 2: VITE_API_BASE_URL 或等價環境變數有設？
echo ""
echo "🔍 Check 2: API base URL 環境變數設定？"
if grep -rqE "VITE_API_BASE_URL|VUE_APP_API|REACT_APP_API" "$TARGET/.env"* 2>/dev/null; then
  echo "  ✅ API base URL env var found"
else
  echo "  ⚠️  沒找到 VITE_API_BASE_URL（或等價），useSSOBridge 須手動傳 apiBaseURL"
fi

# Check 3: 後端 sso-bridge endpoint 健康（owner 手動跑）
echo ""
echo "🔍 Check 3: 後端 sso-bridge endpoint 健康 — owner 跑："
echo "    curl -X POST https://<consumer-subdomain>.cksurvey.tw/api/auth/sso-bridge -d '{}' -i"
echo "    預期 401 + body「缺少 SSO cookie」（非 500/404/timeout）"

# Check 4: ⚠️ owner 真 E2E（不可省略）
echo ""
echo "🔍 Check 4: owner 真 E2E（⚠️  不可省略 — L41/L42/L43 教訓）"
echo "    1. 在 EntryPage / LoginPage / 入口 route 加 useSSOBridge hook"
echo "    2. rebuild frontend + redeploy container"
echo "    3. 全新無痕視窗 → https://www.cksurvey.tw/login → Google 登入"
echo "    4. 進 dashboard → 點對應卡片"
echo "    5. 跳到子網域應自動進系統（不顯示 LINE/Google 登入 UI）"

# Check 5: ⚠️ L41-RECURRENCE 防護 — backend log ground-truth
echo ""
echo "🔍 Check 5: ⚠️  Owner E2E 後跑：backend log 真實出現 SSO-BRIDGE？"
echo "    docker logs <consumer-backend-container> 2>&1 | grep '\[SSO-BRIDGE\] received cookies'"
echo "    應看到 'ck_employee=present' 字串。"
echo "    若 0 hits → 前端從沒呼叫 backend → install 是 dormant（重蹈 lvrland 中午狀態）"

echo ""
echo "═════════════════════════════════════════════════════════"
echo " ✅ Install 完成。在 EntryPage 加 useSSOBridge 後跑 Check 3-5。"
echo "═════════════════════════════════════════════════════════"
