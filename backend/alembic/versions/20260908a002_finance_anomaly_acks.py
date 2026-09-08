"""案件金流異常的「判讀」紀錄（owner 2026-09-08）

> 「5 筆的『已收 17,850』已付清、發票多開 —— 是否異常案件標註機制並增列篩選查詢，
>  以利解除或處理異常費用之案件機制」

## 為什麼是一張獨立的表，而不是報價單上的一個 boolean

異常本身是**推導**的（見 `app/services/erp/finance_anomaly.py`）：
發票額 > 請款額這件事，問一次數字就知道。把它存成旗標，那一刻起
就有了第二份宣告 —— 發票補開了、請款追加了，旗標不會跟著動，
於是列表說異常而數字已經正常（或反過來，更糟）。
本 repo 反覆出事的形狀就是這個（L145 家族）。

⇒ 這張表存的**不是異常**，是「有人看過了，原因是 X」。
   異常照樣被算出來、照樣顯示；判讀只讓它從「待處理」移到「已判讀」。
   **解除的是待辦，不是事實。**

唯一鍵是 `(quotation_id, anomaly_type)`：同一張報價單可能同時有兩種異常
（例如發票多開又請款超過合約），兩者要分開判讀 —— 混成一筆的話，
判讀了 A 就等於連 B 一起消音。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260908a002'
down_revision = '20260908a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erp_finance_anomaly_acks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_id", sa.Integer(), nullable=False,
                  comment="報價單 id（異常以報價單為單位，因為請款・發票・應付都掛在它上面）"),
        sa.Column("anomaly_type", sa.String(length=50), nullable=False,
                  comment="判準代碼，見 finance_anomaly.ANOMALY_TYPES"),
        sa.Column("reason", sa.Text(), nullable=False,
                  comment="判讀原因 —— 必填。沒有原因的判讀等於把問題藏起來"),
        sa.Column("acked_by", sa.String(length=100), nullable=True, comment="判讀人"),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("quotation_id", "anomaly_type",
                            name="uq_finance_anomaly_ack"),
    )
    op.create_index("ix_finance_anomaly_ack_quotation",
                    "erp_finance_anomaly_acks", ["quotation_id"])


def downgrade() -> None:
    op.drop_index("ix_finance_anomaly_ack_quotation",
                  table_name="erp_finance_anomaly_acks")
    op.drop_table("erp_finance_anomaly_acks")
