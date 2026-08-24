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

# 2026-08-24：scripts/ 先前**完全沒有被安裝** —— 而容器裡確實跑著一支
# scripts/query.py（240 行，2026-06-03 手改後三個月沒回到任何 repo）。
# 兩個缺口疊在一起的後果：改動不會進 diff，而重跑本腳本也不會部署它
# ⇒ 版控與 runtime 各走各的，且**兩邊都不會報錯**。
# ⚠️ 這裡刻意**不覆蓋既有檔案**（`cp -n`）—— 容器裡那支可能還有其他
#    未回流的手改，直接覆蓋會把它們清掉而沒有人知道。要強制更新請先
#    比對 diff 再手動處理。
mkdir -p "$TARGET/scripts"
cp -n "$SRC_DIR/scripts/"*.py "$TARGET/scripts/" 2>/dev/null || true
chmod +x "$TARGET/scripts/"*.py 2>/dev/null || true

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
