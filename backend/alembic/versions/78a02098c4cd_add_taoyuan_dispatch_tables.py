"""add_taoyuan_dispatch_tables

Revision ID: 78a02098c4cd
Revises: 5c2da4a2d8aa
Create Date: 2026-01-19 16:09:23.254166

桃園查估派工管理系統資料表
- 擴充 project_agency_contacts (專案通訊錄)
- taoyuan_projects (轄管工程清單)
- taoyuan_dispatch_orders (派工紀錄)
- taoyuan_dispatch_project_link (派工-工程關聯)
- taoyuan_dispatch_document_link (派工-公文關聯)
- taoyuan_contract_payments (契金管控)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78a02098c4cd'
down_revision: Union[str, Sequence[str], None] = '5c2da4a2d8aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ============================================================
    # 1. 擴充 project_agency_contacts (專案通訊錄)
    # ============================================================
    op.add_column('project_agency_contacts',
        sa.Column('line_name', sa.String(100), nullable=True, comment='LINE名稱'))
    op.add_column('project_agency_contacts',
        sa.Column('org_short_name', sa.String(100), nullable=True, comment='單位簡稱'))
    op.add_column('project_agency_contacts',
        sa.Column('category', sa.String(50), nullable=True, comment='類別(機關/乾坤/廠商)'))
    op.add_column('project_agency_contacts',
        sa.Column('cloud_path', sa.String(500), nullable=True, comment='專案雲端路徑'))
    op.add_column('project_agency_contacts',
        sa.Column('related_project_name', sa.String(500), nullable=True, comment='對應工程名稱'))

    # ============================================================
    # 2. 建立 taoyuan_projects (轄管工程清單)
    # ============================================================
    op.create_table(
        'taoyuan_projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contract_project_id', sa.Integer(), sa.ForeignKey('contract_projects.id'), nullable=True, comment='關聯承攬案件'),

        # 縣府原始資料
        sa.Column('sequence_no', sa.Integer(), nullable=True, comment='項次'),
        sa.Column('review_year', sa.Integer(), nullable=True, comment='審議年度'),
        sa.Column('case_type', sa.String(50), nullable=True, comment='案件類型'),
        sa.Column('district', sa.String(50), nullable=True, comment='行政區'),
        sa.Column('project_name', sa.String(500), nullable=False, comment='工程名稱'),
        sa.Column('start_point', sa.String(200), nullable=True, comment='工程起點'),
        sa.Column('end_point', sa.String(200), nullable=True, comment='工程迄點'),
        sa.Column('road_length', sa.Numeric(10, 2), nullable=True, comment='道路長度(公尺)'),
        sa.Column('current_width', sa.Numeric(10, 2), nullable=True, comment='現況路寬'),
        sa.Column('planned_width', sa.Numeric(10, 2), nullable=True, comment='計畫路寬'),
        sa.Column('public_land_count', sa.Integer(), nullable=True, comment='公有土地筆數'),
        sa.Column('private_land_count', sa.Integer(), nullable=True, comment='私有土地筆數'),
        sa.Column('rc_count', sa.Integer(), nullable=True, comment='RC數量'),
        sa.Column('iron_sheet_count', sa.Integer(), nullable=True, comment='鐵皮屋數量'),
        sa.Column('construction_cost', sa.Numeric(15, 2), nullable=True, comment='工程費'),
        sa.Column('land_cost', sa.Numeric(15, 2), nullable=True, comment='用地費'),
        sa.Column('compensation_cost', sa.Numeric(15, 2), nullable=True, comment='補償費'),
        sa.Column('total_cost', sa.Numeric(15, 2), nullable=True, comment='總經費'),
        sa.Column('review_result', sa.String(100), nullable=True, comment='審議結果'),
        sa.Column('urban_plan', sa.String(200), nullable=True, comment='都市計畫'),
        sa.Column('completion_date', sa.Date(), nullable=True, comment='完工日期'),
        sa.Column('proposer', sa.String(100), nullable=True, comment='提案人'),
        sa.Column('remark', sa.Text(), nullable=True, comment='備註'),

        # 派工關聯欄位
        sa.Column('sub_case_name', sa.String(200), nullable=True, comment='分案名稱'),
        sa.Column('case_handler', sa.String(50), nullable=True, comment='案件承辦'),
        sa.Column('survey_unit', sa.String(100), nullable=True, comment='查估單位'),

        # 總控表進度欄位
        sa.Column('land_agreement_status', sa.String(100), nullable=True, comment='土地協議進度'),
        sa.Column('land_expropriation_status', sa.String(100), nullable=True, comment='土地徵收進度'),
        sa.Column('building_survey_status', sa.String(100), nullable=True, comment='地上物查估進度'),
        sa.Column('actual_entry_date', sa.Date(), nullable=True, comment='實際進場日期'),
        sa.Column('acceptance_status', sa.String(100), nullable=True, comment='驗收狀態'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('idx_taoyuan_projects_contract', 'taoyuan_projects', ['contract_project_id'])
    op.create_index('idx_taoyuan_projects_district', 'taoyuan_projects', ['district'])
    op.create_index('idx_taoyuan_projects_name', 'taoyuan_projects', ['project_name'])
    op.create_index('idx_taoyuan_projects_year', 'taoyuan_projects', ['review_year'])

    # ============================================================
    # 3. 建立 taoyuan_dispatch_orders (派工紀錄)
    # ============================================================
    op.create_table(
        'taoyuan_dispatch_orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contract_project_id', sa.Integer(), sa.ForeignKey('contract_projects.id'), nullable=True, comment='關聯承攬案件'),

        sa.Column('dispatch_no', sa.String(50), unique=True, nullable=False, comment='派工單號'),
        sa.Column('agency_doc_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True, comment='關聯機關公文'),
        sa.Column('company_doc_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True, comment='關聯乾坤公文'),

        sa.Column('project_name', sa.String(500), nullable=True, comment='工程名稱/派工事項'),
        sa.Column('work_type', sa.String(50), nullable=True, comment='作業類別'),
        sa.Column('sub_case_name', sa.String(200), nullable=True, comment='分案名稱/派工備註'),
        sa.Column('deadline', sa.String(200), nullable=True, comment='履約期限'),
        sa.Column('case_handler', sa.String(50), nullable=True, comment='案件承辦'),
        sa.Column('survey_unit', sa.String(100), nullable=True, comment='查估單位'),
        sa.Column('cloud_folder', sa.String(500), nullable=True, comment='雲端資料夾'),
        sa.Column('project_folder', sa.String(500), nullable=True, comment='專案資料夾'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('idx_dispatch_contract', 'taoyuan_dispatch_orders', ['contract_project_id'])
    op.create_index('idx_dispatch_work_type', 'taoyuan_dispatch_orders', ['work_type'])
    op.create_index('idx_dispatch_no', 'taoyuan_dispatch_orders', ['dispatch_no'])

    # ============================================================
    # 4. 建立 taoyuan_dispatch_project_link (派工-工程關聯)
    # ============================================================
    op.create_table(
        'taoyuan_dispatch_project_link',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dispatch_order_id', sa.Integer(), sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('taoyuan_project_id', sa.Integer(), sa.ForeignKey('taoyuan_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('dispatch_order_id', 'taoyuan_project_id', name='uq_dispatch_project')
    )

    op.create_index('idx_dispatch_project_dispatch', 'taoyuan_dispatch_project_link', ['dispatch_order_id'])
    op.create_index('idx_dispatch_project_project', 'taoyuan_dispatch_project_link', ['taoyuan_project_id'])

    # ============================================================
    # 5. 建立 taoyuan_dispatch_document_link (派工-公文關聯)
    # ============================================================
    op.create_table(
        'taoyuan_dispatch_document_link',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dispatch_order_id', sa.Integer(), sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('link_type', sa.String(20), nullable=False, comment='agency_incoming/company_outgoing'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('dispatch_order_id', 'document_id', name='uq_dispatch_document')
    )

    op.create_index('idx_dispatch_doc_dispatch', 'taoyuan_dispatch_document_link', ['dispatch_order_id'])
    op.create_index('idx_dispatch_doc_document', 'taoyuan_dispatch_document_link', ['document_id'])
    op.create_index('idx_dispatch_doc_type', 'taoyuan_dispatch_document_link', ['link_type'])

    # ============================================================
    # 6. 建立 taoyuan_contract_payments (契金管控)
    # ============================================================
    op.create_table(
        'taoyuan_contract_payments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dispatch_order_id', sa.Integer(), sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False),

        # 7種作業類別的派工日期/金額
        sa.Column('work_01_date', sa.Date(), nullable=True, comment='01.地上物查估-派工日期'),
        sa.Column('work_01_amount', sa.Numeric(15, 2), nullable=True, comment='01.地上物查估-派工金額'),
        sa.Column('work_02_date', sa.Date(), nullable=True, comment='02.土地協議市價查估-派工日期'),
        sa.Column('work_02_amount', sa.Numeric(15, 2), nullable=True, comment='02.土地協議市價查估-派工金額'),
        sa.Column('work_03_date', sa.Date(), nullable=True, comment='03.土地徵收市價查估-派工日期'),
        sa.Column('work_03_amount', sa.Numeric(15, 2), nullable=True, comment='03.土地徵收市價查估-派工金額'),
        sa.Column('work_04_date', sa.Date(), nullable=True, comment='04.相關計畫書製作-派工日期'),
        sa.Column('work_04_amount', sa.Numeric(15, 2), nullable=True, comment='04.相關計畫書製作-派工金額'),
        sa.Column('work_05_date', sa.Date(), nullable=True, comment='05.測量作業-派工日期'),
        sa.Column('work_05_amount', sa.Numeric(15, 2), nullable=True, comment='05.測量作業-派工金額'),
        sa.Column('work_06_date', sa.Date(), nullable=True, comment='06.樁位測釘作業-派工日期'),
        sa.Column('work_06_amount', sa.Numeric(15, 2), nullable=True, comment='06.樁位測釘作業-派工金額'),
        sa.Column('work_07_date', sa.Date(), nullable=True, comment='07.辦理教育訓練-派工日期'),
        sa.Column('work_07_amount', sa.Numeric(15, 2), nullable=True, comment='07.辦理教育訓練-派工金額'),

        # 彙總欄位
        sa.Column('current_amount', sa.Numeric(15, 2), nullable=True, comment='本次派工金額'),
        sa.Column('cumulative_amount', sa.Numeric(15, 2), nullable=True, comment='累進派工金額'),
        sa.Column('remaining_amount', sa.Numeric(15, 2), nullable=True, comment='剩餘金額'),
        sa.Column('acceptance_date', sa.Date(), nullable=True, comment='完成驗收日期'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('idx_payment_dispatch', 'taoyuan_contract_payments', ['dispatch_order_id'])


def downgrade() -> None:
    """Downgrade schema."""

    # 刪除契金管控
    op.drop_index('idx_payment_dispatch', 'taoyuan_contract_payments')
    op.drop_table('taoyuan_contract_payments')

    # 刪除派工-公文關聯
    op.drop_index('idx_dispatch_doc_type', 'taoyuan_dispatch_document_link')
    op.drop_index('idx_dispatch_doc_document', 'taoyuan_dispatch_document_link')
    op.drop_index('idx_dispatch_doc_dispatch', 'taoyuan_dispatch_document_link')
    op.drop_table('taoyuan_dispatch_document_link')

    # 刪除派工-工程關聯
    op.drop_index('idx_dispatch_project_project', 'taoyuan_dispatch_project_link')
    op.drop_index('idx_dispatch_project_dispatch', 'taoyuan_dispatch_project_link')
    op.drop_table('taoyuan_dispatch_project_link')

    # 刪除派工紀錄
    op.drop_index('idx_dispatch_no', 'taoyuan_dispatch_orders')
    op.drop_index('idx_dispatch_work_type', 'taoyuan_dispatch_orders')
    op.drop_index('idx_dispatch_contract', 'taoyuan_dispatch_orders')
    op.drop_table('taoyuan_dispatch_orders')

    # 刪除轄管工程清單
    op.drop_index('idx_taoyuan_projects_year', 'taoyuan_projects')
    op.drop_index('idx_taoyuan_projects_name', 'taoyuan_projects')
    op.drop_index('idx_taoyuan_projects_district', 'taoyuan_projects')
    op.drop_index('idx_taoyuan_projects_contract', 'taoyuan_projects')
    op.drop_table('taoyuan_projects')

    # 移除 project_agency_contacts 擴充欄位
    op.drop_column('project_agency_contacts', 'related_project_name')
    op.drop_column('project_agency_contacts', 'cloud_path')
    op.drop_column('project_agency_contacts', 'category')
    op.drop_column('project_agency_contacts', 'org_short_name')
    op.drop_column('project_agency_contacts', 'line_name')
