"""create document_chunks table

Revision ID: 20260315a002
Revises: 20260316a001
Create Date: 2026-03-15

文件分段 Embedding — 段落級向量搜尋提升 RAG 長文件召回精度
"""
from alembic import op
import sqlalchemy as sa

revision = "20260315a002"
down_revision = "20260316a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        comment="文件分段 Embedding 表",
    )

    op.create_index("ix_doc_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_doc_chunks_doc_idx", "document_chunks", ["document_id", "chunk_index"])

    # pgvector embedding column (conditionally add)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE document_chunks ADD COLUMN embedding vector(768);
                CREATE INDEX ix_doc_chunks_embedding
                    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("document_chunks")
