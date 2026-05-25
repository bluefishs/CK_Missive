#!/usr/bin/env bash
# CK_Missive 範本一鍵套用工具
#
# 把 CK_Missive 的 L4 Plug-and-Play 資產（fitness functions / static guards /
# ADR templates / observability configs）部署到目標 repo。
#
# 用法:
#     bash scripts/install-template-to.sh <TARGET_REPO_PATH> [--dry-run] [--include=fitness,guards,adr,obs,playbook]
#
# 範例:
#     bash scripts/install-template-to.sh ../CK_lvrland_Webmap
#     bash scripts/install-template-to.sh ../CK_Hermes --dry-run
#     bash scripts/install-template-to.sh ../CK_PileMgmt --include=fitness,guards
#
# 預設安裝全部 4 類資產。
#
# 安裝後動作（人工）:
#   1. 改 scripts/checks/run_fitness.sh 內 WIKI_DIR / SERVICES_ROOT 變數
#   2. 改 ADR 範本 header 的 repo 名稱
#   3. 跑 bash scripts/checks/run_fitness.sh 取得 baseline
#
# 範本來源版本: CK_Missive v5.10.1+ (2026-04-28，含 fitness step 7 + L21 prevention)
# 對應文件: docs/architecture/TEMPLATE_EXTRACTION.md

set -euo pipefail

# === 參數解析 ===
TARGET=""
DRY_RUN=0
INCLUDE="fitness,guards,adr,obs,playbook,standards,pipeline,capability"

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=1 ;;
        --include=*) INCLUDE="${arg#--include=}" ;;
        --help|-h)
            sed -n '2,18p' "$0"; exit 0 ;;
        *)
            if [ -z "$TARGET" ]; then TARGET="$arg"; fi ;;
    esac
done

if [ -z "$TARGET" ]; then
    echo "ERROR: 缺 target repo 路徑" >&2
    echo "用法: bash scripts/install-template-to.sh <TARGET_REPO_PATH>" >&2
    exit 1
fi
if [ ! -d "$TARGET" ]; then
    echo "ERROR: target 不存在: $TARGET" >&2
    exit 1
fi

# 取絕對路徑
TARGET="$(cd "$TARGET" && pwd)"
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================================"
echo "CK_Missive 範本套用工具"
echo "  Source: $SOURCE"
echo "  Target: $TARGET"
echo "  Include: $INCLUDE"
echo "  Mode:    $([ $DRY_RUN -eq 1 ] && echo 'DRY RUN' || echo 'APPLY')"
echo "============================================================"

# === 工具函數 ===
copy_file() {
    local src="$1" dst="$2"
    if [ ! -f "$src" ]; then
        echo "  [SKIP] source not found: $src"
        return
    fi
    if [ -f "$dst" ]; then
        echo "  [EXISTS] $dst"
        return
    fi
    if [ $DRY_RUN -eq 1 ]; then
        echo "  [DRY-RUN] would copy: $src → $dst"
    else
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        echo "  [COPIED] $dst"
    fi
}

copy_dir() {
    local src="$1" dst="$2"
    if [ ! -d "$src" ]; then
        echo "  [SKIP] source dir not found: $src"
        return
    fi
    if [ $DRY_RUN -eq 1 ]; then
        echo "  [DRY-RUN] would copy dir: $src → $dst"
    else
        mkdir -p "$dst"
        cp -r "$src/"* "$dst/" 2>/dev/null || true
        echo "  [COPIED dir] $dst"
    fi
}

# === 1. Fitness Functions (7 step + scanners + L21 prevention) ===
if [[ "$INCLUDE" == *"fitness"* ]]; then
    echo ""
    echo "[1/5] Fitness Functions"
    copy_file "$SOURCE/scripts/checks/run_fitness.sh"                      "$TARGET/scripts/checks/run_fitness.sh"
    copy_file "$SOURCE/scripts/checks/service_dir_entropy.py"              "$TARGET/scripts/checks/service_dir_entropy.py"
    copy_file "$SOURCE/scripts/checks/config_dead_reader_scan.py"          "$TARGET/scripts/checks/config_dead_reader_scan.py"
    copy_file "$SOURCE/scripts/checks/soul_mirror_drift_check.py"          "$TARGET/scripts/checks/soul_mirror_drift_check.py"
    copy_file "$SOURCE/scripts/checks/wiki_kg_link_audit.py"               "$TARGET/scripts/checks/wiki_kg_link_audit.py"
    copy_file "$SOURCE/scripts/checks/kg_embedding_coverage_check.py"      "$TARGET/scripts/checks/kg_embedding_coverage_check.py"
    copy_file "$SOURCE/scripts/checks/adr_lifecycle_check.py"              "$TARGET/scripts/checks/adr_lifecycle_check.py"
    copy_file "$SOURCE/scripts/checks/agent_evolution_health.py"           "$TARGET/scripts/checks/agent_evolution_health.py"
    copy_file "$SOURCE/scripts/checks/lessons_drift_check.py"              "$TARGET/scripts/checks/lessons_drift_check.py"
    copy_file "$SOURCE/scripts/checks/dead_ui_detector.py"                 "$TARGET/scripts/checks/dead_ui_detector.py"
    copy_file "$SOURCE/scripts/checks/notify_consumers.py"                 "$TARGET/scripts/checks/notify_consumers.py"
    copy_file "$SOURCE/scripts/checks/README.md"                           "$TARGET/scripts/checks/README.md"
fi

