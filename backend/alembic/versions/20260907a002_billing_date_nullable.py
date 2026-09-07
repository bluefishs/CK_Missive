"""請款日期可為空 —— 系統自動建立的第一期不該宣稱一個沒有發生的日期

owner 2026-09-07：「系統自動建立的第一期日期也必須先改為空白，避免誤解。」

## 為什麼要動欄位

「成案即應收」自動建的第一期是**佔位**：它存在的理由是「讓夜間吹哨者有東西可催」
（09-03 量到 90 張成案有金額卻無請款，稽催鏈對它們是啞的）。

但它一直被迫填一個日期 —— 先是 `date.today()`（系統建立日），09-07 改成報價單日期。
兩者都有同一個問題：**畫面上它與真的請款日期長得一模一樣**，
於是「這個案請過款了嗎」這個問題，看畫面得到的答案是錯的。

⇒ 沒有請款就沒有請款日期。欄位改為可空，自動建立的那一筆留白。

## 稽催怎麼辦

改用 `COALESCE(billing_date, 報價單日期)` —— 請款日缺就用報價單日期當時間錨點。
稽催不會因此失效，而畫面不再宣稱一個沒有發生的動作。

⚠️ 這個遷移**只放寬約束**，不改任何既有的值（回填由服務層另外做，
且只動「自動建立且未收款」的那些）。降級時若已有 NULL，先補報價單日期再收緊，
避免 downgrade 直接失敗。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260907a002'
down_revision = '20260907a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('erp_billings', 'billing_date',
                    existing_type=sa.Date(), nullable=True,
                    comment='請款日期；系統自動建立的第一期留白（沒有請款就沒有請款日期）')


def downgrade() -> None:
    # 先把 NULL 補成報價單日期（再退回今天），否則收緊約束會直接失敗
    op.execute("""
        UPDATE erp_billings b
           SET billing_date = COALESCE(
                 (SELECT q.quoted_at FROM erp_quotations q WHERE q.id = b.erp_quotation_id),
                 CURRENT_DATE)
         WHERE b.billing_date IS NULL
    """)
    op.alter_column('erp_billings', 'billing_date',
                    existing_type=sa.Date(), nullable=False)
