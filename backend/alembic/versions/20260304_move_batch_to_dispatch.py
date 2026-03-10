"""feat: move batch_no/batch_label from work_records to dispatch_orders

結案批次概念屬於派工單層級，從 work_records 遷移至 dispatch_orders。
work_records 欄位保留（向後相容），不再前端讀寫。

Revision ID: 20260304a001
Revises: 20260303a001
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260304a001'
down_revision = '20260303a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增欄位至 dispatch_orders
    op.add_column('taoyuan_dispatch_orders',
        sa.Column('batch_no', sa.Integer(), nullable=True,
                  comment='批次序號 (第幾批結案，如 1,2,3...)'))
    op.add_column('taoyuan_dispatch_orders',
        sa.Column('batch_label', sa.String(50), nullable=True,
                  comment='批次標籤 (如：第1批結案、補充結案)'))
    op.create_index('ix_taoyuan_dispatch_orders_batch_no',
                    'taoyuan_dispatch_orders', ['batch_no'])

    # 2. 資料遷移：將每個 dispatch 下 work_records 的最高 batch_no 複製過來
    op.execute("""
        UPDATE taoyuan_dispatch_orders d
        SET batch_no = sub.max_batch_no,
            batch_label = sub.batch_label
        FROM (
            SELECT
                wr.dispatch_order_id,
                wr.batch_no AS max_batch_no,
                wr.batch_label
            FROM taoyuan_work_records wr
            INNER JOIN (
                SELECT dispatch_order_id, MAX(batch_no) AS max_batch_no
                FROM taoyuan_work_records
                WHERE batch_no IS NOT NULL
                GROUP BY dispatch_order_id
            ) agg ON wr.dispatch_order_id = agg.dispatch_order_id
                  AND wr.batch_no = agg.max_batch_no
        ) sub
        WHERE d.id = sub.dispatch_order_id
    """)


def downgrade() -> None:
    op.drop_index('ix_taoyuan_dispatch_orders_batch_no',
                  table_name='taoyuan_dispatch_orders')
    op.drop_column('taoyuan_dispatch_orders', 'batch_label')
    op.drop_column('taoyuan_dispatch_orders', 'batch_no')
