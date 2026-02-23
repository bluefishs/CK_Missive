"""add document_entities and entity_relations tables

Revision ID: add_entity_tables
Revises: add_feedback_score
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "add_entity_tables"
down_revision = "add_feedback_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # document_entities
    op.create_table(
        "document_entities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_name", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("context", sa.String(500), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_document_entities_id", "document_entities", ["id"])
    op.create_index("ix_document_entities_document_id", "document_entities", ["document_id"])
    op.create_index("ix_document_entities_entity_type", "document_entities", ["entity_type"])
    op.create_index("ix_doc_entities_name_type", "document_entities", ["entity_name", "entity_type"])
    op.create_index("ix_doc_entities_doc_type", "document_entities", ["document_id", "entity_type"])

    # entity_relations
    op.create_table(
        "entity_relations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_entity_name", sa.String(200), nullable=False),
        sa.Column("source_entity_type", sa.String(50), nullable=False),
        sa.Column("target_entity_name", sa.String(200), nullable=False),
        sa.Column("target_entity_type", sa.String(50), nullable=False),
        sa.Column("relation_type", sa.String(100), nullable=False),
        sa.Column("relation_label", sa.String(100), nullable=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("extracted_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_entity_relations_id", "entity_relations", ["id"])
    op.create_index("ix_entity_relations_document_id", "entity_relations", ["document_id"])
    op.create_index("ix_entity_rel_source", "entity_relations", ["source_entity_name", "source_entity_type"])
    op.create_index("ix_entity_rel_target", "entity_relations", ["target_entity_name", "target_entity_type"])
    op.create_index("ix_entity_rel_type", "entity_relations", ["relation_type"])


def downgrade() -> None:
    op.drop_table("entity_relations")
    op.drop_table("document_entities")
