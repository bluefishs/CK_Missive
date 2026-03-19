"""add source column to government_agencies

Revision ID: 7e898cff87c7
Revises: 20260317a002
Create Date: 2026-03-19 17:19:46.650058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e898cff87c7'
down_revision: Union[str, Sequence[str], None] = '20260317a002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 source 欄位追蹤機關資料來源 (manual/auto/import)"""
    op.add_column(
        'government_agencies',
        sa.Column('source', sa.String(20), server_default='manual', nullable=False, comment='資料來源: manual/auto/import'),
    )


def downgrade() -> None:
    """移除 source 欄位"""
    op.drop_column('government_agencies', 'source')
