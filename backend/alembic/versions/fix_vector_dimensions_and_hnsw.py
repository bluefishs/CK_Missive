"""修正向量維度 384→768 + 補充 HNSW 索引

1. canonical_entities.embedding: vector(384) → vector(768) 匹配 nomic-embed-text 實際輸出
2. ai_search_history.query_embedding: 補建 HNSW 索引
3. canonical_entities.embedding: 新建 HNSW 索引

注意: documents.embedding 和 ai_search_history.query_embedding 的 DB 欄位
      已經是 vector(768)（先前手動遷移），本次只修正 canonical_entities。

Revision ID: fix_vector_dims_hnsw
Revises: add_perf_critical_indexes
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_vector_dims_hnsw'
down_revision = 'add_perf_critical_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """修正 canonical_entities 向量維度 + 建 HNSW 索引"""

    conn = op.get_bind()

    # 檢查 pgvector 是否可用
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if result.scalar() is None:
        import logging
        logging.getLogger("alembic").warning(
            "pgvector 不可用，跳過向量維度修正"
        )
        return

    # ---------------------------------------------------------------
    # 1. canonical_entities.embedding: vector(384) → vector(768)
    # ---------------------------------------------------------------
    col_check = conn.execute(sa.text("""
        SELECT format_type(a.atttypid, a.atttypmod) as type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        WHERE c.relname = 'canonical_entities' AND a.attname = 'embedding'
    """))
    row = col_check.first()
    if row and 'vector(384)' in str(row[0]):
        op.execute("""
            ALTER TABLE canonical_entities
            ALTER COLUMN embedding TYPE vector(768)
        """)

    # ---------------------------------------------------------------
    # 2. canonical_entities: 建 HNSW 索引
    # ---------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS ix_canonical_entities_embedding")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_canonical_entities_embedding_hnsw
        ON canonical_entities USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ---------------------------------------------------------------
    # 3. ai_search_history: 升級為 HNSW 索引
    # ---------------------------------------------------------------
    search_col = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_search_history' AND column_name = 'query_embedding'
    """))
    if search_col.scalar():
        op.execute("DROP INDEX IF EXISTS ix_search_history_query_embedding")
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_search_history_query_embedding_hnsw
            ON ai_search_history USING hnsw (query_embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)


def downgrade() -> None:
    """還原向量維度和索引"""

    # canonical_entities 還原為 384
    op.execute("""
        ALTER TABLE canonical_entities
        ALTER COLUMN embedding TYPE vector(384)
    """)

    # 還原索引為 IVFFlat
    op.execute("DROP INDEX IF EXISTS ix_canonical_entities_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_search_history_query_embedding_hnsw")

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_search_history_query_embedding
        ON ai_search_history USING ivfflat (query_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
