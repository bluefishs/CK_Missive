# -*- coding: utf-8 -*-
"""User Alias Admin Schemas — Identity Unification (ADR-0025).

R8 (v6.9 / 2026-05-09)：從 endpoints/user_alias_admin.py 遷出（SSOT 對齊）。
原內聯 BaseModel 違反 development-rules §3 — Pydantic Schema 必須統一在 schemas/。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MergeAliasRequest(BaseModel):
    canonical_id: int = Field(
        ...,
        description="canonical user id（NULL canonical_user_id 者）",
    )
    alias_id: int = Field(..., description="要被指派為 alias 的 user id")
    harmonize_role: bool = Field(
        default=False,
        description="規則 B：預設 false 不統一 role；true 才把 alias.role 改為 canonical.role",
    )
    notes: Optional[str] = Field(default=None, max_length=500)


class MergeAliasResponse(BaseModel):
    canonical_id: int
    alias_id: int
    alias_role_before: Optional[str] = None
    alias_role_after: Optional[str] = None
    canonical_role: Optional[str] = None
    harmonized: bool


class EmptyRequest(BaseModel):
    """POST-only 端點的空 body。"""
    pass
