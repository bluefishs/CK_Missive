# -*- coding: utf-8 -*-
"""Security Admin Schemas — OWASP Top 10 issue/scan tracking.

R8 (v6.9 / 2026-05-09)：從 endpoints/security.py 遷出（SSOT 對齊）。
注意：filename 為 security_admin.py 避開既有 schemas/secure.py 命名衝突。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class IssueCreate(BaseModel):
    project_name: str = "CK_Missive"
    title: str
    description: Optional[str] = None
    severity: str = "medium"
    owasp_category: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    remediation: Optional[str] = None
    assigned_to: Optional[str] = None


class IssueUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    remediation: Optional[str] = None
    resolved_by: Optional[str] = None


class ScanCreate(BaseModel):
    project_name: str = "CK_Missive"
    scan_type: str = "quick"
    project_path: Optional[str] = None


class ListQuery(BaseModel):
    project_name: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    page: int = 1
    limit: int = 20
