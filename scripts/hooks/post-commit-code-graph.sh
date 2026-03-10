#!/bin/bash
# GitNexus post-commit hook — 自動增量更新代碼圖譜
#
# 安裝方式:
#   cp scripts/hooks/post-commit-code-graph.sh .git/hooks/post-commit
#   chmod +x .git/hooks/post-commit
#
# 或使用 git config:
#   git config core.hooksPath scripts/hooks
#
# 此 hook 在每次 commit 後自動執行 GitNexus 增量模式，
# 僅掃描已變更的檔案，通常 <2 秒完成。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 若從 scripts/hooks/ 執行，調整路徑
if [ -f "$SCRIPT_DIR/../../scripts/generate-code-graph.py" ]; then
    PROJECT_ROOT="$SCRIPT_DIR/../.."
elif [ -f "$PROJECT_ROOT/scripts/generate-code-graph.py" ]; then
    : # already correct
else
    # Fallback: try git root
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
fi

GENERATOR="$PROJECT_ROOT/scripts/generate-code-graph.py"

if [ ! -f "$GENERATOR" ]; then
    echo "[GitNexus] Generator not found: $GENERATOR"
    exit 0  # non-blocking
fi

# Run in background to avoid slowing down commits
(
    cd "$PROJECT_ROOT" || exit 0
    python "$GENERATOR" --incremental 2>/dev/null
) &

exit 0
