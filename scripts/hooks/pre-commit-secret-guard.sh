#!/usr/bin/env bash
# pre-commit-secret-guard.sh — 阻擋敏感檔案誤 add（可隨 repo 分發）
#
# 安裝（每個開發者首次 clone 後執行一次）：
#   bash scripts/hooks/install-hooks.sh
#
# 或手動：
#   cp scripts/hooks/pre-commit-secret-guard.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# 敏感檔案模式（禁止 commit）
SENSITIVE_PATTERNS='\.env$|\.env\.[^.]+$|credentials\.json$|\.pem$|\.key$|secrets/.+\.(txt|yml|yaml)$'
# 允許例外（範例 / 樣板檔）
ALLOWED_EXCEPTIONS='\.env\.example$|\.env\.template$|\.env\.sample$|secrets/README\.md$|secrets/\.gitkeep$'

SENSITIVE_FILES=$(git diff --cached --name-only | grep -E "$SENSITIVE_PATTERNS" | grep -vE "$ALLOWED_EXCEPTIONS" || true)

if [ -n "$SENSITIVE_FILES" ]; then
    echo -e "${RED}[pre-commit] ✖ 偵測到敏感檔案欲進入版本控制：${NC}"
    echo "$SENSITIVE_FILES" | sed 's/^/    /'
    echo -e "${YELLOW}[pre-commit] 對策：${NC}"
    echo "    1. 若為真實密碼 → git reset HEAD <file> 取消加入，確認 .gitignore 已涵蓋"
    echo "    2. 若為範例檔 → 改名為 .env.example / .template / .sample"
    echo "    3. 若確定要提交（極少情境） → git commit --no-verify"
    exit 1
fi

# 額外檢查：diff 內容含疑似密碼關鍵字（寬鬆警告，不阻擋）
SUSPICIOUS_LINES=$(git diff --cached -U0 | grep -E '^\+' | grep -viE '^\+\+\+' \
    | grep -iE '(password|passwd|secret|api[_-]?key|token|credential)\s*[:=]\s*["\x27]?[A-Za-z0-9_-]{16,}' \
    | head -3 || true)

if [ -n "$SUSPICIOUS_LINES" ]; then
    echo -e "${YELLOW}[pre-commit] ⚠ 警告：staged diff 含疑似密碼關鍵字（前 3 行）：${NC}"
    echo "$SUSPICIOUS_LINES" | sed 's/^/    /'
    echo -e "${YELLOW}[pre-commit] 請人工確認非真實密碼；若確認無虞，此警告不阻擋 commit。${NC}"
fi

echo -e "${GREEN}[pre-commit] ✓ 敏感檔案檢查通過${NC}"
exit 0
