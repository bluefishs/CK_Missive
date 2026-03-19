"""ERP API Endpoints"""
from fastapi import APIRouter
from . import quotations, invoices, billings, vendor_payables

router = APIRouter()
router.include_router(quotations.router, prefix="/quotations", tags=["ERP 報價管理"])
router.include_router(invoices.router, prefix="/invoices", tags=["ERP 發票管理"])
router.include_router(billings.router, prefix="/billings", tags=["ERP 請款管理"])
router.include_router(vendor_payables.router, prefix="/vendor-payables", tags=["ERP 廠商應付"])
