# -*- coding: utf-8 -*-
"""User Alias Admin Endpoints — Identity Unification (ADR-0025).

v5.8.0 坤哥意識體 Phase Identity。

端點：
- POST /admin/users/alias-candidates — 偵測潛在分身（full_name 重複）
- POST /admin/users/merge-alias — 合併分身（alias → canonical）
- POST /admin/users/merge-history — 合併歷史查詢

規則 B（權限隔離）：預設 harmonize_role=False，不動 alias 自身 role。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.database import get_async_db
from app.extended.models import User
from app.services.user_alias_service import (
    detect_potential_aliases,
    merge_alias,
)

router = APIRouter()


class MergeAliasRequest(BaseModel):
    canonical_id: int = Field(..., description="canonical user id（NULL canonical_user_id 者）")
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


@router.post("/alias-candidates", summary="偵測潛在分身（同名多筆 user）")
async def alias_candidates(
    _body: EmptyRequest,
    db: AsyncSession = Depends(get_async_db),
    _admin: User = Depends(require_admin()),
):
    """掃 users 表 full_name 重複者，回 cluster 供 admin UI 合併。"""
    clusters = await detect_potential_aliases(db)
    return {
        "success": True,
        "total_clusters": len(clusters),
        "clusters": clusters,
    }


@router.post(
    "/merge-alias",
    response_model=MergeAliasResponse,
    summary="合併分身（Identity Unification）",
)
async def merge_user_alias(
    request: MergeAliasRequest,
    db: AsyncSession = Depends(get_async_db),
    admin: User = Depends(require_admin()),
):
    """將 alias_id 指向 canonical_id。

    規則 B（權限隔離）：harmonize_role=False 時不動 alias 自身 role。
    alias user 仍可獨立登入，僅可見性 + 身份展開到 canonical group。
    """
    try:
        result = await merge_alias(
            db,
            canonical_id=request.canonical_id,
            alias_id=request.alias_id,
            actor_id=admin.id,
            harmonize_role=request.harmonize_role,
            notes=request.notes,
        )
        return MergeAliasResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/merge-history", summary="分身合併歷史")
async def merge_history(
    _body: EmptyRequest,
    db: AsyncSession = Depends(get_async_db),
    _admin: User = Depends(require_admin()),
):
    """回 user_merge_log 最近 100 筆。"""
    rows = (await db.execute(
        text("""
            SELECT
                id, canonical_id, alias_id, canonical_role, alias_role,
                role_harmonized, merged_by, merged_at, notes, reversed_at
            FROM user_merge_log
            ORDER BY merged_at DESC
            LIMIT 100
        """)
    )).all()
    return {
        "success": True,
        "total": len(rows),
        "items": [
            {
                "id": r[0],
                "canonical_id": r[1],
                "alias_id": r[2],
                "canonical_role": r[3],
                "alias_role": r[4],
                "role_harmonized": r[5],
                "merged_by": r[6],
                "merged_at": r[7].isoformat() if r[7] else None,
                "notes": r[8],
                "reversed_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ],
    }
