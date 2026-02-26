#!/bin/bash
# session-init.sh - SessionStart hook (workspace template v1.0)
# Auto-detects project name, branch, recent commits, and test file counts
# Install: cp to <project>/.claude/hooks/session-init.sh

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
PROJECT_NAME=$(basename "$PROJECT_DIR")

# Gather context (all read-only operations)
BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || echo "unknown")
RECENT_COMMITS=$(git -C "$PROJECT_DIR" log --oneline -5 2>/dev/null || echo "no commits")
DIRTY_FILES=$(git -C "$PROJECT_DIR" status --short 2>/dev/null | head -10)

# Auto-detect test files (Python + JS/TS)
BE_TESTS=$(find "$PROJECT_DIR" -path "*/tests/test_*.py" -o -path "*/tests/*_test.py" 2>/dev/null | wc -l | tr -d ' ')
FE_TESTS=$(find "$PROJECT_DIR/src" -name "*.test.*" -o -name "*.spec.*" 2>/dev/null | wc -l | tr -d ' ')

# Build context string
CONTEXT="## ${PROJECT_NAME} 專案快照
- **分支**: ${BRANCH}
- **最近提交**:
\`\`\`
${RECENT_COMMITS}
\`\`\`
- **未提交變更**: ${DIRTY_FILES:-（無）}
- **測試檔案**: 後端 ${BE_TESTS} / 前端 ${FE_TESTS}"

# Output JSON with additionalContext
cat <<EOF
{
  "additionalContext": $(echo "$CONTEXT" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"${PROJECT_NAME} context unavailable\"")
}
EOF
