"""案件附件加文件類型（區分系統產出與客戶回簽）

Revision ID: 20260819a002
Revises: 20260819a001
Create Date: 2026-08-19

owner 2026-08-19：「產生報價單只是步驟一，其需將客戶回簽檔案上傳確認
才正式完成邀標報價承攬」「客戶回簽上傳的實際素材請規劃匯入對應 pm/cases」。

# 為什麼要這個欄位

`pm_case_attachments` 現在沒有任何分類欄位（只有 `mime_type`），所以

    系統產出的報價單     報價單_QT2026_008.pdf
    客戶回簽的報價單     回簽報價單_B115-C013-0_朱冠綸_….pdf
    其他佐證             隨便什麼檔名

三者在資料上**長得一模一樣**，只能靠檔名猜 —— 而靠檔名比對正是本專案
反覆踩過的那一類：檔名一改，判定就靜靜失效，而且不會有人發現。

「這個案子有沒有客戶回簽」是**成案的判準**，不能建立在猜測上。

# 三個值，以及為什麼 NULL 有意義

    generated_quotation  系統輸出的報價單（archive() 自動標）
    signed_quotation     客戶回簽的報價單
    other                人工判定過、確認是其他佐證
    NULL                 **還沒有人分類過**

`NULL` 與 `other` 刻意分開：「不知道它是什麼」與「它是其他」是兩件事。
既有紀錄一律留 NULL，**不猜**（現有資料只有 2 筆，猜錯的代價雖小，
但「系統替你決定了一個你沒說過的分類」這件事本身就不該發生）。

# 不做 enum

用 String + 應用層 Literal 驗證。這一組值會長（例如日後加「委託合約」
「驗收文件」），而 PostgreSQL 的 enum 加值要 migration；
本專案既有的分類欄位（`erp_quotations.status`、`pm_cases.status`）
也都是 String，一致比較重要。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260819a002'
down_revision = '20260819a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'pm_case_attachments',
        sa.Column('doc_type', sa.String(length=32), nullable=True,
                  comment='文件類型：generated_quotation/signed_quotation/other；'
                          'NULL＝尚未分類（與 other 意思不同）'),
    )
    op.create_index('ix_pm_case_attachments_doc_type', 'pm_case_attachments', ['doc_type'])


def downgrade() -> None:
    op.drop_index('ix_pm_case_attachments_doc_type', table_name='pm_case_attachments')
    op.drop_column('pm_case_attachments', 'doc_type')