# === 2. Static Guards (ADR-0028) ===
if [[ "$INCLUDE" == *"guards"* ]]; then
    echo ""
    echo "[2/5] Static Guards"
    copy_file "$SOURCE/scripts/checks/async_session_race_guard.py"  "$TARGET/scripts/checks/async_session_race_guard.py"
    copy_file "$SOURCE/scripts/checks/sse_headers_guard.py"         "$TARGET/scripts/checks/sse_headers_guard.py"
    copy_file "$SOURCE/scripts/checks/schema_lazy_load_guard.py"    "$TARGET/scripts/checks/schema_lazy_load_guard.py"
fi

# === 3. ADR templates ===
if [[ "$INCLUDE" == *"adr"* ]]; then
    echo ""
    echo "[3/5] ADR Templates"
    copy_file "$SOURCE/docs/adr/0028-error-contract-silent-failure-policy.md"  "$TARGET/docs/adr/0028-error-contract-silent-failure-policy.md"
    copy_file "$SOURCE/docs/adr/0029-adr-lifecycle-policy.md"                   "$TARGET/docs/adr/0029-adr-lifecycle-policy.md"
    copy_file "$SOURCE/docs/adr/0030-hermes-go-no-go-revision.md"              "$TARGET/docs/adr/0030-hermes-go-no-go-revision.md"
fi

# === 4. Observability ===
if [[ "$INCLUDE" == *"obs"* ]]; then
    echo ""
    echo "[4/5] Observability Configs"
    copy_dir  "$SOURCE/configs/grafana/dashboards" "$TARGET/configs/grafana/dashboards"
    copy_file "$SOURCE/configs/grafana/README.md"        "$TARGET/configs/grafana/README.md"
    copy_file "$SOURCE/configs/grafana/promtail-pm2.yml" "$TARGET/configs/grafana/promtail-pm2.yml"
    copy_file "$SOURCE/configs/prometheus/alerts.yml"    "$TARGET/configs/prometheus/alerts.yml"
fi

# === 5. Architecture Playbooks ===
if [[ "$INCLUDE" == *"playbook"* ]]; then
    echo ""
    echo "[5/8] Architecture Playbooks"
    copy_file "$SOURCE/docs/architecture/STANDARD_REFERENCE.md"             "$TARGET/docs/architecture/STANDARD_REFERENCE.md"
    copy_file "$SOURCE/docs/architecture/TEMPLATE_EXTRACTION.md"            "$TARGET/docs/architecture/TEMPLATE_EXTRACTION.md"
    copy_file "$SOURCE/docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md" "$TARGET/docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md"
    copy_file "$SOURCE/docs/architecture/WAVE_1_RETROSPECTIVE.md"           "$TARGET/docs/architecture/WAVE_1_RETROSPECTIVE.md"
    copy_file "$SOURCE/backend/app/core/timeouts.py"                        "$TARGET/backend/app/core/timeouts.py"
fi

# === 6. Standards (v6.10 新增 — 落地門檻 + 持續監控) ===
if [[ "$INCLUDE" == *"standards"* ]]; then
    echo ""
    echo "[6/8] Standards"
    copy_file "$SOURCE/docs/architecture/MODULARIZATION_STANDARDS_v1.md"  "$TARGET/docs/architecture/MODULARIZATION_STANDARDS_v1.md"
    copy_file "$SOURCE/docs/architecture/CAPABILITY_GOVERNANCE.md"        "$TARGET/docs/architecture/CAPABILITY_GOVERNANCE.md"
    copy_file "$SOURCE/.claude/rules/adr-anti-half-wired-sop.md"          "$TARGET/.claude/rules/adr-anti-half-wired-sop.md"
fi

# === 7. Pipeline (v6.10 新增 — 每日自動巡檢流水線) ===
if [[ "$INCLUDE" == *"pipeline"* ]]; then
    echo ""
    echo "[7/8] Optimization Pipeline"
    copy_file "$SOURCE/docs/architecture/OPTIMIZATION_PIPELINE.md"                       "$TARGET/docs/architecture/OPTIMIZATION_PIPELINE.md"
    copy_file "$SOURCE/backend/app/services/optimization_pipeline_orchestrator.py"      "$TARGET/backend/app/services/optimization_pipeline_orchestrator.py"
fi

# === 8. Capability Governance Tools (v6.10 新增 — dead capability 自動偵測) ===
if [[ "$INCLUDE" == *"capability"* ]]; then
    echo ""
    echo "[8/8] Capability Governance Tools"
    copy_file "$SOURCE/scripts/checks/capability_usage_audit.py"  "$TARGET/scripts/checks/capability_usage_audit.py"
fi

# === 結尾提醒 ===
echo ""
echo "============================================================"
if [ $DRY_RUN -eq 1 ]; then
    echo "DRY RUN 完成 — 沒有實際 copy。執行不加 --dry-run 套用。"
else
    echo "✅ 套用完成。下一步（人工）："
    echo ""
    echo "  1. cd $TARGET"
    echo "  2. 修改 scripts/checks/run_fitness.sh 內 WIKI_DIR / SERVICES_ROOT 等變數"
    echo "  3. 修改 ADR header 的 repo 名稱"
    echo "  4. 跑 bash scripts/checks/run_fitness.sh 取得 baseline"
    echo "  5. git status 確認改動 → git add + commit"
    echo ""
    echo "  詳細指引: $TARGET/docs/architecture/TEMPLATE_EXTRACTION.md §0"
fi
echo "============================================================"
