"""補齊 7 個 ForeignKey 欄位的索引

calendar: assigned_user_id, created_by
core: client_agency_id
document: uploaded_by (attachments)
erp: created_by (quotations)
finance: user_id (ledgers)
invoice: user_id (expense_invoices)

Revision ID: 20260325a001
Revises: 20260324a004
Create Date: 2026-03-25
"""
from alembic import op

revision = '20260325a001'
down_revision = '20260324a004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_document_calendar_events_assigned_user_id',
                    'document_calendar_events', ['assigned_user_id'])
    op.create_index('ix_document_calendar_events_created_by',
                    'document_calendar_events', ['created_by'])
    op.create_index('ix_contract_projects_client_agency_id',
                    'contract_projects', ['client_agency_id'])
    op.create_index('ix_document_attachments_uploaded_by',
                    'document_attachments', ['uploaded_by'])
    op.create_index('ix_erp_quotations_created_by',
                    'erp_quotations', ['created_by'])
    op.create_index('ix_finance_ledgers_user_id',
                    'finance_ledgers', ['user_id'])
    op.create_index('ix_expense_invoices_user_id',
                    'expense_invoices', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_expense_invoices_user_id', table_name='expense_invoices')
    op.drop_index('ix_finance_ledgers_user_id', table_name='finance_ledgers')
    op.drop_index('ix_erp_quotations_created_by', table_name='erp_quotations')
    op.drop_index('ix_document_attachments_uploaded_by', table_name='document_attachments')
    op.drop_index('ix_contract_projects_client_agency_id', table_name='contract_projects')
    op.drop_index('ix_document_calendar_events_created_by', table_name='document_calendar_events')
    op.drop_index('ix_document_calendar_events_assigned_user_id', table_name='document_calendar_events')
