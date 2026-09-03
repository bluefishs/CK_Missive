"""erp_invoices 加 source —— 發票是誰建的，此前靠 notes 前綴分辨

Revision ID: 20260903a001
Revises: 20260902a001
Create Date: 2026-09-03

## 為什麼

09-03 全景覆盤 C／A87：170 張發票裡 121 張由總表匯入、47 張系統自動補建、1 張手動，
對帳時只能 `notes LIKE '由 115報價單彙整總表%'`。來源是個欄位不是一段字。

值域：manual／xls_import／auto_from_billing。回填依 notes 前綴；認不出的留 manual。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260903a001'
down_revision = '20260902a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('erp_invoices', sa.Column('source', sa.String(length=24), nullable=True, comment='manual/xls_import/auto_from_billing'))
    op.execute("""
        UPDATE erp_invoices SET source = CASE
            WHEN notes LIKE '由 115報價單彙整總表%' OR notes LIKE '由報價單彙整匯入%' THEN 'xls_import'
            WHEN notes LIKE '系統自動補建%' THEN 'auto_from_billing'
            ELSE 'manual' END
        WHERE source IS NULL
    """)


def downgrade() -> None:
    op.drop_column('erp_invoices', 'source')
