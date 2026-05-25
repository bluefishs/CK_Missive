#!/usr/bin/env bash
# scripts/sync_toolkit.sh — 同步 master scripts/ 到 ck-modular-toolkit
#
# v6.10 P1 統一同步策略（選項 D）
#
# 用法：
#   bash scripts/sync_toolkit.sh           # 同步 + diff 確認
#   bash scripts/sync_toolkit.sh --check   # 只 diff 不同步（CI 用）
#
# 策略：scripts/checks/ 為 master，shared-modules/ck-modular-toolkit/checks/ 自動同步

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MASTER="${ROOT}/scripts/checks"
TOOLKIT="${ROOT}/shared-modules/ck-modular-toolkit/checks"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

# 同步清單：master → toolkit
declare -a SYNC_FILES=(
    "module_portability_audit.py"
    "naming_convention_audit.py"
    "data/business_keyword_blacklist.yml"
)

echo "============================================================"
echo " Toolkit Sync — master scripts/ → ck-modular-toolkit/"
echo "============================================================"
echo " Master : ${MASTER}"
echo " Toolkit: ${TOOLKIT}"
echo " Mode   : $([ ${CHECK_ONLY} -eq 1 ] && echo CHECK-ONLY || echo SYNC)"
echo ""

DIFF_COUNT=0
SYNC_COUNT=0

for rel in "${SYNC_FILES[@]}"; do
    src="${MASTER}/${rel}"
    dst="${TOOLKIT}/${rel}"

    if [[ ! -f "$src" ]]; then
        echo "  [SKIP] $rel - master not found"
        continue
    fi

    if [[ ! -f "$dst" ]]; then
        echo "  [MISSING] $rel - toolkit copy missing"
        DIFF_COUNT=$((DIFF_COUNT+1))
        if [[ ${CHECK_ONLY} -eq 0 ]]; then
            mkdir -p "$(dirname "$dst")"
            cp -p "$src" "$dst"
            echo "    -> created"
            SYNC_COUNT=$((SYNC_COUNT+1))
        fi
        continue
    fi

    if ! diff -q "$src" "$dst" > /dev/null 2>&1; then
        echo "  [DIFF] $rel"
        DIFF_COUNT=$((DIFF_COUNT+1))
        if [[ ${CHECK_ONLY} -eq 0 ]]; then
            cp -p "$src" "$dst"
            echo "    -> synced"
            SYNC_COUNT=$((SYNC_COUNT+1))
        fi
    else
        echo "  [OK]   $rel"
    fi
done

# 同步 standards/ docs（從 docs/architecture/ → toolkit/standards/）
declare -A STANDARDS_MAP=(
    ["docs/architecture/NAMING_CONVENTIONS.md"]="standards/NAMING_CONVENTIONS.md"
    ["docs/architecture/CONTRACTS_LAYER_GUIDE.md"]="standards/CONTRACTS_LAYER_GUIDE.md"
    ["docs/architecture/CONTRACTS_MIGRATION_PATTERN.md"]="standards/CONTRACTS_MIGRATION_PATTERN.md"
    ["docs/architecture/MODULAR_INVENTORY.md"]="standards/MODULAR_INVENTORY.md"
)

TOOLKIT_ROOT="${ROOT}/shared-modules/ck-modular-toolkit"
for src_rel in "${!STANDARDS_MAP[@]}"; do
    src="${ROOT}/${src_rel}"
    dst="${TOOLKIT_ROOT}/${STANDARDS_MAP[$src_rel]}"

    if [[ ! -f "$src" ]]; then
        continue
    fi

    if [[ ! -f "$dst" ]] || ! diff -q "$src" "$dst" > /dev/null 2>&1; then
        echo "  [DIFF] $src_rel"
        DIFF_COUNT=$((DIFF_COUNT+1))
        if [[ ${CHECK_ONLY} -eq 0 ]]; then
            mkdir -p "$(dirname "$dst")"
            cp -p "$src" "$dst"
            echo "    -> synced"
            SYNC_COUNT=$((SYNC_COUNT+1))
        fi
    fi
done

echo ""
echo "============================================================"
if [[ ${CHECK_ONLY} -eq 1 ]]; then
    echo " Check result: ${DIFF_COUNT} files out-of-sync"
    if [[ ${DIFF_COUNT} -gt 0 ]]; then
        echo " Run 'bash scripts/sync_toolkit.sh' to sync"
        exit 1
    fi
else
    echo " Sync complete: ${SYNC_COUNT} files updated"
fi
echo "============================================================"
