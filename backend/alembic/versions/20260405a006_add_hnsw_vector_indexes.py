"""add HNSW vector indexes on documents and document_chunks

為 documents.embedding 和 document_chunks.embedding 建立 HNSW 索引，
取代預設的順序掃描，大幅提升向量檢索效能（768D cosine）。

Revision ID: 20260405a006
Revises: 20260405a005
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = '20260405a006'
down_revision = '20260405a005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """建立 HNSW 向量索引 (documents + document_chunks)"""

    conn = op.get_bind()

    # 檢查 pgvector 是否可用
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if result.scalar() is None:
        import logging
        logging.getLogger("alembic").warning(
            "pgvector 不可用，跳過 HNSW 索引建立"
        )
        return

    # ---------------------------------------------------------------
    # 1. documents.embedding: HNSW 索引 (768D, cosine)
    # ---------------------------------------------------------------
    doc_col = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'embedding'
    """))
    if doc_col.scalar():
        # 先移除舊的 IVFFlat / btree 索引（如有）
        op.execute("DROP INDEX IF EXISTS ix_documents_embedding")
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_documents_embedding_hnsw
            ON documents
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

    # ---------------------------------------------------------------
    # 2. document_chunks.embedding: HNSW 索引 (768D, cosine)
    # ---------------------------------------------------------------
    chunk_col = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'embedding'
    """))
    if chunk_col.scalar():
        op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
            ON document_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)


def downgrade() -> None:
    """移除 HNSW 索引"""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding_hnsw")
