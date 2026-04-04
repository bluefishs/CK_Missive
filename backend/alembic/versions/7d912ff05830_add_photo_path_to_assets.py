"""add photo_path to assets

Revision ID: 7d912ff05830
Revises: 20260401a002
Create Date: 2026-04-02 15:35:00.954493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7d912ff05830'
down_revision: Union[str, Sequence[str], None] = '20260401a002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add photo_path column to assets table."""
    op.add_column('assets', sa.Column('photo_path', sa.String(500), nullable=True, comment='資產照片路徑'))


def downgrade() -> None:
    """Remove photo_path column from assets table."""
    op.drop_column('assets', 'photo_path')
