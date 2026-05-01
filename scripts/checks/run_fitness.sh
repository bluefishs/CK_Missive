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
echo -e "${CYAN}[1/13] Services directory entropy${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py
fi
echo ""

# ----------------------------------------------------------------------------
# 2. Dead config reader（掃多個高信號檔）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[2/13] Dead config reader scan (multi-target v3)${NC}"

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
echo -e "${CYAN}[3/13] SOUL.md mirror drift check${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py
fi
echo ""

# ----------------------------------------------------------------------------
# 4. Wiki ↔ KG 雙向引用率
# ----------------------------------------------------------------------------
echo -e "${CYAN}[4/13] Wiki ↔ KG link audit${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py
fi
echo ""

# ----------------------------------------------------------------------------
# 5. KG pgvector embedding 覆蓋率
# ----------------------------------------------------------------------------
echo -e "${CYAN}[5/13] KG pgvector embedding coverage${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/kg_embedding_coverage_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/kg_embedding_coverage_check.py
fi
echo ""

# ----------------------------------------------------------------------------
# 6. Architecture docs presence
# ----------------------------------------------------------------------------
echo -e "${CYAN}[6/13] Architecture standard docs presence${NC}"
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
# 7. Agent evolution health（坤哥進化引擎是否在跑 — L21 prevention）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[7/13] Agent evolution health${NC}"
# exit codes: 0 healthy / 1 warning (trigger 久未觸發但 redis OK) / 2 error (redis 不可達)
# non-strict 模式 — exit 1/2 都僅警告（dev 環境可能沒 redis），strict 才算 fail
PYTHONIOENCODING=utf-8 python scripts/checks/agent_evolution_health.py 2>&1 || EVOLUTION_EXIT=$?
EVOLUTION_EXIT=${EVOLUTION_EXIT:-0}
if [[ $EVOLUTION_EXIT -ne 0 ]] && $STRICT; then
    FAIL_COUNT=$((FAIL_COUNT+1))
fi
echo ""

# ----------------------------------------------------------------------------
# 8. Dispatch cache contract（派工 invalidate 必須透過 hook，cache 一致性）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[8/13] Dispatch cache contract${NC}"
if $STRICT; then
    bash scripts/checks/dispatch_cache_contract.sh || FAIL_COUNT=$((FAIL_COUNT+1))
else
    bash scripts/checks/dispatch_cache_contract.sh || true
fi
echo ""

# ----------------------------------------------------------------------------
# 9. Stub import lint（DDD 邊界落實，2026-Q3 stub 移除前置）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[9/13] Stub import lint (DDD boundary)${NC}"
# warning-only mode：v5.10.2 已清 26 處最大宗，剩 ~58 處列入 Q3 移除前 follow-up
# strict 模式才報 fail（鼓勵新增程式碼用新路徑，不增加 stub debt）
if $STRICT; then
    bash scripts/checks/stub_import_lint.sh || FAIL_COUNT=$((FAIL_COUNT+1))
else
    bash scripts/checks/stub_import_lint.sh || true
fi
echo ""

# ----------------------------------------------------------------------------
# 10. Memory metrics alive check（坤哥意識體觀測，防 hollow gauge L21）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[10/13] Memory Wiki metrics alive${NC}"
# 需要 ck-backend 啟動才能 scrape /metrics — dev 模式可能後端沒起來，warning-only
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/memory_metrics_alive_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/memory_metrics_alive_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 11. SOUL evolution alive check（v5.11 Phase 2，鏈路 4 silent gap 防護）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[11/13] SOUL evolution alive${NC}"
# 防 KUNGE_LEARNING_VERIFICATION 鏈路 4 silent gap 重演（autobiography 寫但
# SOUL 沒同步）— evolutions/ 有檔但 SOUL「我的成長」仍 placeholder 即報警
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_evolution_alive_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_evolution_alive_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 12. Memory signal consumer lint（v5.12 Phase D，孤兒 signal 治理）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[12/13] Memory signal consumer lint${NC}"
# 偵測 redis-based signal 是否完全孤兒（0 caller）
# 防止 v5.10.2 #4 silent failure 同類問題重演
if $STRICT; then
    bash scripts/checks/signal_consumer_lint.sh || FAIL_COUNT=$((FAIL_COUNT+1))
else
    bash scripts/checks/signal_consumer_lint.sh || true
fi
echo ""

# ----------------------------------------------------------------------------
# 13. Cron 健康度（v6.2 Phase C2，防 cron silent fail 雪崩）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[13/13] Cron health check${NC}"
# 連續失敗 ≥ 2 / 上次成功 > 預期 × 2 / never_run 但 next_run 已過 → fail
# warning-only mode：dev 環境後端可能未啟動，endpoint 不可達不算 fail
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/cron_health_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/cron_health_check.py || true
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
