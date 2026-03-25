"""
1. 關聯表 (Association Tables)

- project_vendor_association: 專案-廠商關聯
- project_user_assignment: 專案-使用者關聯
"""
from ._base import *

# 案件與廠商關聯表
project_vendor_association = Table(
    'project_vendor_association',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('contract_projects.id'), primary_key=True),
    Column('vendor_id', Integer, ForeignKey('partner_vendors.id'), primary_key=True),
    Column('role', String(50), comment="廠商在專案中的角色 (主承包商/分包商/供應商)"),
    Column('contract_amount', Float, comment="該廠商的合約金額"),
    Column('start_date', Date, comment="合作開始日期"),
    Column('end_date', Date, comment="合作結束日期"),
    Column('status', String(20), comment="合作狀態"),
    Column('created_at', DateTime, server_default=func.now(), comment="關聯建立時間"),
    Column('updated_at', DateTime, server_default=func.now(), comment="關聯更新時間"),
    extend_existing=True
)

# 統一人員指派表 - PM 案件 + 承攬案件共用 (v2.0.0)
# 透過 case_code (建案) 或 project_id (成案) 關聯
project_user_assignment = Table(
    'project_user_assignments',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('project_id', Integer, ForeignKey('contract_projects.id'), nullable=True,
           comment="承攬案件 ID (成案後填入，未成案時為 NULL)"),
    Column('case_code', String(50), nullable=True, index=True,
           comment="建案案號 (跨模組橋樑，未成案時透過此欄關聯)"),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
           comment="系統使用者 ID (可為空，支援外部人員)"),
    Column('staff_name', String(100), nullable=True,
           comment="人員姓名 (user_id 為空時使用，或作為快取)"),
    Column('role', String(50), default='member', comment="角色"),
    Column('is_primary', Boolean, default=False, comment="是否為主要負責人"),
    Column('assignment_date', Date, comment="指派日期"),
    Column('start_date', Date, comment="開始日期"),
    Column('end_date', Date, comment="結束日期"),
    Column('status', String(50), default='active', comment="狀態: active/inactive/completed"),
    Column('notes', Text, comment="備註"),
    Column('created_at', DateTime, server_default=func.now(), comment="建立時間"),
    Column('updated_at', DateTime, server_default=func.now(), comment="更新時間"),
    extend_existing=True
)
