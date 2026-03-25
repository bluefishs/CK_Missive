"""partner_vendors 加 vendor_type/tax_id/notes + pm_cases 加 client_vendor_id FK + 資料遷移

Revision ID: 20260324a004
Revises: 20260324a003
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '20260324a004'
down_revision = '20260324a003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. partner_vendors 新增欄位
    op.add_column('partner_vendors', sa.Column(
        'vendor_type', sa.String(20), server_default='subcontractor', nullable=True,
        comment='類型: subcontractor=協力廠商, client=委託單位'))
    op.create_index('ix_partner_vendors_vendor_type', 'partner_vendors', ['vendor_type'])
    op.add_column('partner_vendors', sa.Column('tax_id', sa.String(20), nullable=True, comment='統一編號'))
    op.add_column('partner_vendors', sa.Column('notes', sa.Text(), nullable=True, comment='備註'))

    # 2. pm_cases 新增 client_vendor_id FK
    op.add_column('pm_cases', sa.Column(
        'client_vendor_id', sa.Integer(),
        sa.ForeignKey('partner_vendors.id', ondelete='SET NULL'),
        nullable=True, comment='委託單位 FK'))
    op.create_index('ix_pm_cases_client_vendor_id', 'pm_cases', ['client_vendor_id'])

    # 3. 既有 partner_vendors 標記為 subcontractor
    op.execute("UPDATE partner_vendors SET vendor_type = 'subcontractor' WHERE vendor_type IS NULL")

    # 4. 將 PM cases 的 client_name 遷移為 partner_vendors (type=client)
    # 跳過 vendor_name 已存在的（不論 type，避免 unique violation）
    op.execute("""
        INSERT INTO partner_vendors (vendor_name, vendor_type)
        SELECT DISTINCT client_name, 'client'
        FROM pm_cases
        WHERE client_name IS NOT NULL
          AND client_name != ''
          AND NOT EXISTS (
            SELECT 1 FROM partner_vendors pv
            WHERE pv.vendor_name = pm_cases.client_name
          )
    """)

    # 5. 回填 pm_cases.client_vendor_id（匹配任何同名 vendor）
    op.execute("""
        UPDATE pm_cases
        SET client_vendor_id = pv.id
        FROM partner_vendors pv
        WHERE pv.vendor_name = pm_cases.client_name
          AND pm_cases.client_vendor_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_pm_cases_client_vendor_id', table_name='pm_cases')
    op.drop_column('pm_cases', 'client_vendor_id')
    op.drop_index('ix_partner_vendors_vendor_type', table_name='partner_vendors')
    op.drop_column('partner_vendors', 'notes')
    op.drop_column('partner_vendors', 'tax_id')
    op.drop_column('partner_vendors', 'vendor_type')
