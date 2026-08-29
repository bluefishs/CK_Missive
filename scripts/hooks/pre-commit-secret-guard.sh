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

# ============================================================
# 供應商金鑰前綴（阻擋）—— 2026-08-30 新增
# ============================================================
# 為什麼要這一層：下面那個「關鍵字 + [:=]」的判準**看不見裸字面**。
# 實測（同日）：
#   const apiKey = "sk-proj-…"   → 警告（有關鍵字）
#   const k      = "sk-proj-…"   → **完全無聲**
#   X = "sk-ant-api03-…"         → **完全無聲**
#   value: ghp_…／id = AKIA…      → **完全無聲**
# ⇒ **最高信心、也最傷的那種形狀，正好是它看不見的那種。**
#
# 這一層阻擋（不只警告），理由：①前綴具體 ⇒ 誤報極低
# ②洩漏憑證進了 git 歷史是不可逆的。實測對全 repo 追蹤中的檔案掃描，
# **只有 1 個命中**（`backend/tests/unit/test_autobiography.py` 的測試用假金鑰，
# 已加下方 allowlist 標記）；佔位字串 `sk-proj-xxxxx` 因長度不足而正確不命中。
#
# 合法用途的出口：在該行加上 `pragma: allowlist secret`。
KEY_PREFIX_PATTERN='(sk-ant-[A-Za-z0-9_-]{24,}|sk-proj-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{30,})'

KEY_HITS=$(git diff --cached -U0 | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "$KEY_PREFIX_PATTERN" \
    | grep -viE 'pragma:[[:space:]]*allowlist[[:space:]]*secret' \
    | head -5 || true)

if [ -n "$KEY_HITS" ]; then
    echo -e "${RED}[pre-commit] ✖ 偵測到疑似供應商金鑰（前 5 行）：${NC}"
    echo "$KEY_HITS" | sed 's/^/    /'
    echo -e "${YELLOW}[pre-commit] 對策：${NC}"
    echo "    1. 若為真實金鑰 → 移除並**立即在供應商端撤銷**（已進 git 歷史則不可逆）"
    echo "    2. 若為測試用假值 → 該行加註 'pragma: allowlist secret'"
    echo "    3. 環境變數化：os.getenv('X') / import.meta.env.VITE_X"
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
