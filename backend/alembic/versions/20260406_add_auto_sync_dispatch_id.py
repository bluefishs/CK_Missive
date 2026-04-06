"""add auto_sync_dispatch_id to taoyuan_document_project_link

Adds a proper FK column to track which dispatch order auto-created
a document-project link, replacing fragile string-based notes matching.

Revision ID: 20260406a001
Revises: 20260405a007
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260406a001'
down_revision = '20260405a007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'taoyuan_document_project_link',
        sa.Column(
            'auto_sync_dispatch_id',
            sa.Integer(),
            sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='SET NULL'),
            nullable=True,
            comment='Dispatch that auto-created this link (NULL=manual)',
        ),
    )
    op.create_index(
        'ix_taoyuan_document_project_link_auto_sync_dispatch_id',
        'taoyuan_document_project_link',
        ['auto_sync_dispatch_id'],
    )

    # Backfill: parse dispatch_no from notes and resolve to dispatch order ID.
    # Pattern: "自動同步自派工單 XXX-YYY" or "自動同步自派工單關聯 (公文建立時)"
    # We only backfill rows whose notes contain a specific dispatch_no.
    op.execute("""
        UPDATE taoyuan_document_project_link AS dpl
        SET auto_sync_dispatch_id = d.id
        FROM taoyuan_dispatch_orders AS d
        WHERE dpl.notes LIKE '%自動同步自派工單 ' || d.dispatch_no || '%'
          AND dpl.notes NOT LIKE '%自動同步自派工單關聯%'
          AND dpl.auto_sync_dispatch_id IS NULL
    """)


def downgrade():
    op.drop_index(
        'ix_taoyuan_document_project_link_auto_sync_dispatch_id',
        table_name='taoyuan_document_project_link',
    )
    op.drop_column('taoyuan_document_project_link', 'auto_sync_dispatch_id')
