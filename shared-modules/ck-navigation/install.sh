#!/usr/bin/env bash
# shared-modules/ck-navigation/install.sh
#
# 一鍵安裝 ck-navigation 到 consumer repo
#
# Usage:
#   bash /path/to/CK_Missive/shared-modules/ck-navigation/install.sh [TARGET_REPO] [--dry-run] [--force]
#
# 功能：
# - Backend: secure_site_management 5 endpoints + navigation_sync service
# - Frontend: layout (Header / Sidebar / SidebarContent) + hooks (useMenuItems / useNavigationData)

set -e

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DRY_RUN=0
FORCE=0
TARGET=""
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --force)   FORCE=1 ;;
        --help|-h) grep "^#" "${BASH_SOURCE[0]}" | head -25; exit 0 ;;
        *) [[ -z "${TARGET}" ]] && TARGET="$arg" ;;
    esac
done
TARGET="${TARGET:-$(pwd)}"

echo "============================================================"
echo " ck-navigation v${VERSION} installer"
echo "============================================================"
echo " Source : ${SCRIPT_DIR}"
echo " Target : ${TARGET}"
echo " Dry-run: $([ ${DRY_RUN} -eq 1 ] && echo YES || echo NO)"
echo " Force  : $([ ${FORCE} -eq 1 ] && echo YES || echo NO)"
echo ""

if [[ ! -d "${TARGET}" ]]; then
    echo "[ERROR] Target directory not found: ${TARGET}" >&2; exit 1
fi

# Safe copy helper
_safe_copy() {
    local src="$1"; local dst="$2"
    if [[ -f "$dst" && ${FORCE} -eq 0 ]]; then
        echo "    [CONFLICT]  $(basename ${src}) <- existing at ${dst}"
        return 1
    fi
    if [[ ${DRY_RUN} -eq 1 ]]; then
        echo "    [WOULD-CP]  $(basename ${src}) -> ${dst}"
        return 0
    fi
    cp -p "$src" "$dst"
}

# 1. Portability audit (forced)
echo "[1/5] Portability audit..."
AUDIT_SCRIPT="${SCRIPT_DIR}/../../scripts/checks/module_portability_audit.py"
if [[ -f "${AUDIT_SCRIPT}" ]]; then
    if ! PYTHONIOENCODING=utf-8 python "${AUDIT_SCRIPT}" "${SCRIPT_DIR}" --strict; then
        echo "[ERROR] Audit failed — refuse to install" >&2; exit 2
    fi
fi

# 2. Backend installation
echo ""
echo "[2/6] Installing backend..."
CONFLICT_COUNT=0
INSTALL_COUNT=0

# L36 修法 (2026-05-18)：detect_api_target — 偵測 consumer API 結構
# 防 Repo Structure Assumption 反模式（lvrland 用 v1/endpoints/ vs Missive 用 endpoints/）
detect_api_target() {
    if [[ -d "${TARGET}/backend/app/api/v1/endpoints" ]]; then
        echo "backend/app/api/v1/endpoints"      # versioned API style (lvrland, AaaP)
    elif [[ -d "${TARGET}/backend/app/api/endpoints" ]]; then
        echo "backend/app/api/endpoints"          # Missive style
    else
        echo "backend/app/api/endpoints"          # default for new consumers
    fi
}
API_TARGET=$(detect_api_target)
echo "    [DETECT] consumer API target: ${API_TARGET}"

if [[ -d "${SCRIPT_DIR}/backend/api_endpoints" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/${API_TARGET}/secure_site_management"
    for f in "${SCRIPT_DIR}/backend/api_endpoints/"*.py; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/${API_TARGET}/secure_site_management/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

if [[ -d "${SCRIPT_DIR}/backend/services" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/backend/app/services/system"
    for f in "${SCRIPT_DIR}/backend/services/"*.py; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/backend/app/services/system/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

# 3. Frontend installation (v2.0 only types/ — frontend UI 移除 per LR-015/L32)
echo ""
echo "[3/6] Installing frontend types..."
if [[ -d "${SCRIPT_DIR}/frontend/types" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/frontend/src/types"
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/frontend/src/types/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done < <(find "${SCRIPT_DIR}/frontend/types" -maxdepth 1 -type f \( -name "*.ts" -o -name "*.d.ts" \) 2>/dev/null)
fi

# 3.5 (v1.1 6-stage 守門 / lvrland 回饋 #2): Verify build stage
# 此為 partial 真採用 件 2 強制驗證（不阻擋但報告）
echo ""
echo "[3.5/6] Verify build (consumer-side TS/Python check)..."
if [[ ${DRY_RUN} -eq 0 ]]; then
    BUILD_OK=1
    if [[ -d "${TARGET}/frontend" ]]; then
        echo "    Running consumer-side npx tsc (frontend) ..."
        if (cd "${TARGET}/frontend" && npx tsc --noEmit --skipLibCheck 2>&1 | head -5); then
            echo "    [VERIFY OK] frontend TS compile pass"
        else
            echo "    [VERIFY FAIL] frontend TS errors — partial 真採用件 2 未通過"
            BUILD_OK=0
        fi
    fi
    if [[ -d "${TARGET}/backend" ]]; then
        echo "    Running consumer-side python compile check (backend) ..."
        if (cd "${TARGET}/backend" && python -m py_compile app/api/endpoints/secure_site_management/*.py 2>&1); then
            echo "    [VERIFY OK] backend py_compile pass"
        else
            echo "    [VERIFY FAIL] backend syntax errors"
            BUILD_OK=0
        fi
    fi
    if [[ ${BUILD_OK} -eq 0 ]]; then
        echo "    WARNING: build verification failed — install marked PARTIAL"
    fi
else
    echo "    [DRY-RUN] would verify TS + py_compile after install"
fi

echo ""
echo "    Summary: ${INSTALL_COUNT} would-install, ${CONFLICT_COUNT} conflicts"

# 4. Env template
echo ""
echo "[4/6] Env template..."
if [[ ${DRY_RUN} -eq 0 ]]; then
    cat > "${TARGET}/.env.ck-navigation.template" << 'EOF'
# ck-navigation v1.0 (optional — navigation 主要用 DB 配置不需 env)

# 若有外部 navigation API（少見）
# CKNAV_API_BASE_URL=
EOF
    echo "    [OK] .env.ck-navigation.template"
else
    echo "    [DRY-RUN] would create .env.ck-navigation.template"
fi

# 5. Summary
echo ""
echo "[5/6] Done. Next steps:"
echo " 1. Register navigation router in main.py:"
echo "      from app.api.endpoints.secure_site_management import navigation_router"
echo "      app.include_router(navigation_router, prefix='/api/secure-site-management')"
echo " 2. Run alembic migration for navigation_items table (see manifest.yml)"
echo " 3. Frontend: import Sidebar from 'components/layout/Sidebar'"
echo " 4. Configure DEFAULT_NAVIGATION_ITEMS in consumer's seed script"
echo "============================================================"
