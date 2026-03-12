"""add taoyuan_dispatch_entity_link table

Revision ID: 20260312a001
Revises: add_dispatch_mgmt
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = '20260312a001'
down_revision = 'add_dispatch_mgmt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'taoyuan_dispatch_entity_link',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dispatch_order_id', sa.Integer(),
                  sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('canonical_entity_id', sa.Integer(),
                  sa.ForeignKey('canonical_entities.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='auto',
                  comment='來源: auto/manual/llm'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0',
                  comment='信心分數 0-1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_dispatch_entity',
        'taoyuan_dispatch_entity_link',
        ['dispatch_order_id', 'canonical_entity_id'],
    )


def downgrade() -> None:
    op.drop_table('taoyuan_dispatch_entity_link')
