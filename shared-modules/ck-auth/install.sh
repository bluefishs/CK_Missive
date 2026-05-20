#!/usr/bin/env bash
# shared-modules/ck-auth/install.sh
#
# 一鍵安裝 ck-auth 到 consumer repo (CK_AaaP / lvrland / pile / KMapAdvisor)
#
# Usage:
#   bash /path/to/CK_Missive/shared-modules/ck-auth/install.sh [TARGET_REPO]
#
# Examples:
#   # 安裝到 lvrland
#   bash CK_Missive/shared-modules/ck-auth/install.sh /d/CKProject/CK_lvrland_Webmap
#
#   # 安裝到當前 cwd
#   bash CK_Missive/shared-modules/ck-auth/install.sh
#
# 安裝前審計（強制）：
#   - 跑 module_portability_audit 確認 PORTABLE
#   - 若 NOT_PORTABLE 拒絕安裝

set -e

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse args: --dry-run / --force / --no-frontend / first positional = TARGET
# v6.10.1 (2026-05-20): 加 --no-frontend 預設啟用（避免 LR-015 重演）
#   ck-auth v1.0 frontend (withAuth/useAuthGuard) hardcode `import { ROUTES } from '../../router/types'`
#   + 5 層 transitive deps → consumer --force 必爆 ≥10 TS errors（同 ck-navigation v1.0 19 TS errors）
#   v2.0 BREAKING 完整重設計待 owner 排程；本 flag 為短期 mitigation
DRY_RUN=0
FORCE=0
NO_FRONTEND=1
TARGET=""
for arg in "$@"; do
    case "$arg" in
        --dry-run)      DRY_RUN=1 ;;
        --force)        FORCE=1 ;;
        --no-frontend)  NO_FRONTEND=1 ;;
        --frontend)     NO_FRONTEND=0 ;;
        --help|-h)
            grep "^#" "${BASH_SOURCE[0]}" | head -30
            exit 0
            ;;
        *) [[ -z "${TARGET}" ]] && TARGET="$arg" ;;
    esac
done
TARGET="${TARGET:-$(pwd)}"

echo "============================================================"
echo " ck-auth v${VERSION} installer"
echo "============================================================"
echo ""
echo " Source  : ${SCRIPT_DIR}"
echo " Target  : ${TARGET}"
echo " Dry-run : $([ ${DRY_RUN} -eq 1 ] && echo YES || echo NO)"
echo " Force   : $([ ${FORCE} -eq 1 ] && echo YES || echo NO)"
echo ""

# Conflict detection helper
_check_conflict() {
    local target_file="$1"
    if [[ -f "$target_file" ]]; then
        if [[ ${FORCE} -eq 1 ]]; then
            echo "    [OVERWRITE] $target_file"
            return 0
        fi
        echo "    [CONFLICT]  $target_file (existing, use --force to overwrite)"
        return 1
    fi
    return 0
}

# Copy helper (dry-run aware, conflict-aware)
_safe_copy() {
    local src="$1"
    local dst="$2"
    if [[ -f "$dst" && ${FORCE} -eq 0 ]]; then
        if [[ ${DRY_RUN} -eq 1 ]]; then
            echo "    [CONFLICT]  $(basename ${src}) <- existing at ${dst} (use --force)"
        else
            echo "    [SKIP]      $(basename ${src}) - existing target (use --force)"
        fi
        return 1
    fi
    if [[ ${DRY_RUN} -eq 1 ]]; then
        echo "    [WOULD-CP]  $(basename ${src}) -> ${dst}"
        return 0
    fi
    cp -p "$src" "$dst"
}

# ---------------------------------------------------------------
# 1. 前置檢查
# ---------------------------------------------------------------
if [[ ! -d "${TARGET}" ]]; then
    echo "[ERROR] Target directory not found: ${TARGET}" >&2
    exit 1
fi

# 預期 target 至少有 backend/ 或 frontend/
if [[ ! -d "${TARGET}/backend" && ! -d "${TARGET}/frontend" ]]; then
    echo "[WARN] Target lacks backend/ or frontend/ - may not be a CK project"
    read -p "Continue anyway? [y/N] " confirm
    if [[ "${confirm}" != "y" ]]; then exit 0; fi
fi

# ---------------------------------------------------------------
# 2. Portability Audit (強制)
# ---------------------------------------------------------------
echo "[1/5] Running portability audit..."
AUDIT_SCRIPT="${SCRIPT_DIR}/../../scripts/checks/module_portability_audit.py"
if [[ -f "${AUDIT_SCRIPT}" ]]; then
    if ! PYTHONIOENCODING=utf-8 python "${AUDIT_SCRIPT}" "${SCRIPT_DIR}" --strict; then
        echo "[ERROR] Audit failed - ck-auth has critical business coupling" >&2
        echo "        Refuse to install. Fix source first." >&2
        exit 2
    fi
    echo "    [OK] Audit passed"
else
    echo "    [SKIP] Audit script not found (running in standalone mode)"
fi

