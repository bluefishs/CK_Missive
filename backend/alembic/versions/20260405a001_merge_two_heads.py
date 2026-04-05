"""merge two heads (20260404a001 + 20260404b001)

Revision ID: 20260405a001
Revises: 20260404a001, 20260404b001
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260405a001'
down_revision: Union[str, Sequence[str], None] = ('20260404a001', '20260404b001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
