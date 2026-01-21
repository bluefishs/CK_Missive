"""merge_heads_and_add_coordinates

Revision ID: 133fbad5cf1e
Revises: b2c3d4e5f6g7, add_link_unique_constraints
Create Date: 2026-01-21 17:09:45.311738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '133fbad5cf1e'
down_revision: Union[str, Sequence[str], None] = ('b2c3d4e5f6g7', 'add_link_unique_constraints')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 合併分支 - 欄位已在 b2c3d4e5f6g7 中添加
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
