#!/bin/bash
# post-write-lint.sh - PostToolUse hook for Write|Edit (workspace template v1.0)
# Runs linter on modified files: ESLint for TS/JS, Flake8 for Python
# Install: cp to <project>/.claude/hooks/post-write-lint.sh

# Read hook input from stdin
INPUT=$(cat)

# Extract file path from tool input
FILE_PATH=$(echo "$INPUT" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Skip if no file path
if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

case "$FILE_PATH" in
  *.ts|*.tsx|*.js|*.jsx)
    # Run ESLint on the specific file
    RESULT=$(cd "$PROJECT_DIR" && npx eslint "$FILE_PATH" --max-warnings 0 --no-color 2>&1)
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
      ESCAPED=$(echo "$RESULT" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
      cat <<EOF
{
  "additionalContext": "ESLint 檢查失敗 (${FILE_PATH}):\n${ESCAPED:-$RESULT}\n\n請修復上述 lint 錯誤後重新儲存。"
}
EOF
    fi
    ;;
  *.py)
    # Run flake8 - uses project-level config (setup.cfg, .flake8, tox.ini) automatically
    RESULT=$(cd "$PROJECT_DIR" && python -m flake8 "$FILE_PATH" 2>&1)
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
      ESCAPED=$(echo "$RESULT" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
      cat <<EOF
{
  "additionalContext": "Flake8 檢查失敗 (${FILE_PATH}):\n${ESCAPED:-$RESULT}\n\n請修復上述 lint 錯誤後重新儲存。"
}
EOF
    fi
    ;;
esac

exit 0
