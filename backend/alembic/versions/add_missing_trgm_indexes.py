"""
補充缺失的 GIN trigram 索引

為 AI 自然語言搜尋的 content 欄位、RLS 權限過濾的 assignee 欄位，
以及機關搜尋的 agency_short_name/agency_code 欄位建立 GIN trigram 索引。

Revision ID: add_missing_trgm
Revises: add_trgm_gin_idx
Create Date: 2026-02-06
"""
from alembic import op

# revision identifiers
revision = 'add_missing_trgm'
down_revision = 'add_trgm_gin_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    建立補充 GIN trigram 索引

    優化場景：
    1. AI 搜尋 with_keyword_full() 中 content 欄位的 ILIKE
    2. RLS 權限過濾 with_assignee_access() 中 assignee 欄位的 ILIKE
    3. 機關搜尋 with_keyword() 中 agency_short_name/agency_code 的 ILIKE
    """
    # 公文內容欄位（AI 自然語言搜尋核心欄位）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_content_trgm
        ON documents USING gin(content gin_trgm_ops)
    """)

    # 公文承辦人欄位（RLS 權限過濾）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_assignee_trgm
        ON documents USING gin(assignee gin_trgm_ops)
    """)

    # 機關簡稱（機關搜尋 QueryBuilder）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agencies_short_name_trgm
        ON government_agencies USING gin(agency_short_name gin_trgm_ops)
    """)

    # 機關代碼（機關搜尋 QueryBuilder）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agencies_code_trgm
        ON government_agencies USING gin(agency_code gin_trgm_ops)
    """)


def downgrade() -> None:
    """移除補充 GIN 索引"""
    op.execute("DROP INDEX IF EXISTS idx_agencies_code_trgm")
    op.execute("DROP INDEX IF EXISTS idx_agencies_short_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_assignee_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_content_trgm")
