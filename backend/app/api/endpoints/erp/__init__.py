"""ERP API Endpoints — 全部端點需認證"""
from fastapi import APIRouter, Depends
from app.core.dependencies import require_permission
from . import quotations, invoices, billings, vendor_payables, vendor_accounts
from . import client_accounts
from . import expenses, expenses_io, ledger, financial_summary, einvoice_sync, filing_gaps, quotation_items
from . import assets
from . import operational

# ⚠️ 2026-08-29 owner 裁示「ERP 權限收斂」：由 `require_auth()`（只問有沒有登入）
# 提升為 `require_permission("reports:erp:view")`。
#
# ## 為什麼
#
# 在此之前，**系統內任何登入者**（含一般同仁 staff）直接打 API 就能拉取
# 統一帳本、營運帳目、報價單與財務總覽 —— 前端選單把按鈕藏起來，
# 但那不是防禦（security through obscurity）。
#
# ## 前置條件已實測滿足（不是假設）
#
#   role_permissions 的 `reports:erp:view`：admin ✓ exec ✓ finance ✓ ops ✓ staff ✗
#   現有使用者：admin 5 人、staff 6 人、superuser 1 人
#   `require_permission` 對 superuser **短路放行**（dependencies.py:289）
#
# ⇒ 收斂後 **staff 6 人失去 ERP API 存取**，那正是目的；
#   admin/superuser 不受影響。外部評估文件說「admin 僅有 6 項權限、
#   同步前不可收斂」—— **實測 admin 有 33 項，那個前置警告已經過期**。
#
# ## 為什麼在 router 層而不是逐支端點
#
# ERP 目錄下 107 支端點，逐支改會漏（今天已經看過「同一條規則掃所有寫入
# 路徑」漏掉一支的代價）。router 層是單一收斂點，新增端點自動繼承。
# ⚠️ 反面風險：**同一個 router 底下若有真正該公開的端點，會被一起擋掉** ——
# 已由 weekly 65 `router_level_auth_mixing_audit` 守這件事。
router = APIRouter(dependencies=[Depends(require_permission("reports:erp:view"))])
router.include_router(quotations.router, prefix="/quotations", tags=["ERP 報價管理"])
router.include_router(invoices.router, prefix="/invoices", tags=["ERP 發票管理"])
router.include_router(billings.router, prefix="/billings", tags=["ERP 請款管理"])
router.include_router(vendor_payables.router, prefix="/vendor-payables", tags=["ERP 廠商應付"])
router.include_router(vendor_accounts.router, prefix="/vendor-accounts", tags=["ERP 廠商帳款"])
router.include_router(expenses.router, prefix="/expenses", tags=["費用報銷"])
router.include_router(expenses_io.router, prefix="/expenses", tags=["費用報銷 IO"])
router.include_router(ledger.router, prefix="/ledger", tags=["統一帳本"])
router.include_router(financial_summary.router, prefix="/financial-summary", tags=["財務彙總"])
# 2026-08-16 owner：「承攬報價案件對應填報人員通報管控」
router.include_router(filing_gaps.router, prefix="/filing-gaps", tags=["填報缺口"])
# 2026-08-16 owner：「線上報價單機制」
router.include_router(quotation_items.router, prefix="/quotation-items", tags=["報價明細"])
router.include_router(einvoice_sync.router, prefix="/einvoice-sync", tags=["電子發票同步"])
router.include_router(client_accounts.router, prefix="/client-accounts", tags=["ERP 委託單位帳款"])
router.include_router(assets.router, prefix="/assets", tags=["ERP 資產管理"])
router.include_router(operational.router, prefix="/operational", tags=["ERP 營運帳目"])
