"""contract_projects 加 client_vendor_id —— 承攬案的委託單位終於有「鍵」

Revision ID: 20260904a003
Revises: 20260904a002
Create Date: 2026-09-04

owner 2026-09-04 /loop：「由資料庫表單對應名稱標準化與語意定義釐清，避免對應錯誤或無法關聯」。

實測承攬案的委託單位有三個欄位、沒有一個是 partner_vendors 的鍵：
  - client_agency      文字（285 筆都有）
  - client_agency_id   → government_agencies（34/285 有值；01 公部門案用）
  - client_type        agency 284／vendor 1
而 PM 案存的是 client_vendor_id（partner_vendors）。兩邊「不是同一個 id 空間」，
所以委託單位帳款、報價單的委託單位篩選、客戶主檔對承攬案，全部只能靠**名稱字串**對——
一天內因此出了三次事（竹崎地政無法點／張啟良三筆主檔／大有國際在主檔是 subcontractor）。

本 migration：加 client_vendor_id（FK partner_vendors，SET NULL），並回填：
  ① 同 case_code 的 PM 案有 client_vendor_id ⇒ 直接抄（244 筆）
  ② 否則 client_agency 去空白後與 partner_vendors.vendor_name 精確相等 ⇒ 對上（27 筆；client 型優先）
  ③ 對不到的留 NULL（實測 14 筆，全是 client_agency 空白）
名稱欄位保留＝顯示快照；鍵是 id。規則入 FIELD_SEMANTICS「主檔鍵與名稱快照」。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260904a003'
down_revision = '20260904a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('contract_projects', sa.Column(
        'client_vendor_id', sa.Integer(),
        sa.ForeignKey('partner_vendors.id', ondelete='SET NULL'),
        nullable=True, comment='委託單位（partner_vendors 的鍵；client_agency 只是名稱快照）',
    ))
    op.create_index('ix_contract_projects_client_vendor_id', 'contract_projects', ['client_vendor_id'])
    # ① 抄 PM 案
    op.execute("""
        UPDATE contract_projects c SET client_vendor_id = p.client_vendor_id
        FROM pm_cases p
        WHERE p.case_code = c.case_code AND p.client_vendor_id IS NOT NULL AND c.client_vendor_id IS NULL
    """)
    # ② 精確名稱（client 型優先，其次任何型；同名多筆取 id 最小）
    op.execute("""
        UPDATE contract_projects c SET client_vendor_id = v.id
        FROM (
            SELECT DISTINCT ON (btrim(vendor_name)) btrim(vendor_name) AS name, id
            FROM partner_vendors
            ORDER BY btrim(vendor_name), (vendor_type = 'client') DESC, id
        ) v
        WHERE c.client_vendor_id IS NULL AND c.client_agency IS NOT NULL AND btrim(c.client_agency) = v.name
    """)


def downgrade() -> None:
    op.drop_index('ix_contract_projects_client_vendor_id', table_name='contract_projects')
    op.drop_column('contract_projects', 'client_vendor_id')
