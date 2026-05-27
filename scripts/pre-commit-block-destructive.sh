#!/usr/bin/env bash
#
# ADR-0010 Tier 5 — pre-commit hook 偵測不可逆 destructive 動作
#
# 跨 repo 通用 hook。安裝方式（per repo）：
#   ln -sf "$PWD/scripts/pre-commit-block-destructive.sh" .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# 或加入 husky / pre-commit framework：
#   husky add .husky/pre-commit "bash scripts/pre-commit-block-destructive.sh"
#
# 偵測規則（per ADR-0010 §Tier 1 + §Tier 5）：
#   D1  DROP TABLE / DROP COLUMN (any DB migration .sql / .py / .js / .ts file)
#   D2  TRUNCATE TABLE
#   D3  wrangler kv namespace delete <id>
#   D4  wrangler kv key delete --prefix
#   D5  rm -rf <prod-volume-pattern>
#   D6  git push --force / git reset --hard 出現在 script 內
#
# 規則例外（允許）：
#   - 註解或 markdown 文件中描述（grep 排除 .md 並偵測 line 是否以 # / // / -- 開頭）
#   - test fixture / SQL migration history 中 reverse （加 `-- ALLOW-DESTRUCTIVE: <reason>` 註）
#
# Bypass（緊急情況）：
#   ALLOW_DESTRUCTIVE=1 git commit -m "..."
#   或 git commit --no-verify（不建議；違反 ADR-0010 Tier 5）
#
# Exit code：
#   0  pass
#   1  blocked（含 reason 與檔案 + 行號）
#
set -euo pipefail

# 允許用環境變數臨時跳過（緊急情況；commit message 應註明）
if [[ "${ALLOW_DESTRUCTIVE:-}" == "1" ]]; then
  echo "[pre-commit] ⚠️  ALLOW_DESTRUCTIVE=1 — 跳過 destructive 偵測。請在 commit message 註明原因（ADR-0010 例外通道）。"
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 取出本次 commit staged 變更（diff filter ACMR 排除 deleted）
STAGED=$(git diff --cached --name-only --diff-filter=ACMR)

if [[ -z "$STAGED" ]]; then
  exit 0
fi

# 排除 .md / lock / ADR doc / 本 hook 本身
RELEVANT_FILES=()
while IFS= read -r f; do
  case "$f" in
    *.md|*.lock|*.lockb|*.svg|*.png|*.jpg|*.jpeg|*.gif|*.ico|*.woff|*.woff2|*.ttf|*.eot)
      continue
      ;;
    *adrs/*|*ADR*|scripts/pre-commit-block-destructive.sh|scripts/install-pre-commit-hook.sh|scripts/install-pre-commit-hook.ps1|scripts/audit-destructive-ops.cjs|docs/destructive-ops-audit.md|docs/.destructive-ops-audit-snapshot.json|docs/NEXT-SESSION-OWNER-ACTIONS.md|docs/SSO-METRICS-SPEC.md|docs/DR-DRILL-PLAYBOOK.md|docs/SSO-IMPLEMENTATION-STATUS.md|docs/RESTART-RECOVERY-SOP.md)
      continue
      ;;
  esac
  RELEVANT_FILES+=("$f")
done <<< "$STAGED"

if [[ ${#RELEVANT_FILES[@]} -eq 0 ]]; then
  exit 0
fi

BLOCKED=0
TMPOUT="$(mktemp)"
trap 'rm -f "$TMPOUT"' EXIT

check_pattern() {
  local rule="$1"
  local pattern="$2"
  local desc="$3"
  # only check added / modified lines（git diff --cached 起頭 +）
  local hits
  hits=$(git diff --cached --unified=0 -- "${RELEVANT_FILES[@]}" \
    | grep -nE '^\+' \
    | grep -vE '^\+\+\+' \
    | grep -iE "$pattern" \
    | grep -ivE '^\+\s*(#|//|--|\*|/\*)' \
    || true)
  if [[ -n "$hits" ]]; then
    echo "[pre-commit] ❌ Rule $rule blocked — $desc" >> "$TMPOUT"
    echo "$hits" | sed 's/^/    /' >> "$TMPOUT"
    BLOCKED=1
  fi
}

check_pattern "D1-DropTable"    'DROP[[:space:]]+TABLE'                          'DROP TABLE (per ADR-0010 Tier 1 禁止)'
check_pattern "D1-DropColumn"   'DROP[[:space:]]+COLUMN'                         'DROP COLUMN (per ADR-0010 Tier 4 禁止)'
check_pattern "D2-Truncate"     'TRUNCATE[[:space:]]+TABLE'                      'TRUNCATE TABLE (per ADR-0010 Tier 1 禁止)'
check_pattern "D3-KVNamespaceDelete" 'wrangler[[:space:]]+kv[[:space:]]+namespace[[:space:]]+delete' 'wrangler kv namespace delete (per ADR-0010 Tier 1 禁止)'
check_pattern "D4-KVKeyPrefix"  'wrangler[[:space:]]+kv[[:space:]]+key[[:space:]]+delete.*--prefix'  'wrangler kv key delete --prefix (per ADR-0010 Tier 1 禁止)'
check_pattern "D5-RmRf"         'rm[[:space:]]+-rf?[[:space:]]+[^"]*(prod|production|R2|data|volume)' 'rm -rf production-pattern (per ADR-0010 Tier 1 禁止)'
check_pattern "D6-ForcePush"    'git[[:space:]]+push[[:space:]]+.*--force|git[[:space:]]+push[[:space:]]+-f[[:space:]]'    'git push --force (per ADR-0010 Tier 1 禁止)'
check_pattern "D6-ResetHard"    'git[[:space:]]+reset[[:space:]]+--hard'         'git reset --hard (per ADR-0010 Tier 1 禁止)'

if [[ $BLOCKED -eq 1 ]]; then
  echo ""
  echo "==========================================================="
  echo "  ADR-0010 Tier 5 pre-commit hook 拒絕本次 commit"
  echo "==========================================================="
  cat "$TMPOUT"
  echo ""
  echo "如為合法用途（GDPR right-to-erasure / drill / 廢棄專案），"
  echo "請在 commit 訊息註明原因並用："
  echo "    ALLOW_DESTRUCTIVE=1 git commit ..."
  echo ""
  echo "詳見 adrs/0010-data-retention-and-irreversible-ops-policy.md §例外處理"
  echo ""
  exit 1
fi

exit 0
