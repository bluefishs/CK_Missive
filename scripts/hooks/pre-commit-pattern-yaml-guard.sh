#!/usr/bin/env bash
# pre-commit-pattern-yaml-guard.sh — 2026-04-24 ADR-0028
#
# 掃 staged wiki/memory/{patterns,failures,proposals,evolutions}/*.md
# 檢查 id-like YAML 欄位（template_hash / pattern_id / session_id 等）
# 純數字未加引號 → 會被 YAML parse 為 int → sorted mixed types 爆錯
# 造成 /api/ai/memory/nebula/graph 500 高頻錯誤。
#
# 失敗時提示 --fix 自動修正指令。

set -eo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# 只在有 memory/*.md staged 變更時執行
STAGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null \
    | grep -E '^wiki/memory/(patterns|failures|proposals|evolutions)/.*\.md$' || true)

if [ -z "$STAGED" ]; then
    exit 0
fi

echo "[pattern-yaml-guard] 偵測到 memory/*.md 變更，執行型別檢查..."

GUARD_SCRIPT="$PROJECT_ROOT/scripts/checks/pattern_yaml_type_guard.py"
if [ ! -f "$GUARD_SCRIPT" ]; then
    echo "[pattern-yaml-guard] 跳過 — guard script 不存在：$GUARD_SCRIPT"
    exit 0
fi

if python "$GUARD_SCRIPT"; then
    echo "[pattern-yaml-guard] OK"
    exit 0
fi

echo ""
echo "[pattern-yaml-guard] 發現型別問題。自動修正："
echo "    python scripts/checks/pattern_yaml_type_guard.py --fix"
echo "    git add wiki/memory/"
echo ""
exit 1
