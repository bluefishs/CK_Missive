"""新增 dispatch_order_id 唯一約束到 taoyuan_contract_payments 表

防止同一派工單重複建立契金記錄（upsert 競態條件防護）。

Revision ID: add_payment_dispatch_uq
Revises: add_query_embedding_history
Create Date: 2026-02-11
"""
from alembic import op


# revision identifiers
revision = 'add_payment_dispatch_uq'
down_revision = 'add_query_embedding_history'
branch_labels = None
depends_on = None


def upgrade():
    # 先清理可能存在的重複記錄（保留最新的）
    op.execute("""
        DELETE FROM taoyuan_contract_payments
        WHERE id NOT IN (
            SELECT MAX(id) FROM taoyuan_contract_payments
            GROUP BY dispatch_order_id
        )
    """)
    op.create_unique_constraint(
        'uq_payment_dispatch_order',
        'taoyuan_contract_payments',
        ['dispatch_order_id']
    )


def downgrade():
    op.drop_constraint('uq_payment_dispatch_order', 'taoyuan_contract_payments', type_='unique')
