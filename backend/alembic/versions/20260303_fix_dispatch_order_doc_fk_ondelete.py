"""fix: add ondelete SET NULL to dispatch order document FK columns

Fixes 500 error when deleting documents referenced by dispatch orders.
The agency_doc_id and company_doc_id columns were missing ondelete clause,
defaulting to RESTRICT which blocks deletion.

Revision ID: 20260303a001
Revises: 4a48d26606e3
Create Date: 2026-03-03
"""
from alembic import op

# revision identifiers
revision = '20260303a001'
down_revision = '4a48d26606e3'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing constraints (default RESTRICT)
    op.drop_constraint(
        'taoyuan_dispatch_orders_agency_doc_id_fkey',
        'taoyuan_dispatch_orders',
        type_='foreignkey'
    )
    op.drop_constraint(
        'taoyuan_dispatch_orders_company_doc_id_fkey',
        'taoyuan_dispatch_orders',
        type_='foreignkey'
    )

    # Re-create with SET NULL
    op.create_foreign_key(
        'taoyuan_dispatch_orders_agency_doc_id_fkey',
        'taoyuan_dispatch_orders', 'documents',
        ['agency_doc_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'taoyuan_dispatch_orders_company_doc_id_fkey',
        'taoyuan_dispatch_orders', 'documents',
        ['company_doc_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint(
        'taoyuan_dispatch_orders_agency_doc_id_fkey',
        'taoyuan_dispatch_orders',
        type_='foreignkey'
    )
    op.drop_constraint(
        'taoyuan_dispatch_orders_company_doc_id_fkey',
        'taoyuan_dispatch_orders',
        type_='foreignkey'
    )

    op.create_foreign_key(
        'taoyuan_dispatch_orders_agency_doc_id_fkey',
        'taoyuan_dispatch_orders', 'documents',
        ['agency_doc_id'], ['id']
    )
    op.create_foreign_key(
        'taoyuan_dispatch_orders_company_doc_id_fkey',
        'taoyuan_dispatch_orders', 'documents',
        ['company_doc_id'], ['id']
    )
