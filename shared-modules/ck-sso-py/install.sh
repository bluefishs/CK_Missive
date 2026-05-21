#!/usr/bin/env bash
# ck-sso-py install.sh v1.0 (2026-05-21)
#
# 安裝 ck-sso-py 到 consumer repo (lvrland/pile/AaaP/hermes-agent/...)。
# 含 L41 教訓制度化：4 acceptance check 任一 fail 拒絕 install。
#
# Usage:
#   bash <ck-sso-py-path>/install.sh --target=<consumer-repo-root> --system-name=<name>
#
# Example:
#   bash D:/CKProject/CK_Missive/shared-modules/ck-sso-py/install.sh \
#     --target=D:/CKProject/CK_lvrland_Webmap \
#     --system-name=lvrland

set -euo pipefail

# ─── 解析參數 ─────────────────────────────────────────────────
TARGET=""
SYSTEM_NAME=""
DRY_RUN="false"
FORCE="false"

for arg in "$@"; do
  case $arg in
    --target=*) TARGET="${arg#*=}" ;;
    --system-name=*) SYSTEM_NAME="${arg#*=}" ;;
    --dry-run) DRY_RUN="true" ;;
    --force) FORCE="true" ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

if [[ -z "$TARGET" || -z "$SYSTEM_NAME" ]]; then
  echo "Usage: $0 --target=<consumer-repo-root> --system-name=<name> [--dry-run] [--force]"
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  echo "❌ TARGET dir not exist: $TARGET"
  exit 1
fi

# system_name title-case for comments (missive → Missive)
SYSTEM_TITLE="$(echo "$SYSTEM_NAME" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "═════════════════════════════════════════════════════════"
echo " ck-sso-py v1.0 install"
echo "─────────────────────────────────────────────────────────"
echo "  Source:      $SCRIPT_DIR"
echo "  Target:      $TARGET"
echo "  System name: $SYSTEM_NAME ($SYSTEM_TITLE)"
echo "  Dry-run:     $DRY_RUN"
echo "  Force:       $FORCE"
echo "═════════════════════════════════════════════════════════"

# ─── 拷貝檔案 ─────────────────────────────────────────────────

copy_file() {
  local src="$1"
  local dst="$2"
  if [[ -f "$dst" && "$FORCE" != "true" ]]; then
    echo "⚠️  SKIP (exists): $dst (use --force to overwrite)"
    return 0
  fi
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 DRY-RUN: copy $src → $dst"
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "✅ COPIED: $dst"
  fi
}

# 1) backend/app/core/ck_sso.py (純函數 100% portable)
copy_file \
  "$SCRIPT_DIR/backend/core/ck_sso.py" \
  "$TARGET/backend/app/core/ck_sso.py"

# 2) backend/app/api/endpoints/auth/sso_bridge.py (sed-replace SYSTEM_NAME)
TEMPLATE="$SCRIPT_DIR/backend/api_endpoints/sso_bridge.py.template"
DST_BRIDGE="$TARGET/backend/app/api/endpoints/auth/sso_bridge.py"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "🔍 DRY-RUN: sed-render $TEMPLATE → $DST_BRIDGE (SYSTEM_NAME=$SYSTEM_NAME)"
else
  if [[ -f "$DST_BRIDGE" && "$FORCE" != "true" ]]; then
    echo "⚠️  SKIP (exists): $DST_BRIDGE"
  else
    mkdir -p "$(dirname "$DST_BRIDGE")"
    sed -e "s/__SYSTEM_NAME__/$SYSTEM_NAME/g" \
        -e "s/__SYSTEM_NAME_TITLE__/$SYSTEM_TITLE/g" \
        "$TEMPLATE" > "$DST_BRIDGE"
    echo "✅ RENDERED: $DST_BRIDGE (SYSTEM_NAME=$SYSTEM_NAME)"
  fi
fi

# 3) backend/tests/unit/test_ck_sso_verify.py
copy_file \
  "$SCRIPT_DIR/backend/tests/test_ck_sso_verify.py" \
  "$TARGET/backend/tests/unit/test_ck_sso_verify.py"

