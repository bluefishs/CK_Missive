#!/usr/bin/env bash
# CK_Missive Bridge — install into Hermes skill directory
# Usage: bash install.sh [hermes_skill_dir]
set -euo pipefail

TARGET="${1:-$HOME/.hermes/skills/ck-missive-bridge}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$TARGET"
cp "$SRC_DIR/SKILL.md" "$TARGET/"
cp "$SRC_DIR/tools.py" "$TARGET/"
cp "$SRC_DIR/tool_spec.json" "$TARGET/"

cat <<EOF

✅ CK_Missive Bridge installed to: $TARGET

必要環境變數（加到 ~/.hermes/config.env 或 shell）：
  export MISSIVE_BASE_URL=http://host.docker.internal:8001
  export MISSIVE_API_TOKEN=<token-from-missive-admin>
  export MISSIVE_TIMEOUT_S=60

驗證：
  hermes tools list | grep missive_
  hermes chat "查案號 CK2026001 的最新狀態"

EOF
