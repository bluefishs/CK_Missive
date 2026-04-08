"""add entity version control columns

Revision ID: 20260408a004
Revises: 20260408a003
Create Date: 2026-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260408a004'
down_revision: Union[str, Sequence[str], None] = '20260408a003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('canonical_entities', sa.Column(
        'version', sa.Integer(), nullable=False, server_default='1',
        comment='實體版本號',
    ))
    op.add_column('canonical_entities', sa.Column(
        'valid_from', sa.DateTime(), server_default=sa.func.now(),
        comment='此版本生效時間',
    ))
    op.add_column('canonical_entities', sa.Column(
        'valid_to', sa.DateTime(), nullable=True,
        comment='此版本失效時間 (NULL=當前有效)',
    ))


def downgrade() -> None:
    op.drop_column('canonical_entities', 'valid_to')
    op.drop_column('canonical_entities', 'valid_from')
    op.drop_column('canonical_entities', 'version')
