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
echo -e "${CYAN}[1/61] Services directory entropy${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/service_dir_entropy.py
fi
echo ""

# ----------------------------------------------------------------------------
# 2. Dead config reader（掃多個高信號檔）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[2/61] Dead config reader scan (multi-target v3)${NC}"

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
echo -e "${CYAN}[3/61] SOUL.md mirror drift check${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/soul_mirror_drift_check.py
fi
echo ""

# ----------------------------------------------------------------------------
# 4. Wiki ↔ KG 雙向引用率
# ----------------------------------------------------------------------------
echo -e "${CYAN}[4/61] Wiki ↔ KG link audit${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_kg_link_audit.py
fi
echo ""

# ----------------------------------------------------------------------------
# 5. KG pgvector embedding 覆蓋率
# ----------------------------------------------------------------------------
echo -e "${CYAN}[5/61] KG pgvector embedding coverage${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/kg_embedding_coverage_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/kg_embedding_coverage_check.py
fi
echo ""

# ----------------------------------------------------------------------------
# 6. Architecture docs presence
# ----------------------------------------------------------------------------
echo -e "${CYAN}[6/61] Architecture standard docs presence${NC}"
# v6.13 (2026-05-31) L52 family: container 內 docs/ 未 mount 是設計 (host-side only)
if [[ ! -d "docs/architecture" ]]; then
    echo -e "  ${YELLOW}[INFO]${NC} docs/architecture not present (container env, host-side check only)"
else
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
fi
echo ""

# ----------------------------------------------------------------------------
# 7. Agent evolution health（坤哥進化引擎是否在跑 — L21 prevention）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[7/61] Agent evolution health${NC}"
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
echo -e "${CYAN}[8/61] Dispatch cache contract${NC}"
if $STRICT; then
    bash scripts/checks/dispatch_cache_contract.sh || FAIL_COUNT=$((FAIL_COUNT+1))
else
    bash scripts/checks/dispatch_cache_contract.sh || true
fi
echo ""

