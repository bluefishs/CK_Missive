#!/bin/bash
# ============================================================
# Fitness Tier 2 Weekly — 12 trend tracking step (~3 min)
#
# v6.12 治理進化 #2 完整落地 (2026-05-30)
# 對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md §4
#
# 包含 step (趨勢追蹤 + governance metric):
#   - 3 SOUL.md mirror drift
#   - 4 Wiki↔KG link audit
#   - 5 KG pgvector embedding 覆蓋率
#   - 7 Agent evolution health
#   - 10 Memory Wiki metrics alive
#   - 11 SOUL evolution alive
#   - 21 alias_rls_audit
#   - 51 tender_freshness_audit
#   - 53 tender_subscription_watchdog
#   - 55 tender_enrichment_freshness
#   - 59 diary density audit
#   - 61 facade adoption audit
#
# 用法:
#   bash scripts/checks/run_fitness_weekly.sh           # warning mode
#   bash scripts/checks/run_fitness_weekly.sh --strict  # 任一 RED exit 1 (cron 用)
#
# 失敗動作 (--strict 模式):
#   - 連續 2 週同 step RED → 推 LINE 提示 owner 排 sprint
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

echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN} Fitness Tier 2 Weekly — 23 trend step    ${NC}"
echo -e "${CYAN}===========================================${NC}"
echo ""

FAIL_COUNT=0
FAIL_STEPS=()
WARN_COUNT=0
WARN_STEPS=()

# 註（2026-08-03）：**刻意不傳 --strict 給子腳本**。
# 各 audit 的 --strict 語意是「任何 warning 也 exit 2」，會把 YELLOW 升級成 RED——
# 例如 tender_freshness 的「3 天 stale」其中 2 天是週末（政府不發標），
# 傳 --strict 就變成每個週末都告警。不傳旗標時各腳本回原生三態
# （0=GREEN / 1=YELLOW / 2+=RED），由本腳本自己決定哪一級才 exit 1。
#
# 前一版曾用 detect_flag() 依 --help 偵測該傳哪個旗標，那是為了解決
# 「23 步只有 5 支認得 --strict、其餘 argparse 直接報錯」的問題（連 9 週假紅）。
# 現在改為一律不傳，那個問題自然消失，偵測函式也就不需要了。

run_step() {
    local step_num="$1"
    local step_name="$2"
    local script="$3"

    echo -e "${CYAN}[$step_num/23] $step_name${NC}"
    if [[ ! -f "$script" ]]; then
        # 腳本不見了要算失敗 —— 原本只印一行 warning 就 return，
        # 等於「檢查消失」與「檢查通過」同樣是綠（alias_rls_audit 正是這個狀況）。
        echo -e "  ${RED}✗${NC} script not found: $script"
        FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name (腳本不存在)")
        echo ""
        return
    fi

    # 計數與「是否 exit 1」必須分離。
    # 2026-08-02 修：原本非 --strict 分支是 `|| true`，FAIL_COUNT 恆為 0
    # → 結尾**永遠印「✅ all passed」，不管實際紅幾步**。當日實跑：中間明明
    # tender_freshness（48 天陳舊）與 cross-repo template drift 兩步 RED，結論卻是全綠。
    # 子腳本不帶 --strict 時本來就會回非 0（實測 2 / 1），資訊一直都在，是被 `|| true` 丟掉。
    # warning mode 的語意是「不阻斷」，不是「不報告」。
    # 三態：0=GREEN / 1=YELLOW / 2+=RED（見上方「刻意不傳 --strict」說明）
    local rc=0
    PYTHONIOENCODING=utf-8 python "$script" 2>&1 || rc=$?
    if [[ $rc -eq 1 ]]; then
        WARN_COUNT=$((WARN_COUNT+1)); WARN_STEPS+=("$step_num $step_name")
    elif [[ $rc -ne 0 ]]; then
        FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name")
    fi
    echo ""
}