# ─── L41 4 acceptance check ──────────────────────────────────

echo ""
echo "═════════════════════════════════════════════════════════"
echo " L41 教訓：4 acceptance check（任一 fail = install 不算真活）"
echo "═════════════════════════════════════════════════════════"

FAIL_COUNT=0

# Check 1: backend secret 與 CF Pages 一致（owner 手動比對 hex，這裡只檢查 .env 有設）
echo ""
echo "🔍 Check 1: backend .env 包含 CK_SSO_JWT_SECRET？"
if [[ -f "$TARGET/.env" ]] && grep -q "^CK_SSO_JWT_SECRET=" "$TARGET/.env"; then
  echo "  ✅ CK_SSO_JWT_SECRET found in .env"
  echo "  ⚠️  ACTION：owner 必手動比對 hex 與 CF Pages JWT_SECRET（重蹈 L41 風險）"
else
  echo "  ❌ CK_SSO_JWT_SECRET NOT FOUND in $TARGET/.env"
  echo "     請手動加入：CK_SSO_JWT_SECRET=<與 CF Pages JWT_SECRET 同值 hex>"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Check 2: verify 失敗 log 是 warning 非 debug（L37/L41 反模式守護）
echo ""
echo "🔍 Check 2: verify_ck_sso_jwt 失敗 log 是 warning 非 debug？"
if grep -q "logger.warning.*JWT.*INVALID\|logger.warning.*EXPIRED\|logger.warning.*ISSUER" \
   "$TARGET/backend/app/core/ck_sso.py" 2>/dev/null; then
  echo "  ✅ warning logs 命中（L37 silent fail 反模式已守護）"
else
  echo "  ❌ 沒命中 warning logs - 可能 ck_sso.py 是舊版（debug 級 silent fail）"
  echo "     確認版本：head -20 $TARGET/backend/app/core/ck_sso.py"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Check 3: SSO bridge endpoint 健康（需 backend running 才能跑，提示 owner）
echo ""
echo "🔍 Check 3: SSO bridge endpoint 健康（owner 手動跑）"
echo "  ACTION：backend running 時跑："
echo "    curl -X POST http://localhost:8001/api/auth/sso-bridge -d '{}' -i"
echo "    預期 401 + body「缺少 SSO cookie」（非 500/404/timeout）"

# Check 4: owner 真 E2E（不可省略！L41 教訓）
echo ""
echo "🔍 Check 4: owner 真 E2E（⚠️  不可省略 - L41 教訓）"
echo "  ACTION：完整流程"
echo "    1. 全新無痕視窗 → https://www.cksurvey.tw/login → Google 登入"
echo "    2. 進 dashboard → 點 $SYSTEM_TITLE 卡片"
echo "    3. 跳到 $SYSTEM_NAME.cksurvey.tw 應自動進系統"
echo "    4. backend log 應出現:"
echo "       [SSO-BRIDGE] received cookies=[...,ck_employee=present...]"
echo "       LOGIN_SUCCESS auth_provider=ck_sso_bridge"
echo "    5. 若仍 401 → 看 [CK_SSO] warning log 找 4 種 JWT exception 真因"
echo "       SIGNATURE INVALID → secret 不一致（與 CF Pages 對齊）"
echo "       EXPIRED → 重新 login www"
echo "       ISSUER INVALID / MISSING CLAIM → 異常情況需追"

# ─── 結算 ─────────────────────────────────────────────────────

echo ""
echo "═════════════════════════════════════════════════════════"
if [[ $FAIL_COUNT -gt 0 ]]; then
  echo " ⚠️  Install completed but $FAIL_COUNT auto-check FAILED"
  echo "    請修上述 fail 項目後重跑"
  echo "    或忽略，但 Check 4 owner E2E 必跑"
  echo "═════════════════════════════════════════════════════════"
  exit 1
else
  echo " ✅ Install + 2 auto-check PASS"
  echo " ⚠️  剩 Check 3 + Check 4 須 owner 手動跑（L41 教訓不可省略）"
  echo "═════════════════════════════════════════════════════════"
  exit 0
fi
