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

# 深度（flow）vs 廣度（sweep）二選一
# 註：先前用 python str.replace 加這段時靜默失敗（不匹配不會報錯），
#     導致 --sweep 被當成 flow 的參數傳下去而無效 —— 改為行為單位編輯。
ARGS=()
MODE="flow"
for a in "$@"; do
  if [ "$a" = "--sweep" ]; then MODE="sweep"; else ARGS+=("$a"); fi
done

if [ "$MODE" = "sweep" ]; then
  echo "[2/2] 全站頁面健康掃描（廣度）..."
  SCRIPT=".shared-selfaudit/ui_page_sweep.cjs"
else
  echo "[2/2] 流程檢核（深度）..."
  SCRIPT=".shared-selfaudit/ui_flow_smoke.cjs"
fi

COOKIE="$COOKIE_VAL" USER_INFO="$USER_INFO_VAL"   node "$ROOT/scripts/checks/$SCRIPT" "${ARGS[@]}"
