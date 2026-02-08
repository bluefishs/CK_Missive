"""合併 Phase 4 所有遷移 head

合併 add_mfa_fields 和 add_pgvector_embedding 為單一 head

Revision ID: merge_phase4_heads
Revises: add_mfa_fields, add_pgvector_embedding
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'merge_phase4_heads'
down_revision = ('add_mfa_fields', 'add_pgvector_embedding')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