# Step 1-12
run_step "1" "SOUL.md mirror drift"           "scripts/checks/soul_mirror_drift_check.py"
run_step "2" "Wiki↔KG link audit"             "scripts/checks/wiki_kg_link_audit.py"
run_step "3" "KG pgvector embedding 覆蓋率"   "scripts/checks/kg_embedding_coverage_check.py"
run_step "4" "Agent evolution health"         "scripts/checks/agent_evolution_health.py"
run_step "5" "Memory Wiki metrics alive"      "scripts/checks/memory_metrics_alive_check.py"
run_step "6" "SOUL evolution alive"           "scripts/checks/soul_evolution_alive_check.py"
# 2026-08-02 修檔名：原引用 alias_rls_audit.py（不存在），實際是 step 21 的 coverage 版。
# 原本「腳本不存在」只印 warning 不計失敗 → 這一步等於從未執行過而沒人知道。
run_step "7" "alias_rls coverage audit"       "scripts/checks/alias_rls_coverage_audit.py"
run_step "8" "tender_freshness"               "scripts/checks/tender_freshness_audit.py"
run_step "9" "tender_subscription_watchdog"   "scripts/checks/tender_subscription_watchdog_audit.py"
run_step "10" "tender_enrichment_freshness"   "scripts/checks/tender_enrichment_freshness_audit.py"
run_step "11" "diary density audit"           "scripts/checks/diary_density_audit.py"
run_step "12" "facade adoption audit"         "scripts/checks/facade_adoption_audit.py"
run_step "13" "paths.py vs compose mount"     "scripts/checks/paths_compose_mount_audit.py"
run_step "14" "governance alignment audit"    "scripts/checks/governance_alignment_audit.py"
run_step "15" "cross-repo template drift"     "scripts/checks/cross_repo_template_drift_audit.py"
run_step "16" "cross-repo uncommitted audit"  "scripts/checks/cross_repo_uncommitted_audit.py"
run_step "17" "hermes baseline gate audit"    "scripts/checks/hermes_baseline_gate_audit.py"
run_step "18" "paths sub-path mount audit"    "scripts/checks/paths_subpath_mount_audit.py"
run_step "19" "repository coverage audit"     "scripts/checks/repository_coverage_audit.py"
run_step "20" "cross-domain link audit"       "scripts/checks/cross_domain_link_audit.py"
run_step "21" "knowledge dedup audit"         "scripts/checks/knowledge_dedup_audit.py"
run_step "22" "graph domain tagging audit"    "scripts/checks/graph_domain_tagging_audit.py"
# 2026-08-02：docs/architecture 累積 102 份文件卻無任何檢核在問「還算數嗎」
run_step "23" "doc reference integrity"       "scripts/checks/doc_reference_integrity_audit.py"

# ============================================================
# Summary
# ============================================================
echo -e "${CYAN}===========================================${NC}"
if [[ $FAIL_COUNT -eq 0 && $WARN_COUNT -eq 0 ]]; then
    echo -e "${GREEN} ✅ Tier 2 weekly all passed${NC}"
else
    [[ $FAIL_COUNT -gt 0 ]] && echo -e "${RED} ✗ Tier 2 weekly: $FAIL_COUNT step(s) RED${NC}"
    for s in "${FAIL_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${RED}✗${NC} $s"
    done
    [[ $WARN_COUNT -gt 0 ]] && echo -e "${YELLOW} ⚠ YELLOW $WARN_COUNT step(s)（非故障，待確認）${NC}"
    for s in "${WARN_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${YELLOW}⚠${NC} $s"
    done
    # exit 1 只由 RED 觸發，不含 YELLOW —— 否則 cron 會因為「週末沒發標」每週報一次
    if $STRICT && [[ $FAIL_COUNT -gt 0 ]]; then
        echo -e "${RED} STRICT mode → exit 1 (連續 2 週同 step RED 將推 LINE)${NC}"
        exit 1
    fi
fi
echo -e "${CYAN}===========================================${NC}"
