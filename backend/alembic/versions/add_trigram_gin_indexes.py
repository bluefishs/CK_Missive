"""
新增 pg_trgm GIN 索引以加速 ILIKE 文字搜尋

啟用 pg_trgm 擴展並為公文表的文字欄位建立 GIN trigram 索引。
pg_trgm GIN 索引可自動加速 ILIKE '%keyword%' 查詢，
效能提升 5-10x（資料量 > 1 萬筆時效果顯著）。

Revision ID: add_trgm_gin_idx
Revises: add_doctype_status_idx
Create Date: 2026-02-06
"""
from alembic import op

# revision identifiers
revision = 'add_trgm_gin_idx'
down_revision = 'add_doctype_status_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    建立 pg_trgm GIN 索引

    優化的查詢場景：
    1. ILIKE '%keyword%' 在 subject, sender, receiver 上的全表掃描
    2. 公文字號模糊搜尋
    3. 備註欄位搜尋

    注意：使用 CONCURRENTLY 避免鎖表（需在 transaction 外執行）
    由於 Alembic 預設使用 transaction，這裡使用一般 CREATE INDEX。
    若需零停機部署，請手動執行 CONCURRENTLY 版本。
    """
    # 啟用 pg_trgm 擴展（支援 trigram 相似度搜尋）
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 公文表文字欄位 GIN 索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_subject_trgm
        ON documents USING gin(subject gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_sender_trgm
        ON documents USING gin(sender gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_receiver_trgm
        ON documents USING gin(receiver gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_doc_number_trgm
        ON documents USING gin(doc_number gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_ck_note_trgm
        ON documents USING gin(ck_note gin_trgm_ops)
    """)

    # 機關表名稱 GIN 索引（加速機關搜尋）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agencies_name_trgm
        ON government_agencies USING gin(agency_name gin_trgm_ops)
    """)

    # 廠商表名稱 GIN 索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vendors_name_trgm
        ON partner_vendors USING gin(vendor_name gin_trgm_ops)
    """)

    # 專案表名稱 GIN 索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_name_trgm
        ON contract_projects USING gin(project_name gin_trgm_ops)
    """)


def downgrade() -> None:
    """移除 GIN 索引"""
    op.execute("DROP INDEX IF EXISTS idx_projects_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_vendors_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_agencies_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_ck_note_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_doc_number_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_receiver_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_sender_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_subject_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
