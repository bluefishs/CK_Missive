"""
資安管理 ORM 模型

基於 OWASP Top 10 2025 標準，參照 CK_Showcase security-center 架構。

Version: 1.0.0
Created: 2026-03-27
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, JSON
from sqlalchemy.sql import func

from ._base import Base


class SecurityIssue(Base):
    """資安問題"""
    __tablename__ = "security_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(100), nullable=False, index=True)
    scan_id = Column(Integer, nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(
        String(20), nullable=False, default="medium",
        comment="critical/high/medium/low/info",
    )
    status = Column(
        String(20), nullable=False, default="open",
        comment="open/in_progress/resolved/wont_fix/false_positive",
    )
    owasp_category = Column(
        String(5), nullable=True,
        comment="A01-A10 OWASP Top 10 2025",
    )
    cwe_id = Column(String(20), nullable=True, comment="CWE 編號")
    cvss_score = Column(Float, nullable=True, comment="CVSS 分數 0-10")
    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True, comment="修復建議")
    assigned_to = Column(String(100), nullable=True)
    due_date = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    extra_data = Column(JSON, nullable=True, comment="額外資訊")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SecurityScan(Base):
    """資安掃描記錄"""
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(100), nullable=False, index=True)
    project_path = Column(String(500), nullable=True)
    scan_type = Column(
        String(20), nullable=False, default="quick",
        comment="full/quick/dependency/custom",
    )
    status = Column(
        String(20), nullable=False, default="pending",
        comment="pending/running/completed/failed/cancelled",
    )
    total_issues = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    security_score = Column(Float, nullable=True, comment="安全分數 0-100")
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    scan_config = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
