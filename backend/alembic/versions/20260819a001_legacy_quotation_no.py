"""報價單保留舊案號（個人管理時期的編號）

Revision ID: 20260819a001
Revises: 20260818a002
Create Date: 2026-08-19

owner 2026-08-19：「新統整匯入與比對更新，對之前提及個人管理導致公司無法統整，
故舊有資料仍有保留『案號如 B114-B002』，而成案編號 CK2026_01_01_007
為系統統一碼機制」。

# 為什麼需要這個欄位

兩套編號並存，而且**兩套都要留**：

    B114-B002        個人管理時期的報價單號（Excel 彙整、回簽 PDF 檔名都用它）
    QT2026_022       系統報價單號
    CK2026_PM_01_007 系統案號
    CK2026_01_01_007 成案編號

舊案號不是要被取代的東西 —— 它是**與紙本、雲端硬碟檔名、客戶往來信件
對得起來的唯一線索**。回簽 PDF 的檔名就長這樣：
`回簽報價單_B115-C013-0_朱冠綸_太平區洪厝段360地號_建物標示圖.pdf`，
沒有這個欄位就無法把那批檔案掛回系統。

掃過全庫，**沒有任何現成欄位可以放它**（`external_id` 屬 KG、
`original_name` 屬附件檔名），所以新增而不是借用。

# 命名

`legacy_quotation_no` —— 講清楚它是「舊的報價單編號」。

**不叫 `old_code`／`external_no`**：前者沒說是什麼的舊編號，
後者會與 KG 的 `external_id`（外部系統實體）混淆。

# 為什麼放在 erp_quotations 而不是 pm_cases

Excel 彙整的每一列就是**一張報價單**（有報價日期、報價金額、是否成立），
不是一個案件。一個案件可能有多次報價（`B115-C017a/b/c` 就是同一位客戶的
三個標的），掛在 pm_cases 上會需要一對多而失真。

# 唯一性

加**部分唯一索引**（只約束非 NULL）：同一個舊案號不該匯入兩次。
既有 77 筆全部是 NULL，不受影響。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260819a001'
down_revision = '20260818a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'erp_quotations',
        sa.Column('legacy_quotation_no', sa.String(length=64), nullable=True,
                  comment='個人管理時期的報價單編號（如 B114-B002），供與紙本／回簽檔對帳'),
    )
    # 部分唯一：只約束有值的，避免既有 NULL 互相衝突
    op.execute(
        "CREATE UNIQUE INDEX ix_erp_quotations_legacy_no "
        "ON erp_quotations (legacy_quotation_no) "
        "WHERE legacy_quotation_no IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_erp_quotations_legacy_no")
    op.drop_column('erp_quotations', 'legacy_quotation_no')
