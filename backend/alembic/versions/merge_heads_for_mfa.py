"""合併多個 head 為 MFA 遷移做準備

Revision ID: merge_heads_for_mfa
Revises: add_ai_prompt_versions, add_ai_synonyms
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'merge_heads_for_mfa'
down_revision = ('add_ai_prompt_versions', 'add_ai_synonyms')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