# ----------------------------------------------------------------------------
# 9. Stub import lint（DDD 邊界落實，2026-Q3 stub 移除前置）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[9/61] Stub import lint (DDD boundary)${NC}"
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
echo -e "${CYAN}[10/61] Memory Wiki metrics alive${NC}"
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
echo -e "${CYAN}[11/61] SOUL evolution alive${NC}"
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
echo -e "${CYAN}[12/61] Memory signal consumer lint${NC}"
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
echo -e "${CYAN}[13/61] Cron health check${NC}"
# 連續失敗 ≥ 2 / 上次成功 > 預期 × 2 / never_run 但 next_run 已過 → fail
# warning-only mode：dev 環境後端可能未啟動，endpoint 不可達不算 fail
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/cron_health_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/cron_health_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 14. Wiki Unicode 重名偵測（v6.2 Phase C3，wiki_compiler 寫檔正規化）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[14/61] Wiki Unicode dup check${NC}"
# wiki_compiler 寫過 NFC + CJK Compatibility 兩種正規化的同名檔
# warning-only：dup 不阻擋 ship，但提醒 wiki_compiler 該補 NFC normalize
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_unicode_dup_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/wiki_unicode_dup_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 15. Integration liveness check（F14 / v3.0 洞察 11 — 8 接觸面活體驗證）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[15/61] Integration liveness check${NC}"
# 對 v3.0 SYSTEM_INTEGRATION_REVIEW 8 接觸面 evidence query
# warning-only：dev 環境 mirror/diary 可能 sparse
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/integration_liveness_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/integration_liveness_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 16. LINE notify 7d heartbeat（F15 / v3.0 洞察 15 — 體感推送 watchdog）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[16/61] LINE notify 7d heartbeat${NC}"
# silent skip 對主流程對，但對體感層 silent = 死亡。
# 連續 7 天 0 推送 → 警報（5/04 5 天無人察覺事故預防）
# warning-only：dev 環境 cron 可能未跑 / .env 未設皆視為 OK
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/line_notify_heartbeat_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/line_notify_heartbeat_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 17. Alias RLS E2E check（TaskB / ADR-0025 半接通事故預防）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[17/61] Alias RLS bidirectional check${NC}"
# 對 user_merge_log 每筆紀錄驗證雙向 RLS 展開正確
# 永久防範：merge 寫了但 RLS 沒展開（13 天 dormant 事故）
# warning-only：DB 不可達 / 無 merge 紀錄皆 OK；CI 模式才 exit 1
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/alias_rls_e2e_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/alias_rls_e2e_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 18. Memory Wiki freshness（ADR-0022 半接通防範）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[18/61] Memory Wiki freshness check${NC}"
# diary/patterns/critiques/evolutions 寫入鏈活體驗證
# warning-only：dev 環境寬容；CI 模式且 diary critical 才 exit 1
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/memory_diary_freshness_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/memory_diary_freshness_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 19. Generic filter audit（regex 黑名單 false-positive rate）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[19/61] Generic filter audit${NC}"
# 對所有黑名單型 regex 過濾做 false-positive rate 量測
# 防範：5/06 GENERIC_ADMIN_KEYWORDS 過寬誤殺業務公文
# warning-only：超出預期上限 2x 才 fail
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/generic_filter_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/generic_filter_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 20. Role permissions consistency（ADR-0034 配套）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[20/61] Role permissions consistency${NC}"
# 4 維度 audit：dangling / orphan / admin coverage / 敏感 nav 缺權限
# 防範：role_permissions ↔ site_navigation_items 雙軌不同步
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/role_permissions_consistency_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/role_permissions_consistency_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 21. Alias RLS Coverage Audit（R4a / v6.9 — ADR-0025 靜態防範）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[21/61] Alias RLS coverage audit${NC}"
# 靜態掃 endpoints/ 找疑似有 user-scoped SQL filter 但無 RLS / admin 標記的檔案
# 與 step 17 alias_rls_e2e_check 互補（step 17 = runtime / step 21 = compile-time）
# 防 ADR-0025 半接通類事故重演 — owner 應每月檢視 risk 清單
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/alias_rls_coverage_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/alias_rls_coverage_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 22. Domain Score Freshness Watchdog（L29 / v6.9 — 坤哥成長中斷防範）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[22/61] Domain score freshness${NC}"
# 防 L29「domain_scores Redis 全空 silent skip」重演
# 至少 3 個 domain 有資料才算健康；全空 → self_evaluator domain tracking 又斷了
# warning-only：dev 環境 Redis 可能未啟；CI 模式才 exit 1
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/domain_score_freshness_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/domain_score_freshness_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 23. Capability Usage Audit（v6.10 retro — dead investment 自動偵測）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[23/61] Capability usage audit${NC}"
# 偵測 7d/30d usage = 0 的 capability（tools/KG/memory loop/ADR）
# 強制 A/B/C 決策矩陣 — 避免「12 dead investment 累積無人察覺」重演
# --quick 跳過 ADR grep（Windows 慢，月度大盤點才用完整模式）
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/capability_usage_audit.py --quick --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/capability_usage_audit.py --quick || true
fi
echo ""

