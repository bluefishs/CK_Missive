"""新增 taoyuan_dispatch_work_types 正規化關聯表

將派工單的 work_type 逗號分隔字串正規化為獨立 M:N 關聯表。
保留原 work_type 欄位向後相容。

Revision ID: add_dispatch_work_types
Revises: add_batch_fields
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_dispatch_work_types'
down_revision = 'add_batch_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'taoyuan_dispatch_work_types',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dispatch_order_id', sa.Integer(),
                  sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('work_type', sa.String(100), nullable=False, index=True,
                  comment='作業類別名稱 (如：01.地上物查估作業)'),
        sa.Column('sort_order', sa.Integer(), server_default='0',
                  comment='排序順序'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('dispatch_order_id', 'work_type',
                            name='uq_dispatch_work_type'),
    )

    # 遷移既有資料：將 work_type 逗號分隔字串拆分寫入新表
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, work_type FROM taoyuan_dispatch_orders "
            "WHERE work_type IS NOT NULL AND work_type != ''"
        )
    ).fetchall()

    for row in rows:
        dispatch_id = row[0]
        work_type_str = row[1]
        types = [t.strip() for t in work_type_str.split(',') if t.strip()]
        for idx, wt in enumerate(types):
            conn.execute(
                sa.text(
                    "INSERT INTO taoyuan_dispatch_work_types "
                    "(dispatch_order_id, work_type, sort_order) "
                    "VALUES (:did, :wt, :so) "
                    "ON CONFLICT (dispatch_order_id, work_type) DO NOTHING"
                ),
                {"did": dispatch_id, "wt": wt, "so": idx},
            )


def downgrade():
    op.drop_table('taoyuan_dispatch_work_types')
