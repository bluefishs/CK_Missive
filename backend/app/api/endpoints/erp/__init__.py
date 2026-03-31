"""ERP API Endpoints — 全部端點需認證"""
from fastapi import APIRouter, Depends
from app.core.dependencies import require_auth
from . import quotations, invoices, billings, vendor_payables, vendor_accounts
from . import client_accounts
from . import expenses, ledger, financial_summary, einvoice_sync
from . import assets
from . import operational

router = APIRouter(dependencies=[Depends(require_auth())])
router.include_router(quotations.router, prefix="/quotations", tags=["ERP 報價管理"])
router.include_router(invoices.router, prefix="/invoices", tags=["ERP 發票管理"])
router.include_router(billings.router, prefix="/billings", tags=["ERP 請款管理"])
router.include_router(vendor_payables.router, prefix="/vendor-payables", tags=["ERP 廠商應付"])
router.include_router(vendor_accounts.router, prefix="/vendor-accounts", tags=["ERP 廠商帳款"])
router.include_router(expenses.router, prefix="/expenses", tags=["費用報銷"])
router.include_router(ledger.router, prefix="/ledger", tags=["統一帳本"])
router.include_router(financial_summary.router, prefix="/financial-summary", tags=["財務彙總"])
router.include_router(einvoice_sync.router, prefix="/einvoice-sync", tags=["電子發票同步"])
router.include_router(client_accounts.router, prefix="/client-accounts", tags=["ERP 委託單位帳款"])
router.include_router(assets.router, prefix="/assets", tags=["ERP 資產管理"])
router.include_router(operational.router, prefix="/operational", tags=["ERP 營運帳目"])
