#!/bin/bash
# ============================================================
# SOUL.md 手動同步腳本（Missive → CK_AaaP/hermes-stack）
#
# 為什麼是手動？
# - soul_loader.py docstring 聲稱「同步鏡像」但無實作（v5.9.6 發現）
# - 自動跨 repo 寫檔風險高（可能覆蓋 AaaP 端手動 edit）
# - Manual gate 讓 Owner 確認後執行 + 跨 repo commit
#
# 用法：
#   bash scripts/sync/sync_soul_to_hermes.sh           # dry-run
#   bash scripts/sync/sync_soul_to_hermes.sh --apply   # 實際同步
#
# 同步後流程（Owner 動作）：
#   cd ../CK_AaaP
#   git add runbooks/hermes-stack/SOUL.md
#   git commit -m "sync: SOUL.md from CK_Missive (drift YYYY-MM-DD)"
#   git push
#
# 關聯：
#   - scripts/checks/soul_mirror_drift_check.py（偵測 drift）
#   - docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4
#   - backend/app/services/memory/soul_loader.py docstring（待誠實化）
# ============================================================

set -uo pipefail

APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
    APPLY=true
fi

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SOURCE="wiki/SOUL.md"
TARGET="../CK_AaaP/runbooks/hermes-stack/SOUL.md"

echo -e "${CYAN}=== SOUL.md Sync (Missive → CK_AaaP/hermes-stack) ===${NC}"
echo ""

if [[ ! -f "$SOURCE" ]]; then
    echo -e "${RED}✗ Source missing: $SOURCE${NC}"
    exit 2
fi

if [[ ! -f "$TARGET" ]]; then
    echo -e "${YELLOW}⚠ Target missing: $TARGET${NC}"
    echo "  CK_AaaP 可能未 clone 在 ../ 路徑下"
    exit 2
fi

SOURCE_SIZE=$(wc -c < "$SOURCE")
TARGET_SIZE=$(wc -c < "$TARGET")
DELTA=$((SOURCE_SIZE - TARGET_SIZE))

echo "Source:  $SOURCE  ($SOURCE_SIZE bytes)"
echo "Target:  $TARGET  ($TARGET_SIZE bytes)"
echo "Delta:   $DELTA bytes"
echo ""

# 比對
if cmp -s "$SOURCE" "$TARGET"; then
    echo -e "${GREEN}✅ Files identical — no sync needed${NC}"
    exit 0
fi

# 顯示 unified diff 摘要
echo -e "${YELLOW}=== Unified diff (head) ===${NC}"
diff -u "$TARGET" "$SOURCE" 2>&1 | head -30

echo ""
if $APPLY; then
    echo -e "${CYAN}=== Applying sync ===${NC}"
    cp "$SOURCE" "$TARGET"
    echo -e "${GREEN}✓ Copied $SOURCE → $TARGET${NC}"
    echo ""
    echo "下一步（Owner 動作）："
    echo "  cd ../CK_AaaP"
    echo "  git add runbooks/hermes-stack/SOUL.md"
    echo "  git commit -m \"sync: SOUL.md from CK_Missive (drift $(date +%Y-%m-%d))\""
    echo "  git push"
else
    echo -e "${YELLOW}=== Dry-run mode (no changes applied) ===${NC}"
    echo "重跑加 --apply 才會實際覆蓋 target：bash $0 --apply"
fi
