#!/usr/bin/env bash
# 視覺走查 — 一鍵執行（2026-08-05）
#
# 斷言式檢核看不到「截字／遮蔽／配色語意／版面錯位」，而那正是使用者會抱怨的那一類。
# 本走查把圖拍齊，**判讀在 session 內由人或 AI 進行** —— 不掛 cron，
# 因為 cron 裡沒有人在看圖。
#
# 紀律：每發現一個缺陷，必須轉成 ui_flow_smoke 的斷言，否則下次還要再看一遍。
#
#   bash scripts/checks/run_visual_walk.sh
#   MSYS_NO_PATHCONV=1 bash scripts/checks/run_visual_walk.sh --routes=/documents,/kunge
#
# ⚠️ 用 --routes= 時務必加 MSYS_NO_PATHCONV=1 —— Git Bash 會把 /documents
#    轉成 Windows 路徑，實測變成 https://missive.cksurvey.twc/Program Files/Git/...
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUTH_OUT="$(mktemp)"
trap 'rm -f "$AUTH_OUT"' EXIT

echo "[1/2] 簽發臨時檢核 session..."
if ! MSYS_NO_PATHCONV=1 docker exec ck_missive_backend \
     python //app/scripts/checks/ui_smoke_auth.py > "$AUTH_OUT" 2>/dev/null; then
  echo "  ⚠️  簽發失敗（後端容器未啟動？）—— 僅能拍免登入頁"
fi

COOKIE_VAL="$(grep '^COOKIE=' "$AUTH_OUT" 2>/dev/null | sed 's/^COOKIE=//' | tr -d '\r\n')"
USER_INFO_VAL="$(grep '^USER_INFO=' "$AUTH_OUT" 2>/dev/null | sed 's/^USER_INFO=//' | tr -d '\r\n')"

echo "[2/2] 逐頁截圖（桌面 + 手機）..."
COOKIE="$COOKIE_VAL" USER_INFO="$USER_INFO_VAL" \
  node "$ROOT/scripts/checks/.shared-selfaudit/ui_visual_walk.cjs" "$@"