# ----------------------------------------------------------------------------
# 24. ADR Lifecycle Check（ADR-0029 自動數量治理）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[24/61] ADR lifecycle check${NC}"
# Active ≤ 20 健康 / > 20 觸發強制盤點
# 補位本 session C8（CLAUDE.md/skills 數字漂移）的自動偵測
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/adr_lifecycle_check.py || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/adr_lifecycle_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 25. Dead UI Detector（前端死 route / dead component 偵測）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[25/61] Dead UI detector${NC}"
# 偵測後端有 endpoint 但前端無 UI 觸發點 / 前端 component 0-importer
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/dead_ui_detector.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/dead_ui_detector.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 26. Lessons Drift Check（LESSONS_REGISTRY 自我保護）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[26/61] Lessons drift check${NC}"
# 22 lessons L01~L29 是否仍被引用 / 是否有新 lesson 未入 registry
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/lessons_drift_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/lessons_drift_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 27. Service Line Count Check（後端服務行數監控）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[27/61] Service line count check${NC}"
# 服務行數 > 600 警告（觀察而非拆分依據 — 見 feedback_ddd_over_line_count）
# 配合 MODULARIZATION_STANDARDS §1.1 黃金原則
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/service-line-count-check.py || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/service-line-count-check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 28. Paths Sloppy Calc Guard (v6.10 P1-E：5/18 backup path bug 預防)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[28/61] Paths sloppy calc guard${NC}"
# 偵測 Path(__file__).resolve().parents[N] / parent.parent.parent 散用
# 強制走 app.core.paths SSOT（規約 E）
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/paths_sloppy_calc_guard.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/paths_sloppy_calc_guard.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 29. Contracts Only Import Guard (v6.10 P1 建議 1：12 bounded context 隔離)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[29/61] Contracts only import guard${NC}"
# 偵測跨 bounded context 直 import 內部 module（強制走 contracts/）
# 依據 CONTRACTS_LAYER_GUIDE.md + MODULARIZATION_STANDARDS §1.3
# v6.10 初次跑 baseline ~84，目標 v7.0 前清到 0
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/contracts_only_import_guard.py || true
else
    PYTHONIOENCODING=utf-8 python scripts/checks/contracts_only_import_guard.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 30. Module Portability Audit (v6.10 P1：跨 repo 採用前審計)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[30/61] Module portability audit (contracts/)${NC}"
# 依 data/business_keyword_blacklist.yml 偵測業務耦合 keyword
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/module_portability_audit.py backend/app/services/contracts/ --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/module_portability_audit.py backend/app/services/contracts/ || true
fi
echo ""

# ----------------------------------------------------------------------------
# 31. Naming Convention Audit (v6.10 P1 Phase A：8 大命名規約)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[31/61] Naming convention audit${NC}"
# 依 docs/architecture/NAMING_CONVENTIONS.md 偵測命名違規
# v6.10 過渡期：env_namespace + abc_port_suffix 為 warning；v6.11 升 error
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/naming_convention_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/naming_convention_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 32. Facade Only Check (v6.10 P1 Phase B：12 facades 落地後新增監控)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[32/61] Facade only check${NC}"
# step 29 進階版：要求新 PR 不得超出 baseline 84
# 提供 facade 修法指引（每個違規對應 *Facade）
if $STRICT; then
    # baseline 84 強制不增加（v6.11 強制下降）
    PYTHONIOENCODING=utf-8 python scripts/checks/facade_only_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/facade_only_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 33. Toolkit Sync Audit (v6.10 P1：master scripts/ vs ck-modular-toolkit 同步)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[33/61] Toolkit sync audit${NC}"
