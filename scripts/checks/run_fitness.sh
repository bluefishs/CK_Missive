#!/bin/bash
# ============================================================
# Architecture Fitness Functions — 本地月度覆盤腳本（零 CI 費用）
#
# 用戶規範：不得使用 GitHub Actions 產生費用 → 全本機執行
#
# 用法：
#   bash scripts/checks/run_fitness.sh              # warning 模式
#   bash scripts/checks/run_fitness.sh --strict     # 超標即 exit 1
#
# 建議頻率：每月架構覆盤時跑一次 / 大重構前跑一次
#
# 關聯：
#   docs/architecture/STANDARD_REFERENCE.md §12 Fitness Functions
#   docs/architecture/SERVICE_CONTEXT_MAP.md
# ============================================================

set -uo pipefail

STRICT=false
if [[ "${1:-}" == "--strict" ]]; then
    STRICT=true
fi

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN} Architecture Fitness Run       ${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

FAIL_COUNT=0

# ----------------------------------------------------------------------------
# 1. Services 頂層散戶比例
# ----------------------------------------------------------------------------
echo -e "${CYAN}[1/3] Services directory entropy${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py
fi
echo ""

# ----------------------------------------------------------------------------
# 2. Dead config reader（掃多個高信號檔）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[2/3] Dead config reader scan (multi-target v3)${NC}"

# v3 (2026-04-25): 擴為多 target 掃描
# 原 v1/v2 只掃 ai_config.py → 錯過 record_duration / get_cloud_semaphore 等 dead
# 新增核心 config/factory/metrics 檔案
SCAN_TARGETS=(
    "backend/app/services/ai/core/ai_config.py"
    "backend/app/core/inference_semaphore.py"
    "backend/app/core/inference_provider_metrics.py"
)

for target in "${SCAN_TARGETS[@]}"; do
    if [[ ! -f "$target" ]]; then
        echo -e "  ${YELLOW}⚠${NC} Skipping (missing): $target"
        continue
    fi
    echo ""
    if $STRICT; then
        PYTHONIOENCODING=utf-8 python scripts/checks/config_dead_reader_scan.py --target "$target" --ci || FAIL_COUNT=$((FAIL_COUNT+1))
    else
        PYTHONIOENCODING=utf-8 python scripts/checks/config_dead_reader_scan.py --target "$target"
    fi
done
echo ""

# ----------------------------------------------------------------------------
# 3. SOUL.md 跨 repo drift（坤哥意識體跨通道一致性）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[3/4] SOUL.md mirror drift check${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py
fi
echo ""

# ----------------------------------------------------------------------------
# 4. Wiki ↔ KG 雙向引用率
# ----------------------------------------------------------------------------
echo -e "${CYAN}[4/5] Wiki ↔ KG link audit${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py
fi
echo ""

# ----------------------------------------------------------------------------
# 5. Architecture docs presence
# ----------------------------------------------------------------------------
echo -e "${CYAN}[5/5] Architecture standard docs presence${NC}"
REQUIRED_DOCS=(
    "docs/architecture/STANDARD_REFERENCE.md"
    "docs/architecture/SERVICE_CONTEXT_MAP.md"
)
MISSING=0
for doc in "${REQUIRED_DOCS[@]}"; do
    if [[ -f "$doc" ]]; then
        echo -e "  ${GREEN}✓${NC} $doc"
    else
        echo -e "  ${RED}✗${NC} $doc MISSING"
        MISSING=$((MISSING+1))
    fi
done
if [[ $MISSING -gt 0 ]]; then
    FAIL_COUNT=$((FAIL_COUNT+1))
fi
echo ""

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
echo -e "${CYAN}================================${NC}"
if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN} All fitness checks passed${NC}"
else
    echo -e "${YELLOW} $FAIL_COUNT check(s) with warnings/fails${NC}"
    if $STRICT; then
        echo -e "${RED} STRICT mode → exit 1${NC}"
        exit 1
    fi
fi
echo -e "${CYAN}================================${NC}"
echo ""
echo "本地零費用模式：手動觸發（GitHub Actions 已禁用）"
echo "建議頻率：每月架構覆盤 / 大重構前"
