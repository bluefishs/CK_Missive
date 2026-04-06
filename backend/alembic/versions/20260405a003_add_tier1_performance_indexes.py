"""add tier1 performance indexes

Revision ID: 20260405a003
Revises: 20260405a002
Create Date: 2026-04-05

Affected tables:
  - documents (created_at, updated_at, status+doc_type+doc_date)
  - contract_projects (status, year+status)
  - taoyuan_dispatch_orders (work_type, status)
  - erp_quotations (case_code+project_code)
  - finance_ledgers (entry_type)
  - expense_invoices (status)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260405a003'
down_revision: Union[str, Sequence[str], None] = '20260405a002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Documents table (critical — 1,638 rows, frequent queries) ===
    # Sort by created_at/updated_at
    op.create_index('ix_documents_created_at', 'documents', ['created_at'],
                     postgresql_using='btree', if_not_exists=True)
    op.create_index('ix_documents_updated_at', 'documents', ['updated_at'],
                     postgresql_using='btree', if_not_exists=True)

    # Composite for common filter+sort pattern: status + doc_type + doc_date
    op.create_index('ix_documents_status_type_date', 'documents',
                     ['status', 'doc_type', 'doc_date'],
                     postgresql_using='btree', if_not_exists=True)

    # === Contract Projects table ===
    op.create_index('ix_contract_projects_status', 'contract_projects',
                     ['status'], if_not_exists=True)
    op.create_index('ix_contract_projects_year_status', 'contract_projects',
                     ['year', 'status'], if_not_exists=True)

    # === Taoyuan Dispatch Orders ===
    op.create_index('ix_dispatch_orders_work_type', 'taoyuan_dispatch_orders',
                     ['work_type'], if_not_exists=True)
    # NOTE: taoyuan_dispatch_orders has no 'status' column — skipped

    # === ERP Quotations (cross-module lookup) ===
    op.create_index('ix_erp_quotations_case_project', 'erp_quotations',
                     ['case_code', 'project_code'], if_not_exists=True)

    # === Finance Ledgers ===
    op.create_index('ix_ledger_entry_type', 'finance_ledgers',
                     ['entry_type'], if_not_exists=True)

    # === Expense Invoices (common filter) ===
    op.create_index('ix_expense_invoices_status', 'expense_invoices',
                     ['status'], if_not_exists=True)


def downgrade() -> None:
    # Drop all indexes in reverse order
    op.drop_index('ix_expense_invoices_status', table_name='expense_invoices')
    op.drop_index('ix_ledger_entry_type', table_name='finance_ledgers')
    op.drop_index('ix_erp_quotations_case_project', table_name='erp_quotations')
    op.drop_index('ix_dispatch_orders_work_type', table_name='taoyuan_dispatch_orders')
    op.drop_index('ix_contract_projects_year_status', table_name='contract_projects')
    op.drop_index('ix_contract_projects_status', table_name='contract_projects')
    op.drop_index('ix_documents_status_type_date', table_name='documents')
    op.drop_index('ix_documents_updated_at', table_name='documents')
    op.drop_index('ix_documents_created_at', table_name='documents')
