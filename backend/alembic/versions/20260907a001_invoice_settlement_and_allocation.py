"""發票結算方式與一票多案分攤 —— 讓「不開發票（互抵）」與「同一張發票對應多案」說得出來

owner 2026-09-07：「由報價單總表備註發現，類似同一發票對應多案件、或不開發票（互抵）
幾種情境應如何處理」。

實際資料（2026-09-07 查證）：

* `XLS-B114-C030-1`（18,000 已收）、`XLS-B114-C031-1`（25,500 已收）——匯入時保留的
  發票欄原文是「**不開發票**」。系統目前把它們當一般請款，於是 weekly 104 ⑪
  「已收款但沒有登錄發票」永遠報這兩筆 —— **那不是缺漏，是這筆本來就不開票**。
  永遠是紅的訊號與沒有訊號是同一個下場。
* `XLS-B115-C020-0` 的原文是「115.03.12(尚有餘款未開發票」——**部分開票**。
* 一票多案：`erp_invoices` 只有單一 `erp_quotation_id` 與單一 `billing_id`，
  一張發票跨兩個案子**表達不出來**，於是人只能挑一個案掛上去，另一個案在帳上就看不到那筆收入。

本遷移只加「表達能力」，不動任何既有資料：

1. `erp_billings.settlement_type`：`invoice`（預設，要開票）／`offset`（互抵）／
   `no_invoice`（約定不開票）。既有列一律 `invoice`，行為不變。
2. `erp_billings.settlement_note`：互抵對象與依據（互抵的另一半是哪一筆應付／哪一個案）。
3. `erp_invoice_allocations`：一張發票分攤到多個案／多期請款；
   **有分攤時以分攤為準，沒有分攤時沿用發票本身的 `erp_quotation_id`**（相容既有 155 張）。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260907a001'
down_revision = '20260904a003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('erp_billings', sa.Column(
        'settlement_type', sa.String(20), nullable=False, server_default='invoice',
        comment="結算方式: invoice=開立發票 / offset=互抵 / no_invoice=約定不開票",
    ))
    op.add_column('erp_billings', sa.Column(
        'settlement_note', sa.String(300), nullable=True,
        comment="互抵／不開票的依據與對象（例如：與應付 #51 互抵）",
    ))
    op.create_index('ix_erp_billings_settlement_type', 'erp_billings', ['settlement_type'])

    op.create_table(
        'erp_invoice_allocations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(),
                  sa.ForeignKey('erp_invoices.id', ondelete='CASCADE'), nullable=False,
                  comment='發票'),
        sa.Column('erp_quotation_id', sa.Integer(),
                  sa.ForeignKey('erp_quotations.id', ondelete='CASCADE'), nullable=False,
                  comment='分攤到哪一個案（報價單）'),
        sa.Column('billing_id', sa.Integer(),
                  sa.ForeignKey('erp_billings.id', ondelete='SET NULL'), nullable=True,
                  comment='分攤到哪一期請款（可空）'),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False, comment='該案分攤金額（含稅）'),
        sa.Column('tax_amount', sa.Numeric(15, 2), nullable=True, comment='該案分攤稅額'),
        sa.Column('notes', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_erp_invoice_allocations_invoice', 'erp_invoice_allocations', ['invoice_id'])
    op.create_index('ix_erp_invoice_allocations_quotation', 'erp_invoice_allocations', ['erp_quotation_id'])
    # 同一張發票對同一個案只能有一列（要改金額就改那一列，不要疊加）
    op.create_unique_constraint(
        'uq_invoice_allocation_invoice_quotation',
        'erp_invoice_allocations', ['invoice_id', 'erp_quotation_id'],
    )

    # 把匯入時保留的「不開發票」原文轉成狀態 —— 那是資料本來就有的事實，
    # 只是先前沒有欄位可以放，於是只能留在備註裡而稽核看不懂。
    op.execute("""
        UPDATE erp_billings
           SET settlement_type = 'no_invoice',
               settlement_note = COALESCE(settlement_note, '') ||
                   '2026-09-07：由匯入備註「發票欄原文：不開發票」轉為狀態'
         WHERE notes ILIKE '%發票欄原文：不開發票%'
    """)


def downgrade() -> None:
    op.drop_constraint('uq_invoice_allocation_invoice_quotation', 'erp_invoice_allocations', type_='unique')
    op.drop_index('ix_erp_invoice_allocations_quotation', table_name='erp_invoice_allocations')
    op.drop_index('ix_erp_invoice_allocations_invoice', table_name='erp_invoice_allocations')
    op.drop_table('erp_invoice_allocations')
    op.drop_index('ix_erp_billings_settlement_type', table_name='erp_billings')
    op.drop_column('erp_billings', 'settlement_note')
    op.drop_column('erp_billings', 'settlement_type')
