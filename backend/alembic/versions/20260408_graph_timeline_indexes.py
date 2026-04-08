"""graph timeline indexes

Add composite indexes for timeline queries on entity_relationships
and entity_aliases tables.

Revision ID: 20260408a003
Revises: 20260408a002
Create Date: 2026-04-08
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260408a003"
down_revision = "20260408a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_entity_rel_src_valid",
        "entity_relationships",
        ["source_entity_id", "valid_from"],
    )
    op.create_index(
        "ix_entity_rel_tgt_valid",
        "entity_relationships",
        ["target_entity_id", "valid_from"],
    )
    op.create_index(
        "ix_entity_alias_entity",
        "entity_aliases",
        ["canonical_entity_id", "alias_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_entity_alias_entity", table_name="entity_aliases")
    op.drop_index("ix_entity_rel_tgt_valid", table_name="entity_relationships")
    op.drop_index("ix_entity_rel_src_valid", table_name="entity_relationships")
