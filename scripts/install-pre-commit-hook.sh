#!/usr/bin/env bash
#
# 安裝 pre-commit-block-destructive.sh 為 git pre-commit hook
#
# 跨 repo 用法（從 CK_Website 拷貝到目標 repo 後）：
#   bash scripts/install-pre-commit-hook.sh
#
# 或：
#   bash scripts/install-pre-commit-hook.sh --check   # dry-run，看會做什麼
#
set -euo pipefail

CHECK_ONLY=0
if [[ "${1:-}" == "--check" ]]; then CHECK_ONLY=1; fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/scripts/pre-commit-block-destructive.sh"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [[ ! -f "$HOOK_SRC" ]]; then
  echo "❌ 找不到 $HOOK_SRC"
  echo "   先把 pre-commit-block-destructive.sh 拷貝到目標 repo 的 scripts/"
  exit 1
fi

if [[ -f "$HOOK_DST" ]] && ! grep -q "pre-commit-block-destructive" "$HOOK_DST" 2>/dev/null; then
  echo "⚠️  $HOOK_DST 已存在但不是本 hook。需手動合併或備份。"
  echo "    現有 hook:"
  head -5 "$HOOK_DST"
  exit 2
fi

if [[ $CHECK_ONLY -eq 1 ]]; then
  echo "[dry-run] 將建立 symlink: $HOOK_DST → $HOOK_SRC"
  exit 0
fi

ln -sf "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_SRC"

echo "✅ pre-commit hook 已安裝："
echo "   $HOOK_DST → $HOOK_SRC"
echo ""
echo "驗證："
echo "   echo 'DROP TABLE foo;' > /tmp/test.sql && git add /tmp/test.sql && git commit -m test"
echo "   應看到 [pre-commit] ❌ Rule D1-DropTable blocked"
echo ""
echo "緊急 bypass（不建議）："
echo "   ALLOW_DESTRUCTIVE=1 git commit ..."
