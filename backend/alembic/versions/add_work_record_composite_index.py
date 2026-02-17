"""新增作業紀錄複合索引 (dispatch_order_id, sort_order, record_date)

優化列表查詢效能，覆蓋主要的排序與篩選路徑。

Revision ID: add_work_record_idx
Revises: add_chain_fields
Create Date: 2026-02-17
"""
from alembic import op

# revision identifiers
revision = 'add_work_record_idx'
down_revision = 'add_chain_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'ix_work_records_dispatch_sort_date',
        'taoyuan_work_records',
        ['dispatch_order_id', 'sort_order', 'record_date'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_work_records_dispatch_sort_date',
        table_name='taoyuan_work_records',
    )