# 偵測 ck-modular-toolkit 是否與 master scripts/ 同步
# 防 toolkit 落後 master 反模式（選項 D 統一同步策略）
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/toolkit_sync_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/toolkit_sync_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 34. Transitive Deps Audit (v6.10 P1 LR-015 配套：防 package 半接通)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[34/61] Transitive deps audit${NC}"
# 偵測 shared-modules/{pkg}/ 內 import 是否 self-contained
# 對應 PACKAGING_PATTERN Rule 7 (Self-Contained Imports)
# 起因：5/18 ck-navigation v1.0 半接通事件 (LR-015 諷刺對齊)
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/transitive_deps_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/transitive_deps_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 35. React Query queryKey Drift Audit (v6.10.1 L39：防 silent dead invalidate)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[35/61] queryKey drift audit${NC}"
# 偵測 invalidateQueries 寫的 key 是否對應任何 useQuery / SSOT key
# 起因：5/20 dispatch=158「公文 2 筆」chronic bug 揭發 12 個 silent dead invalidate
# L39 dict-key drift 反模式（同 L28 schema drift + L29 contract drift）
# baseline-aware enforce — 修一個減一個，禁淨增加
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/queryKey_drift_audit.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/queryKey_drift_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# 36. Autobiography Scheduler Freshness Check (v6.10.2 B 配套)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[36/61] autobiography freshness check${NC}"
# 偵測 wiki/memory/evolutions/2026-Wnn.md 最新檔距當前週 > 2 週即警示
# 起因：5/20 揭發過去 5 個月 memory_weekly_autobiography_job silent miss
# （cron 排程在，週日 18:00 沒真實跑；手動跑邏輯正常）
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/autobiography_freshness_check.py --ci || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/autobiography_freshness_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 37: cross-repo docker network audit (ADR CK_AaaP#0043, 2026-05-21)
# 揭發跨 repo network 命名 + 4 層分網路達標度
# ----------------------------------------------------------------------------
echo -e "${CYAN}[37/61] cross-repo docker network audit (ADR-0043)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/network_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/network_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 38: docker compose volume consistency audit (L43, 2026-05-21)
# 揭發同邏輯 volume（postgres/redis）跨 compose 檔指向不同實體名的 drift
# 起因：5/21 production compose 指向 ck_missive_postgres_data（空殼）
# vs dev/infra compose 指向 ck_missive_postgres_dev_data（真實主庫）
# 切換 compose 時 silent 掛錯 volume → 業務 API 全 500 dormant ~10h
# ----------------------------------------------------------------------------
echo -e "${CYAN}[38/61] docker compose volume consistency (L43)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/docker_compose_volume_consistency.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/docker_compose_volume_consistency.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 39: facade consumer audit (v6.10 P1 build-without-consumer 反模式, 2026-05-22)
# 揭發 contracts/facades/ 內 method 的 caller 數
# 起因：5/22 owner 問「為何一直中斷」，揭發 scheduler 5 個月 silent fail 走錯
# import path，而正確的 IntegrationFacade.push_admin_alert 真實有實作但無 caller
# RETRO_20260519 §2.1 看 facade 級揭發 9/12 zero caller；本 step 看 method 級
# ----------------------------------------------------------------------------
echo -e "${CYAN}[39/61] facade consumer audit (v6.10 P1)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/facade_consumer_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/facade_consumer_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 40: compose vs Dockerfile HEALTHCHECK SSOT (L45 family, 2026-05-25)
# 觸發：5/22 frontend container unhealthy — compose healthcheck :80 override
# Dockerfile :3000 nginx 真實 listen port，FailingStreak=36 dormant 18 分鐘
# 屬於 L43「跨檔資源 SSOT 治理失效」家族第 4 案例（L41 jwt / L43 volume / L44 sso / L45 hc）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[40/61] compose vs Dockerfile HEALTHCHECK SSOT (L45)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/compose_dockerfile_healthcheck_ssot.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/compose_dockerfile_healthcheck_ssot.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 41: cross-repo secret SSOT audit (L41 配套, 2026-05-25)
# 觸發：L41 6 天 dormant — ck-sso-py signer 用 secret A，missive verifier 用 secret B
# 偵測 CROSS_REPO_SHARED_KEYS（CK_SSO_JWT_SECRET / CK_SSO_ENABLED）跨 repo drift
# 安全：只比對 sha256 hash 前 8 字元，不印實值
# ----------------------------------------------------------------------------
echo -e "${CYAN}[41/61] cross-repo secret SSOT audit (L41)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/cross_repo_secret_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/cross_repo_secret_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 42: cross-repo SSO auth state audit (L44 配套, 2026-05-25)
# 觸發：L44 ck-sso-js v1.0 session-permanent lock 跨 subdomain 失敗
# 偵測 ck-sso-js sso-bridge.ts md5 跨 repo drift + LoginPage onSuccess anti-pattern
# ----------------------------------------------------------------------------
echo -e "${CYAN}[42/61] cross-repo SSO auth state audit (L44)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/cross_repo_auth_state_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/cross_repo_auth_state_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 43: DB schema drift audit (next_session_resume #1, 2026-05-26)
# 觸發：L43 災難根因之一是 alembic 不需資料就推進；衍生「新加 model 忘 migration」風險
# 雙重偵測：mtime heuristic (model newer than migration) + alembic check (live container)
# 嚴重度區分：added column/table = RED；added index/modified/removed = YELLOW
# ----------------------------------------------------------------------------
echo -e "${CYAN}[43/61] DB schema drift audit (next_session_resume #1)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/db_schema_drift_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/db_schema_drift_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 44: container lifecycle audit (next_session_resume #4, 2026-05-26)
# 觸發：2026-04-21 cloudflared latest tag silent 升版觸發 chronic QUIC timeout
# 偵測 docker ps + compose 內 :latest tag (public image) + 跨 repo 版本 drift
# 本地 build image (ck_* prefix 或無 namespace) 跳過 (latest 是合理模式)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[44/61] container lifecycle audit (next_session_resume #4)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/container_lifecycle_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/container_lifecycle_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 45: subdomain registry audit (next_session_resume #3, 2026-05-26)
# 觸發: 跨 repo subdomain typo（如 pile vs pilemgmt）→ CORS preflight 失敗 / silent 404
# 對照 configs/subdomain-registry.yaml SSOT 驗證:
#   - active 公網真活
#   - forbidden_typos 不在 production code 出現
# ----------------------------------------------------------------------------
echo -e "${CYAN}[45/61] subdomain registry audit (next_session_resume #3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/subdomain_registry_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/subdomain_registry_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 46: SSO autoload completeness audit (next_session_resume #7, 2026-05-27)
# 觸發：shared-modules/ck-sso-js v1.1 useSSOBridge 已備但 consumer 接通完整度未驗
# 對每個 consumer repo（lvrland / pile）驗證 4 個 check:
#   1. frontend/src/lib/ck-sso-js/ 副本存在
#   2. LoginPage 用 useSSOBridge 或 attemptSSOBridge
#   3. .env.example 宣告 VITE_API_BASE_URL
#   4. .env.example 宣告 CK_SSO_ENABLED 或 VITE_CK_SSO_ENABLED
# Check 1-2 RED, Check 3-4 YELLOW
# ----------------------------------------------------------------------------
echo -e "${CYAN}[46/61] SSO autoload completeness audit (next_session_resume #7)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/sso_autoload_completeness_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/sso_autoload_completeness_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 47: startup dependency race audit (v6.12 P3, 2026-05-27)
# 觸發：naïve `depends_on: - postgres` 只等 start 不等 healthy → race condition
# 偵測 list 形式 depends_on / 缺 condition / service_started（非 service_healthy）
# 所有 critical depends_on 應該用 dict + condition: service_healthy
# ----------------------------------------------------------------------------
echo -e "${CYAN}[47/61] startup dependency race audit (v6.12 P3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/startup_dependency_race_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/startup_dependency_race_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 48: DB pool exhaustion audit (v6.12 P3, 2026-05-27)
# 觸發：SQLAlchemy pool exhausted 時 connection 進 wait queue silent，業務 endpoint 慢但 healthcheck 仍 200
# 抓 /health endpoint pool stats {size, checked_in, checked_out, overflow, max_overflow}
# RED util > 90% / YELLOW util > 50% or overflow active / GREEN < 50%
# ----------------------------------------------------------------------------
echo -e "${CYAN}[48/61] DB pool exhaustion audit (v6.12 P3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/db_pool_exhaustion_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/db_pool_exhaustion_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 49: Synthetic baseline freshness audit (v6.12 P3, 2026-05-27)
# 觸發：5/22-5/27 6+ 天 synthetic_baseline_inject cron rc=1 silent dead
# 真因鏈：docker container MCP_SERVICE_TOKEN env missing → endpoint 403 in 8ms
# 同 L48 family — silent dormant + missing audit enforcement
# 掃 backend-error.log 抓 Total/Success/Error 比例，全失敗 → RED
# ----------------------------------------------------------------------------
echo -e "${CYAN}[49/61] Synthetic baseline freshness audit (v6.12 P3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/synthetic_baseline_freshness_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/synthetic_baseline_freshness_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 50: Frontend bundle size drift audit (v6.12 P3, 2026-05-27)
# 觸發：GitHub Actions 停用後 CI bundle-size-check 不再跑 → bundle 可 silent 膨脹
# 對齊 frontend/scripts/bundle-size-check.js 閾值（10.5MB raw / 3.5MB gzip / 1.5MB single）
# 首跑揭發：total raw 10.68 MB > 10.5 MB threshold → RED
# ----------------------------------------------------------------------------
echo -e "${CYAN}[50/61] Frontend bundle size drift audit (v6.12 P3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/frontend_bundle_size_drift_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/frontend_bundle_size_drift_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 51: Tender source freshness audit (v6.12 P3, 2026-05-27)
# 觸發：2026-04-08 起 PCC scraper 50 天 silent dormant（scheduler.py 缺 cron job）
# 同 L48 family — silent dormant + missing audit enforcement
# 查 tender_records per source MAX(announce_date)，>7 天 → RED
# ----------------------------------------------------------------------------
echo -e "${CYAN}[51/61] Tender source freshness audit (v6.12 P3)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_freshness_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_freshness_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 52: Container Host Dependency Audit (L49 family, 2026-05-27)
# 觸發：OA-3 PM2 廢除後 backup 用 docker CLI / files rglob OSError / file_path Windows \\
# 偵測：docker subprocess / shutil.which docker / /var/run/docker.sock (RED) +
#       rglob('*') 無 OSError 容錯 / attachment.file_path 未 normalize (YELLOW)
# L41-L49 family meta-pattern：跨平台/環境隱式依賴 → 立法 + audit 三件套
# ----------------------------------------------------------------------------
echo -e "${CYAN}[52/61] container host dependency audit (L49)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/container_host_dependency_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/container_host_dependency_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 53: Tender Subscription Scheduler Watchdog (L48 family, 2026-05-28 Step 5C)
# 觸發：subscription_scheduler.check_all_subscriptions 若未排程將 silent dormant
# 同 L48 PCC scraper 50 天 silent — counter 連 24h 無 invocation → RED
# ----------------------------------------------------------------------------
echo -e "${CYAN}[53/61] tender subscription scheduler watchdog (L48)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_subscription_watchdog_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_subscription_watchdog_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 54: PowerShell UTF-8 BOM audit (L49 family #11, 2026-05-28)
# 觸發：install-task-scheduler.ps1 parser error line 104 真因
# Windows PS 5.1 預設 cp950 讀 ps1，中文無 BOM → mis-decode → try/catch 結構崩
# ----------------------------------------------------------------------------
echo -e "${CYAN}[54/61] powershell utf-8 bom audit (L49 #11)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/powershell_bom_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/powershell_bom_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 55: Tender Enrichment Freshness (ADR-0046 Phase 5, 2026-05-28)
# 觸發：ezbid → PCC enrichment 每日 03:30 cron 是否真活
# 監測 pcc_match_at 最近時間，>30h 無 enrich → RED (同 L48 family silent dormant)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[55/61] tender enrichment freshness (ADR-0046)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_enrichment_freshness_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/tender_enrichment_freshness_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 56: Tender MEDIUM Review Queue Health (L51 / ADR-0046 task E, 2026-05-29)
# 監測 MEDIUM review queue backlog 是否被 admin 消化
# pending > 5000 → RED / > 2000 或 oldest > 30d → YELLOW
# ----------------------------------------------------------------------------
echo -e "${CYAN}[56/61] tender review queue health (ADR-0046 task E)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python backend/scripts/checks/tender_review_queue_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python backend/scripts/checks/tender_review_queue_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 57: Container env vs Host .env Alignment Audit (L51, 2026-05-29)
# 防 L48 SSO / L51 LINE 同型「host .env 有但 compose 未注入」silent fail 反覆
# .env 有值但 compose 未注入 → RED (silent fail 風險)
# informational — 預設不入 STRICT fail（部分 RED 為 false positive，需人工判斷）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[57/61] container env alignment audit (L51 LINE incident)${NC}"
PYTHONIOENCODING=utf-8 python scripts/checks/container_env_alignment_audit.py || true
echo ""

# ----------------------------------------------------------------------------
# step 58: Agent Query Starvation Check (L51.7 坤哥覆盤, 2026-05-30)
# 監測 agent_query 鏈是否「引擎跑著但無人用」反模式
# shadow_baseline 24h n=0 → RED (近期無活動)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[58/61] agent query starvation check (L51.7 kunge review)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/agent_query_starvation_check.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/agent_query_starvation_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 59: Diary Density Audit (L51.7 Sprint 2.P2.11, 2026-05-30)
# 監測 wiki/memory/diary entry 含 entity 引用比例
# 推升 v7_reference_density_diary_pct 從 16.7% → ≥30%
# ----------------------------------------------------------------------------
echo -e "${CYAN}[59/61] diary density audit (L51.7 Sprint 2.P2.11)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/diary_density_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/diary_density_audit.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 60: Container Image Freshness Check (L51.7.1 incident #8, 2026-05-30)
# 對 11 個 critical backend 檔做 host vs container md5 比對
# 任一 drift → RED（docker cp 修法未跟 rebuild image 反模式）
# 防 L51 5 防護層 silent disabled 36h 再次發生
# ----------------------------------------------------------------------------
echo -e "${CYAN}[60/62] container image freshness check (L51 incident #8)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/container_image_freshness_check.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/container_image_freshness_check.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 61: Facade Adoption Audit (P1.7 incremental, 2026-05-30)
# 監測 13 facades 業務 code importer 趨勢（baseline vs current）
# informational only — facade 收口為 v6.12 規劃，不入 strict fail
# ----------------------------------------------------------------------------
echo -e "${CYAN}[61/62] facade adoption audit (P1.7 v6.12 路線)${NC}"
PYTHONIOENCODING=utf-8 python scripts/checks/facade_adoption_audit.py || true
echo ""

# ----------------------------------------------------------------------------
# step 62: Integration E2E Validation (v6.13, 2026-05-31)
# 對齊 owner「坤哥+Hermes+智能體整合連通真活 突破性 非一次性」訴求
# 5 鏈 E2E 驗證: Missive health / kunge_snapshot / tools manifest / Hermes gateway / bridge skill
# 任一鏈斷 → 寫 integration-health marker + 將觸發 LINE alert (透過 cron job)
# ----------------------------------------------------------------------------
echo -e "${CYAN}[62/63] integration e2e validation (v6.13 整合連通 持續驗證)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/integration_e2e_validation.py || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/integration_e2e_validation.py || true
fi
echo ""

# ----------------------------------------------------------------------------
# step 63: Transaction Pollution Audit (L64, 2026-06-03)
# 觸發: LINE 推播鏈 silent fail（吞錯不 rollback 污染共用 session）—
#       2026-01-09 BUGFIX_TRANSACTION_POLLUTION 復發。
# 偵測: try 內對注入式共用 session (self.db/ctx.db) 做 DB 操作，但 except
#       既未 rollback 也未 re-raise → 後續 query / 推播段會 silent 撞交易錯。
# baseline 2026-06-03: 59 候選（advisory；逐步收斂，新增不得超過 baseline）
# ----------------------------------------------------------------------------
echo -e "${CYAN}[63/63] transaction pollution audit (L64 交易污染防復發)${NC}"
if $STRICT; then
    PYTHONIOENCODING=utf-8 python scripts/checks/transaction_pollution_audit.py --strict || FAIL_COUNT=$((FAIL_COUNT+1))
else
    PYTHONIOENCODING=utf-8 python scripts/checks/transaction_pollution_audit.py || true
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
