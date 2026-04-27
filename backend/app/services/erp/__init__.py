"""ERP Services bounded context.

Wave 1: 4 ERP services already housed here (quotation/invoice/billing/vendor_payable).
Wave 2 (2026-04-27, v5.10.0+): expanded to include expense / finance / invoice
processing modules previously scattered at services/ top level.
"""
# Wave 1 (existing)
from .quotation_service import ERPQuotationService
from .invoice_service import ERPInvoiceService
from .billing_service import ERPBillingService
from .vendor_payable_service import ERPVendorPayableService

# Wave 2 expense / finance
from .expense_invoice import ExpenseInvoiceService
from .expense_approval import ExpenseApprovalService
from .expense_import import ExpenseImportService
from .finance_ledger import FinanceLedgerService
from .finance_export import FinanceExportService

# Wave 2 invoice processing
from .invoice_ocr_service import InvoiceOCRService, InvoiceOCRResult
# invoice_recognizer / invoice_ocr_parser / invoice_qr_decoder are mostly
# function-based modules — import from specific submodule path.

__all__ = [
    # Wave 1
    "ERPQuotationService", "ERPInvoiceService",
    "ERPBillingService", "ERPVendorPayableService",
    # Wave 2 expense/finance
    "ExpenseInvoiceService", "ExpenseApprovalService", "ExpenseImportService",
    "FinanceLedgerService", "FinanceExportService",
    # Wave 2 invoice
    "InvoiceOCRService", "InvoiceOCRResult",
]
