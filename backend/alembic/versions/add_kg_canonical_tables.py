"""Add knowledge graph canonical entity tables

Revision ID: add_kg_canonical
Revises: add_entity_tables
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers
revision = 'add_kg_canonical'
down_revision = 'add_entity_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. canonical_entities
    op.create_table(
        'canonical_entities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('canonical_name', sa.String(300), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('alias_count', sa.Integer(), server_default='1'),
        sa.Column('mention_count', sa.Integer(), server_default='0'),
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('canonical_name', 'entity_type', name='uq_canonical_name_type'),
    )
    op.create_index('ix_canonical_entities_id', 'canonical_entities', ['id'])
    op.create_index('ix_canonical_entities_entity_type', 'canonical_entities', ['entity_type'])
    op.create_index('ix_canonical_entity_name_trgm', 'canonical_entities', ['canonical_name'])

    # pgvector embedding 欄位（僅 PGVECTOR_ENABLED=true）
    pgvector_enabled = os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"
    if pgvector_enabled:
        try:
            from pgvector.sqlalchemy import Vector
            op.add_column('canonical_entities', sa.Column('embedding', Vector(384), nullable=True))
        except Exception:
            pass

    # 2. entity_aliases
    op.create_table(
        'entity_aliases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('alias_name', sa.String(300), nullable=False),
        sa.Column('canonical_entity_id', sa.Integer(),
                  sa.ForeignKey('canonical_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), server_default='auto'),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('alias_name', 'canonical_entity_id', name='uq_alias_canonical'),
    )
    op.create_index('ix_entity_aliases_id', 'entity_aliases', ['id'])
    op.create_index('ix_entity_alias_name', 'entity_aliases', ['alias_name'])
    op.create_index('ix_entity_aliases_canonical_entity_id', 'entity_aliases', ['canonical_entity_id'])

    # 3. document_entity_mentions
    op.create_table(
        'document_entity_mentions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('canonical_entity_id', sa.Integer(),
                  sa.ForeignKey('canonical_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mention_text', sa.String(300), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('context', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_document_entity_mentions_id', 'document_entity_mentions', ['id'])
    op.create_index('ix_document_entity_mentions_document_id', 'document_entity_mentions', ['document_id'])
    op.create_index('ix_document_entity_mentions_canonical_entity_id', 'document_entity_mentions', ['canonical_entity_id'])
    op.create_index('ix_doc_mention_doc_entity', 'document_entity_mentions', ['document_id', 'canonical_entity_id'])

    # 4. entity_relationships
    op.create_table(
        'entity_relationships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_entity_id', sa.Integer(),
                  sa.ForeignKey('canonical_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_entity_id', sa.Integer(),
                  sa.ForeignKey('canonical_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relation_type', sa.String(100), nullable=False),
        sa.Column('relation_label', sa.String(100), nullable=True),
        sa.Column('weight', sa.Float(), server_default='1.0'),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('invalidated_at', sa.DateTime(), nullable=True),
        sa.Column('first_document_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('document_count', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_entity_relationships_id', 'entity_relationships', ['id'])
    op.create_index('ix_entity_relationships_source_entity_id', 'entity_relationships', ['source_entity_id'])
    op.create_index('ix_entity_relationships_target_entity_id', 'entity_relationships', ['target_entity_id'])
    op.create_index('ix_entity_relationship_src_tgt', 'entity_relationships', ['source_entity_id', 'target_entity_id'])
    op.create_index('ix_entity_relationship_type', 'entity_relationships', ['relation_type'])
    op.create_index('ix_entity_relationship_valid', 'entity_relationships', ['valid_from', 'valid_to'])

    # 5. graph_ingestion_events
    op.create_table(
        'graph_ingestion_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('entities_found', sa.Integer(), server_default='0'),
        sa.Column('entities_new', sa.Integer(), server_default='0'),
        sa.Column('entities_merged', sa.Integer(), server_default='0'),
        sa.Column('relations_found', sa.Integer(), server_default='0'),
        sa.Column('llm_provider', sa.String(20), nullable=True),
        sa.Column('processing_ms', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(20), server_default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_graph_ingestion_events_id', 'graph_ingestion_events', ['id'])
    op.create_index('ix_graph_ingestion_events_document_id', 'graph_ingestion_events', ['document_id'])


def downgrade() -> None:
    op.drop_table('graph_ingestion_events')
    op.drop_table('entity_relationships')
    op.drop_table('document_entity_mentions')
    op.drop_table('entity_aliases')
    op.drop_table('canonical_entities')
