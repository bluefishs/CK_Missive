#!/bin/bash
#
# dispatch_cache_contract.sh — 派工 cache 契約 lint
#
# 領域：派工 write-side 必須透過 useDispatchCacheInvalidator 集中 invalidate，
# 不可在 mutation 中直接寫 `invalidateQueries({ queryKey: ['dispatch-morning-status'] })`。
#
# 為什麼：
#   v5.10.x 曾因散落 9 處 invalidate 漏掉一處而導致派工總覽顯示漂移。
#   集中到 hook 後，新 mutation 從 hook 提供的 4 個方法擇一即可，無從遺漏。
#
# 違規：在 frontend/src 內找到「直接 invalidate dispatch-morning-status」
#      但不在 useDispatchCacheInvalidator.ts 自己的檔案
#
# 用法：bash scripts/checks/dispatch_cache_contract.sh
# 退出碼：0 = 合規 / 1 = 有違規

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_SRC="$REPO_ROOT/frontend/src"
HOOK_FILE="hooks/taoyuan/useDispatchCacheInvalidator.ts"

cd "$REPO_ROOT" || exit 2

echo "=== Dispatch Cache Contract Lint ==="
echo "領域：派工 write-side 必須透過 useDispatchCacheInvalidator hook"
echo ""

# 找直接 invalidate dispatch-morning-status 的（排除 hook 自己 + 註解 + 字串文件）
violations=$(grep -rn "invalidateQueries.*dispatch-morning-status" \
    "$FRONTEND_SRC" \
    --include="*.ts" --include="*.tsx" \
    2>/dev/null | grep -v "$HOOK_FILE" || true)

if [ -n "$violations" ]; then
    echo "[FAIL] 發現直接 invalidate 違規（必須透過 hook）："
    echo ""
    echo "$violations"
    echo ""
    echo "修復方式："
    echo "  1. 引入：import { useDispatchCacheInvalidator } from '<相對路徑>/hooks/taoyuan/useDispatchCacheInvalidator';"
    echo "  2. 在元件內：const dispatchCache = useDispatchCacheInvalidator();"
    echo "  3. 在 onSuccess 內呼叫對應方法："
    echo "       - 派工本體 CRUD       → dispatchCache.invalidateDispatchAggregate()"
    echo "       - 作業紀錄 CRUD       → dispatchCache.invalidateWorkRecord()"
    echo "       - 工程關聯 link/unlink → dispatchCache.invalidateProjectLinks()"
    echo "       - 看板狀態切換         → dispatchCache.invalidateKanbanStatus(projectId)"
    echo "       - 純 morning-status   → dispatchCache.invalidateMorningStatusOnly()"
    exit 1
fi

# 統計 hook 使用情況（informational）
hook_users=$(grep -rln "useDispatchCacheInvalidator" \
    "$FRONTEND_SRC" \
    --include="*.ts" --include="*.tsx" \
    2>/dev/null | grep -v "$HOOK_FILE" | wc -l)

echo "[OK] 所有派工 invalidate 集中於 useDispatchCacheInvalidator"
echo "     目前 $hook_users 處透過 hook 呼叫"
exit 0
