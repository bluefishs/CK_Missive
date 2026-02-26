"""新增效能關鍵索引 — FK 索引 + pgvector HNSW

1. OfficialDocument: contract_project_id, sender_agency_id, receiver_agency_id
2. DocumentAttachment: document_id
3. pgvector: 從 IVFFlat 升級為 HNSW (小型資料集效能更佳)

Revision ID: add_perf_critical_indexes
Revises: add_kg_canonical
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_perf_critical_indexes'
down_revision = 'add_kg_canonical'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增遺漏的 FK 索引 + HNSW 向量索引"""

    # ---------------------------------------------------------------
    # 1. OfficialDocument FK 索引 (缺少 index=True 的外鍵)
    # ---------------------------------------------------------------
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_contract_project_id
        ON documents (contract_project_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_sender_agency_id
        ON documents (sender_agency_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_receiver_agency_id
        ON documents (receiver_agency_id)
    """)

    # ---------------------------------------------------------------
    # 2. DocumentAttachment FK 索引
    # ---------------------------------------------------------------
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_attachments_document_id
        ON document_attachments (document_id)
    """)

    # ---------------------------------------------------------------
    # 3. pgvector: IVFFlat → HNSW (無需訓練資料，小型資料集更佳)
    # ---------------------------------------------------------------
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if result.scalar() is None:
        import logging
        logging.getLogger("alembic").warning(
            "pgvector 不可用，跳過 HNSW 索引建立"
        )
        return

    # 確認 embedding 欄位存在
    col_check = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'embedding'
    """))
    if col_check.scalar() is None:
        return

    # 移除舊的 IVFFlat 索引，改用 HNSW
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_embedding_hnsw
        ON documents USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """還原索引變更"""
    op.execute("DROP INDEX IF EXISTS ix_documents_contract_project_id")
    op.execute("DROP INDEX IF EXISTS ix_documents_sender_agency_id")
    op.execute("DROP INDEX IF EXISTS ix_documents_receiver_agency_id")
    op.execute("DROP INDEX IF EXISTS ix_document_attachments_document_id")

    # 還原為 IVFFlat
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding_hnsw")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_embedding
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
