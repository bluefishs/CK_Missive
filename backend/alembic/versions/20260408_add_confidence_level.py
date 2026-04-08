"""add confidence_level to entity_relationships

Add confidence_level column to track how each relationship was derived:
- extracted: directly from NER extraction
- inferred: from LLM semantic inference
- ambiguous: pending human review

Revision ID: 20260408a002
Revises: 20260408a001
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260408a002'
down_revision = '20260408a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'entity_relationships',
        sa.Column(
            'confidence_level',
            sa.String(20),
            nullable=False,
            server_default='extracted',
            comment='置信度: extracted (直接提取) / inferred (語意推導) / ambiguous (待審核)',
        ),
    )


def downgrade() -> None:
    op.drop_column('entity_relationships', 'confidence_level')
