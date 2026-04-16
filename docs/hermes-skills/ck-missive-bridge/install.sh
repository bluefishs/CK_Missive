#!/usr/bin/env bash
# CK_Missive Bridge v2.0 — install into Hermes skill directory
# Usage: bash install.sh [hermes_skill_dir]
set -euo pipefail

TARGET="${1:-$HOME/.hermes/skills/ck-missive-bridge}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$TARGET/references"
cp "$SRC_DIR/SKILL.md" "$TARGET/"
cp "$SRC_DIR/tools.py" "$TARGET/"
cp "$SRC_DIR/tool_spec.json" "$TARGET/"
cp -r "$SRC_DIR/references/"* "$TARGET/references/" 2>/dev/null || true

cat <<EOF

  CK_Missive Bridge v2.0 installed to: $TARGET

  必要環境變數（加到 ~/.hermes/.env）：
    MISSIVE_BASE_URL=https://missive.cksurvey.tw
    MISSIVE_API_TOKEN=<token-from-missive-admin>
    MISSIVE_TIMEOUT_S=60

  驗證：
    hermes tools list | grep missive_
    hermes chat "查案號 CK2026001 的最新狀態"

  升級：重新執行本腳本即可覆蓋。

EOF
