"""erp_quotations 加 quote_kind —— 同一張表裝了三種東西，先前只靠 case_code 段落分辨

Revision ID: 20260902a001
Revises: 20260830a001
Create Date: 2026-09-02

## 為什麼

owner 09-02 晚問「為何報價單有 01 委辦招標？」——因為 `erp_quotations` 同時是
①01 投標報價（標案建案時開的 draft）②02 承攬報價（人工／XLS 匯入）
③成案時自動建的 0 元金流錨點。三者共用一張表、沒有欄位標明種類，
於是「XLS 只對 02、01 不可誤刪」這條規則只能靠人記住 case_code 的段落規則。

## 為什麼 nullable

存量 258 筆用 `BACKFILL_SQL` 依 case_code 回填（規則單一來源＝
`app/services/erp/quote_kind.py`，測試用已知案號同時打 Python 與 SQL 兩邊）；
認不出類別的（舊制 03 類等）留 NULL＝「未分類」，與任一種類都不同。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260902a001'
down_revision = '20260830a001'
branch_labels = None
depends_on = None

# 與 app/services/erp/quote_kind.py::BACKFILL_SQL 相同 —— 這裡不 import app（migration 不該依賴應用層）
_BACKFILL = """
UPDATE erp_quotations SET quote_kind = CASE
    WHEN notes LIKE '隨承攬案件%自動建立%' THEN 'finance_anchor'
    WHEN case_code ~ '^CK\\d{4}_(PM|GN|FN|DP)_01_' OR case_code ~ '^CK\\d{4}_01_\\d{2}_' THEN 'tender'
    WHEN case_code ~ '^CK\\d{4}_(PM|GN|FN|DP)_02_' OR case_code ~ '^CK\\d{4}_02_\\d{2}_' THEN 'contract'
    ELSE NULL END
WHERE quote_kind IS NULL
"""


def upgrade() -> None:
    op.add_column(
        'erp_quotations',
        sa.Column('quote_kind', sa.String(length=20), nullable=True,
                  comment='tender/contract/finance_anchor'),
    )
    op.create_index('ix_erp_quotations_quote_kind', 'erp_quotations', ['quote_kind'])
    op.execute(_BACKFILL)


def downgrade() -> None:
    op.drop_index('ix_erp_quotations_quote_kind', table_name='erp_quotations')
    op.drop_column('erp_quotations', 'quote_kind')