# ---------------------------------------------------------------
# 3. Backend installation
# ---------------------------------------------------------------
echo ""
echo "[2/5] Installing backend (dry-run safe)..."
CONFLICT_COUNT=0
INSTALL_COUNT=0
if [[ -d "${SCRIPT_DIR}/backend/api_endpoints" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/backend/app/api/endpoints/auth"
    for f in "${SCRIPT_DIR}/backend/api_endpoints/"*.py; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/backend/app/api/endpoints/auth/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

if [[ -d "${SCRIPT_DIR}/backend/core" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/backend/app/core"
    for f in "${SCRIPT_DIR}/backend/core/"*.py; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/backend/app/core/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

# ---------------------------------------------------------------
# 4. Frontend installation
# ---------------------------------------------------------------
echo ""
echo "[3/5] Installing frontend (dry-run safe)..."
# v6.10.1 (2026-05-20): --no-frontend 預設啟用 — 避免 LR-015 重演
#   ck-auth v1.0 frontend hardcoded ROUTES → consumer --force 必爆 ≥10 TS errors
#   v2.0 BREAKING 拆 backend-only 待 owner 排程；short-term mitigation：跳 frontend
#   Consumer 須自寫 LoginPanel / withAuth / useAuthGuard / authService / useLineLogin
if [[ ${NO_FRONTEND} -eq 1 ]]; then
    echo "    [SKIP] Frontend skipped (default v6.10.1+, use --frontend to override)"
    echo "    Reason: ck-auth v1.0 frontend has hardcoded ROUTES + 5-layer transitive deps"
    echo "            Consumer --force would cause >= 10 TS compile errors (LR-015 pattern)"
    echo "            v2.0 BREAKING (拆 backend-only) 待 owner 排程"
elif [[ -d "${SCRIPT_DIR}/frontend/components" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/frontend/src/components/auth"
    for f in "${SCRIPT_DIR}/frontend/components/"*.tsx; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/frontend/src/components/auth/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

if [[ ${NO_FRONTEND} -eq 0 && -d "${SCRIPT_DIR}/frontend/services" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/frontend/src/services" "${TARGET}/frontend/src/api"
    _safe_copy "${SCRIPT_DIR}/frontend/services/authService.ts" "${TARGET}/frontend/src/services/authService.ts" \
        && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    _safe_copy "${SCRIPT_DIR}/frontend/services/authApi.ts" "${TARGET}/frontend/src/api/authApi.ts" \
        && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
fi

if [[ -d "${SCRIPT_DIR}/frontend/hooks" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/frontend/src/hooks/utility"
    for f in "${SCRIPT_DIR}/frontend/hooks/"*.ts; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/frontend/src/hooks/utility/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

if [[ -d "${SCRIPT_DIR}/frontend/types" ]]; then
    [[ ${DRY_RUN} -eq 0 ]] && mkdir -p "${TARGET}/frontend/src/types"
    for f in "${SCRIPT_DIR}/frontend/types/"*.d.ts; do
        [[ -f "$f" ]] || continue
        dst="${TARGET}/frontend/src/types/$(basename "$f")"
        _safe_copy "$f" "$dst" && INSTALL_COUNT=$((INSTALL_COUNT+1)) || CONFLICT_COUNT=$((CONFLICT_COUNT+1))
    done
fi

echo ""
echo "    Summary: ${INSTALL_COUNT} would-install, ${CONFLICT_COUNT} conflicts"

# ---------------------------------------------------------------
# 5. Env template
# ---------------------------------------------------------------
echo ""
echo "[4/5] Generating .env.ck-auth.template..."
cat > "${TARGET}/.env.ck-auth.template" << 'EOF'
# ck-auth v1.0 required environment variables
# 將以下變數複製到 consumer repo 的 .env 內並填值

# === Google OAuth ===
CKAUTH_GOOGLE_CLIENT_ID=
CKAUTH_GOOGLE_CLIENT_SECRET=
CKAUTH_GOOGLE_REDIRECT_URI=

# === LINE Login (optional) ===
CKAUTH_LINE_CHANNEL_ID=
CKAUTH_LINE_CHANNEL_SECRET=
CKAUTH_LINE_CALLBACK_URL=

# === JWT ===
CKAUTH_JWT_SECRET_KEY=
CKAUTH_JWT_ALGORITHM=HS256
CKAUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60

# === Session ===
CKAUTH_SESSION_TTL_SECONDS=3600

# === v6.x 兼容性（舊變數，可選填，會自動 fallback）===
# GOOGLE_CLIENT_ID=
# LINE_CHANNEL_ID=
# JWT_SECRET_KEY=
EOF
echo "    [OK] .env.ck-auth.template (12 vars, namespace-prefixed)"

# ---------------------------------------------------------------
# 6. Summary
# ---------------------------------------------------------------
echo ""
echo "[5/5] Installation complete!"
echo ""
echo "============================================================"
echo " Next steps:"
echo "============================================================"
echo " 1. Configure env vars: cp .env.ck-auth.template .env (and fill values)"
echo " 2. Add User model that inherits BaseUser (see README)"
echo " 3. Register auth router in your FastAPI app:"
echo "      from app.api.endpoints.auth import auth_router"
echo "      app.include_router(auth_router, prefix='/api/auth')"
echo " 4. Add CSRF middleware in main.py"
echo " 5. Run frontend: npm install (no new deps if React/Antd already present)"
echo ""
echo " Documentation: ${SCRIPT_DIR}/README.md"
echo " Version: ${VERSION}"
echo "============================================================"
