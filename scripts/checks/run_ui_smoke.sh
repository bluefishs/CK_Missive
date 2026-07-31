#!/usr/bin/env bash
# UI 流程自我檢核 — 一鍵執行（2026-07-31）
#
# 用途：把 owner 連日反覆手動點的那批頁面自動跑一遍，跑一次就知道哪一頁壞了。
# 自行簽發臨時 admin session（20 分鐘、jti 前綴 ui-smoke-），不碰任何人的登入狀態。
#
#   bash scripts/checks/run_ui_smoke.sh              # 全部
#   bash scripts/checks/run_ui_smoke.sh --only=line  # 單項
#
# 退出碼：0 全過 / 1 有 FAIL / 2 未驗完（有 SKIP，不得視為通過）
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUTH_OUT="$(mktemp)"
trap 'rm -f "$AUTH_OUT"' EXIT

echo "[1/2] 簽發臨時檢核 session..."
if ! MSYS_NO_PATHCONV=1 docker exec ck_missive_backend \
     python //app/scripts/checks/ui_smoke_auth.py > "$AUTH_OUT" 2>/dev/null; then
  echo "  ⚠️  簽發失敗（後端容器未啟動？）—— 僅能跑免登入項目"
fi

COOKIE_VAL="$(grep '^COOKIE=' "$AUTH_OUT" 2>/dev/null | sed 's/^COOKIE=//' | tr -d '\r\n')"
USER_INFO_VAL="$(grep '^USER_INFO=' "$AUTH_OUT" 2>/dev/null | sed 's/^USER_INFO=//' | tr -d '\r\n')"

echo "[2/2] 執行瀏覽器檢核..."
COOKIE="$COOKIE_VAL" USER_INFO="$USER_INFO_VAL" \
  node "$ROOT/scripts/checks/ui_flow_smoke.cjs" "$@"
