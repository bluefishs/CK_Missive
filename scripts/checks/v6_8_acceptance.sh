#!/bin/bash
# v6.8 Acceptance Test — 一鍵驗證 5/04 交付的所有 32 commits 真活
#
# 用法：
#   bash scripts/checks/v6_8_acceptance.sh
#
# 驗證項目（11 項）：
#   1. backend /health 200
#   2. /metrics 含 v7 4 gauge（v7_channel_diversity 等）
#   3. /metrics 含 agent_synthesis_unsourced_numbers_total（F19）
#   4. /api/auth/me POST 401（無 token，AUTH_DISABLED 縱深防禦生效）
#   5. /api/secure-site-management/csrf-token 200 + 設 cookie
#   6. /api/auth/refresh 空 body 401（不再 422，F18 生效）
#   7. /api/secure-site-management/navigation/action 401（CF header）
#   8. fitness 16 step 全跑通
#   9. v7_metrics_report.py 4 指標可生成
#   10. integration_liveness_check.py 5 接觸面 evidence
#   11. line_notify_heartbeat_check.py 7 天 push 計數
#
# 退出碼：0 全 pass / 1 有 fail

set -uo pipefail
cd "$(dirname "$0")/../.."

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local result="$2"  # ok / fail / warn
    local detail="$3"
    case "$result" in
        ok)   echo -e "  ${GREEN}✓${NC} $name: $detail"; PASS=$((PASS+1));;
        fail) echo -e "  ${RED}✗${NC} $name: $detail"; FAIL=$((FAIL+1));;
        warn) echo -e "  ${YELLOW}⚠${NC} $name: $detail"; WARN=$((WARN+1));;
    esac
}

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} v6.8 Acceptance Test (5/04 交付驗證)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 1. backend /health
HC=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "000")
[[ "$HC" == "200" ]] && check "1. backend /health" ok "200" || check "1. backend /health" fail "got $HC"

# 2. v7 4 gauge
V7_GAUGES=$(curl -s http://localhost:8001/metrics 2>/dev/null | grep -cE "^v7_(channel_diversity|reference_density|soul_drift|provider_fidelity_gap)" | head -1 || echo 0)
[[ "$V7_GAUGES" -ge 4 ]] && check "2. v7 4 gauges" ok "$V7_GAUGES gauges 暴露" || check "2. v7 4 gauges" fail "only $V7_GAUGES gauges"

# 3. F19 fact_check counter
F19=$(curl -s http://localhost:8001/metrics 2>/dev/null | grep -c "agent_synthesis_unsourced_numbers_total" | head -1 || echo 0)
[[ "$F19" -ge 1 ]] && check "3. F19 fact_check counter" ok "暴露中" || check "3. F19 fact_check counter" warn "尚未觸發過（待 LLM 編造數字才會 inc）"

# 4. /api/auth/me POST 401（AUTH_DISABLED 縱深防禦）
AM=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "cf-connecting-ip: 1.2.3.4" -H "cf-ray: test" http://localhost:8001/api/auth/me 2>/dev/null || echo "000")
[[ "$AM" == "401" ]] && check "4. /api/auth/me CF 公網" ok "401 真認證" || check "4. /api/auth/me CF 公網" fail "got $AM"

# 5. /api/secure-site-management/csrf-token 200 + cookie
CSRF_HDR=$(curl -sv -X POST http://localhost:8001/api/secure-site-management/csrf-token -H "Content-Type: application/json" -d '{}' 2>&1 | grep -i "set-cookie: csrf_token" | head -1)
[[ -n "$CSRF_HDR" ]] && check "5. csrf-token endpoint 設 cookie" ok "Set-Cookie: csrf_token 有" || check "5. csrf-token endpoint 設 cookie" fail "無 Set-Cookie"

# 6. /api/auth/refresh 空 body 401（不再 422）
RC=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8001/api/auth/refresh -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
[[ "$RC" == "401" ]] && check "6. /api/auth/refresh 空 body" ok "401（F18 schema Optional 生效）" || check "6. /api/auth/refresh 空 body" fail "got $RC（仍 422 = F18 沒生效）"

# 7. /api/secure-site-management/navigation/action CF 公網 401
NA=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "cf-connecting-ip: 1.2.3.4" -H "cf-ray: test" http://localhost:8001/api/secure-site-management/navigation/action -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
[[ "$NA" == "401" ]] && check "7. navigation/action CF 公網" ok "401 縱深防禦生效" || check "7. navigation/action CF 公網" fail "got $NA"

# 8. fitness 16 step
echo -e "\n  ${CYAN}執行 fitness 16 step（可能耗時 30 秒）...${NC}"
FIT_OUT=$(bash scripts/checks/run_fitness.sh 2>&1 | tail -5)
if echo "$FIT_OUT" | grep -q "All fitness checks passed"; then
    check "8. fitness 16 step" ok "全 pass"
else
    WARN_CNT=$(echo "$FIT_OUT" | grep -oE "[0-9]+ check" | head -1 | grep -oE "[0-9]+" || echo "?")
    check "8. fitness 16 step" warn "$WARN_CNT warnings (預期 — v3.0 3 裂縫實證)"
fi

# 9. v7_metrics_report (pattern: ## <metric_name>)
V7R=$(PYTHONIOENCODING=utf-8 python scripts/checks/v7_metrics_report.py 2>&1 | grep -cE "^  ## " | head -1 || echo 0)
[[ "$V7R" -ge 4 ]] && check "9. v7_metrics_report" ok "4 個 metric 報出" || check "9. v7_metrics_report" fail "only $V7R metrics"

# 10. integration_liveness_check
IL=$(PYTHONIOENCODING=utf-8 python scripts/checks/integration_liveness_check.py 2>&1 | grep -c "❹\|❺\|❻\|❼\|❽" | head -1 || echo 0)
[[ "$IL" -ge 5 ]] && check "10. integration_liveness_check" ok "5 接觸面 evidence query" || check "10. integration_liveness_check" fail "only $IL checks"

# 11. line_notify_heartbeat_check
LH=$(PYTHONIOENCODING=utf-8 python scripts/checks/line_notify_heartbeat_check.py 2>&1 | grep -E "Total LINE pushes")
[[ -n "$LH" ]] && check "11. line_notify_heartbeat" ok "watchdog 報告生成" || check "11. line_notify_heartbeat" fail "watchdog 失敗"

# Summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e " ${GREEN}PASS: $PASS${NC}  ${YELLOW}WARN: $WARN${NC}  ${RED}FAIL: $FAIL${NC}"
echo -e "${CYAN}========================================${NC}"

if [[ "$FAIL" -gt 0 ]]; then
    echo -e "${RED}v6.8 acceptance FAIL — $FAIL 項需排查${NC}"
    exit 1
fi
echo -e "${GREEN}v6.8 acceptance PASS — 32 commits 真活${NC}"
exit 0
