"""add erp composite indexes

Revision ID: 20260322a002
Revises: 20260321a002
Create Date: 2026-03-22

Phase 7-E: 新增 FinanceLedger 和 EInvoiceSyncLog 複合索引
- idx_ledger_case_date: 加速月度趨勢查詢
- idx_ledger_source: 加速來源追蹤查詢
- idx_einvoice_buyer: 加速統編篩選
- idx_einvoice_query_date: 加速日期範圍查詢
"""
from alembic import op


# revision identifiers
revision = "20260322a002"
down_revision = "20260321a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_ledger_case_date", "finance_ledgers", ["case_code", "transaction_date"])
    op.create_index("idx_ledger_source", "finance_ledgers", ["source_type", "source_id"])
    op.create_index("idx_einvoice_buyer", "einvoice_sync_logs", ["buyer_ban"])
    op.create_index("idx_einvoice_query_date", "einvoice_sync_logs", ["query_start", "query_end"])


def downgrade() -> None:
    op.drop_index("idx_einvoice_query_date", table_name="einvoice_sync_logs")
    op.drop_index("idx_einvoice_buyer", table_name="einvoice_sync_logs")
    op.drop_index("idx_ledger_source", table_name="finance_ledgers")
    op.drop_index("idx_ledger_case_date", table_name="finance_ledgers")
