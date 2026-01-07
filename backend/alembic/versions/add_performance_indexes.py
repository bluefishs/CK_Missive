"""
新增效能優化索引

建立日期: 2026-01-06
說明: 為常用查詢欄位建立複合索引，提升查詢效能

Revision ID: add_performance_indexes
Revises: enhance_attachments_001
Create Date: 2026-01-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = 'enhance_attachments_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增效能優化索引"""

    # =========================================================================
    # documents 表索引
    # =========================================================================

    # 公文類型+日期複合索引 (常用於分類查詢)
    op.create_index(
        'idx_documents_type_date',
        'documents',
        ['doc_type', sa.text('doc_date DESC')],
        if_not_exists=True
    )

    # 公文狀態索引 (常用於狀態篩選)
    op.create_index(
        'idx_documents_status',
        'documents',
        ['status'],
        if_not_exists=True
    )

    # 承攬案件外鍵索引 (關聯查詢優化)
    op.create_index(
        'idx_documents_contract_project_id',
        'documents',
        ['contract_project_id'],
        if_not_exists=True
    )

    # 發文機關外鍵索引
    op.create_index(
        'idx_documents_sender_agency_id',
        'documents',
        ['sender_agency_id'],
        if_not_exists=True
    )

    # 受文機關外鍵索引
    op.create_index(
        'idx_documents_receiver_agency_id',
        'documents',
        ['receiver_agency_id'],
        if_not_exists=True
    )

    # 收發文分類索引
    op.create_index(
        'idx_documents_category',
        'documents',
        ['category'],
        if_not_exists=True
    )

    # 文號唯一索引 (如果尚未存在)
    # 注意: doc_number 可能已有唯一約束，這裡使用 if_not_exists
    op.create_index(
        'idx_documents_doc_number',
        'documents',
        ['doc_number'],
        unique=True,
        if_not_exists=True
    )

    # =========================================================================
    # contract_projects 表索引
    # =========================================================================

    # 年度+狀態複合索引 (案件列表常用)
    op.create_index(
        'idx_projects_year_status',
        'contract_projects',
        ['year', 'status'],
        if_not_exists=True
    )

    # 專案編號索引
    op.create_index(
        'idx_projects_project_code',
        'contract_projects',
        ['project_code'],
        if_not_exists=True
    )

    # 委託機關外鍵索引
    op.create_index(
        'idx_projects_client_agency_id',
        'contract_projects',
        ['client_agency_id'],
        if_not_exists=True
    )

    # =========================================================================
    # government_agencies 表索引
    # =========================================================================

    # 機關名稱索引 (用於搜尋匹配)
    op.create_index(
        'idx_agencies_name',
        'government_agencies',
        ['agency_name'],
        if_not_exists=True
    )

    # 機關簡稱索引
    op.create_index(
        'idx_agencies_short_name',
        'government_agencies',
        ['agency_short_name'],
        if_not_exists=True
    )

    # =========================================================================
    # partner_vendors 表索引
    # =========================================================================

    # 廠商名稱索引
    op.create_index(
        'idx_vendors_name',
        'partner_vendors',
        ['vendor_name'],
        if_not_exists=True
    )

    # 廠商代碼索引
    op.create_index(
        'idx_vendors_code',
        'partner_vendors',
        ['vendor_code'],
        if_not_exists=True
    )

    # =========================================================================
    # 關聯表索引
    # =========================================================================

    # project_vendor_association 複合索引
    op.create_index(
        'idx_project_vendor_project_id',
        'project_vendor_association',
        ['project_id'],
        if_not_exists=True
    )

    op.create_index(
        'idx_project_vendor_vendor_id',
        'project_vendor_association',
        ['vendor_id'],
        if_not_exists=True
    )

    # project_user_assignments 索引
    op.create_index(
        'idx_project_user_project_id',
        'project_user_assignments',
        ['project_id'],
        if_not_exists=True
    )

    op.create_index(
        'idx_project_user_user_id',
        'project_user_assignments',
        ['user_id'],
        if_not_exists=True
    )


def downgrade() -> None:
    """移除效能優化索引"""

    # documents 表
    op.drop_index('idx_documents_type_date', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_status', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_contract_project_id', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_sender_agency_id', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_receiver_agency_id', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_category', table_name='documents', if_exists=True)
    op.drop_index('idx_documents_doc_number', table_name='documents', if_exists=True)

    # contract_projects 表
    op.drop_index('idx_projects_year_status', table_name='contract_projects', if_exists=True)
    op.drop_index('idx_projects_project_code', table_name='contract_projects', if_exists=True)
    op.drop_index('idx_projects_client_agency_id', table_name='contract_projects', if_exists=True)

    # government_agencies 表
    op.drop_index('idx_agencies_name', table_name='government_agencies', if_exists=True)
    op.drop_index('idx_agencies_short_name', table_name='government_agencies', if_exists=True)

    # partner_vendors 表
    op.drop_index('idx_vendors_name', table_name='partner_vendors', if_exists=True)
    op.drop_index('idx_vendors_code', table_name='partner_vendors', if_exists=True)

    # 關聯表
    op.drop_index('idx_project_vendor_project_id', table_name='project_vendor_association', if_exists=True)
    op.drop_index('idx_project_vendor_vendor_id', table_name='project_vendor_association', if_exists=True)
    op.drop_index('idx_project_user_project_id', table_name='project_user_assignments', if_exists=True)
    op.drop_index('idx_project_user_user_id', table_name='project_user_assignments', if_exists=True)
