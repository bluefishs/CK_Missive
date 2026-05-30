#!/bin/bash
# ============================================================
# Fitness Tier 1 Daily — 7 critical step (~1 min)
#
# v6.12 治理進化 #2 落地 (2026-05-30)
# 對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md §3
#
# 包含 step:
#   - 38 docker_compose_volume_consistency
#   - 40 compose/dockerfile healthcheck SSOT
#   - 47 startup race condition
#   - 57 container env alignment
#   - 58 agent_query starvation
#   - 60 container image freshness
#
# 用法:
#   bash scripts/checks/run_fitness_daily.sh           # warning mode
#   bash scripts/checks/run_fitness_daily.sh --strict  # 任一 RED exit 1 (cron 用)
#
# 失敗動作 (--strict 模式):
#   exit 1 → cron job 抓住 → 推 LINE
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

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN} Fitness Tier 1 Daily — 7 critical step ${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

FAIL_COUNT=0
FAIL_STEPS=()

run_step() {
    local step_num="$1"
    local step_name="$2"
    local cmd="$3"

    echo -e "${CYAN}[$step_num/7] $step_name${NC}"
    if $STRICT; then
        if eval "$cmd" --strict 2>&1; then
            true
        else
            FAIL_COUNT=$((FAIL_COUNT+1))
            FAIL_STEPS+=("$step_num $step_name")
        fi
    else
        eval "$cmd" 2>&1 || true
    fi
    echo ""
}

# Step 1/6: container env alignment (step 57)
run_step "1" "container env alignment audit" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/container_env_alignment_audit.py"

# Step 2/6: container image freshness (step 60, L51.7.1)
run_step "2" "container image freshness check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/container_image_freshness_check.py"

# Step 3/6: docker_compose volume consistency (step 38, L43)
if [[ -f scripts/checks/docker_compose_volume_consistency.py ]]; then
    run_step "3" "docker_compose volume consistency" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/docker_compose_volume_consistency.py"
else
    echo -e "${CYAN}[3/7] docker_compose volume consistency${NC}"
    echo "  ${YELLOW}⚠${NC} script not found, skip"
    echo ""
fi

# Step 4/6: compose/dockerfile healthcheck SSOT (step 40, L45)
if [[ -f scripts/checks/compose_dockerfile_healthcheck_ssot.py ]]; then
    run_step "4" "compose/dockerfile healthcheck SSOT" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/compose_dockerfile_healthcheck_ssot.py"
else
    echo -e "${CYAN}[4/7] compose/dockerfile healthcheck SSOT${NC}"
    echo "  ${YELLOW}⚠${NC} script not found, skip"
    echo ""
fi

# Step 5/6: startup race condition audit (step 47)
if [[ -f scripts/checks/startup_race_condition_audit.py ]]; then
    run_step "5" "startup race condition audit" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/startup_race_condition_audit.py"
else
    echo -e "${CYAN}[5/7] startup race condition audit${NC}"
    echo "  ${YELLOW}⚠${NC} script not found, skip"
    echo ""
fi

# Step 6/6: agent_query starvation (step 58, L51.7)
run_step "6" "agent_query starvation check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/agent_query_starvation_check.py"

# Step 7/7: cron silent dormant (v6.12 #2 補完, 2026-05-30)
run_step "7" "cron silent dormant check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/cron_silent_dormant_check.py"

# ============================================================
# Summary
# ============================================================
echo -e "${CYAN}=========================================${NC}"
if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN} ✅ Tier 1 daily all passed${NC}"
else
    echo -e "${YELLOW} ⚠ Tier 1 daily: $FAIL_COUNT step(s) RED${NC}"
    for s in "${FAIL_STEPS[@]}"; do
        echo -e "   ${RED}✗${NC} $s"
    done
    if $STRICT; then
        echo -e "${RED} STRICT mode → exit 1 (cron 將觸發 LINE 推送)${NC}"
        exit 1
    fi
fi
echo -e "${CYAN}=========================================${NC}"
