"""RolePermissions ORM model — ADR-0034 動態 role permissions。"""
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB

from ._base import Base


class RolePermissions(Base):
    """每個 role 對應的 permission set（SSOT 取代前端 hardcoded USER_ROLES）。

    superuser 的 permissions = ['*']（wildcard，hasPermission 短路）。
    其他 role 列出具體 permission keys，與 site_navigation_items.permission_required 對應。
    """
    __tablename__ = "role_permissions"

    role = Column(String(20), primary_key=True)
    permissions = Column(JSONB, nullable=False, default=list)
    can_login = Column(Boolean, nullable=False, default=True)
    name_zh = Column(String(50), nullable=True)
    description_zh = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self) -> str:
        n = len(self.permissions) if self.permissions else 0
        return f"<RolePermissions role={self.role} perms={n}>"
