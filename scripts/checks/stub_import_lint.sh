#!/bin/bash
#
# stub_import_lint.sh — DDD 邊界落實 lint
#
# 領域：Wave 1-8 services DDD 遷移後保留 73 個 stub 做向後相容（2026-Q3 移除）。
# 生產代碼必須直接 import 新路徑，不可走 stub —— 否則 Q3 移除時會斷裂。
#
# 為什麼：
#   v5.10.2（2026-04-29）外科手術級清掉 26 處 audit/case_code/notification stub
#   引用，後續維護者必須沿用新路徑（services.audit / services.contract /
#   services.notification 等子包），不可走 *_service.py shim。
#
# Tests 例外：tests/ 故意 import stub 測 backward compat，本 lint 自動排除。
#
# 用法：bash scripts/checks/stub_import_lint.sh
# 退出：0 = 合規 / 1 = 違規

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

echo "=== Stub Import Lint (DDD boundary enforcement) ==="
echo ""

# 已知主要 Wave 1-8 stub。新增 stub 時加進此清單。
STUBS=(
    audit_service
    case_code_service
    notification_service
    document_service
    agency_service
    vendor_service
    project_service
    project_staff_service
    project_analytics_service
    document_calendar_service
    document_calendar_integrator
    document_calendar_sync
    document_export_service
    document_filter_service
    document_import_service
    document_import_logic_service
    document_query_filter_service
    document_serial_number_service
    document_statistics_service
    document_dispatch_linker_service
    agency_matching_service
    agency_statistics_service
    agency_contact_service
    case_field_sync_service
    project_agency_contact_service
    audit_event_loggers
    audit_mixin
    notification_template_service
    notification_dispatcher
    notification_helpers
    expense_invoice_service
    expense_approval_service
    expense_import_service
    finance_export_service
    finance_ledger_service
    financial_summary_service
    invoice_recognizer
    invoice_ocr_service
    invoice_qr_decoder
    line_bot_service
    line_flex_builder
    line_image_handler
    line_push_scheduler
    telegram_bot_service
    discord_bot_service
    discord_helpers
    channel_adapter
    sender_context
    agent_stream_helper
    backup_scheduler
    system_health_service
    receiver_normalizer
    google_client
    google_sync_scheduler
    project_notification_service
    reminder_service
    tender_search_service
    tender_analytics_service
    wiki_service
    wiki_coverage_service
)

violations=0
violations_files=""

for stub in "${STUBS[@]}"; do
    # 排除：stub 自己 + .pyc cache + tests/
    matches=$(grep -rln "from app\.services\.${stub} import" backend/app backend/main.py \
        --include="*.py" 2>/dev/null | \
        grep -v "/${stub}\.py$" | \
        grep -v "__pycache__" || true)
    if [ -n "$matches" ]; then
        echo "[VIOLATION] services.${stub} (stub) still imported from production code:"
        echo "$matches" | sed 's/^/    /'
        violations=$((violations + $(echo "$matches" | wc -l)))
        violations_files="$violations_files\n$matches"
    fi
done

echo ""
if [ $violations -eq 0 ]; then
    echo "[OK] 生產代碼 0 處 stub import — DDD 邊界已落實"
    echo "     Tests 故意 import stub 測 backward compat，已排除"
    echo ""
    echo "為新增的 mutation / module 提醒："
    echo "  ✗ 不要：from app.services.audit_service import AuditService"
    echo "  ✓ 要：  from app.services.audit import AuditService"
    exit 0
fi

echo "==="
echo "[FAIL] 共 $violations 處 stub import — 違反 DDD 邊界"
echo ""
echo "修復方式（領域 → 新路徑對照）："
echo "  audit_service        → services.audit         (AuditService)"
echo "  case_code_service    → services.contract      (CaseCodeService)"
echo "  notification_service → services.notification  (NotificationService)"
echo "                       → services.notification.service (CRITICAL_FIELDS / NotificationType / NotificationSeverity)"
echo "  document_service     → services.document      (DocumentService)"
echo "  ... 其他 stub 對應子包見 docs/architecture/SERVICE_CONTEXT_MAP.md"
exit 1
