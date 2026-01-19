"""merge_all_heads_for_taoyuan

Revision ID: 5c2da4a2d8aa
Revises: add_foreign_key_relations, add_agency_contacts, merge_and_remaining_indexes
Create Date: 2026-01-19 16:09:17.725273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2da4a2d8aa'
down_revision: Union[str, Sequence[str], None] = ('add_foreign_key_relations', 'add_agency_contacts', 'merge_and_remaining_indexes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
