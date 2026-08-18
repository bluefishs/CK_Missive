#!/bin/bash
# ============================================================
# SOUL.md 手動同步腳本（Missive → CK_AaaP/hermes-stack）
#
# ⛔ 2026-08-02：**目前不應執行本腳本**（保留供未來架構改變時參考）
#
#   1. 目標檔不生效：Hermes `active_profile=meta`，實際載入的是
#      `/opt/data/profiles/meta/SOUL.md`；本腳本寫的 hermes-stack/SOUL.md
#      對應 root `/opt/data/SOUL.md` —— 寫過去沒有任何效果。
#      （這正是 2026-06-02 記載的「一直在改錯檔」。）
#   2. 前提已不成立：ADR-CK-003（2026-06-03）定調坤哥（Missive 意識體）與
#      meta（AaaP 整體大腦）是**不同意識體**，內容不同是設計而非 drift。
#   3. 若有人把它改成寫入 meta：會覆蓋 6/16 加入的業務查詢強制規則（baseline GO 的關鍵），
#      且 6/16 實測 SOUL 強化為負向（仍捏造 + 慢檢索 113-280s，已還原）。
#
#   已登記於 docs/architecture/TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md §1.9。
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
FORCE=false
for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=true ;;
        --i-know-this-is-forbidden) FORCE=true ;;
    esac
done

# -- fail-closed guard (2026-08-18) ---------------------------------------
# 上面那道 ⛔ 禁令原本只活在註解裡 —— 2026-08-15 有人把本腳本包成每日 Windows
# 排程 `CK_Missive-SOUL-Mirror-Sync --apply`（不在版控、無決策紀錄），從此每天
# 04:45 把坤哥人格覆蓋掉 CK_AaaP 的 Meta 部署源 SOUL.md，且 LastResult=0 一路綠燈。
# 2026-08-18 覆盤揪出並還原。教訓：**「不應執行」若沒有寫成 exit，就不是禁令，
# 只是建議** —— 包一層 scheduler 就繞過去了，而且繞過去時沒有任何東西會叫。
# 對策：--apply 預設 fail-closed；要真的跑必須額外明示 --i-know-this-is-forbidden，
# 讓「刻意違反」在命令列上留下痕跡（排程若照舊參數呼叫，會被擋下並回非 0）。
if [[ "$APPLY" == true && "$FORCE" != true ]]; then
    echo "[BLOCKED] 拒絕執行：本腳本自 2026-08-02 起不應執行（見檔頭三點理由）。" >&2
    echo "   坤哥（Missive 意識體）與 meta（AaaP 整體大腦）是不同意識體，" >&2
    echo "   內容不同是 ADR-CK-003 的設計，不是 drift。" >&2
    echo "   已登記：docs/architecture/TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md 1.9" >&2
    echo "   若架構真的改變、確定要同步：加 --i-know-this-is-forbidden 明示。" >&2
    exit 3
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
