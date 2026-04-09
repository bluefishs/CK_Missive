"""add graph_domain column and performance indexes

Revision ID: 20260409a001
Revises: 20260408a004
Create Date: 2026-04-09

Adds:
- canonical_entities.graph_domain VARCHAR(20) NOT NULL DEFAULT 'knowledge'
- Partial index ix_ce_domain_knowledge for KG-only queries
- Composite index ix_ce_source_mention for federation ranking
- Composite index ix_doc_mention_entity_doc for reverse lookups
- Index ix_agent_trace_created for trace queries
- Data migration to populate graph_domain from entity_type
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260409a001'
down_revision: Union[str, Sequence[str], None] = '20260408a004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Code graph entity types
_CODE_TYPES = (
    'py_module', 'py_class', 'py_function',
    'ts_module', 'ts_component', 'ts_hook', 'ts_interface', 'ts_type', 'ts_enum',
    'api_endpoint', 'service', 'repository', 'schema', 'config', 'middleware', 'db_table',
)

# ERP entity types
_ERP_TYPES = (
    'erp_quotation', 'erp_invoice', 'erp_billing', 'erp_expense',
    'erp_asset', 'erp_ledger', 'erp_vendor', 'erp_client',
)


def upgrade() -> None:
    # 1. Add graph_domain column with default
    op.add_column('canonical_entities', sa.Column(
        'graph_domain', sa.String(20), nullable=False,
        server_default='knowledge',
        comment="圖譜域: knowledge (KG) / code (Code Graph) / erp (ERP)",
    ))

    # 2. Data migration: populate graph_domain from entity_type
    ce = sa.table(
        'canonical_entities',
        sa.column('graph_domain', sa.String),
        sa.column('entity_type', sa.String),
    )

    op.execute(
        ce.update()
        .where(ce.c.entity_type.in_(_CODE_TYPES))
        .values(graph_domain='code')
    )
    op.execute(
        ce.update()
        .where(ce.c.entity_type.in_(_ERP_TYPES))
        .values(graph_domain='erp')
    )
    # Everything else already defaults to 'knowledge'

    # 3. Partial index for KG-only queries (most common access pattern)
    op.create_index(
        'ix_ce_domain_knowledge',
        'canonical_entities',
        ['entity_type'],
        postgresql_where=sa.text("graph_domain = 'knowledge'"),
    )

    # 4. Composite index for federation ranking
    op.create_index(
        'ix_ce_source_mention',
        'canonical_entities',
        ['source_project', sa.text('mention_count DESC')],
    )

    # 5. Composite index for reverse lookups (entity -> documents)
    op.create_index(
        'ix_doc_mention_entity_doc',
        'document_entity_mentions',
        ['canonical_entity_id', 'document_id'],
    )

    # 6. Index for trace queries ordered by time
    op.create_index(
        'ix_agent_trace_created',
        'agent_query_traces',
        [sa.text('created_at DESC')],
    )


def downgrade() -> None:
    op.drop_index('ix_agent_trace_created', table_name='agent_query_traces')
    op.drop_index('ix_doc_mention_entity_doc', table_name='document_entity_mentions')
    op.drop_index('ix_ce_source_mention', table_name='canonical_entities')
    op.drop_index('ix_ce_domain_knowledge', table_name='canonical_entities')
    op.drop_column('canonical_entities', 'graph_domain')
