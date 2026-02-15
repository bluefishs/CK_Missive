"""新增 taoyuan_work_records 作業歷程表

追蹤工程的每個工作里程碑：派工 → 會勘 → 查估檢視 → 送件 → 修正 → 審查 → 協議 → 定稿 → 土地鑑界 → 結案

Revision ID: add_work_records_table
Revises: add_payment_dispatch_uq
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_work_records_table'
down_revision = 'add_payment_dispatch_uq'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'taoyuan_work_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        # 關聯
        sa.Column('dispatch_order_id', sa.Integer(),
                  sa.ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'),
                  nullable=False, index=True, comment='關聯派工單'),
        sa.Column('taoyuan_project_id', sa.Integer(),
                  sa.ForeignKey('taoyuan_projects.id', ondelete='CASCADE'),
                  nullable=True, index=True, comment='關聯工程項次'),
        sa.Column('incoming_doc_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='SET NULL'),
                  nullable=True, index=True, comment='觸發的機關來文'),
        sa.Column('outgoing_doc_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='SET NULL'),
                  nullable=True, index=True, comment='對應的公司發文'),
        # 作業資訊
        sa.Column('milestone_type', sa.String(50), nullable=False, index=True,
                  comment='里程碑類型: dispatch/survey/site_inspection/submit_result/revision/review_meeting/negotiation/final_approval/boundary_survey/closed/other'),
        sa.Column('description', sa.String(500), comment='事項描述'),
        sa.Column('submission_type', sa.String(200),
                  comment='發文類別: 檢送成果(紙本+電子檔)/檢修正後成果 等'),
        # 時間
        sa.Column('record_date', sa.Date(), nullable=False, index=True,
                  comment='紀錄日期(民國轉西元)'),
        sa.Column('deadline_date', sa.Date(), nullable=True, comment='期限日期'),
        sa.Column('completed_date', sa.Date(), nullable=True, comment='完成日期'),
        # 狀態
        sa.Column('status', sa.String(30), server_default='pending', index=True,
                  comment='pending/in_progress/completed/overdue'),
        sa.Column('sort_order', sa.Integer(), server_default='0', comment='排序順序'),
        sa.Column('notes', sa.Text(), comment='備註'),
        # 系統欄位
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('taoyuan_work_records')
